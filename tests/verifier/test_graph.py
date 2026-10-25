"""A malformed question must be refused, not answered."""

from __future__ import annotations

import networkx as nx
import pytest

from causalista.verifier import (
    CausalProblem,
    InvalidProblemError,
    check_adjustment_set,
    is_valid_adjustment_set,
    parse_edge,
)

CONFOUNDED = ["c -> t", "c -> y", "t -> y"]


def test_edges_can_be_text_or_pairs() -> None:
    from_text = CausalProblem.from_edges(CONFOUNDED, "t", "y")
    from_pairs = CausalProblem.from_edges([("c", "t"), ("c", "y"), ("t", "y")], "t", "y")
    assert set(from_text.graph.edges) == set(from_pairs.graph.edges)
    assert from_text.observed == {"c", "t", "y"}
    assert from_text.covariates == {"c"}


@pytest.mark.parametrize("text", ["a b", "a <- b", "a -> b -> c", "a ->", "-> b", "a->b->c"])
def test_malformed_edges_are_rejected(text: str) -> None:
    with pytest.raises(InvalidProblemError):
        parse_edge(text)


def test_edge_spacing_does_not_matter() -> None:
    assert parse_edge("a->b") == parse_edge("  a   ->   b ") == ("a", "b")


def test_cycle_is_rejected() -> None:
    with pytest.raises(InvalidProblemError, match="cycle"):
        CausalProblem.from_edges(["t -> y", "y -> m", "m -> t"], "t", "y")


def test_treatment_and_outcome_must_exist_and_differ() -> None:
    with pytest.raises(InvalidProblemError, match="not in the graph"):
        CausalProblem.from_edges(CONFOUNDED, "x", "y")
    with pytest.raises(InvalidProblemError, match="not in the graph"):
        CausalProblem.from_edges(CONFOUNDED, "t", "z")
    with pytest.raises(InvalidProblemError, match="different"):
        CausalProblem.from_edges(CONFOUNDED, "t", "t")


def test_treatment_and_outcome_must_be_in_the_table() -> None:
    with pytest.raises(InvalidProblemError, match="column of the table"):
        CausalProblem.from_edges(CONFOUNDED, "t", "y", unobserved=["t"])
    with pytest.raises(InvalidProblemError, match="column of the table"):
        CausalProblem.from_edges(CONFOUNDED, "t", "y", unobserved=["y"])


def test_unknown_unobserved_variable_is_rejected() -> None:
    with pytest.raises(InvalidProblemError, match="unobserved"):
        CausalProblem.from_edges(CONFOUNDED, "t", "y", unobserved=["typo"])


def test_duplicated_edge_is_rejected() -> None:
    with pytest.raises(InvalidProblemError, match="twice"):
        CausalProblem.from_edges(["c -> t", "c -> t", "t -> y"], "t", "y")


def test_unobserved_variables_leave_the_table() -> None:
    problem = CausalProblem.from_edges(CONFOUNDED, "t", "y", unobserved=["c"])
    assert problem.unobserved == {"c"}
    assert problem.observed_covariates == frozenset()
    assert problem.covariates == {"c"}


def test_extra_nodes_are_columns_with_no_edges() -> None:
    problem = CausalProblem.from_edges(["t -> y"], "t", "y", extra_nodes=["noise"])
    assert problem.observed_covariates == {"noise"}


def test_the_graph_cannot_be_changed_afterwards() -> None:
    original = nx.DiGraph([("c", "t"), ("c", "y"), ("t", "y")])
    problem = CausalProblem(original, "t", "y", frozenset(original.nodes))
    original.add_edge("y", "c")  # would create a cycle, but the problem owns a copy
    assert not problem.graph.has_edge("y", "c")
    with pytest.raises(nx.NetworkXError):
        problem.graph.add_edge("y", "c")


def test_unknown_variable_in_a_set_is_an_error_not_a_verdict() -> None:
    problem = CausalProblem.from_edges(CONFOUNDED, "t", "y")
    with pytest.raises(ValueError, match="not in the graph"):
        is_valid_adjustment_set(problem, ["typo"])
    with pytest.raises(ValueError, match="not in the graph"):
        check_adjustment_set(problem, ["c", "typo"])


def test_a_bare_string_is_not_a_set_of_names() -> None:
    problem = CausalProblem.from_edges(CONFOUNDED, "t", "y")
    with pytest.raises(TypeError):
        is_valid_adjustment_set(problem, "c")
