"""The score of an answer: section 5 of the specification.

The verifier decides, on the true graph, whether the answer is right. A confident error
(a causal effect asserted with an invalid set, or in a world where the effect is not
identifiable) costs more than abstaining when an answer existed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from causalista.task.answer import Answer
from causalista.verifier import (
    AdjustmentCheck,
    CausalProblem,
    ForbiddenReason,
    check_adjustment_set,
    identify,
)


class Outcome(StrEnum):
    CORRECT = "correct"
    CONFIDENT_ERROR = "confident_error"
    UNDUE_ABSTENTION = "undue_abstention"
    INVALID = "invalid"
    """The text was not an answer the runner could use."""


# The weights are a research decision of André's. An invalid answer is scored like a
# confident error (proposal, pending his confirmation) and reported apart from it.
SCORE = {
    Outcome.CORRECT: 1.0,
    Outcome.CONFIDENT_ERROR: -1.0,
    Outcome.UNDUE_ABSTENTION: -0.5,
    Outcome.INVALID: -1.0,
}
OUTCOME_NAME = {
    Outcome.CORRECT: "acerto",
    Outcome.CONFIDENT_ERROR: "erro confiante",
    Outcome.UNDUE_ABSTENTION: "abstenção indevida",
    Outcome.INVALID: "resposta inválida",
}
_FORBIDDEN_NAME = {
    ForbiddenReason.TREATMENT: "é a própria intervenção",
    ForbiddenReason.OUTCOME: "é o próprio resultado",
    ForbiddenReason.MEDIATOR: "é consequência da intervenção e faz parte do efeito",
    ForbiddenReason.DESCENDANT_OF_MEDIATOR: "é consequência de uma coluna que faz parte do efeito",
    ForbiddenReason.DESCENDANT_OF_OUTCOME: "é consequência do resultado",
}


@dataclass(frozen=True)
class Judgement:
    outcome: Outcome
    score: float
    world_identifiable: bool
    check: AdjustmentCheck | None
    """The verifier's verdict on the set, when the answer proposed one."""
    reason: str
    """Why, in Portuguese, in the words of the verifier."""


def _names(variables) -> str:
    return ", ".join(sorted(variables)) or "nenhuma coluna"


def _why_invalid(check: AdjustmentCheck) -> str:
    parts = [f"{name} {_FORBIDDEN_NAME[reason]}" for name, reason in sorted(check.forbidden.items())]
    parts += [f"fica aberto o caminho {path.text}" for path in check.open_paths]
    return "; ".join(parts)


def judge(problem: CausalProblem, answer: Answer | None, *, invalid: str | None = None) -> Judgement:
    """Score an answer against the true graph. Pass ``answer=None`` for an unusable text."""
    truth = identify(problem)

    def result(outcome: Outcome, reason: str, check: AdjustmentCheck | None = None) -> Judgement:
        return Judgement(outcome, SCORE[outcome], truth.identifiable, check, reason)

    if answer is None:
        return result(Outcome.INVALID, f"Resposta inválida: {invalid or 'sem motivo registrado'}.")

    if not truth.identifiable:
        lacking = f"falta na tabela: {_names(truth.missing)}"
        if not answer.identifiable:
            return result(Outcome.CORRECT, f"O efeito não é identificável ({lacking}).")
        known = answer.adjustment_set <= problem.nodes
        return result(
            Outcome.CONFIDENT_ERROR,
            f"O efeito não é identificável com estas colunas ({lacking}), e a resposta afirmou um efeito.",
            check_adjustment_set(problem, answer.adjustment_set) if known else None,
        )

    if not answer.identifiable:
        return result(
            Outcome.UNDUE_ABSTENTION,
            f"O efeito é identificável ajustando por {_names(truth.adjustment_set)}.",
        )
    strangers = answer.adjustment_set - problem.nodes
    if strangers:
        return result(
            Outcome.CONFIDENT_ERROR,
            f"A resposta afirmou um efeito ajustando por algo que não é coluna da tabela: {_names(strangers)}.",
        )
    check = check_adjustment_set(problem, answer.adjustment_set)
    if check.usable:
        return result(Outcome.CORRECT, f"Ajustar por {_names(answer.adjustment_set)} dá o efeito certo.", check)
    return result(
        Outcome.CONFIDENT_ERROR,
        f"Ajustar por {_names(answer.adjustment_set)} não dá o efeito certo: {_why_invalid(check)}.",
        check,
    )
