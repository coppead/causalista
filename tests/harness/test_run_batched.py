"""A responder that answers many worlds at once is used in batches, and the records stay the same."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from causalista.harness import ADJUST_FOR_EVERYTHING, BackendFailure, Reply, SavedWorld, run
from causalista.task import Answer, Task, make_task, render_answer
from causalista.verifier import CausalProblem

EDGES = ["renda -> oferta", "renda -> cancelou", "oferta -> multa", "multa -> cancelou", "oferta -> cancelou"]
TABLE = pd.DataFrame(
    {"renda": [1.0, 2.5, 3.0, 4.5], "oferta": [0, 1, 0, 1], "multa": [0, 1, 0, 0], "cancelou": [1, 0, 1, 0]}
)


def _world(number: int, folder: Path) -> SavedWorld:
    task = make_task(
        world_id=f"mundo-{number}",
        question="Qual o efeito da oferta sobre o cancelamento?",
        treatment="oferta",
        outcome="cancelou",
        narrative="A renda influencia a oferta e o cancelamento." + " E mais uma frase." * number,
        descriptions={name: f"coluna {name}" for name in TABLE.columns},
        table=TABLE,
    )
    return SavedWorld(
        id=task.world_id,
        folder=folder,
        theory="telecom",
        language="pt",
        level=1,
        task=task,
        problem=CausalProblem.from_edges(EDGES, "oferta", "cancelou"),
        truth={"true_effect": -0.1, "roles": {"renda": "confounder", "multa": "mediator"}},
        twin=None,
    )


@pytest.fixture
def worlds(tmp_path: Path) -> list[SavedWorld]:
    return [_world(number, tmp_path) for number in range(5)]


RIGHT = render_answer(Answer(True, frozenset({"renda"}), (), (), (), complete=False))
FILES = ("batched.jsonl", "single.jsonl")


class OneByOne:
    """A responder like the ones behind an API: one world per call."""

    label = "modelo de teste"

    def __init__(self) -> None:
        self.asked: list[str] = []

    def __call__(self, task: Task) -> Reply:
        self.asked.append(task.world_id)
        return Reply(RIGHT, 0.0, 7)


class Batched(OneByOne):
    """A responder like a model on the local GPU: it also answers several worlds together."""

    def __init__(self) -> None:
        super().__init__()
        self.batches: list[list[str]] = []

    def many(self, tasks: list[Task]) -> list[Reply]:
        self.batches.append([task.world_id for task in tasks])
        return [Reply(RIGHT, 0.0, 7) for _ in tasks]


def _lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_worlds_go_to_many_in_batches_and_never_one_by_one(worlds: list[SavedWorld], tmp_path: Path) -> None:
    responder = Batched()
    records = run(responder, worlds, tmp_path / "out.jsonl", estimate=False, batch=2)

    assert responder.batches == [["mundo-0", "mundo-1"], ["mundo-2", "mundo-3"], ["mundo-4"]]
    assert responder.asked == []
    assert [record["world"] for record in records] == [world.id for world in worlds]
    assert {record["outcome"] for record in records} == {"correct"}


def test_records_are_the_same_as_one_by_one(worlds: list[SavedWorld], tmp_path: Path) -> None:
    batched = run(Batched(), worlds, tmp_path / "batched.jsonl", estimate=False, batch=3)
    single = run(OneByOne(), worlds, tmp_path / "single.jsonl", estimate=False)

    assert batched == single
    in_files = [sorted(_lines(tmp_path / name), key=lambda record: record["world"]) for name in FILES]
    assert in_files[0] == in_files[1]


def test_a_run_that_stopped_continues_where_it_was(worlds: list[SavedWorld], tmp_path: Path) -> None:
    out = tmp_path / "out.jsonl"
    run(Batched(), worlds[:3], out, estimate=False, batch=2)

    responder = Batched()
    records = run(responder, worlds, out, estimate=False, batch=2)

    assert responder.batches == [["mundo-3", "mundo-4"]]
    assert len(_lines(out)) == 5
    assert [record["world"] for record in records] == [world.id for world in worlds]


def test_a_batch_that_fails_is_asked_again_one_world_at_a_time(worlds: list[SavedWorld], tmp_path: Path) -> None:
    class OutOfMemory(Batched):
        def many(self, tasks: list[Task]) -> list[Reply]:
            raise RuntimeError("CUDA out of memory")

    responder = OutOfMemory()
    records = run(responder, worlds, tmp_path / "out.jsonl", estimate=False, batch=4)

    assert responder.asked == [world.id for world in worlds]
    assert {record["outcome"] for record in records} == {"correct"}


def test_a_batch_with_the_wrong_number_of_replies_is_not_trusted(worlds: list[SavedWorld], tmp_path: Path) -> None:
    class Short(Batched):
        def many(self, tasks: list[Task]) -> list[Reply]:
            return super().many(tasks)[:-1]

    responder = Short()
    records = run(responder, worlds, tmp_path / "out.jsonl", estimate=False, batch=5)

    assert responder.asked == [world.id for world in worlds]
    assert len(records) == 5


def test_a_responder_that_fails_both_ways_stops_the_run_and_records_nothing(
    worlds: list[SavedWorld], tmp_path: Path
) -> None:
    class Broken(Batched):
        def many(self, tasks: list[Task]) -> list[Reply]:
            raise RuntimeError("no batch")

        def __call__(self, task: Task) -> Reply:
            raise RuntimeError("no answer")

    # A failure of the machinery is not an answer: no world gets a record.
    with pytest.raises(BackendFailure, match="no answer"):
        run(Broken(), worlds, tmp_path / "out.jsonl", estimate=False)
    assert _lines(tmp_path / "out.jsonl") == []


def test_responders_without_many_work_as_before(worlds: list[SavedWorld], tmp_path: Path) -> None:
    responder = OneByOne()
    records = run(responder, worlds, tmp_path / "out.jsonl", estimate=False, workers=1)
    assert responder.asked == [world.id for world in worlds]
    assert len(records) == 5

    everything = run(ADJUST_FOR_EVERYTHING, worlds, tmp_path / "tudo.jsonl", estimate=False)
    # adjusting for everything takes the mediator in: a confident error in this world
    assert {record["outcome"] for record in everything} == {"confident_error"}
    assert everything[0]["model"] == "ajusta tudo"
