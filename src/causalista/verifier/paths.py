"""Covariate adjustment decided by enumerating paths: the definitional engine.

This module states the adjustment criterion the way the textbook does:

  (a) the set contains no descendant of a node that lies on a causal path from the
      treatment to the outcome, and
  (b) the set blocks every path from the treatment to the outcome that is not causal.

It is slower than ``adjustment.py`` and deliberately shares no code with it: no
d-separation routine, no ancestor or descendant helper. It exists for two reasons: to
check the fast engine, and to say *which* path is open when a set is not valid.
"""

from __future__ import annotations

from collections.abc import Iterable
from itertools import pairwise

import networkx as nx

from causalista.verifier.graph import CausalProblem

Path = tuple[str, ...]


def paths_between(problem: CausalProblem) -> list[Path]:
    """Every path from the treatment to the outcome, ignoring the direction of edges.

    A path visits each variable at most once and ends when it reaches the outcome.
    """
    graph = problem.graph
    found: list[Path] = []

    def extend(path: list[str]) -> None:
        last = path[-1]
        if last == problem.outcome:
            found.append(tuple(path))
            return
        neighbours = sorted(set(graph.predecessors(last)) | set(graph.successors(last)))
        for neighbour in neighbours:
            if neighbour not in path:
                path.append(neighbour)
                extend(path)
                path.pop()

    extend([problem.treatment])
    return found


def is_causal(graph: nx.DiGraph, path: Path) -> bool:
    """Whether every edge of the path points away from the treatment."""
    return all(graph.has_edge(a, b) for a, b in pairwise(path))


def descendants(graph: nx.DiGraph, node: str) -> frozenset[str]:
    """Every variable reachable from ``node`` by following edges forward."""
    seen: set[str] = set()
    stack = [node]
    while stack:
        for child in graph.successors(stack.pop()):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return frozenset(seen)


def colliders(graph: nx.DiGraph, path: Path) -> list[str]:
    """Interior variables of the path where two arrowheads meet (``-> v <-``)."""
    return [
        node
        for before, node, after in zip(path, path[1:], path[2:])
        if graph.has_edge(before, node) and graph.has_edge(after, node)
    ]


def opened_colliders(
    graph: nx.DiGraph, path: Path, adjustment_set: frozenset[str]
) -> dict[str, frozenset[str]]:
    """Colliders of the path opened by the set, each with the members that open it.

    A collider is opened by adjusting for it or for any of its descendants.
    """
    opened: dict[str, frozenset[str]] = {}
    for node in colliders(graph, path):
        because_of = ({node} | descendants(graph, node)) & adjustment_set
        if because_of:
            opened[node] = frozenset(because_of)
    return opened


def is_blocked(graph: nx.DiGraph, path: Path, adjustment_set: frozenset[str]) -> bool:
    """Whether the set blocks the path.

    A path is blocked when it has a non-collider that is in the set, or a collider
    such that neither it nor any of its descendants is in the set.
    """
    collider_nodes = set(colliders(graph, path))
    opened = opened_colliders(graph, path, adjustment_set)
    for node in path[1:-1]:
        if node in collider_nodes:
            if node not in opened:
                return True
        elif node in adjustment_set:
            return True
    return False


def forbidden_by_definition(problem: CausalProblem) -> frozenset[str]:
    """Nodes on a causal path (other than the treatment) and their descendants."""
    forbidden: set[str] = set()
    for path in paths_between(problem):
        if is_causal(problem.graph, path):
            for node in path[1:]:
                forbidden.add(node)
                forbidden |= descendants(problem.graph, node)
    return frozenset(forbidden)


def open_noncausal_paths(problem: CausalProblem, adjustment_set: Iterable[str]) -> list[Path]:
    """The non-causal paths that the set leaves open, shortest first."""
    chosen = frozenset(adjustment_set)
    open_paths = [
        path
        for path in paths_between(problem)
        if not is_causal(problem.graph, path) and not is_blocked(problem.graph, path, chosen)
    ]
    return sorted(open_paths, key=lambda path: (len(path), path))


def satisfies_adjustment_criterion(problem: CausalProblem, adjustment_set: Iterable[str]) -> bool:
    """The adjustment criterion, checked straight from its definition."""
    chosen = frozenset(adjustment_set)
    if problem.treatment in chosen or problem.outcome in chosen:
        return False
    if chosen & forbidden_by_definition(problem):
        return False
    return not open_noncausal_paths(problem, chosen)


def format_path(graph: nx.DiGraph, path: Path) -> str:
    """Write a path with its arrows, e.g. ``oferta <- antiguidade -> cancelamento``."""
    pieces = [path[0]]
    for a, b in pairwise(path):
        pieces.append("->" if graph.has_edge(a, b) else "<-")
        pieces.append(b)
    return " ".join(pieces)
