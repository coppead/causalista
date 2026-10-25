"""Reading a model's answer: forgiving about the wrapping, strict about the content."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from causalista.task import InvalidAnswer, make_task, parse_answer, render_answer

TABLE = pd.DataFrame(
    {
        "oferta": [0, 1, 0, 1],
        "cancelou": [1, 0, 0, 0],
        "antiguidade": [3, 40, 12, 60],
        "valor_fatura": [99.9, 120.0, 80.5, 150.0],
    }
)
TASK = make_task(
    world_id="w",
    question="Qual o efeito de oferta sobre cancelou?",
    treatment="oferta",
    outcome="cancelou",
    narrative="Uma operadora fez uma oferta.",
    descriptions={
        "oferta": "Recebeu a oferta.",
        "cancelou": "Cancelou.",
        "antiguidade": "Meses como cliente.",
        "valor_fatura": "Fatura depois da oferta.",
    },
    table=TABLE,
)
GOOD = {
    "columns": [
        {"column": "antiguidade", "role": "confounder", "reason": "influencia a oferta e o cancelamento"},
        {"column": "valor_fatura", "role": "mediator", "reason": "é consequência da oferta"},
    ],
    "verdict": "identifiable",
    "adjustment_set": ["antiguidade"],
    "missing": [],
    "assumptions": ["Nada além do descrito influenciou a oferta."],
}


def _text(**changes) -> str:
    return json.dumps({**GOOD, **changes}, ensure_ascii=False)


def test_a_plain_answer_is_read() -> None:
    answer = parse_answer(_text(), TASK)
    assert answer.identifiable and answer.adjustment_set == {"antiguidade"}
    assert [role.role for role in answer.roles] == ["confounder", "mediator"]
    assert answer.complete


@pytest.mark.parametrize(
    "wrapped",
    [
        "```json\n{}\n```",
        "<think>A fatura vem depois. {\"verdict\": \"x\"}</think>\n{}",
        "Here is my answer:\n{}\nI hope it helps.",
        "The user wants JSON like {\"verdict\": \"identifiable\", \"adjustment_set\": []}.\n</think>\n\n{}",
    ],
)
def test_the_wrapping_does_not_matter(wrapped: str) -> None:
    answer = parse_answer(wrapped.replace("{}", _text()), TASK)
    assert answer.adjustment_set == {"antiguidade"}


def test_an_answer_the_runner_cannot_use_is_refused() -> None:
    with pytest.raises(InvalidAnswer, match="no JSON object"):
        parse_answer("Ajuste por antiguidade.", TASK)
    with pytest.raises(InvalidAnswer, match="verdict"):
        parse_answer(_text(verdict="talvez"), TASK)
    with pytest.raises(InvalidAnswer, match="list of column names"):
        parse_answer(_text(adjustment_set="antiguidade"), TASK)


def test_a_set_that_names_a_stranger_is_kept_for_the_score_to_judge() -> None:
    answer = parse_answer(_text(adjustment_set=["antiguidade", "renda"]), TASK)
    assert answer.adjustment_set == {"antiguidade", "renda"}


def test_abstaining_empties_the_set() -> None:
    answer = parse_answer(_text(verdict="not_identifiable", adjustment_set=["antiguidade"], missing=["a renda"]), TASK)
    assert not answer.identifiable and answer.adjustment_set == frozenset()
    assert answer.missing == ("a renda",)


def test_missing_parts_make_the_answer_incomplete_but_usable() -> None:
    answer = parse_answer(_text(columns=[GOOD["columns"][0]], assumptions=[]), TASK)
    assert answer.adjustment_set == {"antiguidade"} and not answer.complete
    answer = parse_answer(_text(columns=[{"column": "antiguidade", "role": "instrumento"}]), TASK)
    assert answer.roles == () and not answer.complete


def test_rendering_and_reading_are_inverse() -> None:
    answer = parse_answer(_text(), TASK)
    assert parse_answer(render_answer(answer), TASK) == answer
