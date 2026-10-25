"""Written cases run through the harness like saved worlds, with made-up column summaries."""

from __future__ import annotations

from pathlib import Path

from causalista.harness import ADJUST_FOR_EVERYTHING, case_worlds, run
from causalista.written_cases import CASES_DIR, load_written_cases


def test_every_case_becomes_a_world_with_its_own_columns() -> None:
    file = CASES_DIR / "fase0.yaml"
    worlds = case_worlds([file])
    cases = {case.id: case for case in load_written_cases(file)}
    assert [world.id for world in worlds] == list(cases)
    for world in worlds:
        case = cases[world.id]
        assert [card.column for card in world.task.columns] == list(case.columns)
        assert all(card.summary for card in world.task.columns)
        assert world.task.narrative == case.story
        assert world.level == 3 and world.language == case.language
        assert world.problem.treatment == world.task.treatment


def test_the_summaries_are_the_same_every_time() -> None:
    first, again = case_worlds([CASES_DIR / "fase0.yaml"]), case_worlds([CASES_DIR / "fase0.yaml"])
    assert [c.summary for w in first for c in w.task.columns] == [c.summary for w in again for c in w.task.columns]


def test_a_rule_can_answer_the_cases_and_nothing_is_estimated(tmp_path: Path) -> None:
    records = run(ADJUST_FOR_EVERYTHING, case_worlds([CASES_DIR / "fase0.yaml"]), tmp_path / "r.jsonl", estimate=False)
    assert len(records) == 5
    assert all(record["estimate"] is None and record["true_effect"] is None for record in records)
    assert {record["theory"] for record in records} == {"caso escrito"}
