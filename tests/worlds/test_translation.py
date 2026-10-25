"""Translations of the theory cards: only the words change, and the stories still work."""

from __future__ import annotations

import pytest
import yaml

from causalista.worlds import LANGUAGES, generate_pair, load_theory, retell
from causalista.worlds.narrative import QUESTION, ROLE_WORDS, facts_of
from causalista.worlds.theory import THEORIES_DIR, InvalidTheoryError, Theory, translate_theory

TELECOM = load_theory("telecom")
TRANSLATIONS = sorted(
    (path.parent.name, path.stem) for path in (THEORIES_DIR / "i18n").glob("*/*.yaml")
)


def _mirror(theory: Theory, language: str = "en") -> dict:
    """A translation that mirrors a card: every text marked with the language."""

    def said(text: str) -> str:
        return f"[{language}] {text}"

    return {
        "language": language,
        "status": "revisada",
        "title": said(theory.title),
        "context": said(theory.context),
        "randomized": said(theory.randomized),
        "closing": said(theory.closing),
        "treatment": {"label": said(theory.treatment.label), "dictionary": said(theory.treatment.dictionary)},
        "outcome": {"label": said(theory.outcome.label), "dictionary": said(theory.outcome.dictionary)},
        "variables": {
            name: {
                "label": said(variable.label),
                **({"hidden_fact": said(variable.hidden_fact)} if variable.hidden_fact else {}),
                "roles": {
                    role.value: {
                        "dictionary": said(spec.dictionary),
                        **{link: said(given.fact) for link, given in spec.links.items()},
                        **({"fact": said(spec.fact)} if spec.fact else {}),
                    }
                    for role, spec in variable.roles.items()
                },
            }
            for name, variable in theory.variables.items()
        },
    }


def test_a_translation_changes_the_words_and_nothing_else() -> None:
    translated = translate_theory(TELECOM, _mirror(TELECOM))
    assert translated.language == "en" and translated.id == TELECOM.id
    assert translated.approved, "an approved card with a reviewed translation may be used for training"
    draft = translate_theory(TELECOM, {**_mirror(TELECOM), "status": "rascunho"})
    assert not draft.approved, "a translation nobody has read may not"
    assert translated.effect_sign == TELECOM.effect_sign
    assert translated.treatment.column == TELECOM.treatment.column
    assert translated.context == f"[en] {TELECOM.context}"
    for name, variable in TELECOM.variables.items():
        there = translated.variables[name]
        assert (there.kind, there.scale, there.hideable) == (variable.kind, variable.scale, variable.hideable)
        assert set(there.roles) == set(variable.roles)
        for role, spec in variable.roles.items():
            for link, given in spec.links.items():
                assert there.roles[role].links[link].sign == given.sign
                assert there.roles[role].links[link].fact == f"[en] {given.fact}"


def test_a_translation_that_does_not_mirror_the_card_is_refused() -> None:
    card = _mirror(TELECOM)
    del card["variables"]["renda"]
    with pytest.raises(InvalidTheoryError, match="missing keys"):
        translate_theory(TELECOM, card)

    card = _mirror(TELECOM)
    del card["variables"]["renda"]["roles"]["confounder"]["to_outcome"]
    with pytest.raises(InvalidTheoryError, match="missing keys"):
        translate_theory(TELECOM, card)

    card = _mirror(TELECOM)
    card["variables"]["renda"]["roles"]["mediator"] = {"dictionary": "x"}
    with pytest.raises(InvalidTheoryError, match="unknown keys"):
        translate_theory(TELECOM, card)

    with pytest.raises(InvalidTheoryError, match="unknown language"):
        translate_theory(TELECOM, _mirror(TELECOM, "pt"))
    with pytest.raises(InvalidTheoryError, match="unknown language"):
        translate_theory(TELECOM, _mirror(TELECOM, "xx"))


def test_the_same_world_told_in_another_language() -> None:
    translated = translate_theory(TELECOM, _mirror(TELECOM))
    for seed in range(4):
        for world in generate_pair(TELECOM, seed):
            if world is None:
                continue
            told = retell(world, translated)
            assert told.language == "en" and told.name == f"{world.id}.en1"
            assert told.truth == world.truth and told.table is world.table and told.structure == world.structure
            assert told.question == QUESTION["en"].format(treatment="oferta", outcome="cancelou")
            # The same facts, in the same order, in the other language.
            assert told.narrative.startswith("[en] ")
            assert told.narrative.count("[en] ") == world.narrative.count(". ") + 1 or "[en] " in told.narrative
            for entry, original in zip(told.dictionary, world.dictionary, strict=True):
                assert entry.column == original.column
                assert entry.description == f"[en] {original.description}"


def test_every_language_has_a_question() -> None:
    assert set(QUESTION) == set(LANGUAGES)


# -- the translations that exist in theories/i18n ----------------------------------


@pytest.mark.parametrize(("language", "theory_id"), TRANSLATIONS)
def test_a_translation_file_mirrors_its_card(language: str, theory_id: str) -> None:
    translated = load_theory(theory_id, language)
    original = load_theory(theory_id)
    assert translated.language == language
    shown = [translated.context, translated.randomized, translated.closing]
    for name, variable in translated.variables.items():
        assert variable.label and (variable.hidden_fact is not None) == original.variables[name].hideable
        for spec in variable.roles.values():
            shown += [spec.dictionary, *(link.fact for link in spec.links.values())]
    text = " ".join(shown).lower()
    assert not any(word in text for word in ROLE_WORDS)
    assert "= sim" not in text and "= não" not in text, "a note left in Portuguese"
    raw = yaml.safe_load((THEORIES_DIR / "i18n" / language / f"{theory_id}.yaml").read_text(encoding="utf-8"))
    assert all(isinstance(value, str) and value.strip() for value in (raw["title"], raw["context"]))


@pytest.mark.parametrize(("language", "theory_id"), TRANSLATIONS)
def test_a_translated_story_tells_every_fact_once(language: str, theory_id: str) -> None:
    translated = load_theory(theory_id, language)
    for seed in range(40):
        for world in generate_pair(translated, seed) if seed < 2 else ():
            if world is None:
                continue
            for piece in world.structure.pieces:
                for sentence in facts_of(translated, world.structure)[piece.variable]:
                    assert world.narrative.count(sentence) == 1
    # Without building whole worlds: no sentence of the card may be contained in another.
    sentences = {
        link.fact
        for variable in translated.variables.values()
        for spec in variable.roles.values()
        for link in spec.links.values()
    } | {v.hidden_fact for v in translated.variables.values() if v.hidden_fact}
    for sentence in sentences:
        assert not any(sentence in other and sentence != other for other in sentences), sentence
