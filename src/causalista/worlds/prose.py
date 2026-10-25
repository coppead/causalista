"""Level 2 of the stories: running prose written by an open model, checked by a round trip.

A world told with one fact per sentence (level 1) is rewritten the way a person would
tell it. A second model then reads the prose and is asked, sentence by sentence, whether
the text says each fact of the world, and whether it says any of the facts the theory
card holds for the same variables in their other roles (the complaint registered after
the offer instead of before). The prose is kept only if it says every fact of the world
and none of the others. The prose never replaces the answer key: the graph, the table
and the truth of the world stay as they were.

An earlier design asked the reader to fill in, for each variable, what it influences and
what changes it. On faithful stories the readers reproduced the right table in only 7 to
13 of 32 worlds (2026-10-04), so that check would have thrown most good prose away.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

import numpy as np

from causalista.worlds.narrative import ROLE_WORDS, facts_of
from causalista.worlds.theory import Role, Theory
from causalista.worlds.world import World

Model = Callable[..., str]
"""Takes a prompt (and a ``seed``) and returns the reply of an open model."""

LANGUAGE_NAME = {"pt": "Brazilian Portuguese", "en": "English", "es": "Spanish", "fr": "French", "de": "German"}
# Who is telling the story. Varying the voice keeps the prose from having a single shape.
VOICES = (
    "a manager telling an analyst, in the first person plural, what the company did",
    "an e-mail from the head of the area to the data team",
    "the minutes of a meeting, in the third person",
    "a paragraph of an internal report",
    "an analyst's notes after talking to the people in charge",
)
WRITE = """\
Below is a list of facts about a business situation, one fact per sentence, in {language}. \
Rewrite it as running prose, in {language}, in this voice: {voice}.

Rules:
- Tell every fact of the list. Leave none out.
- Do not add any fact, cause or consequence that is not in the list.
- Keep the meaning of each fact: who influences what, whether it is for more or for less, \
and whether it happened before or after.
- You may change the order, join sentences and change the wording.
- No technical vocabulary of statistics.
- Answer with the prose only, in one to three paragraphs.

Facts:
{facts}"""

REVISE = """\
{first}

A first version of the prose was refused. This is the version:
{prose}

What was wrong with it:
{problems}

Write the prose again, in the same voice, fixing exactly that: every fact of the list must \
be told, and nothing that is not in the list may be said. Answer with the prose only."""

READ = """\
Read the text below, written in {language}. It describes how the data of a table were \
generated.

Text:
{prose}

Below is a list of numbered statements. For each one, say whether the text says it. A \
statement counts as said (true) when the text states the same fact, even in other words \
or spread over two sentences. It does not count (false) when the text does not mention \
it, only says something related, says it about another moment (before instead of after), \
or says it in the opposite direction (more instead of less).

Statements:
{statements}

