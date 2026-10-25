"""The hand-written cases: the declared answer must be the verifier's answer."""

from __future__ import annotations

import copy

import pytest
import yaml

from causalista.written_cases import (
    CASES_DIR,
    InvalidCaseError,
    WrittenCase,
    disagreements,
    load_written_cases,
    parse_case,
)

# Every file of cases: the five of phase 0 and the files that simulate a person's text.
FILES = [CASES_DIR / "fase0.yaml", *sorted((CASES_DIR / "simulados").glob("*.yaml"))]
CASES = [case for file in FILES for case in load_written_cases(file)]
RAW = {
    raw["id"]: raw
    for file in FILES
    for raw in yaml.safe_load(file.read_text(encoding="utf-8"))["cases"]
}
ROLE_WORDS = (
    "confundidor", "mediador", "colisor", "confounder", "mediator", "collider",
    "confusor", "factor de confusión", "colisionador",
)  # fmt: skip


def test_no_two_cases_share_an_id() -> None:
    ids = [case.id for case in CASES]
    assert len(ids) == len(set(ids))


@pytest.fixture(params=CASES, ids=[case.id for case in CASES])
def case(request: pytest.FixtureRequest) -> WrittenCase:
    return request.param


def test_the_declared_answer_is_the_verifiers_answer(case: WrittenCase) -> None:
    assert disagreements(case) == []


def test_the_table_and_the_graph_name_the_same_variables(case: WrittenCase) -> None:
    assert set(case.columns) == set(case.problem.observed)
    assert set(case.not_in_table) == set(case.problem.unobserved)


def test_the_story_does_not_give_the_answer_away(case: WrittenCase) -> None:
    shown = " ".join([case.story, *case.columns.values()]).lower()
    assert not any(word in shown for word in ROLE_WORDS)


def test_twins_tell_the_same_variables_and_have_another_answer(case: WrittenCase) -> None:
    # Twins differ in one fact: a role, or whether something is in the table. The table
    # may therefore differ by one column at most.
    if case.twin is None:
        pytest.skip("this case has no twin")
    twin = next(other for other in CASES if other.id == case.twin)
    assert twin.twin == case.id
    assert len(set(twin.columns) ^ set(case.columns)) <= 1
    assert (twin.identifiable, twin.adjust_for) != (case.identifiable, case.adjust_for)


def test_the_five_cases_of_phase_0_cover_the_kinds_of_decision() -> None:
    five = load_written_cases(CASES_DIR / "fase0.yaml")
    assert len(five) == 5
    assert any(not case.identifiable for case in five)
    assert any(case.identifiable and not case.adjust_for for case in five)
    assert any(case.twin for case in five)
    assert len({case.theme for case in five}) >= 4


def test_the_simulated_cases_are_many_varied_and_in_three_languages() -> None:
    simulated = [case for file in FILES[1:] for case in load_written_cases(file)]
    assert len(simulated) >= 48
    assert {case.language for case in simulated} == {"pt", "en", "es"}
    not_identifiable = sum(not case.identifiable for case in simulated) / len(simulated)
    assert 0.3 <= not_identifiable <= 0.6
    assert all(case.style and case.persona for case in simulated)
    assert len({case.style for case in simulated}) >= 8


# -- a wrong answer must be caught ---------------------------------------------


def _changed(case_id: str, **answer) -> WrittenCase:
    raw = copy.deepcopy(RAW[case_id])
    raw["answer"].update(answer)
    return parse_case(raw)


def test_a_wrong_answer_is_caught() -> None:
    # A column measured after the treatment, moved to the adjustment set.
    wrong = _changed(
        "rh_avaliacao_depois",
        adjust_for=["engajamento", "meses_casa", "avaliacao_desempenho"],
        do_not_adjust_for={},
    )
    assert disagreements(wrong)
    # A confounder left out.
    assert disagreements(_changed("banco_aumento_limite", adjust_for=[], indifferent=["meses_conta", "score_credito"]))
    # A harmful column declared harmless.
    wrong = _changed("email_campanha_sorteio", do_not_adjust_for={"visitou_site": "x"}, indifferent=["compras_12m", "falou_chat"])
    assert disagreements(wrong)
    # The wrong missing variable.
    raw = copy.deepcopy(RAW["saude_acompanhamento"])
    raw["answer"] = {"identifiable": True, "adjust_for": ["idade", "doencas_cronicas"]}
    assert disagreements(parse_case(raw))


def test_a_malformed_case_is_refused() -> None:
    raw = copy.deepcopy(RAW["saude_acompanhamento"])
    raw["answer"]["adjust_for"] = ["idade"]
    with pytest.raises(InvalidCaseError, match="adjust_for"):
        parse_case(raw)

    raw = copy.deepcopy(RAW["banco_aumento_limite"])
    del raw["columns"]["meses_conta"]
    with pytest.raises(InvalidCaseError, match="same variables"):
        parse_case(raw)

    raw = copy.deepcopy(RAW["banco_aumento_limite"])
    raw["author"] = "alguém"
    with pytest.raises(InvalidCaseError, match="author"):
        parse_case(raw)
