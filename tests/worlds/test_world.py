"""Whole worlds: numbers, story, table, and the separation between seen and hidden."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from causalista.worlds import Kind, Role, Theory, generate_pair, read_world, save_world
from causalista.worlds.mechanism import OVERLAP, Simulator
from causalista.worlds.narrative import build_narrative, facts_of
from causalista.worlds.structure import sample_structure, sample_twin

SEEDS = range(5)
ROLE_WORDS = ("confundidor", "mediador", "colisor", "confounder", "mediator", "collider")


@pytest.fixture(scope="module")
def worlds(theory: Theory):
    made = []
    for seed in SEEDS:
        made.extend(world for world in generate_pair(theory, seed) if world is not None)
    return made


def test_generation_is_reproducible(theory: Theory) -> None:
    first, _ = generate_pair(theory, 3)
    again, _ = generate_pair(theory, 3)
    assert first.narrative == again.narrative
    assert first.truth == again.truth
    pd.testing.assert_frame_equal(first.table, again.table)


def test_the_table_has_exactly_the_observed_columns(theory: Theory, worlds) -> None:
    for world in worlds:
        assert set(world.table.columns) == set(world.problem.observed)
        assert len(world.table) == world.parameters.rows
        assert [entry.column for entry in world.dictionary] == list(world.table.columns)
        assert not world.table.isna().any().any()
        for piece in world.structure.pieces:
            if piece.hidden:
                continue
            column = world.table[piece.variable]
            kind = theory.variables[piece.variable].kind
            if kind is Kind.BINARY:
                assert set(column.unique()) <= {0, 1}
            if kind is Kind.SCORE:
                assert column.between(0, 10).all()
            assert column.nunique() > 1, f"{piece.variable} is constant"
        assert set(world.table[world.problem.treatment].unique()) == {0, 1}


def test_rates_hit_their_targets_and_groups_overlap(theory: Theory, worlds) -> None:
    for world in worlds:
        simulator = Simulator(theory, world.structure, world.parameters)
        numbers = simulator.truth()
        rates = world.parameters.rates
        assert numbers["treated_share"] == pytest.approx(rates[world.problem.treatment], abs=0.005)
        if theory.outcome.kind is Kind.BINARY:
            assert numbers["outcome_mean"] == pytest.approx(rates[world.problem.outcome], abs=0.005)
        # In a world where the treatment was drawn by lot, everyone has the same chance.
        assert OVERLAP[0] <= numbers["propensity_low"] <= numbers["propensity_high"] <= OVERLAP[1]


def test_the_true_effect_follows_the_theory(theory: Theory, worlds) -> None:
    # In every theme each route from the treatment to the outcome acts in the direction
    # the theory says (a card with a mediator that acts the other way is refused).
    for world in worlds:
        has_route = world.structure.direct_effect or world.structure.count(Role.MEDIATOR) > 0
        if has_route:
            assert world.truth.true_effect * theory.effect_sign > 0
        else:
            # The same people are simulated with and without the treatment, so with no
            # route the difference is exactly zero, not merely small.
            assert world.truth.true_effect == 0


def test_setting_the_treatment_overrides_its_causes(theory: Theory) -> None:
    world, _ = generate_pair(theory, 5)
    simulator = Simulator(theory, world.structure, world.parameters)
    noise = simulator.draw_noise(5_000, np.random.default_rng(0))
    treated = simulator.evaluate(noise, do=1).values
    untreated = simulator.evaluate(noise, do=0).values
    assert treated[simulator.treatment].min() == 1 and untreated[simulator.treatment].max() == 0
    for piece in world.structure.pieces:
        if piece.role in (Role.CONFOUNDER, Role.TREATMENT_CAUSE, Role.OUTCOME_CAUSE, Role.UNRELATED):
            # What comes before the treatment cannot be changed by it.
            assert np.array_equal(treated[piece.variable], untreated[piece.variable])


def test_twins_share_every_number_they_have_in_common(theory: Theory) -> None:
    for seed in SEEDS:
        world, twin = generate_pair(theory, seed)
        if twin is None:
            continue
        assert world.twin_id == twin.id and twin.twin_id == world.id
        assert world.parameters.rows == twin.parameters.rows
        shared = world.parameters.weights.keys() & twin.parameters.weights.keys()
        assert shared
        for edge in shared:
            assert world.parameters.weights[edge] == twin.parameters.weights[edge]
        assert world.truth.identifiable != twin.truth.identifiable or (
            world.truth.adjustment_set != twin.truth.adjustment_set
        )


def test_the_story_tells_every_fact_and_gives_nothing_away(theory: Theory, worlds) -> None:
    for world in worlds:
        told = facts_of(theory, world.structure)
        for piece in world.structure.pieces:
            for sentence in told[piece.variable]:
                assert world.narrative.count(sentence) == 1
            hidden_fact = theory.variables[piece.variable].hidden_fact
            if hidden_fact:
                assert (hidden_fact in world.narrative) == piece.hidden
        assert world.narrative.startswith(theory.context)
        assigned = any(p.role in (Role.CONFOUNDER, Role.TREATMENT_CAUSE) for p in world.structure.pieces)
        assert world.narrative.endswith(theory.closing if assigned else theory.randomized)

        seen = " ".join([world.narrative, world.question, *(e.description for e in world.dictionary)])
        assert not any(word in seen.lower() for word in ROLE_WORDS)
        if world.truth.true_effect != 0:
            assert f"{abs(world.truth.true_effect):.3f}" not in seen


def test_the_dictionary_describes_each_column_in_its_role(theory: Theory, worlds) -> None:
    for world in worlds:
        roles = {piece.variable: piece.role for piece in world.structure.pieces}
        for entry in world.dictionary:
            if entry.column in roles:
                spec = theory.variables[entry.column].roles[roles[entry.column]]
                assert entry.description == spec.dictionary


def test_saving_keeps_the_answer_key_apart(worlds, tmp_path) -> None:
    world = worlds[0]
    home = save_world(world, tmp_path)
    visible = sorted(path.name for path in (home / "visible").iterdir())
    assert visible == ["about.json", "dictionary.json", "narrative.txt", "question.txt", "table.csv"]
    assert [path.name for path in (home / "hidden").iterdir()] == ["answer_key.json"]

    shown = "".join(path.read_text(encoding="utf-8") for path in (home / "visible").iterdir())
    for secret in ("true_effect", "adjustment_set", "identifiable", "edges", "role"):
        assert secret not in shown

    pd.testing.assert_frame_equal(pd.read_csv(home / "visible" / "table.csv"), world.table)
    key = json.loads((home / "hidden" / "answer_key.json").read_text(encoding="utf-8"))
    assert key["truth"]["true_effect"] == world.truth.true_effect
    assert sorted(map(tuple, key["edges"])) == sorted(world.problem.graph.edges)


def test_a_saved_world_can_be_read_back(theory: Theory, worlds, tmp_path) -> None:
    for world in worlds[:2]:
        again = read_world(save_world(world, tmp_path), theory)
        assert again.truth == world.truth and again.structure == world.structure
        assert again.parameters.weights == dict(world.parameters.weights)
        assert (again.narrative, again.question, again.dictionary) == (world.narrative, world.question, world.dictionary)
        assert (again.name, again.twin_id) == (world.name, world.twin_id)
        pd.testing.assert_frame_equal(again.table, world.table)


def _places(theory: Theory, structure, story: str) -> dict[str, int]:
    """The place of each fact in the story: 0 for the first fact told, 1 for the next, and so on."""
    sentences = {sentence for told in facts_of(theory, structure).values() for sentence in told}
    return {sentence: place for place, sentence in enumerate(sorted(sentences, key=story.index))}


def test_the_order_of_the_sentences_follows_no_pattern(theory: Theory) -> None:
    # A model trained on stories in which the two sentences of a variable always came
    # together, the link with the intervention first, leaned on that order: it went from
    # 100% to 65% when the same sentences were shuffled (2026-10-05).
    together = apart = intervention_first = outcome_first = 0
    for seed in range(300):
        structure = sample_structure(theory, np.random.default_rng([seed, 0]))
        story = build_narrative(theory, structure, np.random.default_rng([seed, 4]))
        place = _places(theory, structure, story)
        for piece in structure.pieces:
            if piece.role is not Role.CONFOUNDER:
                continue
            links = theory.variables[piece.variable].roles[piece.role].links
            first, second = place[links["to_treatment"].fact], place[links["to_outcome"].fact]
            together += abs(first - second) == 1
            apart += abs(first - second) > 1
            intervention_first += first < second
            outcome_first += second < first
    assert 0.2 < apart / (apart + together) < 0.8
    assert 0.35 < intervention_first / (intervention_first + outcome_first) < 0.65


def test_the_stories_of_twins_differ_only_in_the_fact_that_changed(theory: Theory) -> None:
    for seed in range(150):
        rng = np.random.default_rng([seed, 0])
        structure = sample_structure(theory, rng)
        twin = sample_twin(theory, structure, rng)
        if twin is None:
            continue
        story, other = (build_narrative(theory, s, np.random.default_rng([seed, 4])) for s in (structure, twin))
        here, there = _places(theory, structure, story), _places(theory, twin, other)
        shared = [sentence for sentence in here if sentence in there]
        assert sorted(shared, key=here.get) == sorted(shared, key=there.get), seed