Answer with one JSON object that maps each number to true or false, and nothing else: \
{{"1": true, "2": false}}"""


def statements_of(world: World, theory: Theory) -> dict[str, bool]:
    """Every sentence the card holds about the variables of this world, and whether this world says it.

    The sentences that are not said are the ones of the other roles of the same
    variables, the notice that a variable is missing from a table that has it, and the
    other way the treatment could have been assigned.
    """
    said = [sentence for sentences in facts_of(theory, world.structure).values() for sentence in sentences]
    assigned = any(p.role in (Role.CONFOUNDER, Role.TREATMENT_CAUSE) for p in world.structure.pieces)
    said.append(theory.closing if assigned else theory.randomized)

    others = [theory.randomized if assigned else theory.closing]
    for piece in world.structure.pieces:
        variable = theory.variables[piece.variable]
        for spec in variable.roles.values():
            others += [link.fact for link in spec.links.values()] + ([spec.fact] if spec.fact else [])
        if variable.hidden_fact:
            others.append(variable.hidden_fact)

    expected = dict.fromkeys(said, True)
    for sentence in others:
        expected.setdefault(sentence, False)
    return expected


def differences(read: dict[str, bool], expected: dict[str, bool]) -> list[str]:
    """Where a reading departs from what the world says. Empty when the text is faithful."""
    found = []
    for sentence, wanted in expected.items():
        got = read.get(sentence)
        if got is not wanted:
            what = "a fact of the world is missing" if wanted else "a fact that is not of this world is said"
            found.append(f"{what}: {sentence}")
    return found


def write_prompt(world: World, voice: str) -> str:
    return WRITE.format(language=LANGUAGE_NAME[world.language], voice=voice, facts=world.narrative)


def revise_prompt(world: World, voice: str, prose: str, problems: Sequence[str]) -> str:
    """Ask for the prose again, saying which facts were left out or were added."""
    listed = []
    for problem in problems:
        kind, _, sentence = problem.partition(": ")
        if kind == "a fact of the world is missing":
            listed.append(f"- this fact of the list was left out: {sentence}")
        elif kind == "a fact that is not of this world is said":
            listed.append(f"- this is not in the list and must not be said: {sentence}")
    return REVISE.format(first=write_prompt(world, voice), prose=prose, problems="\n".join(listed))


def read_prompt(prose: str, sentences: list[str], language: str) -> str:
    numbered = "\n".join(f"{number}. {sentence}" for number, sentence in enumerate(sentences, start=1))
    return READ.format(language=LANGUAGE_NAME[language], prose=prose, statements=numbered)


def read(text: str, expected: dict[str, bool], language: str, reader: Model, *, seed: int = 0) -> dict[str, bool] | None:
    """Have a model say which of the sentences a story states. None when its reply cannot be used.

    The sentences are shown in a shuffled order, so that the reader cannot lean on the
    order in which the story tells them.
    """
    sentences = list(expected)
    order = np.random.default_rng([seed, 6]).permutation(len(sentences))
    shown = [sentences[i] for i in order]
    try:
        reply = json.loads(reader(read_prompt(text, shown, language)))
        return {sentence: reply[str(number)] is True for number, sentence in enumerate(shown, start=1)}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


@dataclass(frozen=True)
class Telling:
    world: World | None
    """The world told in prose, or None when no attempt passed the check."""
    attempts: int
    problems: tuple[str, ...]
    """Why the last attempt was refused."""


def tell_in_prose(
    world: World, theory: Theory, *, writer: Model, readers: Sequence[Model], attempts: int = 2
) -> Telling:
    """Rewrite the story of a level-1 world as prose, and keep it only if every reader agrees with it.

    With two readers a missing fact has to slip past both. Measured on 32 faithful
    stories (2026-10-04): one reader alone missed a removed fact in 6% to 12% of them,
    and none of the three tried missed a variable whose role had been swapped.
    """
    if world.level != 1 or theory.language != world.language or theory.id != world.theory_id:
        raise ValueError("needs a level-1 world and its theory card, in the same language")
    expected = statements_of(world, theory)
    rng = np.random.default_rng([world.parameters.seed, 5, sum(map(ord, world.name))])
    problems: tuple[str, ...] = ()
    voice = VOICES[int(rng.integers(len(VOICES)))]
    prose = ""
    for attempt in range(attempts):
        # A second attempt is a revision: the writer is told which facts it left out or added.
        fixable = prose and any(": " in problem for problem in problems)
        prompt = revise_prompt(world, voice, prose, problems) if fixable else write_prompt(world, voice)
        prose = " ".join(writer(prompt, seed=int(rng.integers(1 << 30))).split())
        if not prose or any(word in prose.lower() for word in ROLE_WORDS):
            problems = ("the prose is empty or uses a word that gives a role away",)
            continue
        for reader in readers:
            got = read(prose, expected, world.language, reader, seed=world.parameters.seed)
            problems = ("the reader's reply could not be used",) if got is None else tuple(differences(got, expected))
            if problems:
                break
        if not problems:
            return Telling(replace(world, narrative=prose, level=2), attempt + 1, ())
    return Telling(None, attempts, problems)
