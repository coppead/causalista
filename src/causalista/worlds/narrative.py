"""What an analyst is told about a world: the story and the dictionary of the table.

Level 1 of the specification: direct facts, one per sentence, taken from the theory
card. The story never names a role (confounder, mediator, collider) and never states
the effect that is being asked about.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass

import numpy as np

from causalista.worlds.structure import Structure
from causalista.worlds.theory import LINKS_OF_ROLE, Kind, Role, Theory

KIND_LABEL = {
    "pt": {
        Kind.BINARY: "binária (0 ou 1)",
        Kind.COUNT: "contagem",
        Kind.CONTINUOUS: "valor contínuo",
        Kind.SCORE: "nota de 0 a 10",
    },
    "en": {
        Kind.BINARY: "binary (0 or 1)",
        Kind.COUNT: "count",
        Kind.CONTINUOUS: "continuous value",
        Kind.SCORE: "score from 0 to 10",
    },
    "es": {
        Kind.BINARY: "binaria (0 o 1)",
        Kind.COUNT: "conteo",
        Kind.CONTINUOUS: "valor continuo",
        Kind.SCORE: "nota de 0 a 10",
    },
    "fr": {
        Kind.BINARY: "binaire (0 ou 1)",
        Kind.COUNT: "comptage",
        Kind.CONTINUOUS: "valeur continue",
        Kind.SCORE: "note de 0 à 10",
    },
    "de": {
        Kind.BINARY: "binär (0 oder 1)",
        Kind.COUNT: "Anzahl",
        Kind.CONTINUOUS: "stetiger Wert",
        Kind.SCORE: "Note von 0 bis 10",
    },
}
QUESTION = {
    "pt": "Qual o efeito de {treatment} sobre {outcome}?",
    "en": "What is the effect of {treatment} on {outcome}?",
    "es": "¿Cuál es el efecto de {treatment} sobre {outcome}?",
    "fr": "Quel est l'effet de {treatment} sur {outcome} ?",
    "de": "Welchen Effekt hat {treatment} auf {outcome}?",
}
P_SCATTERED = 0.5   # how often the facts about one variable are spread through the story
# Words that would give a role away. No story, in any language, may use them.
ROLE_WORDS = (
    "confundidor", "mediador", "colisor",
    "confounder", "mediator", "collider",
    "confusor", "factor de confusión", "colisionador",
    "facteur de confusion", "médiateur", "collisionneur",
    "störfaktor", "kollider",
)  # fmt: skip


@dataclass(frozen=True)
class ColumnInfo:
    column: str
    kind: str
    description: str


def _labelled_facts(theory: Theory, structure: Structure) -> dict[str, list[tuple[str, str]]]:
    """For each variable, its sentences with what each one tells: a link, a loose fact, or the absence."""
    told: dict[str, list[tuple[str, str]]] = {}
    for piece in structure.pieces:
        variable = theory.variables[piece.variable]
        spec = variable.roles[piece.role]
        sentences = [(name, spec.links[name].fact) for name in LINKS_OF_ROLE[piece.role]]
        if spec.fact:
            sentences.append(("fact", spec.fact))
        if piece.hidden:
            sentences.append(("hidden", variable.hidden_fact))
        told[piece.variable] = sentences
    return told


def facts_of(theory: Theory, structure: Structure) -> dict[str, list[str]]:
    """The sentences that describe each variable of the world, by variable."""
    return {
        name: [sentence for _, sentence in sentences]
        for name, sentences in _labelled_facts(theory, structure).items()
    }


def build_narrative(theory: Theory, structure: Structure, rng: np.random.Generator) -> str:
    """Tell the world: the context, the facts in a random order, and how treatment was assigned.

    In about half of the worlds the facts about one variable stay together, in a random
    order; in the others every fact goes to a random place of the story. With a fixed
    order inside each variable, a model trained on these stories leaned on the order:
    measured on 2026-10-05, it went from 100% to 65% when the same sentences were shuffled.

    Twins share the draws, and the place of a fact depends only on the variable and on
    what the fact tells, so the stories of two twins differ only in the fact that changed.
    """
    told = _labelled_facts(theory, structure)
    order = [structure.pieces[i].variable for i in rng.permutation(len(structure.pieces))]
    scattered = rng.random() < P_SCATTERED
    salt = int(rng.integers(2**32))

    def place(variable: str, fact: str) -> int:
        return zlib.crc32(f"{salt}|{variable}|{fact}".encode())

    turn = {name: index for index, name in enumerate(order)}
    facts = [(name, fact, sentence) for name in order for fact, sentence in told[name]]
    facts.sort(key=lambda item: (0 if scattered else turn[item[0]], place(item[0], item[1])))

    sentences = [theory.context]
    seen: set[str] = set()
    for _, _, sentence in facts:
        if sentence not in seen:  # two roles may share a sentence; say it once
            seen.add(sentence)
            sentences.append(sentence)

    assigned_by_something = any(
        piece.role in (Role.CONFOUNDER, Role.TREATMENT_CAUSE) for piece in structure.pieces
    )
    sentences.append(theory.closing if assigned_by_something else theory.randomized)
    return " ".join(sentences)


def build_dictionary(theory: Theory, structure: Structure, columns: list[str]) -> list[ColumnInfo]:
    """Describe each column of the table, in the order the table has them."""
    roles = {piece.variable: piece.role for piece in structure.pieces}
    kinds = KIND_LABEL[theory.language]
    entries = []
    for column in columns:
        if column == theory.treatment.column:
            entries.append(ColumnInfo(column, kinds[Kind.BINARY], theory.treatment.dictionary))
        elif column == theory.outcome.column:
            entries.append(ColumnInfo(column, kinds[theory.outcome.kind], theory.outcome.dictionary))
        else:
            variable = theory.variables[column]
            entries.append(ColumnInfo(column, kinds[variable.kind], variable.roles[roles[column]].dictionary))
    return entries
