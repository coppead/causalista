"""The task given to a model: what it sees, how it answers and how the answer is scored."""

from causalista.task.answer import Answer, ColumnRole, InvalidAnswer, parse_answer, render_answer
from causalista.task.ideal import ideal_answer
from causalista.task.prompt import ROLES, VERDICTS, ColumnCard, Task, build_prompt, make_task, task_of
from causalista.task.score import OUTCOME_NAME, SCORE, Judgement, Outcome, judge

__all__ = [
    "OUTCOME_NAME",
    "ROLES",
    "SCORE",
    "VERDICTS",
    "Answer",
    "ColumnCard",
    "ColumnRole",
    "InvalidAnswer",
    "Judgement",
    "Outcome",
    "Task",
    "build_prompt",
    "ideal_answer",
    "judge",
    "make_task",
    "parse_answer",
    "render_answer",
    "task_of",
]
