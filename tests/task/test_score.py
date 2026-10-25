"""The score table of section 5, row by row, and the reasons that come with it."""

from __future__ import annotations

import pytest

from causalista.task import Answer, Outcome, judge
from causalista.verifier import CausalProblem

IDENTIFIABLE = CausalProblem.from_edges(
    ["renda -> oferta", "renda -> cancelou", "oferta -> multa", "multa -> cancelou", "oferta -> cancelou"],
    "oferta",
    "cancelou",
)
NOT_IDENTIFIABLE = CausalProblem.from_edges(
    ["renda -> oferta", "renda -> cancelou", "antiguidade -> cancelou", "oferta -> cancelou"],
    "oferta",
    "cancelou",
    unobserved=["renda"],
)


def _answer(identifiable: bool, *columns: str) -> Answer:
    return Answer(identifiable, frozenset(columns), (), (), (), complete=False)


@pytest.mark.parametrize(
    ("problem", "answer", "outcome", "score"),
    [
        (IDENTIFIABLE, _answer(True, "renda"), Outcome.CORRECT, 1.0),
        (IDENTIFIABLE, _answer(True), Outcome.CONFIDENT_ERROR, -1.0),
        (IDENTIFIABLE, _answer(False), Outcome.UNDUE_ABSTENTION, -0.5),
        (NOT_IDENTIFIABLE, _answer(False), Outcome.CORRECT, 1.0),
        (NOT_IDENTIFIABLE, _answer(True, "antiguidade"), Outcome.CONFIDENT_ERROR, -1.0),
        (NOT_IDENTIFIABLE, _answer(True), Outcome.CONFIDENT_ERROR, -1.0),
    ],
)
def test_the_score_table(problem: CausalProblem, answer: Answer, outcome: Outcome, score: float) -> None:
    judgement = judge(problem, answer)
    assert (judgement.outcome, judgement.score) == (outcome, score)
    assert judgement.world_identifiable == (problem is IDENTIFIABLE)


def test_the_reason_names_what_went_wrong() -> None:
    assert "oferta <- renda -> cancelou" in judge(IDENTIFIABLE, _answer(True)).reason
    with_mediator = judge(IDENTIFIABLE, _answer(True, "renda", "multa"))
    assert with_mediator.outcome is Outcome.CONFIDENT_ERROR
    assert "multa é consequência da intervenção" in with_mediator.reason
    assert "renda" in judge(IDENTIFIABLE, _answer(False)).reason
    assert "falta na tabela: renda" in judge(NOT_IDENTIFIABLE, _answer(True)).reason


def test_adjusting_for_the_outcome_is_a_confident_error() -> None:
    assert judge(IDENTIFIABLE, _answer(True, "renda", "cancelou")).outcome is Outcome.CONFIDENT_ERROR


def test_asserting_an_effect_with_something_that_is_not_a_column_is_a_confident_error() -> None:
    # A hidden variable named in the set, or a name the table does not have at all.
    hidden = judge(NOT_IDENTIFIABLE, _answer(True, "renda"))
    assert hidden.outcome is Outcome.CONFIDENT_ERROR and "falta na tabela: renda" in hidden.reason
    stranger = judge(IDENTIFIABLE, _answer(True, "renda", "satisfação"))
    assert stranger.outcome is Outcome.CONFIDENT_ERROR and stranger.check is None
    assert "não é coluna da tabela: satisfação" in stranger.reason
    assert judge(NOT_IDENTIFIABLE, _answer(True, "satisfação")).outcome is Outcome.CONFIDENT_ERROR


def test_an_unusable_text_is_scored_apart() -> None:
    judgement = judge(IDENTIFIABLE, None, invalid="no JSON object in the answer")
    assert judgement.outcome is Outcome.INVALID and judgement.score == -1.0
    assert "no JSON object" in judgement.reason
