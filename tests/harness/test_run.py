"""The harness: worlds read back from disk, answers recorded, and the numbers added up."""

from __future__ import annotations

import json

import pytest

from causalista.harness import (
    ADJUST_FOR_EVERYTHING,
    ADJUST_FOR_NOTHING,
    BackendFailure,
    Reply,
    by,
    load_worlds,
    run,
    summarise,
)
from causalista.task import ideal_answer, render_answer
from causalista.worlds import generate_pair, load_theory, save_world

THEORY = load_theory("telecom")


@pytest.fixture(scope="module")
def saved(tmp_path_factory):
    folder = tmp_path_factory.mktemp("worlds")
    worlds = [world for seed in range(3) for world in generate_pair(THEORY, seed) if world is not None]
    for world in worlds:
        save_world(world, folder)
    return folder, {world.name: world for world in worlds}


class AnswerKey:
    """A responder that always gives the ideal answer."""

    label = "gabarito"

    def __init__(self, worlds):
        self.worlds = worlds

    def __call__(self, task):
        return Reply(render_answer(ideal_answer(self.worlds[task.world_id], THEORY)), 0.0)


def test_a_saved_world_comes_back_as_it_was(saved) -> None:
    folder, worlds = saved
    loaded = load_worlds(folder)
    assert [world.id for world in loaded] == sorted(worlds)
    for world in loaded:
        original = worlds[world.id]
        assert world.task.narrative == original.narrative
        assert (world.task.treatment, world.task.outcome) == (original.problem.treatment, original.problem.outcome)
        assert set(world.problem.observed) == set(original.problem.observed)
        assert set(world.problem.unobserved) == set(original.problem.unobserved)
        assert world.truth["identifiable"] == original.truth.identifiable
        assert (world.language, world.level, world.theory) == ("pt", 1, "telecom")


def test_the_answer_key_scores_one_everywhere(saved, tmp_path) -> None:
    folder, worlds = saved
    records = run(AnswerKey(worlds), load_worlds(folder), tmp_path / "gabarito.jsonl", workers=2)
    numbers = summarise(records)
    assert numbers["score"] == 1.0 and numbers["correct"] == 1.0 and numbers["roles_right"] == 1.0
    assert all(record["answer"]["complete"] for record in records)
    # An effect is computed only where the answer asserted one.
    assert numbers["answered"] == sum(record["world_identifiable"] for record in records)
    for record in records:
        if record["estimate"]:
            assert record["estimate"]["low"] <= record["estimate"]["effect"] <= record["estimate"]["high"]


def test_naive_rules_are_confident_and_often_wrong(saved, tmp_path) -> None:
    folder, _ = saved
    worlds = load_worlds(folder)
    for rule in (ADJUST_FOR_EVERYTHING, ADJUST_FOR_NOTHING):
        records = run(rule, worlds, tmp_path / f"{rule.everything}.jsonl", estimate=False)
        numbers = summarise(records)
        assert numbers["undue_abstention"] == 0 and numbers["invalid"] == 0
        assert numbers["correct_when_not_identifiable"] in (0, None)
        assert all(record["roles_right"] is None for record in records)
        assert all("falta na tabela" in r["reason"] for r in records if not r["world_identifiable"])


def test_a_run_can_be_resumed_and_a_failure_of_the_machinery_is_never_an_answer(saved, tmp_path) -> None:
    folder, worlds = saved
    loaded = load_worlds(folder)
    out = tmp_path / "resumed.jsonl"
    run(AnswerKey(worlds), loaded[:2], out, estimate=False)

    calls = []

    class Flaky(AnswerKey):
        def __call__(self, task):
            calls.append(task.world_id)
            if len(calls) == 1:
                raise RuntimeError("the server went away")
            return super().__call__(task)

    # The world whose call failed gets no record; the others are answered.
    records = run(Flaky(worlds), loaded, out, workers=1, estimate=False)
    assert sorted(calls) == sorted(world.id for world in loaded[2:])
    assert len(records) == len(loaded) - 1 == len(out.read_text(encoding="utf-8").splitlines())
    assert all(record["outcome"] == "correct" for record in records)

    # The next run asks only for the world that is missing.
    records = run(AnswerKey(worlds), loaded, out, estimate=False)
    assert len(records) == len(loaded) and all(record["outcome"] == "correct" for record in records)


def test_a_backend_that_keeps_failing_stops_the_run(saved, tmp_path) -> None:
    folder, worlds = saved
    out = tmp_path / "broken.jsonl"

    class Broken(AnswerKey):
        def __call__(self, task):
            raise MemoryError("CUDA error: out of memory")

    with pytest.raises(BackendFailure, match="out of memory"):
        run(Broken(worlds), load_worlds(folder), out, workers=1, estimate=False)
    assert not out.exists() or out.read_text(encoding="utf-8") == ""


def test_the_numbers_can_be_split(saved, tmp_path) -> None:
    folder, worlds = saved
    records = run(AnswerKey(worlds), load_worlds(folder), tmp_path / "split.jsonl", estimate=False)
    assert set(by(records, "theory")) == {"telecom"}
    assert sum(group["worlds"] for group in by(records, "world_identifiable").values()) == len(records)
    assert json.loads(json.dumps(summarise(records)))  # plain numbers, ready to be written down
