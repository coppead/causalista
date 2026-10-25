"""The causal question: a graph, a treatment, an outcome, and what is in the table."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

import networkx as nx

_EDGE = re.compile(r"^\s*([\w.]+)\s*->\s*([\w.]+)\s*$")


class InvalidProblemError(ValueError):
    """The graph or the question is malformed."""


def parse_edge(text: str) -> tuple[str, str]:
    """Parse ``"cause -> effect"`` into ``("cause", "effect")``."""
    match = _EDGE.match(text)
    if match is None:
        raise InvalidProblemError(f"an edge must look like 'cause -> effect', got {text!r}")
    return match.group(1), match.group(2)


@dataclass(frozen=True, eq=False)
class CausalProblem:
    """A causal graph plus the question asked of it.

    ``graph`` holds every variable of the world, including the ones that are not in
    the table. ``observed`` is the set of variables that are columns of the table; the
    treatment and the outcome are always among them.
    """

    graph: nx.DiGraph
    treatment: str
    outcome: str
    observed: frozenset[str]

    def __post_init__(self) -> None:
        # Own a frozen copy, so that nobody can change the graph after validation.
        object.__setattr__(self, "graph", nx.freeze(nx.DiGraph(self.graph)))
        object.__setattr__(self, "observed", frozenset(self.observed))
        self._validate()

    @classmethod
    def from_edges(
        cls,
        edges: Iterable[str | tuple[str, str]],
        treatment: str,
        outcome: str,
        *,
        unobserved: Iterable[str] = (),
        extra_nodes: Iterable[str] = (),
    ) -> CausalProblem:
        """Build a problem from edges written as ``"cause -> effect"`` or as pairs.

        ``unobserved`` lists the variables that are not in the table. ``extra_nodes``
        adds variables that have no edges (columns unrelated to everything).
        """
        graph = nx.DiGraph()
        graph.add_nodes_from(extra_nodes)
        for edge in edges:
            cause, effect = parse_edge(edge) if isinstance(edge, str) else edge
            if graph.has_edge(cause, effect):
                raise InvalidProblemError(f"edge listed twice: {cause} -> {effect}")
            graph.add_edge(cause, effect)
        hidden = frozenset(unobserved)
        unknown = hidden - set(graph.nodes)
        if unknown:
            raise InvalidProblemError(f"unobserved variables not in the graph: {sorted(unknown)}")
        return cls(graph, treatment, outcome, frozenset(graph.nodes) - hidden)

    @property
    def nodes(self) -> frozenset[str]:
        return frozenset(self.graph.nodes)

    @property
    def covariates(self) -> frozenset[str]:
        """Every variable other than the treatment and the outcome."""
        return self.nodes - {self.treatment, self.outcome}

    @property
    def observed_covariates(self) -> frozenset[str]:
        """The columns of the table other than the treatment and the outcome."""
        return self.observed - {self.treatment, self.outcome}

    @property
    def unobserved(self) -> frozenset[str]:
        return self.nodes - self.observed

    def _validate(self) -> None:
        nodes = set(self.graph.nodes)
        for name in nodes:
            if not isinstance(name, str) or not name:
                raise InvalidProblemError(f"variable names must be non-empty strings, got {name!r}")
        for role, name in (("treatment", self.treatment), ("outcome", self.outcome)):
            if name not in nodes:
                raise InvalidProblemError(f"{role} {name!r} is not in the graph")
        if self.treatment == self.outcome:
            raise InvalidProblemError("treatment and outcome must be different variables")
        if not nx.is_directed_acyclic_graph(self.graph):
            cycle = " -> ".join(str(edge[0]) for edge in nx.find_cycle(self.graph))
            raise InvalidProblemError(f"the graph has a cycle through: {cycle}")
        unknown = self.observed - nodes
        if unknown:
            raise InvalidProblemError(f"observed variables not in the graph: {sorted(unknown)}")
        for role, name in (("treatment", self.treatment), ("outcome", self.outcome)):
            if name not in self.observed:
                raise InvalidProblemError(f"the {role} {name!r} must be a column of the table")
