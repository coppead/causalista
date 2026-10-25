"""Layers 2 and 3, exhaustively: every graph, every set, three independent answers.

For every directed acyclic graph with up to five variables, and every possible
adjustment set, three ways of deciding must agree:

  * the fast engine (proper back-door graph + d-separation),
  * the definition (enumerating paths),
  * linear models (does a regression with infinitely many rows recover the effect?).

Then, for every choice of which covariates are in the table, the shortcut that decides
identifiability must agree with trying every set.

Fixing the treatment and the outcome to the first two names loses nothing: the
enumeration covers every graph, so every arrangement of roles appears.
"""

from __future__ import annotations

import pytest

from causalista.verifier import (
    CausalProblem,
    check_adjustment_set,
    identify,
    is_identifiable_by_adjustment,
    is_valid_adjustment_set,
    paths,
)
from tests.verifier.oracles import Edge, all_dags, linear_oracle, subsets

NAMES = ("t", "y", "a", "b", "c")


def _describe(edges: list[Edge], chosen: frozenset[str]) -> str:
    return f"edges={sorted(edges)}, set={sorted(chosen)}"


def _smallest_reveal(
    verdicts: dict[frozenset[str], bool], hidden: frozenset[str]
) -> frozenset[str] | None:
    """Brute force: the smallest set of hidden variables that must enter the table.

    Revealing ``revealed`` leaves ``hidden - revealed`` out of the table; the effect is
    then identifiable if some valid set avoids every variable still hidden.
    """
    for revealed in subsets(hidden):
        still_hidden = hidden - revealed
        if any(valid and not chosen & still_hidden for chosen, valid in verdicts.items()):
            return revealed
    return None


def _check_graph(edges: list[Edge], names: tuple[str, ...]) -> int:
    """Check one graph completely. Returns how many verdicts were compared."""
    covariates = names[2:]
    problem = CausalProblem.from_edges(edges, "t", "y", extra_nodes=names)
    recovers_true_effect = linear_oracle(problem)

    verdicts: dict[frozenset[str], bool] = {}
    for chosen in subsets(covariates):
        fast = is_valid_adjustment_set(problem, chosen)
        by_definition = paths.satisfies_adjustment_criterion(problem, chosen)
        in_linear_models = recovers_true_effect(chosen)
        assert fast == by_definition, f"fast vs definition: {_describe(edges, chosen)}"
        assert fast == in_linear_models, f"graph vs linear models: {_describe(edges, chosen)}"
        assert check_adjustment_set(problem, chosen).valid == fast
        verdicts[chosen] = fast

    for hidden in subsets(covariates):
        partial = CausalProblem.from_edges(edges, "t", "y", unobserved=hidden, extra_nodes=names)
        usable = [chosen for chosen, valid in verdicts.items() if valid and not chosen & hidden]
        context = f"edges={sorted(edges)}, hidden={sorted(hidden)}"

        assert is_identifiable_by_adjustment(partial) == bool(usable), context
        result = identify(partial)
        assert result.identifiable == bool(usable), context
        if usable:
            assert result.adjustment_set in usable, context
            assert len(result.adjustment_set) == min(len(chosen) for chosen in usable), context
            assert result.canonical_set in usable, context
            assert not result.open_paths, context
            assert result.missing == frozenset(), context
        else:
            assert result.adjustment_set is None, context
            assert result.open_paths, context
            assert result.missing == _smallest_reveal(verdicts, hidden), context

    return len(verdicts)


@pytest.mark.parametrize("size", [2, 3, 4])
def test_every_graph_up_to_four_variables(size: int) -> None:
    names = NAMES[:size]
    graphs = 0
    for edges in all_dags(names):
        _check_graph(edges, names)
        graphs += 1
    assert graphs == {2: 3, 3: 25, 4: 543}[size]


@pytest.mark.slow
def test_every_graph_with_five_variables() -> None:
    graphs = 0
    verdicts = 0
    for edges in all_dags(NAMES):
        verdicts += _check_graph(edges, NAMES)
        graphs += 1
    assert graphs == 29281
    assert verdicts == 29281 * 8
