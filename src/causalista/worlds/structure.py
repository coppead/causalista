"""The structure of a world: which variables are in it and what role each one plays.

A structure is drawn from a theory card, so it only ever contains what the card allows.
The graph and the answer key are derived from it; the answer key always comes from the
verifier, never from the role labels.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass, replace

import numpy as np

from causalista.verifier import CausalProblem, identify
from causalista.worlds.theory import Role, Theory

MIN_VARIABLES = 3
MAX_VARIABLES = 8
MAX_MEDIATORS = 2
MAX_COLLIDERS = 2
# How often each role is drawn, among the roles a variable allows.
ROLE_WEIGHT = {
    Role.CONFOUNDER: 0.34,
    Role.MEDIATOR: 0.16,
    Role.COLLIDER: 0.16,
    Role.OUTCOME_CAUSE: 0.14,
    Role.TREATMENT_CAUSE: 0.10,
    Role.UNRELATED: 0.10,
}
# Twins must have different answers, so two non-identifiable worlds never form a pair.
# With the two numbers below, a bit over 40% of the worlds are not identifiable.
P_HIDDEN_CONFOUNDER = 0.65
P_TABLE_TWIN = 0.6              # how often the twin differs by what is in the table
P_SECOND_HIDDEN = 0.2
P_DIRECT_EFFECT = 0.85          # otherwise the treatment has no effect of its own
P_DIRECT_EFFECT_WITH_MEDIATOR = 0.7
# A variable can also be missing from the table without harm: a cause of the outcome only,
# or of the treatment only. Without such worlds, "the story says something is not in the
# table" would always mean "not identifiable", and a model could learn the sentence
# instead of the reasoning (measured on 2026-10-05: that one rule got 100% of the verdicts).
# The number of missing variables must not give the verdict away either (with one harmless
# absence at most, "two things are missing" always meant "not identifiable"), so a world
# can miss two harmless variables, and no world misses more than MAX_HIDDEN.
MAX_HIDDEN = 2
P_HIDDEN_HARMLESS = 0.9             # a first harmless absence, when no confounder is missing
P_HARMLESS_BESIDE_CONFOUNDER = 0.5  # the same, when a confounder is already missing
P_SECOND_HARMLESS = 0.9             # a second harmless absence
P_HARMLESS_TWIN = 0.6           # how often such a world is paired with "the same variable, now a confounder"
HARMLESS = (Role.OUTCOME_CAUSE, Role.TREATMENT_CAUSE)


@dataclass(frozen=True)
class Piece:
    """One variable of a world, with the role it plays there."""

    variable: str
    role: Role
    hidden: bool = False


@dataclass(frozen=True)
class Structure:
    pieces: tuple[Piece, ...]
    direct_effect: bool
    """Whether the treatment acts on the outcome other than through mediators."""

    def edges(self, theory: Theory) -> list[tuple[str, str]]:
        treatment, outcome = theory.treatment.column, theory.outcome.column
        edges = [(treatment, outcome)] if self.direct_effect else []
        for piece in self.pieces:
            name = piece.variable
            if piece.role in (Role.CONFOUNDER, Role.TREATMENT_CAUSE):
                edges.append((name, treatment))
            if piece.role in (Role.CONFOUNDER, Role.OUTCOME_CAUSE, Role.MEDIATOR):
                edges.append((name, outcome))
            if piece.role in (Role.MEDIATOR, Role.COLLIDER):
                edges.append((treatment, name))
            if piece.role is Role.COLLIDER:
                edges.append((outcome, name))
        return edges

    def problem(self, theory: Theory) -> CausalProblem:
        """The causal graph of the world and the question asked of it."""
        return CausalProblem.from_edges(
            self.edges(theory),
            theory.treatment.column,
            theory.outcome.column,
            unobserved=[piece.variable for piece in self.pieces if piece.hidden],
            extra_nodes=[piece.variable for piece in self.pieces]
            + [theory.treatment.column, theory.outcome.column],
        )

    def count(self, role: Role) -> int:
        return sum(piece.role is role for piece in self.pieces)


def _within_limits(structure: Structure) -> bool:
    return (
        structure.count(Role.MEDIATOR) <= MAX_MEDIATORS
        and structure.count(Role.COLLIDER) <= MAX_COLLIDERS
        and sum(piece.hidden for piece in structure.pieces) <= MAX_HIDDEN
    )


def _allowed_roles(theory: Theory, name: str, taken: list[Piece]) -> list[Role]:
    """The roles a variable may still take, given the limits on mediators and colliders."""
    used = Structure(tuple(taken), True)
    return [
        role
        for role in theory.variables[name].roles
        if not (role is Role.MEDIATOR and used.count(Role.MEDIATOR) >= MAX_MEDIATORS)
        and not (role is Role.COLLIDER and used.count(Role.COLLIDER) >= MAX_COLLIDERS)
    ]


def _draw_role(allowed: list[Role], rng: np.random.Generator) -> Role:
    weights = np.array([ROLE_WEIGHT[role] for role in allowed])
    return allowed[rng.choice(len(allowed), p=weights / weights.sum())]


def sample_structure(theory: Theory, rng: np.random.Generator) -> Structure:
    """Draw a structure from what the theory card allows."""
    names = sorted(theory.variables)
    size = int(rng.integers(MIN_VARIABLES, min(MAX_VARIABLES, len(names)) + 1))
    order = [names[i] for i in rng.permutation(len(names))]
    chosen, spare = order[:size], order[size:]

    pieces: list[Piece] = []
    for name in chosen:
        allowed = _allowed_roles(theory, name, pieces)
        while not allowed and spare:
            # The only roles of this variable are already at their limit (a variable that
            # can only be a mediator, in a world with two): take another variable.
            name = spare.pop(0)
            allowed = _allowed_roles(theory, name, pieces)
        if allowed:
            pieces.append(Piece(name, _draw_role(allowed, rng)))

    if rng.random() < P_HIDDEN_CONFOUNDER:
        pieces = _hide_a_confounder(theory, pieces, rng)

    has_mediator = any(piece.role is Role.MEDIATOR for piece in pieces)
    p_direct = P_DIRECT_EFFECT_WITH_MEDIATOR if has_mediator else P_DIRECT_EFFECT
    structure = Structure(tuple(pieces), direct_effect=bool(rng.random() < p_direct))
    return _hide_something_harmless(theory, structure)


def _own_rng(structure: Structure, purpose: str) -> np.random.Generator:
    """A source of chance that depends only on the structure.

    Drawing from it leaves the main sequence of draws untouched, so the worlds that this
    rule does not change keep the structure and the numbers they had before it existed.
    """
    text = ";".join(f"{p.variable}:{p.role.value}:{int(p.hidden)}" for p in structure.pieces)
    return np.random.default_rng(zlib.crc32(f"{text}|{int(structure.direct_effect)}|{purpose}".encode()))


def _hide_something_harmless(theory: Theory, structure: Structure) -> Structure:
    """Sometimes leave out of the table one or two variables whose absence does no harm."""
    own = _own_rng(structure, "harmless")
    hidden = sum(piece.hidden for piece in structure.pieces)
    if hidden >= MAX_HIDDEN:
        return structure
    if own.random() >= (P_HIDDEN_HARMLESS if hidden == 0 else P_HARMLESS_BESIDE_CONFOUNDER):
        return structure
    structure = _hide_one_harmless(theory, structure, own)
    if sum(piece.hidden for piece in structure.pieces) < MAX_HIDDEN and own.random() < P_SECOND_HARMLESS:
        structure = _hide_one_harmless(theory, structure, own)
    return structure


def _hide_one_harmless(theory: Theory, structure: Structure, own: np.random.Generator) -> Structure:
    pieces = list(structure.pieces)

    def can_hide(name: str) -> list[Role]:
        variable = theory.variables[name]
        return [role for role in HARMLESS if variable.hideable and role in variable.roles]

    present = [i for i, piece in enumerate(pieces) if not piece.hidden and piece.role in HARMLESS and can_hide(piece.variable)]
    if present:
        index = present[int(own.integers(len(present)))]
        pieces[index] = replace(pieces[index], hidden=True)
        return replace(structure, pieces=tuple(pieces))

    # No such variable in the world: put one in the place of a variable that plays no part
    # in the adjustment (a cause of one side only, or an unrelated one).
    places = [i for i, piece in enumerate(pieces) if not piece.hidden and piece.role in (*HARMLESS, Role.UNRELATED)]
    taken = {piece.variable for piece in pieces}
    newcomers = [name for name in sorted(theory.variables) if name not in taken and can_hide(name)]
    if not places or not newcomers:
        return structure
    name = newcomers[int(own.integers(len(newcomers)))]
    roles = can_hide(name)
    pieces[places[int(own.integers(len(places)))]] = Piece(name, roles[int(own.integers(len(roles)))], hidden=True)
    return replace(structure, pieces=tuple(pieces))


def _hide_a_confounder(theory: Theory, pieces: list[Piece], rng: np.random.Generator) -> list[Piece]:
    """Make sure the world has a confounder that is left out of the table."""
    hideable = [name for name, variable in theory.variables.items() if variable.hideable]
    present = [i for i, piece in enumerate(pieces) if piece.variable in hideable]
    if not present:
        # Swap one variable for one that can be hidden.
        swapped = int(rng.integers(len(pieces)))
        pieces = list(pieces)
        pieces[swapped] = Piece(hideable[int(rng.integers(len(hideable)))], Role.CONFOUNDER)
        present = [swapped]

    order = [present[i] for i in rng.permutation(len(present))]
    how_many = 2 if len(order) > 1 and rng.random() < P_SECOND_HIDDEN else 1
    pieces = list(pieces)
    for index in order[:how_many]:
        pieces[index] = Piece(pieces[index].variable, Role.CONFOUNDER, hidden=True)
    return pieces


def answer_key(theory: Theory, structure: Structure) -> tuple[bool, frozenset[str] | None]:
    """The verdict and the smallest valid set, as the verifier sees them."""
    result = identify(structure.problem(theory))
    return result.identifiable, result.adjustment_set


def sample_twin(theory: Theory, structure: Structure, rng: np.random.Generator) -> Structure | None:
    """A structure that differs from the given one in a single fact and has another answer.

    The fact is either whether one confounder is in the table, or the role of one
    variable (for example a complaint registered before the offer instead of after).
    Returns None when no such change exists.
    """
    # A world that is identifiable although something is missing is often paired with the
    # world where the same missing variable is a confounder: one fact apart, another answer.
    harmless = [i for i, piece in enumerate(structure.pieces) if piece.hidden and piece.role in HARMLESS]
    if harmless and answer_key(theory, structure)[0]:
        own = _own_rng(structure, "twin")
        if own.random() < P_HARMLESS_TWIN:
            index = harmless[int(own.integers(len(harmless)))]
            confounder = Piece(structure.pieces[index].variable, Role.CONFOUNDER, hidden=True)
            return replace(
                structure, pieces=structure.pieces[:index] + (confounder,) + structure.pieces[index + 1 :]
            )

    table_changes: list[Structure] = []
    role_changes: list[Structure] = []
    for index, piece in enumerate(structure.pieces):
        variable = theory.variables[piece.variable]

        def with_piece(change: Piece, index: int = index) -> Structure:
            pieces = structure.pieces[:index] + (change,) + structure.pieces[index + 1 :]
            return replace(structure, pieces=pieces)

        if piece.role is Role.CONFOUNDER and variable.hideable:
            table_changes.append(with_piece(replace(piece, hidden=not piece.hidden)))
        if not piece.hidden:
            role_changes += [
                with_piece(Piece(piece.variable, role))
                for role in variable.roles
                if role is not piece.role
            ]

    def shuffled(candidates: list[Structure]) -> list[Structure]:
        return [candidates[i] for i in rng.permutation(len(candidates))]

    table_first = rng.random() < P_TABLE_TWIN
    ordered = (
        shuffled(table_changes) + shuffled(role_changes)
        if table_first
        else shuffled(role_changes) + shuffled(table_changes)
    )
    base = answer_key(theory, structure)
    for twin in ordered:
        if _within_limits(twin) and answer_key(theory, twin) != base:
            return twin
    return None
