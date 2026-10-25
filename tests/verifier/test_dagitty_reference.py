"""A second opinion from outside: the verifier against dagitty.

``reference/dagitty_reference.json`` holds random problems with the answers given by
dagitty, the reference implementation of the adjustment criterion. The file is
regenerated with ``reference/make_dagitty_reference.py`` (needs R); the comparison
below needs only the file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from causalista.verifier import (
    CausalProblem,
    identify,
    is_valid_adjustment_set,
    valid_adjustment_sets,
)

REFERENCE = json.loads(
    (Path(__file__).parent / "reference" / "dagitty_reference.json").read_text(encoding="utf-8")
)
PROBLEMS = REFERENCE["problems"]


def _problem(raw: dict) -> CausalProblem:
    return CausalProblem.from_edges(
        [tuple(edge) for edge in raw["edges"]],
        raw["treatment"],
        raw["outcome"],
        unobserved=raw["latent"],
        extra_nodes=raw["nodes"],
    )


def test_the_reference_is_not_trivial() -> None:
    verdicts = [valid for raw in PROBLEMS for valid in raw["dagitty"]["valid"]]
    identifiable = [raw["dagitty"]["identifiable"] for raw in PROBLEMS]
    assert len(PROBLEMS) >= 300
    assert len(verdicts) >= 3000
    # Both answers must be well represented, or agreement would mean little.
    assert 0.2 < sum(verdicts) / len(verdicts) < 0.8
    assert 0.2 < sum(identifiable) / len(identifiable) < 0.95


@pytest.mark.parametrize("raw", PROBLEMS, ids=[raw["id"] for raw in PROBLEMS])
def test_agrees_with_dagitty(raw: dict) -> None:
    problem = _problem(raw)
    reference = raw["dagitty"]

    for chosen, expected in zip(raw["sets"], reference["valid"], strict=True):
        assert is_valid_adjustment_set(problem, chosen) == expected, f"set {chosen}"

    # dagitty's listing of "all" sets includes sets with hidden variables; ours lists
    # only sets made of columns of the table. Compare on that common ground.
    hidden = set(raw["latent"])
    ours = sorted(sorted(chosen) for chosen in valid_adjustment_sets(problem))
    theirs = sorted(
        sorted(chosen) for chosen in reference["all_sets"] if not set(chosen) & hidden
    )
    assert ours == theirs

    assert identify(problem).identifiable == reference["identifiable"]
