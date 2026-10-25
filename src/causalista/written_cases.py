"""Hand-written cases: a story, the columns of a table, a declared graph and an answer.

They are the cases of phase 0 and the format of the human-written test (section 7 of
the specification). The files live in ``cases/`` at the root of the repository and are
written to be read by a person. The declared answer is never taken on trust: it is
checked against the verifier.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

from causalista.verifier import CausalProblem, check_adjustment_set, identify

CASES_DIR = Path(__file__).resolve().parents[2] / "cases"
AUTHORS = ("ai", "andre")
STATUSES = ("rascunho", "aprovado")
_REQUIRED = {"id", "author", "status", "theme", "title", "treatment", "outcome", "columns", "story", "edges", "answer"}
_OPTIONAL = {"not_in_table", "twin", "note", "language", "style", "persona"}
LANGUAGES = ("pt", "en", "es", "fr", "de")
_ANSWER_KEYS = {"identifiable", "adjust_for", "do_not_adjust_for", "indifferent", "missing"}


class InvalidCaseError(ValueError):
    """A written case is malformed."""


@dataclass(frozen=True)
class WrittenCase:
    id: str
    author: str
    status: str
    theme: str
    title: str
    story: str
    note: str | None
    twin: str | None
    columns: Mapping[str, str]
    """Every column of the table, treatment and outcome included, with its description."""
    not_in_table: Mapping[str, str]
    problem: CausalProblem
    identifiable: bool
    adjust_for: frozenset[str]
    do_not_adjust_for: Mapping[str, str]
    """Columns that spoil the effect, each with the reason given to the reader."""
    indifferent: frozenset[str]
    missing: frozenset[str]
    language: str = "pt"
    style: str | None = None
    """How the story is written: an e-mail, meeting notes, a report excerpt, a chat message."""
    persona: str | None = None
    """Who is supposed to have written it, for the cases that simulate a person."""

    @property
    def approved(self) -> bool:
        return self.status == "aprovado"


def _keys(where: str, given: Any, required: set[str], allowed: set[str]) -> None:
    if not isinstance(given, Mapping):
        raise InvalidCaseError(f"{where}: expected a mapping, got {type(given).__name__}")
    missing, unknown = required - given.keys(), given.keys() - allowed
    if missing or unknown:
        raise InvalidCaseError(f"{where}: missing keys {sorted(missing)}, unknown keys {sorted(unknown)}")


def _texts(where: str, given: Any) -> Mapping[str, str]:
    if not isinstance(given, Mapping) or not all(isinstance(text, str) and text.strip() for text in given.values()):
        raise InvalidCaseError(f"{where}: expected names with a description each")
    return MappingProxyType({name: " ".join(text.split()) for name, text in given.items()})


def parse_case(raw: Mapping[str, Any]) -> WrittenCase:
    case_id = raw.get("id", "<case without id>") if isinstance(raw, Mapping) else "<case>"
    _keys(case_id, raw, _REQUIRED, _REQUIRED | _OPTIONAL)
    if raw["author"] not in AUTHORS or raw["status"] not in STATUSES:
        raise InvalidCaseError(f"{case_id}: author must be one of {AUTHORS} and status one of {STATUSES}")
    if raw.get("language", "pt") not in LANGUAGES:
        raise InvalidCaseError(f"{case_id}: language must be one of {LANGUAGES}")
    answer = raw["answer"]
    _keys(f"{case_id}: answer", answer, {"identifiable"}, _ANSWER_KEYS)
    if answer["identifiable"] == ("missing" in answer) or answer["identifiable"] != ("adjust_for" in answer):
        raise InvalidCaseError(
            f"{case_id}: an identifiable case gives adjust_for; a non-identifiable one gives missing"
        )

    columns = _texts(f"{case_id}: columns", raw["columns"])
    not_in_table = _texts(f"{case_id}: not_in_table", raw.get("not_in_table", {}))
    problem = CausalProblem.from_edges(
        raw["edges"],
        raw["treatment"],
        raw["outcome"],
        unobserved=not_in_table,
        extra_nodes=[*columns, *not_in_table],
    )
    if problem.nodes != columns.keys() | not_in_table.keys():
        stray = sorted(problem.nodes ^ (columns.keys() | not_in_table.keys()))
        raise InvalidCaseError(f"{case_id}: the edges and the columns do not name the same variables: {stray}")

    return WrittenCase(
        id=case_id,
        author=raw["author"],
        status=raw["status"],
        theme=raw["theme"],
        title=raw["title"],
        story=" ".join(raw["story"].split()),
        note=None if raw.get("note") is None else " ".join(raw["note"].split()),
        twin=raw.get("twin"),
        columns=columns,
        not_in_table=not_in_table,
        problem=problem,
        identifiable=answer["identifiable"],
        adjust_for=frozenset(answer.get("adjust_for", ())),
        do_not_adjust_for=_texts(f"{case_id}: do_not_adjust_for", answer.get("do_not_adjust_for", {})),
        indifferent=frozenset(answer.get("indifferent", ())),
        missing=frozenset(answer.get("missing", ())),
        language=raw.get("language", "pt"),
        style=raw.get("style"),
        persona=raw.get("persona"),
    )


def load_written_cases(path: Path = CASES_DIR / "fase0.yaml") -> list[WrittenCase]:
    """Read every case of a file, failing loudly on anything malformed."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    cases = [parse_case(raw) for raw in document["cases"]]
    ids = [case.id for case in cases]
    if len(set(ids)) < len(ids):
        raise InvalidCaseError(f"{path.name}: duplicated case ids")
    for case in cases:
        if case.twin is not None and case.twin not in ids:
            raise InvalidCaseError(f"{case.id}: the twin {case.twin!r} is not in the file")
    return cases


def disagreements(case: WrittenCase) -> list[str]:
    """Where the declared answer and the verifier differ. Empty when they agree."""
    found: list[str] = []
    verdict = identify(case.problem)
    if verdict.identifiable != case.identifiable:
        return [f"the verifier says identifiable={verdict.identifiable}"]

    if not case.identifiable:
        if verdict.missing != case.missing:
            found.append(f"the verifier says what is missing is {sorted(verdict.missing)}")
        return found

    if verdict.adjustment_set != case.adjust_for:
        found.append(f"the smallest valid set is {sorted(verdict.adjustment_set)}")
    covariates = case.problem.observed_covariates
    sorted_out = case.adjust_for | case.do_not_adjust_for.keys() | case.indifferent
    if sorted_out != covariates:
        found.append(f"columns without a verdict, or named twice: {sorted(sorted_out ^ covariates)}")
    for name in case.do_not_adjust_for:
        if check_adjustment_set(case.problem, case.adjust_for | {name}).valid:
            found.append(f"adjusting for {name} does not spoil the effect")
    for name in case.indifferent:
        if not check_adjustment_set(case.problem, case.adjust_for | {name}).valid:
            found.append(f"adjusting for {name} spoils the effect")
    return found
