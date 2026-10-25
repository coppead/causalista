"""Structures drawn from a theory card, and the answer the verifier gives for them."""

from __future__ import annotations

import numpy as np
import pytest

from causalista.verifier import identify
from causalista.worlds import Role, Theory, sample_structure, sample_twin
from causalista.worlds.structure import (
    HARMLESS,
    MAX_COLLIDERS,
    MAX_HIDDEN,
    MAX_MEDIATORS,
    MAX_VARIABLES,
    MIN_VARIABLES,
    Structure,
    answer_key,
)

SEEDS = range(150)


def _draw(theory: Theory, seed: int) -> tuple[Structure, Structure | None]:
    rng = np.random.default_rng([seed, 0])
    structure = sample_structure(theory, rng)
    return structure, sample_twin(theory, structure, rng)


@pytest.mark.parametrize("seed", SEEDS)
def test_a_structure_contains_only_what_the_card_allows(theory: Theory, seed: int) -> None:
    structure, _ = _draw(theory, seed)
    names = [piece.variable for piece in structure.pieces]
    assert MIN_VARIABLES <= len(names) <= MAX_VARIABLES
    assert len(set(names)) == len(names)
    assert structure.count(Role.MEDIATOR) <= MAX_MEDIATORS
    assert structure.count(Role.COLLIDER) <= MAX_COLLIDERS
    for piece in structure.pieces:
        variable = theory.variables[piece.variable]
        assert piece.role in variable.roles
        if piece.hidden:
            assert piece.role in (Role.CONFOUNDER, *HARMLESS) and variable.hideable


@pytest.mark.parametrize("seed", SEEDS)
def test_the_verifier_agrees_with_what_the_roles_imply(theory: Theory, seed: int) -> None:
    # In this family of worlds the answer can also be read off the roles: the effect is
    # identifiable exactly when no confounder is hidden, and then the smallest valid set
    # is the set of observed confounders. A hidden variable that is not a confounder
    # changes nothing. The verifier does not know about roles, so agreement here checks
    # the generator and the verifier against each other.
    for structure in _draw(theory, seed):
        if structure is None:
            continue
        answer = identify(structure.problem(theory))
        confounders = {p.variable for p in structure.pieces if p.role is Role.CONFOUNDER}
        hidden = {p.variable for p in structure.pieces if p.hidden and p.role is Role.CONFOUNDER}
        assert answer.identifiable == (not hidden)
        if answer.identifiable:
            assert answer.adjustment_set == confounders
            assert answer.missing == frozenset()
        else:
            assert answer.adjustment_set is None
            assert answer.missing == hidden


@pytest.mark.parametrize("seed", SEEDS)
def test_a_twin_changes_one_fact_and_the_answer(theory: Theory, seed: int) -> None:
    structure, twin = _draw(theory, seed)
    if twin is None:
        pytest.skip("this structure has no twin")
    assert twin.direct_effect == structure.direct_effect
    changed = [(a, b) for a, b in zip(structure.pieces, twin.pieces, strict=True) if a != b]
    assert len(changed) == 1
    before, after = changed[0]
    assert before.variable == after.variable
    assert (before.role is after.role) != (before.hidden == after.hidden), (
        "either the role changes or what is in the table changes, never both"
    )
    assert answer_key(theory, structure) != answer_key(theory, twin)


def test_the_limits_hold_far_beyond_the_seeds_above(theory: Theory) -> None:
    # A variable that can only be a mediator (or only a collider) used to slip past the
    # limit about once in 300 worlds; a few hundred seeds did not show it.
    for seed in range(8000):
        structure = sample_structure(theory, np.random.default_rng([seed, 0]))
        assert structure.count(Role.MEDIATOR) <= MAX_MEDIATORS, seed
        assert structure.count(Role.COLLIDER) <= MAX_COLLIDERS, seed
        assert len(structure.pieces) >= MIN_VARIABLES, seed


def test_something_missing_from_the_table_does_not_give_the_verdict_away(theory: Theory) -> None:
    # "The story says something is not in the table, so the effect is not identifiable"
    # used to be right in every world. It must be wrong often enough to be useless.
    right = total = missing_but_fine = 0
    for seed in range(1500):
        for structure in _draw(theory, seed):
            if structure is None:
                continue
            says_missing = any(piece.hidden for piece in structure.pieces)
            identifiable = answer_key(theory, structure)[0]
            total += 1
            right += says_missing != identifiable
            missing_but_fine += says_missing and identifiable
    assert right / total < 0.75, "the sentence about the table still gives the verdict away"
    assert missing_but_fine / total > 0.10


def test_how_many_things_are_missing_does_not_give_the_verdict_away(theory: Theory) -> None:
    # With one harmless absence at most, "two things are missing" always meant "not
    # identifiable". Whatever the number of missing variables, both verdicts must be common.
    verdicts: dict[int, list[bool]] = {}
    for seed in range(1500):
        for structure in _draw(theory, seed):
            if structure is None:
                continue
            missing = sum(piece.hidden for piece in structure.pieces)
            assert missing <= MAX_HIDDEN, seed
            verdicts.setdefault(missing, []).append(answer_key(theory, structure)[0])
    assert all(verdicts[0]), "with nothing missing, the columns of the table are enough"
    for missing in range(1, MAX_HIDDEN + 1):
        identifiable = sum(verdicts[missing]) / len(verdicts[missing])
        assert 0.2 < identifiable < 0.8, (missing, identifiable)


def test_most_structures_have_a_twin_and_the_mix_is_balanced(theory: Theory) -> None:
    verdicts = []
    twins = 0
    for seed in range(1500):
        structure, twin = _draw(theory, seed)
        verdicts.append(answer_key(theory, structure)[0])
        if twin is not None:
            twins += 1
            verdicts.append(answer_key(theory, twin)[0])
    assert twins / 1500 > 0.9
    not_identifiable = 1 - sum(verdicts) / len(verdicts)
    assert 0.35 < not_identifiable < 0.5


def test_the_same_variable_plays_different_roles_across_worlds(theory: Theory) -> None:
    seen: dict[str, set[Role]] = {}
    for seed in range(600):
        structure, _ = _draw(theory, seed)
        for piece in structure.pieces:
            seen.setdefault(piece.variable, set()).add(piece.role)
    for name, variable in theory.variables.items():
        assert seen[name] == set(variable.roles), name


def test_drawing_is_reproducible(theory: Theory) -> None:
    assert _draw(theory, 11) == _draw(theory, 11)
    assert _draw(theory, 11) != _draw(theory, 12)
