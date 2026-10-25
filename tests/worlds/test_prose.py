"""Prose stories: the round trip keeps a faithful text and throws away an unfaithful one."""

from __future__ import annotations

import json
import re

import pytest

from causalista.worlds import Role, Theory, generate_pair
from causalista.worlds.narrative import facts_of
from causalista.worlds.prose import differences, read, read_prompt, statements_of, tell_in_prose, write_prompt

SEEDS = range(6)


@pytest.fixture(scope="module")
def worlds(theory: Theory):
    return [world for seed in SEEDS for world in generate_pair(theory, seed) if world is not None]


def _reader_saying(truth: dict[str, bool]):
    """A reader that answers from a table of what each sentence should get."""

    def reader(prompt: str, **_) -> str:
        shown = re.findall(r"^(\d+)\. (.+)$", prompt.split("Statements:")[1], flags=re.M)
        return json.dumps({number: truth[sentence] for number, sentence in shown})

    return reader


def _writer(prompt: str, **_) -> str:
    return "Contamos, em prosa, tudo o que aconteceu na empresa."


def test_the_statements_are_the_facts_of_the_world_and_the_facts_it_does_not_have(theory: Theory, worlds) -> None:
    for world in worlds:
        expected = statements_of(world, theory)
        said = {sentence for sentence, there in expected.items() if there}
        told = {sentence for sentences in facts_of(theory, world.structure).values() for sentence in sentences}
        assert said == told | {world.narrative.rsplit(". ", 1)[-1].rstrip(".") + "."} or said >= told
        for sentence in said:
            assert sentence in world.narrative
        for sentence, there in expected.items():
            if not there:
                assert sentence not in world.narrative
        for piece in world.structure.pieces:
            hidden_fact = theory.variables[piece.variable].hidden_fact
            if hidden_fact:
                assert expected[hidden_fact] == piece.hidden
        assert expected[theory.closing] != expected[theory.randomized]


def test_a_variable_with_two_roles_brings_the_facts_of_the_other_role(theory: Theory, worlds) -> None:
    for world in worlds:
        expected = statements_of(world, theory)
        for piece in world.structure.pieces:
            variable = theory.variables[piece.variable]
            for role, spec in variable.roles.items():
                for link in spec.links.values():
                    assert link.fact in expected
                    if role is piece.role:
                        assert expected[link.fact]


def test_a_faithful_prose_is_kept_and_nothing_else_changes(theory: Theory, worlds) -> None:
    for world in worlds:
        expected = statements_of(world, theory)
        told = tell_in_prose(world, theory, writer=_writer, readers=[_reader_saying(expected)])
        assert told.world is not None and told.attempts == 1 and told.problems == ()
        assert told.world.level == 2 and told.world.narrative != world.narrative
        assert told.world.name == f"{world.id}.pt2"
        assert told.world.truth == world.truth and told.world.table is world.table
        assert told.world.dictionary == world.dictionary and told.world.question == world.question


def test_an_unfaithful_prose_is_thrown_away(theory: Theory, worlds) -> None:
    world = next(w for w in worlds if any(p.role is Role.CONFOUNDER for p in w.structure.pieces))
    expected = statements_of(world, theory)

    # The prose dropped a fact of the world.
    dropped_fact = next(sentence for sentence, there in expected.items() if there)
    told = tell_in_prose(world, theory, writer=_writer, readers=[_reader_saying(expected), _reader_saying({**expected, dropped_fact: False})])
    assert told.world is None and told.attempts == 2
    assert told.problems == (f"a fact of the world is missing: {dropped_fact}",)

    # The prose says a fact that belongs to another role of a variable, or to no world like this one.
    added_fact = next(sentence for sentence, there in expected.items() if not there)
    problems = differences({**expected, added_fact: True}, expected)
    assert problems == [f"a fact that is not of this world is said: {added_fact}"]


def test_a_role_word_or_a_broken_reply_refuses_the_prose(theory: Theory, worlds) -> None:
    world = worlds[0]
    expected = statements_of(world, theory)
    told = tell_in_prose(world, theory, writer=lambda p, **_: "A renda é um confundidor.", readers=[_reader_saying(expected)])
    assert told.world is None
    told = tell_in_prose(world, theory, writer=_writer, readers=[lambda p, **_: "não sei"])
    assert told.world is None and "could not be used" in told.problems[0]
    # A reply that leaves a sentence out cannot be used either.
    assert read("texto", expected, "pt", lambda p, **_: json.dumps({"1": True})) is None


def test_the_prompts_show_the_facts_and_never_the_roles(theory: Theory, worlds) -> None:
    for world in worlds:
        expected = statements_of(world, theory)
        writing = write_prompt(world, "a manager")
        reading = read_prompt("um texto", list(expected), world.language)
        assert world.narrative in writing
        assert all(sentence in reading for sentence in expected)
        for prompt in (writing, reading):
            assert not any(role.value in prompt for role in (Role.CONFOUNDER, Role.MEDIATOR, Role.COLLIDER))
