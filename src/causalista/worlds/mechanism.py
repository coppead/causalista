"""How the numbers of a world are produced, and what the true effect is.

Every variable gets its value from its causes plus chance. The signs come from the
theory card; the sizes are drawn within the ranges below. Because the mechanism is
known, the true effect is computed directly: the same customers are simulated twice,
once with everyone treated and once with no one treated.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import networkx as nx
import numpy as np
import pandas as pd

from causalista.worlds.structure import Structure
from causalista.worlds.theory import Kind, Role, Theory

Edge = tuple[str, str]

# Sizes of the effects, on the log-odds scale (or in standard deviations, for a
# variable that is not binary). A cause that is not binary acts per standard deviation.
STRENGTH: Mapping[str, tuple[float, float]] = MappingProxyType(
    {
        "to_treatment": (0.4, 1.0),
        "to_outcome": (0.3, 0.9),
        "treatment_to_mediator": (0.6, 1.4),
        "mediator_to_outcome": (0.5, 1.2),
        "into_collider": (0.8, 1.6),
        "direct_effect": (0.3, 1.0),
    }
)
ROWS = (2_000, 5_000, 10_000, 20_000, 50_000)
CALIBRATION_ROWS = 200_000
TRUTH_ROWS = 1_000_000
# Overlap: after accounting for its causes, nobody is almost certain to be treated or not.
OVERLAP = (0.02, 0.98)
SPREAD = 0.5         # of the logarithm, for counts and continuous values
SCORE_SD = 1.8


@dataclass(frozen=True)
class Parameters:
    """Every number needed to rebuild a world exactly."""

    weights: Mapping[Edge, float]
    rates: Mapping[str, float]
    """Target rate of every binary variable (including treatment and a binary outcome)."""
    rows: int
    seed: int


def _strength_of(theory: Theory, structure: Structure, edge: Edge) -> tuple[float, float]:
    treatment, outcome = theory.treatment.column, theory.outcome.column
    cause, effect = edge
    roles = {piece.variable: piece.role for piece in structure.pieces}
    if edge == (treatment, outcome):
        return STRENGTH["direct_effect"]
    if roles.get(effect) is Role.COLLIDER:
        return STRENGTH["into_collider"]
    if roles.get(effect) is Role.MEDIATOR:
        return STRENGTH["treatment_to_mediator"]
    if roles.get(cause) is Role.MEDIATOR:
        return STRENGTH["mediator_to_outcome"]
    return STRENGTH["to_treatment"] if effect == treatment else STRENGTH["to_outcome"]


def _sign_of(theory: Theory, structure: Structure, edge: Edge) -> int:
    treatment, outcome = theory.treatment.column, theory.outcome.column
    cause, effect = edge
    if edge == (treatment, outcome):
        return theory.effect_sign
    for piece in structure.pieces:
        links = theory.variables[piece.variable].roles[piece.role].links
        if piece.variable == cause:
            return links["to_treatment" if effect == treatment else "to_outcome"].sign
        if piece.variable == effect:
            return links["from_treatment" if cause == treatment else "from_outcome"].sign
    raise KeyError(edge)


def sample_parameters(
    theory: Theory,
    structure: Structure,
    rng: np.random.Generator,
    *,
    seed: int,
    like: Parameters | None = None,
) -> Parameters:
    """Draw the sizes of a world's effects.

    With ``like``, every number that also exists in that other world is copied from
    it, so that twin worlds differ only in the fact that separates them.
    """
    weights: dict[Edge, float] = {}
    for edge in structure.edges(theory):
        if like is not None and edge in like.weights:
            weights[edge] = like.weights[edge]
        else:
            low, high = _strength_of(theory, structure, edge)
            weights[edge] = _sign_of(theory, structure, edge) * float(rng.uniform(low, high))

    def rate(name: str, low: float, high: float) -> float:
        if like is not None and name in like.rates:
            return like.rates[name]
        return float(rng.uniform(low, high))

    rates = {theory.treatment.column: rate(theory.treatment.column, *theory.treatment.range)}
    if theory.outcome.kind is Kind.BINARY:
        rates[theory.outcome.column] = rate(theory.outcome.column, *theory.outcome.range)
    for piece in structure.pieces:
        variable = theory.variables[piece.variable]
        if variable.kind is Kind.BINARY:
            typical = variable.scale["rate"]
            rates[piece.variable] = rate(piece.variable, 0.8 * typical, min(1.2 * typical, 0.9))

    rows = like.rows if like is not None else int(rng.choice(ROWS))
    return Parameters(MappingProxyType(weights), MappingProxyType(rates), rows, seed)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


@dataclass(frozen=True)
class Draw:
    """One simulated population."""

    values: dict[str, np.ndarray]
    chance: dict[str, np.ndarray]
    """The probability behind every binary variable."""
    signal: dict[str, np.ndarray]
    """What each variable passes on to its effects."""


class Simulator:
    """Produces the customers of one world, as observed or under an intervention."""

    def __init__(self, theory: Theory, structure: Structure, parameters: Parameters) -> None:
        self.theory = theory
        self.structure = structure
        self.parameters = parameters
        self.treatment = theory.treatment.column
        self.outcome = theory.outcome.column

        graph = structure.problem(theory).graph
        self._order = list(nx.lexicographical_topological_sort(graph))
        self._parents = {node: sorted(graph.predecessors(node)) for node in self._order}
        self._kind = {piece.variable: theory.variables[piece.variable].kind for piece in structure.pieces}
        self._kind[self.treatment] = Kind.BINARY
        self._kind[self.outcome] = theory.outcome.kind
        self._scale = {piece.variable: theory.variables[piece.variable].scale for piece in structure.pieces}
        self._scale[self.outcome] = {
            ("mean" if theory.outcome.kind in (Kind.COUNT, Kind.SCORE) else "median"): theory.outcome.range[0]
        }
        self._intercept: dict[str, float] = {}
        self._calibrate()

    # -- chance ------------------------------------------------------------
    def draw_noise(self, rows: int, rng: np.random.Generator) -> dict[str, np.ndarray]:
        """One draw of chance per customer and variable. Reusing it replays the same customers."""
        return {
            node: rng.uniform(size=rows) if self._kind[node] is Kind.BINARY else rng.standard_normal(rows)
            for node in self._order
        }

    # -- mechanism ---------------------------------------------------------
    def _pull(self, node: str, signal: Mapping[str, np.ndarray], rows: int) -> np.ndarray:
        """The combined push of a variable's causes."""
        total = np.zeros(rows)
        for parent in self._parents[node]:
            total += self.parameters.weights[(parent, node)] * signal[parent]
        return total

    def _value(self, node: str, latent: np.ndarray) -> np.ndarray:
        kind, scale = self._kind[node], self._scale[node]
        if kind is Kind.CONTINUOUS:
            value = scale["median"] * np.exp(SPREAD * latent)
        elif kind is Kind.COUNT:
            value = np.round(scale["mean"] * np.exp(SPREAD * latent - SPREAD**2 / 2))
        else:  # score
            value = np.round(scale["mean"] + SCORE_SD * latent, 1)
            return np.clip(value, scale.get("min", 0.0), scale.get("max", 10.0))
        return np.clip(value, scale.get("min", 0.0), scale.get("max", np.inf))

    def evaluate(self, noise: Mapping[str, np.ndarray], *, do: int | None = None) -> Draw:
        """Compute every variable from its causes and the given draw of chance.

        With ``do``, the treatment is set to that value for everyone, whatever its causes.
        """
        rows = len(noise[self.treatment])
        values: dict[str, np.ndarray] = {}
        signal: dict[str, np.ndarray] = {}
        chance: dict[str, np.ndarray] = {}
        for node in self._order:
            pull = self._pull(node, signal, rows)
            if self._kind[node] is Kind.BINARY:
                chance[node] = _sigmoid(self._intercept.get(node, 0.0) + pull)
                if node == self.treatment and do is not None:
                    values[node] = np.full(rows, float(do))
                else:
                    values[node] = (noise[node] < chance[node]).astype(float)
                signal[node] = values[node]
            else:
                latent = pull + noise[node]
                values[node] = self._value(node, latent)
                signal[node] = latent
        return Draw(values, chance, signal)

    def _calibrate(self) -> None:
        """Set each binary variable's base level so that it happens at its target rate."""
        noise = self.draw_noise(CALIBRATION_ROWS, np.random.default_rng([self.parameters.seed, 1]))
        for node in self._order:
            if self._kind[node] is not Kind.BINARY:
                continue
            # Everything upstream is already calibrated, so the pull on this node is final.
            pull = self._pull(node, self.evaluate(noise).signal, CALIBRATION_ROWS)
            target = self.parameters.rates[node]
            low, high = -20.0, 20.0
            for _ in range(60):
                middle = (low + high) / 2
                if _sigmoid(middle + pull).mean() < target:
                    low = middle
                else:
                    high = middle
            self._intercept[node] = (low + high) / 2

    # -- what the world yields ----------------------------------------------
    def table(self) -> pd.DataFrame:
        """The table an analyst would receive: only the columns that are observed."""
        rng = np.random.default_rng([self.parameters.seed, 2])
        values = self.evaluate(self.draw_noise(self.parameters.rows, rng)).values
        hidden = {piece.variable for piece in self.structure.pieces if piece.hidden}
        columns = [node for node in self._order if node not in hidden]
        columns = [columns[i] for i in rng.permutation(len(columns))]
        frame = pd.DataFrame({name: values[name] for name in columns})
        for name in columns:
            if self._kind[name] in (Kind.BINARY, Kind.COUNT):
                frame[name] = frame[name].astype(int)
            elif self._kind[name] is Kind.CONTINUOUS:
                frame[name] = frame[name].round(2)
        return frame

    def truth(self) -> dict[str, float]:
        """The true effect, and what the simple comparison is expected to show."""
        noise = self.draw_noise(TRUTH_ROWS, np.random.default_rng([self.parameters.seed, 3]))
        treated = self.evaluate(noise, do=1).values
        untreated = self.evaluate(noise, do=0).values
        as_observed = self.evaluate(noise)
        observed, chance = as_observed.values, as_observed.chance
        got_it = observed[self.treatment] == 1
        outcome = observed[self.outcome]
        return {
            "true_effect": float(treated[self.outcome].mean() - untreated[self.outcome].mean()),
            "expected_naive": float(outcome[got_it].mean() - outcome[~got_it].mean()),
            "treated_share": float(got_it.mean()),
            "outcome_mean": float(outcome.mean()),
            "propensity_low": float(np.quantile(chance[self.treatment], 0.01)),
            "propensity_high": float(np.quantile(chance[self.treatment], 0.99)),
        }


def has_overlap(truth: Mapping[str, float]) -> bool:
    return truth["propensity_low"] >= OVERLAP[0] and truth["propensity_high"] <= OVERLAP[1]
