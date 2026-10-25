"""Textbook cases: small graphs with known answers, written to be read by a person.

The cases live in ``textbook_cases.yaml``. They are the first layer of tests of the
verifier and the material for the picture gallery.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from types import MappingProxyType
from typing import Any

import yaml

from causalista.verifier.check import ForbiddenReason
from causalista.verifier.graph import CausalProblem

_REQUIRED = {
    "id", "group", "title", "story", "edges", "treatment", "outcome",
    "identifiable", "valid_sets", "invalid_sets",
}  # fmt: skip
_OPTIONAL = {
    "unobserved", "extra_nodes", "note", "smallest_set", "valid_sets_complete",
    "valid_but_not_in_table", "would_be_identifiable_with",
}  # fmt: skip
_INVALID_SET_KEYS = {"set", "why", "forbidden", "open_paths"}


@dataclass(frozen=True)
class InvalidSet:
    """A tempting set that gives the wrong effect, with the reason."""

    variables: frozenset[str]
    why: str
    forbidden: Mapping[str, ForbiddenReason]
    open_paths: tuple[str, ...]


@dataclass(frozen=True)
class TextbookCase:
    id: str
    group: str
    """The section of the gallery where the case is shown."""
    title: str
    story: str
    note: str | None
    problem: CausalProblem
    identifiable: bool
    smallest_set: frozenset[str] | None
    """The expected smallest valid set; None when the case does not pin it down."""
    valid_sets: tuple[frozenset[str], ...]
    valid_sets_complete: bool
    """Whether ``valid_sets`` lists every valid set made of columns of the table."""
    invalid_sets: tuple[InvalidSet, ...]
    valid_but_not_in_table: tuple[frozenset[str], ...]
    would_be_identifiable_with: frozenset[str] | None
    """For a non-identifiable case: the hidden variables the table would need."""


def _check_keys(where: str, given: Mapping[str, Any], required: set[str], allowed: set[str]) -> None:
    missing = required - given.keys()
    unknown = given.keys() - allowed
    if missing or unknown:
        raise ValueError(f"{where}: missing keys {sorted(missing)}, unknown keys {sorted(unknown)}")


def _parse_invalid_set(case_id: str, raw: Mapping[str, Any]) -> InvalidSet:
    _check_keys(f"{case_id}: invalid set", raw, {"set", "why"}, _INVALID_SET_KEYS)
    return InvalidSet(
        variables=frozenset(raw["set"]),
        why=raw["why"],
        forbidden=MappingProxyType(
            {name: ForbiddenReason(reason) for name, reason in raw.get("forbidden", {}).items()}
        ),
        open_paths=tuple(raw.get("open_paths", ())),
    )


def _parse_case(raw: Mapping[str, Any]) -> TextbookCase:
    case_id = raw.get("id", "<case without id>")
    _check_keys(case_id, raw, _REQUIRED, _REQUIRED | _OPTIONAL)
    problem = CausalProblem.from_edges(
        raw["edges"],
        raw["treatment"],
        raw["outcome"],
        unobserved=raw.get("unobserved", ()),
        extra_nodes=raw.get("extra_nodes", ()),
    )
    smallest = raw.get("smallest_set")
    lacking = raw.get("would_be_identifiable_with")
    return TextbookCase(
        id=case_id,
        group=raw["group"],
        title=raw["title"],
        story=raw["story"],
        note=raw.get("note"),
        problem=problem,
        identifiable=raw["identifiable"],
        smallest_set=None if smallest is None else frozenset(smallest),
        valid_sets=tuple(frozenset(names) for names in raw["valid_sets"]),
        valid_sets_complete=raw.get("valid_sets_complete", True),
        invalid_sets=tuple(_parse_invalid_set(case_id, item) for item in raw["invalid_sets"]),
        valid_but_not_in_table=tuple(
            frozenset(names) for names in raw.get("valid_but_not_in_table", ())
        ),
        would_be_identifiable_with=None if lacking is None else frozenset(lacking),
    )


def load_textbook_cases() -> list[TextbookCase]:
    """Read every textbook case, failing loudly on anything malformed."""
    source = resources.files("causalista.verifier").joinpath("textbook_cases.yaml")
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    cases = [_parse_case(raw) for raw in document["cases"]]
    ids = [case.id for case in cases]
    duplicated = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    if duplicated:
        raise ValueError(f"duplicated case ids: {duplicated}")
    return cases
