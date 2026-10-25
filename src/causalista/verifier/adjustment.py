"""Covariate adjustment decided on the graph: the fast engine.

Implements the adjustment criterion (Shpitser, VanderWeele and Robins, 2010) in the
constructive form of van der Zander, Liśkiewicz and Textor (2014). A set Z is a valid
adjustment set for the total effect of the treatment T on the outcome Y if and only if

  (a) Z contains no forbidden node, and
  (b) Z d-separates T and Y in the proper back-door graph.

``paths.py`` decides the same question straight from the definition, by enumerating
paths. The two are kept independent on purpose, so that each one checks the other.
"""

from __future__ import annotations

from collections.abc import Iterable
from itertools import combinations

import networkx as nx

from causalista.verifier.graph import CausalProblem

# Enumerating every subset doubles with each covariate; beyond this we refuse.
MAX_ENUMERATED_COVARIATES = 16


def as_variable_set(problem: CausalProblem, variables: Iterable[str]) -> frozenset[str]:
    """Normalise a collection of variable names, rejecting names not in the graph."""
    if isinstance(variables, str):
        raise TypeError("pass a collection of variable names, not a single string")
    chosen = frozenset(variables)
    unknown = chosen - problem.nodes
    if unknown:
        raise ValueError(f"variables not in the graph: {sorted(unknown)}")
    return chosen


def causal_nodes(problem: CausalProblem) -> frozenset[str]:
    """Nodes other than the treatment on a directed path from treatment to outcome.

    The outcome itself is included whenever the treatment affects it.
    """
    downstream = nx.descendants(problem.graph, problem.treatment)
    if problem.outcome not in downstream:
        return frozenset()
    upstream_of_outcome = nx.ancestors(problem.graph, problem.outcome) | {problem.outcome}
    return frozenset(downstream & upstream_of_outcome)


def forbidden_nodes(problem: CausalProblem) -> frozenset[str]:
    """Nodes that no valid adjustment set may contain.

    These are the causal nodes and all of their descendants: mediators, the outcome,
    and anything caused by a mediator or by the outcome.
    """
    forbidden: set[str] = set()
    for node in causal_nodes(problem):
        forbidden.add(node)
        forbidden |= nx.descendants(problem.graph, node)
    return frozenset(forbidden)


def proper_backdoor_graph(problem: CausalProblem) -> nx.DiGraph:
    """The graph without the first edge of every causal path from treatment to outcome."""
    graph = nx.DiGraph(problem.graph)
    on_causal_path = causal_nodes(problem)
    first_edges = [
        (problem.treatment, child)
        for child in problem.graph.successors(problem.treatment)
        if child in on_causal_path
    ]
    graph.remove_edges_from(first_edges)
    return graph


def is_valid_adjustment_set(problem: CausalProblem, adjustment_set: Iterable[str]) -> bool:
    """Whether adjusting for the set gives the total effect of treatment on outcome.

    This is a statement about the graph only; it does not ask whether the variables
    are columns of the table. The treatment and the outcome are never part of a valid
    set.
    """
    chosen = as_variable_set(problem, adjustment_set)
    if problem.treatment in chosen or problem.outcome in chosen:
        return False
    if chosen & forbidden_nodes(problem):
        return False
    return nx.is_d_separator(
        proper_backdoor_graph(problem), {problem.treatment}, {problem.outcome}, set(chosen)
    )


def canonical_adjustment_set(problem: CausalProblem) -> frozenset[str]:
    """The observed, non-forbidden ancestors of the treatment or of the outcome.

    If any valid adjustment set can be built from the columns of the table, this one
    is valid (van der Zander, Liśkiewicz and Textor, 2014). It therefore decides
    whether the effect is identifiable by adjustment.
    """
    ancestors = nx.ancestors(problem.graph, problem.treatment) | nx.ancestors(
        problem.graph, problem.outcome
    )
    return frozenset(ancestors & problem.observed_covariates) - forbidden_nodes(problem)


def is_identifiable_by_adjustment(problem: CausalProblem) -> bool:
    """Whether some set of columns of the table is a valid adjustment set."""
    return is_valid_adjustment_set(problem, canonical_adjustment_set(problem))


def valid_adjustment_sets(problem: CausalProblem) -> list[frozenset[str]]:
    """Every valid adjustment set made of columns of the table, smallest first.

    Sets of the same size come in alphabetical order, so the result is deterministic.
    """
    candidates = sorted(problem.observed_covariates - forbidden_nodes(problem))
    if len(candidates) > MAX_ENUMERATED_COVARIATES:
        raise ValueError(
            f"{len(candidates)} candidate covariates is too many to enumerate "
            f"(limit: {MAX_ENUMERATED_COVARIATES})"
        )
    return [
        frozenset(subset)
        for size in range(len(candidates) + 1)
        for subset in combinations(candidates, size)
        if is_valid_adjustment_set(problem, subset)
    ]
