"""The ideal answer to a world: what a model is taught to say in the supervised step.

Every part comes from the answer key: the role of each column from the structure, the
verdict and the set from the verifier, what is missing from the hidden variables. The
one-line reasons state the causal facts of the graph, in the language of the story.
"""

from __future__ import annotations

import networkx as nx

from causalista.task.answer import Answer, ColumnRole
from causalista.verifier import CausalProblem, identify
from causalista.worlds import Role, Theory, World
from causalista.written_cases import WrittenCase

ROLE_NAME = {
    Role.CONFOUNDER: "confounder",
    Role.MEDIATOR: "mediator",
    Role.COLLIDER: "collider",
    Role.OUTCOME_CAUSE: "neutral",
    Role.TREATMENT_CAUSE: "neutral",
    Role.UNRELATED: "neutral",
}
# {t} and {y} are the names of the treatment and outcome columns. Column names keep the
# sentences free of articles and contractions, which differ in every language.
REASON = {
    "pt": {
        Role.CONFOUNDER: "Influencia {t} e influencia {y}.",
        Role.MEDIATOR: "É consequência de {t} e influencia {y}: faz parte do efeito.",
        Role.COLLIDER: "É consequência de {t} e de {y}.",
        Role.OUTCOME_CAUSE: "Influencia só {y}.",
        Role.TREATMENT_CAUSE: "Influencia só {t}.",
        Role.UNRELATED: "Não tem relação com {t} nem com {y}.",
    },
    "en": {
        Role.CONFOUNDER: "It influences {t} and it influences {y}.",
        Role.MEDIATOR: "It is a consequence of {t} and it influences {y}: it is part of the effect.",
        Role.COLLIDER: "It is a consequence of {t} and of {y}.",
        Role.OUTCOME_CAUSE: "It influences only {y}.",
        Role.TREATMENT_CAUSE: "It influences only {t}.",
        Role.UNRELATED: "It is related to neither {t} nor {y}.",
    },
    "es": {
        Role.CONFOUNDER: "Influye en {t} e influye en {y}.",
        Role.MEDIATOR: "Es consecuencia de {t} e influye en {y}: forma parte del efecto.",
        Role.COLLIDER: "Es consecuencia de {t} y de {y}.",
        Role.OUTCOME_CAUSE: "Influye solo en {y}.",
        Role.TREATMENT_CAUSE: "Influye solo en {t}.",
        Role.UNRELATED: "No tiene relación con {t} ni con {y}.",
    },
    "fr": {
        Role.CONFOUNDER: "Elle influence {t} et elle influence {y}.",
        Role.MEDIATOR: "C'est une conséquence de {t} et elle influence {y} : elle fait partie de l'effet.",
        Role.COLLIDER: "C'est une conséquence de {t} et de {y}.",
        Role.OUTCOME_CAUSE: "Elle n'influence que {y}.",
        Role.TREATMENT_CAUSE: "Elle n'influence que {t}.",
        Role.UNRELATED: "Elle n'a de lien ni avec {t} ni avec {y}.",
    },
    "de": {
        Role.CONFOUNDER: "Beeinflusst {t} und beeinflusst {y}.",
        Role.MEDIATOR: "Ist eine Folge von {t} und beeinflusst {y}: gehört zum Effekt.",
        Role.COLLIDER: "Ist eine Folge von {t} und von {y}.",
        Role.OUTCOME_CAUSE: "Beeinflusst nur {y}.",
        Role.TREATMENT_CAUSE: "Beeinflusst nur {t}.",
        Role.UNRELATED: "Hat weder mit {t} noch mit {y} zu tun.",
    },
}
ASSUMPTIONS = {
    "pt": (
        "Nada além do que foi descrito influencia ao mesmo tempo {t} e {y}.",
        "A história diz corretamente o que veio antes e o que veio depois de {t}.",
    ),
    "en": (
        "Nothing other than what was described influences both {t} and {y}.",
        "The story says correctly what came before and what came after {t}.",
    ),
    "es": (
        "Nada más que lo descrito influye a la vez en {t} y en {y}.",
        "La historia dice correctamente qué ocurrió antes y qué ocurrió después de {t}.",
    ),
    "fr": (
        "Rien d'autre que ce qui a été décrit n'influence à la fois {t} et {y}.",
        "L'histoire dit correctement ce qui s'est passé avant et ce qui s'est passé après {t}.",
    ),
    "de": (
        "Nichts außer dem Beschriebenen beeinflusst zugleich {t} und {y}.",
        "Die Geschichte gibt richtig an, was vor und was nach {t} geschah.",
    ),
}


