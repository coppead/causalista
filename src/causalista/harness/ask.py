"""Use the model on a table of your own: build the task, ask a responder, read the answer, estimate.

The model never sees the rows. It reads the story of how the data were generated and the column
dictionary, and names the columns to adjust for (or says the effect is not identifiable). When it
asserts an effect, the estimator computes it from the rows with the chosen columns.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from causalista.estimator import EffectEstimate, estimate_effect, naive_difference
from causalista.harness.backends import Reply, Responder
from causalista.task import Answer, InvalidAnswer, Task, make_task, parse_answer


@dataclass(frozen=True)
class Consultation:
    """Everything that came out of one question about one table."""

    task: Task
    reply: Reply
    answer: Answer | None
    """None when the model's text could not be read as an answer; see ``error``."""
    error: str | None
    estimate: EffectEstimate | None
    """The effect with the chosen columns; None when the answer is "not identifiable" or unusable."""
    naive: EffectEstimate | None
    """The simple difference between treated and untreated, for contrast."""
    ignored: tuple[str, ...]
    """Names in the adjustment set that are not columns of the table (left out of the estimate)."""


def ask(
    table: pd.DataFrame,
    treatment: str,
    outcome: str,
    narrative: str,
    descriptions: dict[str, str],
    responder: Responder,
    *,
    question: str | None = None,
    seed: int = 0,
) -> Consultation:
    """Ask a responder which columns to adjust for, and estimate the effect if it says the data allow it."""
    question = question or f"What is the average effect of {treatment} on {outcome}?"
    task = make_task(
        world_id="own-table", question=question, treatment=treatment, outcome=outcome,
        narrative=narrative, descriptions=descriptions, table=table,
    )
    reply = responder(task)
    try:
        answer = parse_answer(reply.text, task)
    except InvalidAnswer as problem:
        return Consultation(task, reply, None, str(problem), None, None, ())
    if not answer.identifiable:
        return Consultation(task, reply, answer, None, None, None, ())
    columns = {card.column for card in task.columns} - {treatment, outcome}
    chosen = tuple(sorted(answer.adjustment_set & columns))
    ignored = tuple(sorted(answer.adjustment_set - columns))
    try:
        estimate = estimate_effect(table, treatment, outcome, chosen, seed=seed)
        naive = naive_difference(table, treatment, outcome)
    except ValueError as problem:
        return Consultation(task, reply, answer, f"the estimator could not run: {problem}", None, None, ignored)
    return Consultation(task, reply, answer, None, estimate, naive, ignored)


_LABELS = {
    "en": {
        "verdict": "Verdict", "identifiable": "identifiable by adjustment", "not_identifiable": "not identifiable with these columns",
        "adjust": "Adjust for", "nothing": "nothing (the groups are comparable as they are)", "missing": "What is missing",
        "roles": "Column roles", "assumptions": "Assumptions", "effect": "Adjusted effect", "ci": "95% interval",
        "naive": "Naive difference", "rows": "rows", "clipped": "share of rows with near-certain treatment (overlap warning)",
        "ignored": "Named but not in the table (ignored)", "unreadable": "The model's answer could not be read",
        "seconds": "model time", "no_estimate": "No effect is estimated: the data cannot answer with these columns.",
    },
    "pt": {
        "verdict": "Veredito", "identifiable": "identificável por ajuste", "not_identifiable": "não identificável com estas colunas",
        "adjust": "Ajustar por", "nothing": "nada (os grupos já são comparáveis)", "missing": "O que falta",
        "roles": "Papel das colunas", "assumptions": "Hipóteses", "effect": "Efeito ajustado", "ci": "intervalo de 95%",
        "naive": "Diferença simples", "rows": "linhas", "clipped": "fração de linhas com tratamento quase certo (aviso de sobreposição)",
        "ignored": "Citados mas fora da tabela (ignorados)", "unreadable": "A resposta do modelo não pôde ser lida",
        "seconds": "tempo do modelo", "no_estimate": "Nenhum efeito é estimado: os dados não respondem com estas colunas.",
    },
}


def format_consultation(result: Consultation, lang: str = "en") -> str:
    """A short report of a consultation, in English or Portuguese."""
    t = _LABELS["pt" if lang.lower().startswith("pt") else "en"]
    lines = []
    if result.answer is None:
        lines.append(f"{t['unreadable']}: {result.error}")
        lines.append(result.reply.text.strip())
        return "\n".join(lines)
    answer = result.answer
    lines.append(f"{t['verdict']}: {t['identifiable'] if answer.identifiable else t['not_identifiable']}")
    if answer.identifiable:
        chosen = sorted(answer.adjustment_set)
        lines.append(f"{t['adjust']}: {', '.join(chosen) if chosen else t['nothing']}")
    elif answer.missing:
        lines.append(f"{t['missing']}: {', '.join(answer.missing)}")
    if answer.roles:
        lines.append(f"{t['roles']}:")
        lines += [f"  {role.column}: {role.role}. {role.reason}" for role in answer.roles]
    if answer.assumptions:
        lines.append(f"{t['assumptions']}:")
        lines += [f"  - {assumption}" for assumption in answer.assumptions]
    if result.ignored:
        lines.append(f"{t['ignored']}: {', '.join(result.ignored)}")
    if result.estimate is not None and result.naive is not None:
        e, n = result.estimate, result.naive
        lines.append(f"{t['effect']}: {e.effect:+.4f}  ({t['ci']} [{e.low:+.4f}, {e.high:+.4f}]; {e.rows} {t['rows']}; {e.method})")
        lines.append(f"{t['naive']}: {n.effect:+.4f}  ({t['ci']} [{n.low:+.4f}, {n.high:+.4f}])")
        lines.append(f"{t['clipped']}: {e.clipped_share:.1%}")
    elif answer.identifiable and result.error:
        lines.append(result.error)
    else:
        lines.append(t["no_estimate"])
    lines.append(f"({t['seconds']}: {result.reply.seconds:.1f} s)")
    return "\n".join(lines)
