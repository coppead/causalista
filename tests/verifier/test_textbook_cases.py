"""Layer 1: textbook graphs with known answers.

The expected answers are in ``src/causalista/verifier/textbook_cases.yaml``, written
by hand and meant to be read by a person.
"""

from __future__ import annotations

import pytest

from causalista.verifier import check_adjustment_set, identify, valid_adjustment_sets
from causalista.verifier.textbook import TextbookCase, load_textbook_cases
from tests.verifier.oracles import linear_oracle

CASES = load_textbook_cases()


def _names(variables: frozenset[str]) -> str:
    return "{" + ", ".join(sorted(variables)) + "}"


@pytest.fixture(params=CASES, ids=[case.id for case in CASES])
def case(request: pytest.FixtureRequest) -> TextbookCase:
    return request.param


def test_identifiability_matches(case: TextbookCase) -> None:
    result = identify(case.problem)
    assert result.identifiable == case.identifiable
    if case.identifiable:
        assert result.adjustment_set is not None
        assert not result.open_paths
    else:
        assert result.adjustment_set is None
        assert result.open_paths, "a non-identifiable case must show what stays open"


def test_what_the_table_lacks(case: TextbookCase) -> None:
    result = identify(case.problem)
    if case.identifiable:
        assert case.would_be_identifiable_with is None
        assert result.missing == frozenset()
    else:
        assert case.would_be_identifiable_with, "a non-identifiable case must say what is missing"
        assert result.missing == case.would_be_identifiable_with


def test_smallest_set_matches(case: TextbookCase) -> None:
    found = identify(case.problem).adjustment_set
    if not case.identifiable:
        assert case.smallest_set is None
        assert found is None
    elif case.smallest_set is None:
        # Several sets tie for smallest; the case only promises that one exists.
        assert found in valid_adjustment_sets(case.problem)
    else:
        assert found == case.smallest_set


def test_listed_valid_sets_are_valid(case: TextbookCase) -> None:
    for variables in case.valid_sets:
        verdict = check_adjustment_set(case.problem, variables)
        assert verdict.valid, f"{_names(variables)} should be valid"
        assert verdict.usable
        assert not verdict.forbidden
        assert not verdict.open_paths


def test_list_of_valid_sets_is_complete(case: TextbookCase) -> None:
    found = set(valid_adjustment_sets(case.problem))
    listed = set(case.valid_sets)
    if case.valid_sets_complete:
        assert found == listed
    else:
        assert listed <= found
    assert bool(found) == case.identifiable


def test_listed_invalid_sets_are_invalid_for_the_stated_reason(case: TextbookCase) -> None:
    for invalid in case.invalid_sets:
        verdict = check_adjustment_set(case.problem, invalid.variables)
        label = _names(invalid.variables)
        assert not verdict.valid, f"{label} should be invalid"
        assert dict(verdict.forbidden) == dict(invalid.forbidden), f"forbidden nodes of {label}"
        assert sorted(str(path) for path in verdict.open_paths) == sorted(invalid.open_paths), (
            f"open paths of {label}"
        )


def test_sets_that_would_work_if_observed(case: TextbookCase) -> None:
    for variables in case.valid_but_not_in_table:
        verdict = check_adjustment_set(case.problem, variables)
        assert verdict.valid
        assert not verdict.usable
        assert verdict.not_in_table


def test_linear_models_agree_with_every_listed_verdict(case: TextbookCase) -> None:
    recovers_true_effect = linear_oracle(case.problem)
    for variables in case.valid_sets + case.valid_but_not_in_table:
        assert recovers_true_effect(variables), f"{_names(variables)} should recover the effect"
    for invalid in case.invalid_sets:
        assert not recovers_true_effect(invalid.variables), (
            f"{_names(invalid.variables)} should give a biased effect"
        )


def test_there_are_cases_of_both_kinds() -> None:
    assert sum(case.identifiable for case in CASES) >= 5
    assert sum(not case.identifiable for case in CASES) >= 5
