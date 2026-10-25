"""The reasons that come with a verdict: forbidden variables and open paths."""

from __future__ import annotations

from causalista.verifier import (
    CausalProblem,
    ForbiddenReason,
    check_adjustment_set,
    forbidden_nodes,
    identify,
    missing_columns,
    paths,
)


def test_treatment_or_outcome_in_the_set_is_invalid_and_says_why() -> None:
    problem = CausalProblem.from_edges(["c -> t", "c -> y", "t -> y"], "t", "y")

    with_outcome = check_adjustment_set(problem, ["c", "y"])
    assert not with_outcome.valid
    assert with_outcome.forbidden == {"y": ForbiddenReason.OUTCOME}
    # The rest of the set is fine: the only problem is the outcome itself.
    assert not with_outcome.open_paths

    with_treatment = check_adjustment_set(problem, ["t"])
    assert not with_treatment.valid
    assert with_treatment.forbidden == {"t": ForbiddenReason.TREATMENT}
    assert [str(path) for path in with_treatment.open_paths] == ["t <- c -> y"]


def test_outcome_is_refused_even_when_treatment_has_no_effect() -> None:
    problem = CausalProblem.from_edges(["c -> t", "c -> y"], "t", "y")
    verdict = check_adjustment_set(problem, ["c", "y"])
    assert not verdict.valid
    assert verdict.forbidden == {"y": ForbiddenReason.OUTCOME}


def test_each_kind_of_forbidden_variable_is_named() -> None:
    problem = CausalProblem.from_edges(
        ["t -> m", "m -> y", "m -> dm", "y -> dy", "t -> harmless"], "t", "y"
    )
    assert forbidden_nodes(problem) == {"m", "y", "dm", "dy"}
    verdict = check_adjustment_set(problem, ["m", "dm", "dy", "harmless"])
    assert verdict.forbidden == {
        "m": ForbiddenReason.MEDIATOR,
        "dm": ForbiddenReason.DESCENDANT_OF_MEDIATOR,
        "dy": ForbiddenReason.DESCENDANT_OF_OUTCOME,
    }
    assert check_adjustment_set(problem, ["harmless"]).valid


def test_nothing_is_forbidden_when_treatment_does_not_affect_outcome() -> None:
    problem = CausalProblem.from_edges(["c -> t", "c -> y", "y -> after"], "t", "y")
    assert forbidden_nodes(problem) == frozenset()
    assert check_adjustment_set(problem, ["c", "after"]).valid
    assert not check_adjustment_set(problem, ["after"]).valid


def test_open_backdoor_path_is_not_blamed_on_the_set() -> None:
    problem = CausalProblem.from_edges(["c -> t", "c -> y", "t -> y"], "t", "y")
    (path,) = check_adjustment_set(problem, []).open_paths
    assert path.nodes == ("t", "c", "y")
    assert str(path) == "t <- c -> y"
    assert not path.opened_by_adjusting
    assert not path.opened_colliders


def test_collider_opened_by_adjusting_for_it() -> None:
    problem = CausalProblem.from_edges(
        ["t -> k", "u -> k", "u -> y", "t -> y"], "t", "y", unobserved=["u"]
    )
    (path,) = check_adjustment_set(problem, ["k"]).open_paths
    assert str(path) == "t -> k <- u -> y"
    assert path.opened_by_adjusting
    assert path.opened_colliders == {"k": frozenset({"k"})}


def test_collider_opened_by_adjusting_for_its_descendant() -> None:
    problem = CausalProblem.from_edges(
        ["t -> k", "u -> k", "u -> y", "t -> y", "k -> report"], "t", "y", unobserved=["u"]
    )
    (path,) = check_adjustment_set(problem, ["report"]).open_paths
    assert str(path) == "t -> k <- u -> y"
    assert path.opened_colliders == {"k": frozenset({"report"})}


def test_open_paths_come_shortest_first() -> None:
    problem = CausalProblem.from_edges(
        ["c -> t", "c -> y", "u -> w", "w -> t", "u -> y", "t -> y"], "t", "y"
    )
    texts = [str(path) for path in check_adjustment_set(problem, []).open_paths]
    assert texts == ["t <- c -> y", "t <- w <- u -> y"]


def test_not_identifiable_shows_the_path_no_column_can_close() -> None:
    problem = CausalProblem.from_edges(
        ["c -> t", "c -> y", "u -> t", "u -> y", "t -> y"], "t", "y", unobserved=["u"]
    )
    result = identify(problem)
    assert not result.identifiable
    assert result.adjustment_set is None
    assert result.canonical_set == {"c"}
    assert [str(path) for path in result.open_paths] == ["t <- u -> y"]


def test_what_is_missing_names_the_fewest_hidden_variables() -> None:
    problem = CausalProblem.from_edges(
        ["u1 -> t", "u1 -> y", "u2 -> t", "u2 -> y", "u3 -> y", "t -> y"],
        "t",
        "y",
        unobserved=["u1", "u2", "u3"],
    )
    assert identify(problem).missing == {"u1", "u2"}
    assert missing_columns(problem) == {"u1", "u2"}


def test_nothing_helps_when_the_outcome_causes_the_treatment() -> None:
    problem = CausalProblem.from_edges(["y -> t", "u -> t", "u -> y"], "t", "y", unobserved=["u"])
    result = identify(problem)
    assert not result.identifiable
    assert result.missing is None
    assert [str(path) for path in result.open_paths] == ["t <- y", "t <- u -> y"]


def test_identifiable_returns_a_smallest_set_and_the_canonical_one() -> None:
    problem = CausalProblem.from_edges(
        ["c -> t", "c -> y", "p -> y", "a -> t", "t -> y"], "t", "y"
    )
    result = identify(problem)
    assert result.identifiable
    assert result.adjustment_set == {"c"}
    assert result.canonical_set == {"a", "c", "p"}


def test_path_helpers_read_the_graph_as_written() -> None:
    problem = CausalProblem.from_edges(["t -> m", "m -> y", "c -> t", "c -> y"], "t", "y")
    found = paths.paths_between(problem)
    assert sorted(found) == [("t", "c", "y"), ("t", "m", "y")]
    assert paths.is_causal(problem.graph, ("t", "m", "y"))
    assert not paths.is_causal(problem.graph, ("t", "c", "y"))
    assert paths.format_path(problem.graph, ("t", "m", "y")) == "t -> m -> y"
    assert paths.descendants(problem.graph, "c") == {"t", "m", "y"}
