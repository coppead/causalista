"""The answer a model gives, and how it is read.

Reading is forgiving about the wrapping (a code fence, a block of thinking before the
JSON) and strict about what the runner needs: a verdict, and an adjustment set made of
columns of the table. The other parts (a role for each column, what is missing, the
assumptions) are kept as given, and ``complete`` says whether they were all there.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from causalista.task.prompt import ROLES, VERDICTS, Task

_THINKING = re.compile(r"<think>.*?</think>", re.DOTALL)
_END_OF_THINKING = "</think>"


class InvalidAnswer(ValueError):
    """The text is not an answer the runner can use. The message says why."""


@dataclass(frozen=True)
class ColumnRole:
    column: str
    role: str
    reason: str


@dataclass(frozen=True)
class Answer:
    identifiable: bool
    adjustment_set: frozenset[str]
    """Empty when the answer is "not identifiable". May name things that are not columns of the table."""
    roles: tuple[ColumnRole, ...]
    missing: tuple[str, ...]
    assumptions: tuple[str, ...]
    complete: bool
    """Whether every part of the format was there: a role for each column, and assumptions."""


def _first_object(text: str) -> dict[str, Any]:
    """The first JSON object in a text, whatever comes before or after it."""
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start != -1:
        try:
            value, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
            continue
        if isinstance(value, dict):
            return value
        start = text.find("{", start + 1)
    raise InvalidAnswer("no JSON object in the answer")


def _texts(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def parse_answer(text: str, task: Task) -> Answer:
    """Read a model's answer to a task. Raises ``InvalidAnswer`` when the runner cannot use it."""
    # Some models print their reasoning first, with or without the opening tag; the
    # answer is what comes after it.
    raw = _first_object(_THINKING.sub("", text).rsplit(_END_OF_THINKING, 1)[-1])

    verdict = raw.get("verdict")
    if verdict not in VERDICTS:
        raise InvalidAnswer(f"verdict must be one of {VERDICTS}, got {verdict!r}")
    identifiable = verdict == "identifiable"

    chosen = raw.get("adjustment_set", [])
    if not isinstance(chosen, list) or not all(isinstance(name, str) for name in chosen):
        raise InvalidAnswer("adjustment_set must be a list of column names")
    known = {card.column for card in task.columns}
    # A set that names something that is not a column is kept as given: asserting an
    # effect with it is a confident error, and it is the score that says so.

    roles = []
    for item in raw.get("columns") if isinstance(raw.get("columns"), list) else []:
        if isinstance(item, dict) and item.get("column") in known and item.get("role") in ROLES:
            roles.append(ColumnRole(item["column"], item["role"], str(item.get("reason", "")).strip()))
    assumptions = _texts(raw.get("assumptions"))
    judged = [role.column for role in roles]
    return Answer(
        identifiable=identifiable,
        adjustment_set=frozenset(chosen) if identifiable else frozenset(),
        roles=tuple(roles),
        missing=_texts(raw.get("missing")),
        assumptions=assumptions,
        complete=sorted(judged) == sorted(task.covariates) and bool(assumptions),
    )


def render_answer(answer: Answer) -> str:
    """The text of an answer in the format asked of a model. Used for the ideal answers."""

    def line(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    columns = ",\n".join(
        "    " + line({"column": r.column, "role": r.role, "reason": r.reason}) for r in answer.roles
    )
    return "\n".join(
        [
            "{",
            '  "columns": [' + (f"\n{columns}\n  ]," if columns else "],"),
            f'  "verdict": {line(VERDICTS[0] if answer.identifiable else VERDICTS[1])},',
            f'  "adjustment_set": {line(sorted(answer.adjustment_set))},',
            f'  "missing": {line(list(answer.missing))},',
            f'  "assumptions": {line(list(answer.assumptions))}',
            "}",
        ]
    )
