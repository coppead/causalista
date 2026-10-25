"""The scoreboard page: every number on it is a count over the records it was given."""

from __future__ import annotations

import json
import re

from causalista.viz.scoreboard import OUTCOME_CODE, load_runs, render, scoreboard_payload


def _record(world: str, model: str, outcome: str, *, identifiable: bool = True, estimate=None, theory: str = "telecom") -> dict:
    return {
        "world": world, "theory": theory, "language": "pt", "level": 1, "model": model, "checkpoint": None,
        "world_identifiable": identifiable, "outcome": outcome,
        "score": {"correct": 1.0, "undue_abstention": -0.5}.get(outcome, -1.0), "reason": "", "answer": None,
        "roles_right": None, "estimate": estimate, "true_effect": -0.02, "raw": "", "seconds": 0, "output_tokens": None,
    }  # fmt: skip


RUNS = {
    "modelo": [
        _record("w1", "modelo", "correct", estimate={"effect": -0.03, "low": -0.05, "high": -0.01}),
        _record("w2", "modelo", "undue_abstention"),
        _record("w3", "modelo", "confident_error", identifiable=False, estimate={"effect": 0.04, "low": 0.02, "high": 0.06}),
        _record("w4", "modelo", "invalid", theory="educacao"),
    ],
    "ajusta tudo": [_record("w1", "ajusta tudo", "confident_error", estimate={"effect": 0.0, "low": -0.01, "high": 0.01})],
}


def test_the_payload_keeps_one_short_row_per_answer() -> None:
    payload = scoreboard_payload(RUNS, source="outputs/runs/teste")
    assert [world[0] for world in payload["worlds"]] == ["w1", "w2", "w3", "w4"]
    model = next(m for m in payload["models"] if m["label"] == "modelo")
    assert [row[1] for row in model["records"]] == [
        OUTCOME_CODE["correct"], OUTCOME_CODE["undue_abstention"], OUTCOME_CODE["confident_error"], OUTCOME_CODE["invalid"],
    ]  # fmt: skip
    # Covers the truth, and by how much it missed: only where an effect was asserted.
    assert [row[2] for row in model["records"]] == [1, None, 0, None]
    assert model["records"][0][3] == 0.01 and model["records"][1][3] is None
    assert not model["reference"]
    assert next(m for m in payload["models"] if m["label"] == "ajusta tudo")["reference"]
    assert payload["themes"]["telecom"]["unit"] == "pp" and payload["themes"]["educacao"]["unit"] == "nota"
    assert payload["scores"] == [1.0, -0.5, -1.0, -1.0]
    assert "5 respostas" in payload["colophon"]


def test_the_page_carries_exactly_the_payload(tmp_path, monkeypatch) -> None:
    folder = tmp_path / "outputs" / "runs" / "teste"
    folder.mkdir(parents=True)
    for label, records in RUNS.items():
        text = "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n"
        (folder / f"{label.replace(' ', '-')}.jsonl").write_text(text, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert load_runs(folder).keys() == RUNS.keys()
    page = render("teste")
    data = json.loads(re.search(r'<script type="application/json" id="scoreboard-data">(.*?)</script>', page, re.S).group(1))
    expected = scoreboard_payload(load_runs(folder), source="outputs/runs/teste")
    assert data == json.loads(json.dumps(expected))
    assert "os mesmos 4 mundos" in page and "__" not in page.split("<script")[0]
