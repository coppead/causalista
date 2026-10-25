"""The gallery page must show exactly what the verifier answered."""

from __future__ import annotations

import json
import re
import shutil

import pytest

from causalista.verifier import identify, is_valid_adjustment_set
from causalista.verifier.textbook import load_textbook_cases
from causalista.viz.gallery import case_payload, gallery_payload, render, set_key

pytestmark = pytest.mark.skipif(shutil.which("dot") is None, reason="Graphviz is not installed")

CASES = load_textbook_cases()


@pytest.mark.parametrize("case", CASES, ids=[case.id for case in CASES])
def test_every_choice_of_columns_has_the_verdict_of_the_verifier(case) -> None:
    payload = case_payload(case)
    columns = payload["columns"]
    assert columns == sorted(case.problem.observed_covariates)
    assert len(payload["verdicts"]) == 2 ** len(columns)
    for key, verdict in payload["verdicts"].items():
        chosen = [name for name in key.split(",") if name]
        assert set_key(tuple(chosen)) == key
        assert verdict["valid"] == is_valid_adjustment_set(case.problem, chosen)
        assert verdict["valid"] == (not verdict["forbidden"] and not verdict["open"])


@pytest.mark.parametrize("case", CASES, ids=[case.id for case in CASES])
def test_the_answer_and_the_drawing_are_complete(case) -> None:
    payload = case_payload(case)
    answer = identify(case.problem)
    assert payload["answer"]["identifiable"] == answer.identifiable == case.identifiable
    if answer.identifiable:
        assert payload["verdicts"][set_key(tuple(payload["answer"]["smallest"]))]["valid"]
        assert payload["answer"]["missing"] == []
    else:
        assert payload["answer"]["smallest"] is None
        assert payload["answer"]["validCount"] == 0
        assert payload["answer"]["missing"] == sorted(case.would_be_identifiable_with)

    assert {node["name"] for node in payload["nodes"]} == set(case.problem.nodes)
    assert {(edge["from"], edge["to"]) for edge in payload["edges"]} == set(case.problem.graph.edges)
    for node in payload["nodes"]:
        assert 0 < node["x"] < payload["width"] and 0 < node["y"] < payload["height"]
        assert node["hidden"] == (node["name"] in case.problem.unobserved)
    for edge in payload["edges"]:
        assert edge["d"].startswith("M ")
    # Every hand-written explanation belongs to a choice the page can show.
    assert set(payload["why"]) <= set(payload["verdicts"])


def test_cases_are_grouped_in_reading_order() -> None:
    payload = gallery_payload(CASES)
    assert payload["groups"] == [
        "Peças básicas", "Combinações", "Exemplo da especificação", "Armadilhas clássicas",
    ]  # fmt: skip
    seen = [case["group"] for case in payload["cases"]]
    assert seen == sorted(seen, key=payload["groups"].index), "groups must be contiguous"


@pytest.mark.parametrize("standalone", [True, False])
def test_the_page_carries_its_data(standalone: bool) -> None:
    page = render(CASES, standalone=standalone)
    assert "/*__CASES__*/" not in page
    assert page.count("<title>Casos do Causalista</title>") == 1
    assert page.lstrip().startswith("<!doctype html>" if standalone else "<title>")
    embedded = re.search(
        r'<script type="application/json" id="cases-data">(.*?)</script>', page, re.DOTALL
    ).group(1)
    data = json.loads(embedded.replace("<\\/", "</"))
    assert [case["id"] for case in data["cases"]] == [case.id for case in CASES]
