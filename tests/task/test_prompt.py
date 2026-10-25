"""The prompt shows what the analyst knows and nothing of the answer key."""

from __future__ import annotations

import pytest

from causalista.task import build_prompt, task_of
from causalista.task.prompt import INSTRUCTIONS
from causalista.worlds import generate_pair, load_theory

THEORY = load_theory("telecom")


@pytest.fixture(scope="module")
def worlds():
    return [world for seed in range(4) for world in generate_pair(THEORY, seed) if world is not None]


def test_the_prompt_shows_the_story_and_every_column(worlds) -> None:
    for world in worlds:
        task = task_of(world)
        prompt = build_prompt(task)
        assert world.narrative in prompt and world.question in prompt
        assert [card.column for card in task.columns] == list(world.table.columns)
        for entry in world.dictionary:
            assert f"- {entry.column} (" in prompt and entry.description in prompt
        assert set(task.covariates) == set(world.problem.observed_covariates)


def test_the_prompt_gives_nothing_away(worlds) -> None:
    for world in worlds:
        about_the_world = build_prompt(task_of(world)).replace(INSTRUCTIONS, "")
        for hidden in world.problem.unobserved:
            assert f"- {hidden} (" not in about_the_world
        for word in ("confounder", "mediator", "collider", "confundidor", "mediador", "colisor"):
            # The format lists the role names; the part about the world never uses them.
            assert word not in about_the_world.split("## Your answer")[0]
        if world.truth.true_effect != 0:
            assert f"{abs(world.truth.true_effect):.3f}" not in about_the_world


def test_columns_are_summarised_by_kind(worlds) -> None:
    task = task_of(worlds[0])
    kinds = {card.column: card.kind for card in task.columns}
    assert kinds[task.treatment] == "binary"
    for card in task.columns:
        assert card.summary.startswith("share of 1" if card.kind == "binary" else "mean")
