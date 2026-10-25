"""What keeps training and test apart: the signature of a problem, and the structures of the test sets."""

from __future__ import annotations

import json
from pathlib import Path

from causalista.worlds.structure import Structure

ROOT = Path(__file__).resolve().parents[3]
FIRST_TRAINING_SEED = 100_000
"""Training worlds use seeds from here up; every test set uses lower seeds."""


def signature(theory_id: str, pieces: list[tuple[str, str, bool]], direct_effect: bool) -> str:
    """What makes two worlds the same problem: the theme, each variable with its role, and the direct effect."""
    return json.dumps([theory_id, sorted(pieces), direct_effect])


def signature_of(theory_id: str, structure: Structure) -> str:
    return signature(
        theory_id, [(p.variable, p.role.value, p.hidden) for p in structure.pieces], structure.direct_effect
    )


def kept_out(folders: list[str]) -> set[str]:
    found = set()
    for folder in folders:
        for key in (ROOT / "outputs" / "worlds" / folder).glob("*/hidden/answer_key.json"):
            saved = json.loads(key.read_text(encoding="utf-8"))
            pieces = [(p["variable"], p["role"], p["hidden"]) for p in saved["structure"]["pieces"]]
            found.add(signature(saved["theory"], pieces, saved["structure"]["direct_effect"]))
    return found
