"""The ideal answer is the answer key in the format asked of a model: it always scores +1."""

from __future__ import annotations

import pytest

from causalista.task import Outcome, ideal_answer, judge, parse_answer, render_answer, task_of
from causalista.task.ideal import ASSUMPTIONS, REASON
from causalista.worlds import LANGUAGES, Role, generate_pair, load_theory

THEORY = load_theory("telecom")


@pytest.fixture(scope="module")
def worlds():
    return [world for seed in range(6) for world in generate_pair(THEORY, seed) if world is not None]


def test_the_ideal_answer_always_scores_one(worlds) -> None:
    for world in worlds:
        answer = ideal_answer(world, THEORY)
        judgement = judge(world.problem, answer)
        assert judgement.outcome is Outcome.CORRECT and judgement.score == 1.0


def test_the_ideal_answer_survives_writing_and_reading(worlds) -> None:
    for world in worlds:
        answer = ideal_answer(world, THEORY)
        assert parse_answer(render_answer(answer), task_of(world)) == answer
        assert answer.complete


def test_every_column_gets_its_role_and_a_reason(worlds) -> None:
    for world in worlds:
        answer = ideal_answer(world, THEORY)
        said = {role.column: role for role in answer.roles}
        assert list(said) == [c for c in world.table.columns if c in world.problem.observed_covariates]
        for piece in world.structure.pieces:
            if piece.hidden:
                assert piece.variable not in said
                # Only a hidden confounder is something the table lacks.
                lacking = THEORY.variables[piece.variable].label in answer.missing
                assert lacking == (piece.role is Role.CONFOUNDER)
                continue
            expected = piece.role.value if piece.role in (Role.CONFOUNDER, Role.MEDIATOR, Role.COLLIDER) else "neutral"
            assert said[piece.variable].role == expected
            assert world.problem.treatment in said[piece.variable].reason or world.problem.outcome in said[piece.variable].reason
        assert bool(answer.missing) == (not world.truth.identifiable)
        assert set(answer.adjustment_set) == set(world.truth.adjustment_set or ())


def test_every_language_has_every_sentence() -> None:
    for language in LANGUAGES:
        assert set(REASON[language]) == set(Role)
        assert len(ASSUMPTIONS[language]) == 2
