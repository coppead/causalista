"""Tests of the tests: a broken verifier must be caught.

Each test below plants a plausible bug in one engine and confirms that the exhaustive
check over small graphs notices it. If one of these stops failing on the planted bug,
the safety net has a hole.
"""

from __future__ import annotations

import networkx as nx
import pytest

from causalista.verifier import VerifierDisagreement, adjustment, paths
from tests.verifier.oracles import all_dags
from tests.verifier.test_engines_agree import NAMES, _check_graph

FOUR = NAMES[:4]


def _exhaustive_check_fails() -> str | None:
    """Run the exhaustive check; return the first complaint, or None if all is well."""
    for edges in all_dags(FOUR):
        try:
            _check_graph(edges, FOUR)
        except (AssertionError, VerifierDisagreement) as complaint:
            return str(complaint)
    return None


def test_the_check_passes_when_nothing_is_broken() -> None:
    assert _exhaustive_check_fails() is None


def test_catches_forgetting_descendants_of_forbidden_nodes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adjustment, "forbidden_nodes", adjustment.causal_nodes)
    assert _exhaustive_check_fails()


def test_catches_keeping_the_causal_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adjustment, "proper_backdoor_graph", lambda problem: nx.DiGraph(problem.graph))
    assert _exhaustive_check_fails()


def _every_descendant_of_treatment(problem):
    # The classic back-door rule ("no descendant of the treatment") is stricter than
    # the adjustment criterion and wrongly refuses harmless sets.
    return frozenset(nx.descendants(problem.graph, problem.treatment))


def test_catches_refusing_every_descendant_of_treatment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adjustment, "forbidden_nodes", _every_descendant_of_treatment)
    assert _exhaustive_check_fails()


def test_linear_models_catch_a_mistake_shared_by_both_engines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Both engines agree with each other here, and both are wrong. Only the linear
    # models, which know nothing about graph criteria, can notice.
    monkeypatch.setattr(adjustment, "forbidden_nodes", _every_descendant_of_treatment)
    monkeypatch.setattr(paths, "forbidden_by_definition", _every_descendant_of_treatment)
    complaint = _exhaustive_check_fails()
    assert complaint is not None
    assert "graph vs linear models" in complaint


def test_catches_a_wrong_shortcut_for_identifiability(monkeypatch: pytest.MonkeyPatch) -> None:
    def only_causes_of_treatment(problem):
        ancestors = nx.ancestors(problem.graph, problem.treatment)
        return frozenset(ancestors & problem.observed_covariates)

    monkeypatch.setattr(adjustment, "canonical_adjustment_set", only_causes_of_treatment)
    assert _exhaustive_check_fails()


def test_catches_ignoring_descendants_of_colliders(monkeypatch: pytest.MonkeyPatch) -> None:
    def colliders_only(graph, path, adjustment_set):
        return {
            node: frozenset({node})
            for node in paths.colliders(graph, path)
            if node in adjustment_set
        }

    monkeypatch.setattr(paths, "opened_colliders", colliders_only)
    assert _exhaustive_check_fails()


def test_catches_treating_colliders_as_ordinary_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "colliders", lambda graph, path: [])
    assert _exhaustive_check_fails()
