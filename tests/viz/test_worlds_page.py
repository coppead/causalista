"""The page of generated worlds: what it adds to a case, and the rule that picks the worlds."""

from __future__ import annotations

import shutil
from itertools import pairwise

import pytest

from causalista.viz.gallery import choices, set_key
from causalista.viz.worlds_page import (
    MAX_COLUMNS,
    ROWS_SHOWN,
    _difference,
    scale_and_ticks,
    showcase_seeds,
    world_payload,
)
from causalista.worlds import generate_pair, load_theory

pytestmark = pytest.mark.skipif(shutil.which("dot") is None, reason="Graphviz is not installed")

THEORY = load_theory("telecom")


@pytest.fixture(scope="module")
def pair():
    seed = 0
    while True:
        world, twin = generate_pair(THEORY, seed)
        if twin is not None:
            return world, twin
        seed += 1


def test_the_scale_holds_every_value_and_has_round_ticks() -> None:
    values = [-0.177, -0.093, -0.119, -0.102]
    domain, ticks = scale_and_ticks(values, 100.0)
    assert domain[0] <= min(values) and max(values) <= domain[1]
    assert ticks[0] == domain[0] and ticks[-1] == domain[1]
    assert 2 <= len(ticks) <= 8
    in_points = [round(tick * 100, 6) for tick in ticks]
    step = in_points[1] - in_points[0]
    assert step in (0.5, 1, 2, 5, 10, 20, 50, 100)
    assert all(round(b - a, 6) == step for a, b in pairwise(in_points))


def test_the_scale_copes_with_a_single_value() -> None:
    domain, ticks = scale_and_ticks([0.0], 100.0)
    assert domain[0] < 0 < domain[1]
    assert len(ticks) >= 2


def test_the_twin_is_described_without_giving_the_answer_away(pair) -> None:
    world, twin = pair
    here, there = _difference(THEORY, world, twin), _difference(THEORY, twin, world)
    changed = next(a for a, b in zip(world.structure.pieces, twin.structure.pieces) if a != b)
    label = THEORY.variables[changed.variable].label
    assert label in here and label in there
    for sentence in (here, there):
        assert not any(word in sentence.lower() for word in ("confund", "mediad", "colis", "identific"))
    if changed.hidden != next(b for a, b in zip(world.structure.pieces, twin.structure.pieces) if a != b).hidden:
        assert ("não está na tabela" in here) != ("não está na tabela" in there)


def test_a_world_carries_its_dictionary_twin_and_numbers(pair) -> None:
    world, twin = pair
    columns = sorted(world.problem.observed_covariates)
    fake = {
        set_key(choice): {"effect": -0.05, "low": -0.08, "high": -0.02} for choice in choices(columns)
    }
    payload = world_payload(
        THEORY, world, twin, fake, group="Par 1", title="Mundo 1A", twin_title="Mundo 1B"
    )
    assert payload["story"] == world.narrative
    assert [entry["column"] for entry in payload["dictionary"]] == list(world.table.columns)
    assert payload["twin"]["id"] == twin.id and payload["twin"]["title"] == "Mundo 1B"

    numbers = payload["numbers"]
    assert numbers["truth"] == world.truth.true_effect
    assert numbers["estimates"].keys() == payload["verdicts"].keys()
    assert numbers["rows"] == len(world.table)
    assert numbers["unit"] == "pp" and numbers["scale"] == 100
    low, high = numbers["domain"]
    assert low <= min(-0.08, world.truth.true_effect) and max(-0.02, world.truth.true_effect) <= high
    # The answer key never leaks into what the page tells about the twin or the columns.
    shown = " ".join([payload["twin"]["difference"], *(e["description"] for e in payload["dictionary"])])
    assert "identific" not in shown.lower()


def test_the_worlds_shown_follow_a_rule_fixed_in_advance() -> None:
    seeds = showcase_seeds(THEORY, pairs=2)
    assert seeds == showcase_seeds(THEORY, pairs=2), "the same rule must give the same worlds"
    assert seeds == sorted(seeds) and len(set(seeds)) == 2
    for seed in seeds:
        for world in generate_pair(THEORY, seed):
            assert world is not None
            assert len(world.problem.observed_covariates) <= MAX_COLUMNS
            assert len(world.table) in ROWS_SHOWN
