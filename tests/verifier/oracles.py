"""Independent ways of knowing the right answer, used to check the verifier.

Nothing here imports the fast engine. The linear oracle does not even use graph
theory: it computes what a regression would return with infinitely many rows.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from itertools import chain, combinations, product

import networkx as nx
import numpy as np

from causalista.verifier import paths
from causalista.verifier.graph import CausalProblem

Edge = tuple[str, str]


def subsets(items: Iterable[str]) -> Iterator[frozenset[str]]:
    """Every subset, smallest first."""
    ordered = sorted(items)
    for subset in chain.from_iterable(combinations(ordered, n) for n in range(len(ordered) + 1)):
        yield frozenset(subset)


def all_dags(names: Sequence[str]) -> Iterator[list[Edge]]:
    """Every directed acyclic graph over the given labelled nodes, as a list of edges."""
    pairs = list(combinations(names, 2))
    for orientation in product((0, 1, 2), repeat=len(pairs)):
        edges = [
            (a, b) if direction == 1 else (b, a)
            for (a, b), direction in zip(pairs, orientation)
            if direction
        ]
        graph = nx.DiGraph(edges)
        if nx.is_directed_acyclic_graph(graph):
            yield edges


def exists_valid_set_by_definition(problem: CausalProblem) -> bool:
    """Brute force: try every set of columns of the table against the definition."""
    return any(
        paths.satisfies_adjustment_criterion(problem, candidate)
        for candidate in subsets(problem.observed_covariates)
    )


class LinearModel:
    """A linear structural model on the problem's graph, with random coefficients.

    Every variable is a weighted sum of its causes plus independent noise. In such a
    model the total effect and the regression coefficient have exact formulas, so
    there is no sampling: this is the regression "with infinitely many rows".
    """

    def __init__(self, problem: CausalProblem, rng: np.random.Generator) -> None:
        self._index = {name: i for i, name in enumerate(sorted(problem.nodes))}
        self._treatment = self._index[problem.treatment]
        self._outcome = self._index[problem.outcome]
        size = len(self._index)

        weights = np.zeros((size, size))
        for cause, effect in sorted(problem.graph.edges):
            weights[self._index[effect], self._index[cause]] = rng.choice((-1.0, 1.0)) * rng.uniform(
                0.4, 1.2
            )
        noise = rng.uniform(0.5, 1.5, size=size)

        # total[j, i] is the total effect of variable i on variable j.
        total = np.linalg.inv(np.eye(size) - weights)
        self.covariance = total @ np.diag(noise) @ total.T
        self.total_effect = float(total[self._outcome, self._treatment])

    def adjusted_coefficient(self, adjustment_set: Iterable[str]) -> float:
        """The coefficient of the treatment when regressing the outcome on it and the set."""
        columns = [self._treatment] + [self._index[name] for name in sorted(adjustment_set)]
        within = self.covariance[np.ix_(columns, columns)]
        with_outcome = self.covariance[columns, self._outcome]
        return float(np.linalg.solve(within, with_outcome)[0])

    def is_unbiased(self, adjustment_set: Iterable[str]) -> bool:
        error = abs(self.adjusted_coefficient(adjustment_set) - self.total_effect)
        return error <= 1e-8 * max(1.0, abs(self.total_effect))


def linear_oracle(problem: CausalProblem, seeds: Sequence[int] = (11, 23)) -> Callable[[Iterable[str]], bool]:
    """Say whether adjusting for a set recovers the true effect in linear models.

    Two models with different random coefficients are used. A set is declared
    unbiased only if it recovers the effect in both, which rules out coincidences.
    """
    models = [LinearModel(problem, np.random.default_rng(seed)) for seed in seeds]

    def recovers_true_effect(adjustment_set: Iterable[str]) -> bool:
        chosen = frozenset(adjustment_set)
        if problem.treatment in chosen or problem.outcome in chosen:
            return False
        return all(model.is_unbiased(chosen) for model in models)

    return recovers_true_effect
