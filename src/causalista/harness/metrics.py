"""The numbers of the scoreboard, computed from the records of a run."""

from __future__ import annotations

from collections.abc import Iterable


def _share(flags: Iterable[bool]) -> float | None:
    flags = list(flags)
    return sum(flags) / len(flags) if flags else None


def summarise(records: list[dict]) -> dict:
    """Section 7 of the specification: score, confident errors, undue abstentions, and the effect."""
    identifiable = [r for r in records if r["world_identifiable"]]
    not_identifiable = [r for r in records if not r["world_identifiable"]]
    answered = [r for r in records if r["estimate"] is not None]
    return {
        "worlds": len(records),
        "score": sum(r["score"] for r in records) / len(records),
        "correct": _share(r["outcome"] == "correct" for r in records),
        "confident_error": _share(r["outcome"] == "confident_error" for r in records),
        "undue_abstention": _share(r["outcome"] == "undue_abstention" for r in records),
        "invalid": _share(r["outcome"] == "invalid" for r in records),
        # Where each kind of mistake can happen.
        "correct_when_identifiable": _share(r["outcome"] == "correct" for r in identifiable),
        "undue_abstention_when_identifiable": _share(r["outcome"] == "undue_abstention" for r in identifiable),
        "confident_error_when_identifiable": _share(r["outcome"] == "confident_error" for r in identifiable),
        "correct_when_not_identifiable": _share(r["outcome"] == "correct" for r in not_identifiable),
        "confident_error_when_not_identifiable": _share(
            r["outcome"] == "confident_error" for r in not_identifiable
        ),
        # The effect, in the cases where an effect was asserted.
        "answered": len(answered),
        "interval_covers_truth": _share(
            r["estimate"]["low"] <= r["true_effect"] <= r["estimate"]["high"] for r in answered
        ),
        "mean_abs_error": (
            sum(abs(r["estimate"]["effect"] - r["true_effect"]) for r in answered) / len(answered)
            if answered
            else None
        ),
        "complete": _share(bool(r["answer"] and r["answer"]["complete"]) for r in records),
        "roles_right": (
            sum(r["roles_right"] for r in records if r["roles_right"] is not None)
            / sum(r["roles_right"] is not None for r in records)
            if any(r["roles_right"] is not None for r in records)
            else None  # written cases carry no roles to check
        ),
    }


def by(records: list[dict], key: str) -> dict[str, dict]:
    """The same numbers, split by a field of the records (theory, language, level...)."""
    groups: dict[str, list[dict]] = {}
    for record in records:
        groups.setdefault(str(record[key]), []).append(record)
    return {name: summarise(group) for name, group in sorted(groups.items())}
