"""The two questions the verifier answers, with the reasons behind each answer.

1. ``check_adjustment_set``: is this set of variables a valid adjustment set?
2. ``identify``: can the effect be identified by adjustment with the columns of the
   table, and with which set?

Both answers carry an explanation (which variables are forbidden and why, which paths
stay open), because the same explanation feeds the scoring, the ideal answers used in
training, and the pictures that show a decision.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from itertools import combinations
from types import MappingProxyType

import networkx as nx

from causalista.verifier import adjustment, paths
from causalista.verifier.graph import CausalProblem


class VerifierDisagreement(RuntimeError):
    """The two engines gave different answers. This is a bug in the verifier."""


class ForbiddenReason(StrEnum):
    """Why a variable can never be part of an adjustment set."""

    TREATMENT = "treatment"
    OUTCOME = "outcome"
    MEDIATOR = "mediator"
    DESCENDANT_OF_MEDIATOR = "descendant_of_mediator"
    DESCENDANT_OF_OUTCOME = "descendant_of_outcome"


@dataclass(frozen=True)
class OpenPath:
    """A non-causal path from treatment to outcome that an adjustment set leaves open."""

    nodes: tuple[str, ...]
    text: str
    """The path with its arrows, e.g. ``oferta <- antiguidade -> cancelamento``."""
    opened_colliders: Mapping[str, frozenset[str]]
    """Colliders on the path that the set opened, with the members responsible."""

    @property
    def opened_by_adjusting(self) -> bool:
        """True when the path would be closed if nothing had been adjusted for."""
        return bool(self.opened_colliders)

    def __str__(self) -> str:
        return self.text


@dataclass(frozen=True)
class AdjustmentCheck:
    """The verdict on one proposed adjustment set."""

    adjustment_set: frozenset[str]
    valid: bool
    """Whether adjusting for the set gives the total effect, judged on the graph."""
    forbidden: Mapping[str, ForbiddenReason]
    """Members of the set that must never be adjusted for, with the reason."""
    open_paths: tuple[OpenPath, ...]
    """Non-causal paths the set leaves open."""
    not_in_table: frozenset[str]
    """Members of the set that are not columns of the table."""

    @property
    def usable(self) -> bool:
        """Valid and made only of columns of the table."""
        return self.valid and not self.not_in_table


@dataclass(frozen=True)
class Identification:
    """Whether the effect can be identified by adjustment with the table at hand."""

    identifiable: bool
    adjustment_set: frozenset[str] | None
    """A smallest valid set made of columns of the table, or None if there is none."""
    canonical_set: frozenset[str]
    """The candidate that decides the question: it is valid iff any set is."""
    open_paths: tuple[OpenPath, ...]
    """When not identifiable: what stays open even after adjusting for the canonical set."""
    missing: frozenset[str] | None
    """What the table lacks: see ``missing_columns``. Empty when identifiable."""


def missing_columns(problem: CausalProblem) -> frozenset[str] | None:
    """A smallest set of hidden variables whose presence in the table would be enough.

    Returns the empty set when the effect is already identifiable by adjustment, and
    None when no extra column can help. The latter happens only when the outcome is a
    direct cause of the treatment: the two are then linked by an edge that nothing can
    block.
    """
    hidden = sorted(problem.unobserved)
    if len(hidden) > adjustment.MAX_ENUMERATED_COVARIATES:
        raise ValueError(f"{len(hidden)} hidden variables is too many to enumerate")
    for size in range(len(hidden) + 1):
        for revealed in combinations(hidden, size):
            richer_table = CausalProblem(
                problem.graph, problem.treatment, problem.outcome, problem.observed | set(revealed)
            )
            if adjustment.is_identifiable_by_adjustment(richer_table):
                return frozenset(revealed)
    return None


def _open_paths(problem: CausalProblem, chosen: frozenset[str]) -> tuple[OpenPath, ...]:
    graph = problem.graph
    return tuple(
        OpenPath(
            nodes=path,
            text=paths.format_path(graph, path),
            opened_colliders=MappingProxyType(paths.opened_colliders(graph, path, chosen)),
        )
        for path in paths.open_noncausal_paths(problem, chosen)
    )


def _forbidden_reasons(
    problem: CausalProblem, chosen: frozenset[str]
) -> dict[str, ForbiddenReason]:
    on_causal_path = adjustment.causal_nodes(problem)
    forbidden = adjustment.forbidden_nodes(problem)
    after_outcome = nx.descendants(problem.graph, problem.outcome)
    reasons: dict[str, ForbiddenReason] = {}
    for node in sorted(chosen):
        if node == problem.treatment:
            reasons[node] = ForbiddenReason.TREATMENT
        elif node == problem.outcome:
            reasons[node] = ForbiddenReason.OUTCOME
        elif node in on_causal_path:
            reasons[node] = ForbiddenReason.MEDIATOR
        elif node in forbidden:
            reasons[node] = (
                ForbiddenReason.DESCENDANT_OF_OUTCOME
                if node in after_outcome
                else ForbiddenReason.DESCENDANT_OF_MEDIATOR
            )
    return reasons


def check_adjustment_set(problem: CausalProblem, adjustment_set: Iterable[str]) -> AdjustmentCheck:
    """Judge a proposed adjustment set and explain the verdict.

    Both engines are consulted; if they disagree, ``VerifierDisagreement`` is raised
    instead of returning an answer that might be wrong.
    """
    chosen = adjustment.as_variable_set(problem, adjustment_set)
    endpoints = {problem.treatment, problem.outcome}
    covariates_chosen = chosen - endpoints

    valid = adjustment.is_valid_adjustment_set(problem, chosen)
    by_definition = paths.satisfies_adjustment_criterion(problem, chosen)
    if valid != by_definition:
        raise VerifierDisagreement(
            f"engines disagree on {sorted(chosen)}: fast={valid}, definition={by_definition}; "
            f"edges={sorted(problem.graph.edges)}, treatment={problem.treatment!r}, "
            f"outcome={problem.outcome!r}"
        )

    return AdjustmentCheck(
        adjustment_set=chosen,
        valid=valid,
        forbidden=MappingProxyType(_forbidden_reasons(problem, chosen)),
        open_paths=_open_paths(problem, covariates_chosen),
        not_in_table=frozenset(chosen - problem.observed),
    )


def identify(problem: CausalProblem) -> Identification:
    """Decide whether the effect is identifiable by adjustment with the table at hand."""
    canonical = adjustment.canonical_adjustment_set(problem)
    identifiable = adjustment.is_valid_adjustment_set(problem, canonical)

    smallest: frozenset[str] | None = None
    if identifiable:
        candidates = problem.observed_covariates - adjustment.forbidden_nodes(problem)
        if len(candidates) <= adjustment.MAX_ENUMERATED_COVARIATES:
            smallest = adjustment.valid_adjustment_sets(problem)[0]
        else:
            smallest = canonical

    return Identification(
        identifiable=identifiable,
        adjustment_set=smallest,
        canonical_set=canonical,
        open_paths=() if identifiable else _open_paths(problem, canonical),
        missing=frozenset() if identifiable else missing_columns(problem),
    )
