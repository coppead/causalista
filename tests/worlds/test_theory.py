"""A theory card must be complete and coherent, or it is refused."""

from __future__ import annotations

import copy

import pytest

from causalista.worlds.theory import (
    LINKS_OF_ROLE,
    InvalidTheoryError,
    Kind,
    Role,
    Theory,
    load_theory,
    parse_theory,
)

MINIMAL = {
    "id": "tema",
    "status": "rascunho",
    "title": "Um tema",
    "theory": {"name": "Uma teoria", "statement": "O que ela afirma."},
    "context": "Uma empresa quer saber se a ação muda o resultado.",
    "randomized": "A ação foi sorteada.",
    "closing": "Nada mais influenciou a ação.",
    "treatment": {"column": "acao", "label": "a ação", "dictionary": "Recebeu a ação.", "share": [0.2, 0.5]},
    "outcome": {
        "column": "resultado",
        "label": "o resultado",
        "kind": "binary",
        "dictionary": "Teve o resultado.",
        "scale": {"rate": [0.1, 0.3]},
    },
    "effect": {"sign": "-"},
    "variables": {
        "idade": {
            "label": "a idade",
            "kind": "count",
            "scale": {"mean": 40},
            "hidden_fact": "A idade não está na tabela.",
            "roles": {
                "confounder": {
                    "dictionary": "Idade em anos.",
                    "to_treatment": {"sign": "+", "fact": "Os mais velhos recebem mais a ação."},
                    "to_outcome": {"sign": "-", "fact": "Os mais velhos têm menos o resultado."},
                }
            },
        }
    },
}


def _card(**changes):
    card = copy.deepcopy(MINIMAL)
    card.update(changes)
    return card


def test_minimal_card_is_accepted() -> None:
    theory = parse_theory(MINIMAL)
    assert theory.treatment.column == "acao"
    assert theory.effect_sign == -1
    variable = theory.variables["idade"]
    assert variable.kind is Kind.COUNT
    assert variable.hideable
    links = variable.roles[Role.CONFOUNDER].links
    assert links["to_treatment"].sign == 1 and links["to_outcome"].sign == -1
    assert not theory.approved


def test_telecom_card_loads() -> None:
    assert load_theory("telecom").name == "Custo de troca"


def test_every_card_is_rich_enough(theory: Theory) -> None:
    assert len(theory.variables) >= 10
    roles = {role for variable in theory.variables.values() for role in variable.roles}
    assert roles == set(Role), "every kind of piece must be available in the theme"
    assert sum(variable.hideable for variable in theory.variables.values()) >= 2
    # Several variables can play more than one role: that is what makes the role variable.
    assert sum(len(variable.roles) > 1 for variable in theory.variables.values()) >= 6
    for variable in theory.variables.values():
        for role, spec in variable.roles.items():
            assert set(spec.links) == set(LINKS_OF_ROLE[role])


def test_missing_and_unknown_keys_are_refused() -> None:
    card = _card()
    del card["closing"]
    with pytest.raises(InvalidTheoryError, match="missing keys"):
        parse_theory(card)
    with pytest.raises(InvalidTheoryError, match="unknown keys"):
        parse_theory(_card(extra="?"))


def test_a_sign_must_be_plus_or_minus() -> None:
    card = _card()
    card["variables"]["idade"]["roles"]["confounder"]["to_outcome"]["sign"] = "positivo"
    with pytest.raises(InvalidTheoryError, match="sign must be"):
        parse_theory(card)


def test_a_role_must_have_exactly_its_links() -> None:
    card = _card()
    del card["variables"]["idade"]["roles"]["confounder"]["to_treatment"]
    with pytest.raises(InvalidTheoryError, match="missing keys"):
        parse_theory(card)

    card = _card()
    card["variables"]["idade"]["roles"]["confounder"]["from_outcome"] = {"sign": "+", "fact": "x"}
    with pytest.raises(InvalidTheoryError, match="unknown keys"):
        parse_theory(card)


def test_unknown_role_or_kind_is_refused() -> None:
    card = _card()
    card["variables"]["idade"]["roles"]["instrumento"] = {"dictionary": "x"}
    with pytest.raises(InvalidTheoryError, match="unknown role"):
        parse_theory(card)

    card = _card()
    card["variables"]["idade"]["kind"] = "texto"
    with pytest.raises(InvalidTheoryError, match="unknown kind"):
        parse_theory(card)


def test_only_a_possible_confounder_can_be_hidden() -> None:
    card = _card()
    card["variables"]["idade"]["roles"] = {
        "outcome_cause": {
            "dictionary": "Idade em anos.",
            "to_outcome": {"sign": "-", "fact": "Os mais velhos têm menos o resultado."},
        }
    }
    with pytest.raises(InvalidTheoryError, match="hidden_fact"):
        parse_theory(card)


def test_names_must_be_plain_and_distinct() -> None:
    card = _card()
    card["variables"]["Idade do cliente"] = card["variables"].pop("idade")
    with pytest.raises(InvalidTheoryError, match="column name"):
        parse_theory(card)

    card = _card()
    card["variables"]["acao"] = card["variables"].pop("idade")
    with pytest.raises(InvalidTheoryError, match="different names"):
        parse_theory(card)


def test_text_that_yaml_did_not_read_as_text_is_refused() -> None:
    # A reference with ": " in it becomes a mapping in YAML unless it is quoted.
    card = _card()
    card["theory"]["references"] = [{"Autor (2003). Título": "subtítulo."}]
    with pytest.raises(InvalidTheoryError, match="expected a non-empty text"):
        parse_theory(card)


def test_a_mediator_must_carry_the_effect_in_the_direction_of_the_theory() -> None:
    card = _card()
    card["variables"]["idade"]["roles"]["mediator"] = {
        "dictionary": "Idade em anos, depois da ação.",
        "from_treatment": {"sign": "+", "fact": "A ação aumenta a idade."},
        "to_outcome": {"sign": "+", "fact": "Os mais velhos têm mais o resultado."},
    }
    with pytest.raises(InvalidTheoryError, match="direction of effect.sign"):
        parse_theory(card)
    card["variables"]["idade"]["roles"]["mediator"]["to_outcome"]["sign"] = "-"
    parse_theory(card)
