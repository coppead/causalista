"""Layers 2 and 3 on larger graphs, drawn at random.

The exhaustive tests stop at five variables. Here graphs with six to eight variables
are drawn at random, with treatment and outcome in any position, and the same three
answers must agree: the fast engine, the definition, and linear models.
"""

from __future__ import annotations

from itertools import combinations

from hypothesis import given, settings
from hypothesis import strategies as st

from causalista.verifier import (
    CausalProblem,
    check_adjustment_set,
    identify,
    is_valid_adjustment_set,
    paths,
)
from tests.verifier.oracles import exists_valid_set_by_definition, linear_oracle, subsets


@st.composite
def random_problems(draw: st.DrawFn) -> CausalProblem:
    size = draw(st.integers(min_value=6, max_value=8))
    names = [f"v{i}" for i in range(size)]
    order = draw(st.permutations(names))
    density = draw(st.sampled_from([0.2, 0.35, 0.5]))
    edges = [
        (a, b)
        for a, b in combinations(order, 2)
        if draw(st.floats(min_value=0, max_value=1, allow_nan=False)) < density
    ]
    treatment, outcome = draw(st.permutations(names))[:2]
    covariates = [name for name in names if name not in (treatment, outcome)]
    hidden = draw(st.sets(st.sampled_from(covariates), max_size=3))
    return CausalProblem.from_edges(
        edges, treatment, outcome, unobserved=hidden, extra_nodes=names
    )


@settings(max_examples=250, deadline=None)
@given(random_problems())
def test_three_answers_agree_on_random_graphs(problem: CausalProblem) -> None:
    recovers_true_effect = linear_oracle(problem)
    for chosen in subsets(problem.covariates):
        fast = is_valid_adjustment_set(problem, chosen)
        assert fast == paths.satisfies_adjustment_criterion(problem, chosen), sorted(chosen)
        assert fast == recovers_true_effect(chosen), sorted(chosen)


@settings(max_examples=250, deadline=None)
@given(random_problems())
def test_identifiability_shortcut_agrees_with_trying_every_set(problem: CausalProblem) -> None:
    result = identify(problem)
    assert result.identifiable == exists_valid_set_by_definition(problem)
    if result.identifiable:
        verdict = check_adjustment_set(problem, result.adjustment_set)
        assert verdict.usable
        assert check_adjustment_set(problem, result.canonical_set).usable
    else:
        assert result.open_paths