def ideal_answer(world: World, theory: Theory) -> Answer:
    """The answer the answer key gives to a world, in the format asked of a model."""
    if theory.id != world.theory_id or theory.language != world.language:
        raise ValueError("the theory must be the one the world was made from, in the same language")
    names = {"t": world.problem.treatment, "y": world.problem.outcome}
    role_of = {piece.variable: piece.role for piece in world.structure.pieces if not piece.hidden}
    roles = tuple(
        ColumnRole(column, ROLE_NAME[role_of[column]], REASON[world.language][role_of[column]].format(**names))
        for column in world.table.columns
        if column in role_of
    )
    # What the table lacks is the hidden confounders; a hidden variable of another kind does no harm.
    lacking = world.truth.missing or ()
    return Answer(
        identifiable=world.truth.identifiable,
        adjustment_set=frozenset(world.truth.adjustment_set or ()),
        roles=roles,
        missing=tuple(theory.variables[name].label for name in lacking),
        assumptions=tuple(text.format(**names) for text in ASSUMPTIONS[world.language]),
        complete=True,
    )


# A consequence of the treatment that influences nothing else has no role of its own in
# the cards; it gets this reason.
CHILD_OF_TREATMENT = {
    "pt": "É consequência de {t} e não influencia {y}.",
    "en": "It is a consequence of {t} and it does not influence {y}.",
    "es": "Es consecuencia de {t} y no influye en {y}.",
    "fr": "C'est une conséquence de {t} et elle n'influence pas {y}.",
    "de": "Ist eine Folge von {t} und beeinflusst {y} nicht.",
}


def role_in_graph(problem: CausalProblem, column: str) -> Role | None:
    """The role a column plays, read off the graph alone (for cases that come without a structure).

    ``None`` is a consequence of the treatment that leads nowhere: harmless, like the
    neutral roles, but with no place among the roles of the cards.
    """
    graph, t, y = problem.graph, problem.treatment, problem.outcome
    without_t = graph.copy()
    without_t.remove_node(t)
    after_t = column in nx.descendants(graph, t)
    before_t = column in nx.ancestors(graph, t)
    # Influence on the outcome that does not pass through the treatment.
    before_y = column in nx.ancestors(without_t, y)
    if after_t and before_y:
        return Role.MEDIATOR
    if after_t:
        # A consequence of the treatment that is also a consequence of the outcome, or of
        # another cause of the outcome, is a collider.
        other_parents = set(graph.predecessors(column)) - {t}
        causes_of_y = nx.ancestors(without_t, y) | {y}
        collider = column in nx.descendants(graph, y) or any(parent in causes_of_y for parent in other_parents)
        return Role.COLLIDER if collider else None
    if before_t and before_y:
        return Role.CONFOUNDER
    if before_t:
        return Role.TREATMENT_CAUSE
    if before_y:
        return Role.OUTCOME_CAUSE
    return Role.UNRELATED


def ideal_answer_for_case(case: WrittenCase) -> Answer:
    """The answer the verifier gives to a written case, in the format asked of a model."""
    problem = case.problem
    names = {"t": problem.treatment, "y": problem.outcome}
    language = case.language if case.language in REASON else "en"
    roles = []
    for column in case.columns:
        if column in (problem.treatment, problem.outcome):
            continue
        role = role_in_graph(problem, column)
        if role is None:
            roles.append(ColumnRole(column, "neutral", CHILD_OF_TREATMENT[language].format(**names)))
        else:
            roles.append(ColumnRole(column, ROLE_NAME[role], REASON[language][role].format(**names)))
    verdict = identify(problem)
    return Answer(
        identifiable=verdict.identifiable,
        adjustment_set=frozenset(verdict.adjustment_set or ()),
        roles=tuple(roles),
        missing=tuple(name.replace("_", " ") for name in sorted(verdict.missing or ())),
        assumptions=tuple(text.format(**names) for text in ASSUMPTIONS[language]),
        complete=True,
    )
