"""What a model is shown about a world, and the words it is shown them with.

A model sees the question, the story and the dictionary of the table, with a short
summary of each column. It never sees the rows, the graph or the true effect. The same
prompt goes to every model that is compared.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from causalista.worlds import World

ROLES = ("confounder", "mediator", "collider", "neutral")
VERDICTS = ("identifiable", "not_identifiable")

INSTRUCTIONS = """\
You are a careful causal analyst. Someone wants to measure the average effect of an \
intervention on an outcome using a table. You are told how the data were generated and \
what each column is. You do not see the rows.

Decide which columns to adjust for, so that the comparison between those who got the \
intervention and those who did not gives the effect of the intervention. If no set of \
columns of the table can do that, say that the effect is not identifiable.

Each column other than the intervention and the outcome plays one role:
- confounder: it influences who gets the intervention and it influences the outcome. \
Adjust for it. If a confounder is described in the story but is not a column of the \
table, the effect is not identifiable.
- mediator: it is a consequence of the intervention and it influences the outcome. \
Never adjust for it.
- collider: it is a consequence of the intervention and of the outcome. Never adjust for it.
- neutral: it influences only the intervention, only the outcome, or neither. It does \
not matter.

The same column can play different roles in different tables: what decides is what the \
story and the description of the column say, in particular whether the column was \
measured before or after the intervention."""

ANSWER_FORMAT = """\
Answer with one JSON object and nothing else, in this format:
{
  "columns": [
    {"column": "<name>", "role": "confounder" | "mediator" | "collider" | "neutral", "reason": "<one line>"}
  ],
  "verdict": "identifiable" | "not_identifiable",
  "adjustment_set": ["<name>"],
  "missing": ["<what the table lacks>"],
  "assumptions": ["<an assumption you are making>"]
}
- "columns": one entry for every column other than the intervention and the outcome.
- "adjustment_set": the columns to adjust for. Empty if no adjustment is needed, and \
empty if the effect is not identifiable.
- "missing": only if the effect is not identifiable; otherwise empty.
- Write the reasons, what is missing and the assumptions in the language of the story."""


@dataclass(frozen=True)
class ColumnCard:
    """One column of the table, as a model sees it."""

    column: str
    kind: str
    """binary, integer or number, read off the values."""
    summary: str
    description: str


@dataclass(frozen=True)
class Task:
    """Everything a model may see about one world."""

    world_id: str
    question: str
    treatment: str
    outcome: str
    narrative: str
    columns: tuple[ColumnCard, ...]
    """In the order of the table, treatment and outcome included."""

    @property
    def covariates(self) -> tuple[str, ...]:
        return tuple(c.column for c in self.columns if c.column not in (self.treatment, self.outcome))


def _number(value: float) -> str:
    return f"{value:.3g}"


def summarise(values: pd.Series) -> tuple[str, str]:
    """The kind of a column and a short summary of it, both read off its values."""
    if set(values.unique()) <= {0, 1}:
        return "binary", f"share of 1: {values.mean():.2f}"
    kind = "integer" if pd.api.types.is_integer_dtype(values) else "number"
    return kind, f"mean {_number(values.mean())}, min {_number(values.min())}, max {_number(values.max())}"


def make_task(
    *,
    world_id: str,
    question: str,
    treatment: str,
    outcome: str,
    narrative: str,
    descriptions: dict[str, str],
    table: pd.DataFrame,
) -> Task:
    """Put together what a model sees, from the story and a table with its dictionary."""
    missing = [name for name in table.columns if name not in descriptions]
    if missing or treatment not in table.columns or outcome not in table.columns:
        raise ValueError(f"columns without a description, or endpoints not in the table: {missing}")
    cards = tuple(
        ColumnCard(name, *summarise(table[name]), description=descriptions[name]) for name in table.columns
    )
    return Task(world_id, question, treatment, outcome, narrative, cards)


def task_of(world: World) -> Task:
    return make_task(
        world_id=world.id,
        question=world.question,
        treatment=world.problem.treatment,
        outcome=world.problem.outcome,
        narrative=world.narrative,
        descriptions={entry.column: entry.description for entry in world.dictionary},
        table=world.table,
    )


def build_prompt(task: Task) -> str:
    """The text given to a model. Nothing in it comes from the answer key."""
    columns = "\n".join(
        f"- {card.column} ({card.kind}; {card.summary}): {card.description}" for card in task.columns
    )
    return "\n\n".join(
        [
            INSTRUCTIONS,
            f"## Question\n{task.question}\nIntervention column: {task.treatment}\nOutcome column: {task.outcome}",
            f"## How the data were generated\n{task.narrative}",
            f"## Columns of the table\n{columns}",
            f"## Your answer\n{ANSWER_FORMAT}",
        ]
    )
