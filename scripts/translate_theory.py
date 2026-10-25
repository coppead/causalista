"""Translate a theory card with a local open model, and have a second open model check it.

    uv run python scripts/translate_theory.py --theory telecom --language en

The card (Portuguese) is the source of truth. The translation carries only words: labels,
column descriptions and sentences. One model translates; another, of a different family,
reads each pair of sentences and says whether they state the same fact, with the same
direction and the same timing. A sentence that fails is translated again with the
objection; if it fails twice, the file is still written and the sentence is listed, so
that a person fixes it by hand.

Both models must be open (Apache 2.0): the sentences end up in training stories.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import date

import yaml

from causalista.worlds.narrative import ROLE_WORDS
from causalista.worlds.theory import THEORIES_DIR, Theory, load_theory, translate_theory

LANGUAGE_NAME = {"en": "English", "es": "Spanish", "fr": "French", "de": "German"}
LANGUAGE_NAME_PT = {"en": "inglês", "es": "espanhol", "fr": "francês", "de": "alemão"}
# The note that explains a yes-or-no column. Models sometimes leave it in Portuguese.
YES_NO = {
    "en": "(1 = yes, 0 = no)",
    "es": "(1 = sí, 0 = no)",
    "fr": "(1 = oui, 0 = non)",
    "de": "(1 = ja, 0 = nein)",
}

RULES = """\
Rules:
- Translate the meaning exactly. Do not add, drop or soften anything.
- Keep who acts on whom, the direction (more or less, higher or lower) and the timing \
(before or after, and the number of days or months).
- Each sentence must stand alone: name its subject, never "it" or "they" for something \
said in another sentence.
- Plain business language, the way a manager would say it. No technical vocabulary of \
statistics or causal inference.
- Use the given terms for the things that have one, and one word for each thing \
throughout (always "customers", never "clients" in one sentence and "customers" in another).
- Do not let a word change meaning. "Clientes antigos" are customers who have been with the \
company for longer (long-standing customers), not customers who are older in age.
- A sentence that starts with "Quem" is about the people of the situation: say who they are \
(customers, employees, students, patients, companies), as in "Customers who ...".
- "(1 = sim, 0 = não)" becomes the same note in {language}. Amounts in reais stay in reais."""

TRANSLATE = """\
You are translating, from Brazilian Portuguese into {language}, the texts that describe \
a business situation: {title}

{rules}

{glossary}Translate each of the texts below. Answer with one JSON object that maps each \
key to its translation, and nothing else.

{texts}"""

JUDGE = """\
Original (Brazilian Portuguese): {original}
Translation ({language}): {translation}

Does the translation state exactly the same thing as the original? It must have the same \
subject, the same direction (more or less, higher or lower) and the same timing (before or \
after, the same number of days or months), with nothing added and nothing left out. \
Differences of style or word order do not matter, and naming the people that "quem" refers \
to (for example "customers who ...") is not a difference.

Answer with one JSON object and nothing else: {{"same": true or false, "problem": "<what \
differs, in at most 12 words; empty if same>"}}"""


def chat(model: str, prompt: str, host: str) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "format": "json",
        "keep_alive": "30m",
        "options": {"temperature": 0, "seed": 0, "num_predict": 4096, "num_ctx": 12288},
    }
    request = urllib.request.Request(
        f"{host}/api/chat", data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=900) as response:
        content = json.loads(response.read().decode("utf-8"))["message"]["content"]
    try:
        answer = json.loads(content)
    except json.JSONDecodeError:
        return {}  # treated as "nothing came back": the texts are asked again
    return answer if isinstance(answer, dict) else {}


def frame_of(theory: Theory) -> dict[str, str]:
    """The texts that set the scene and the vocabulary."""
    texts = {
        "title": theory.title,
        "context": theory.context,
        "randomized": theory.randomized,
        "closing": theory.closing,
        "treatment.label": theory.treatment.label,
        "treatment.dictionary": theory.treatment.dictionary,
        "outcome.label": theory.outcome.label,
        "outcome.dictionary": theory.outcome.dictionary,
    }
    texts.update({f"label.{name}": variable.label for name, variable in theory.variables.items()})
    return texts


def texts_of_variable(theory: Theory, name: str) -> dict[str, str]:
    """Every sentence of one variable, with a key that says where it goes."""
    variable = theory.variables[name]
    texts = {}
    if variable.hidden_fact:
        texts["hidden_fact"] = variable.hidden_fact
    for role, spec in variable.roles.items():
        texts[f"{role.value}.dictionary"] = spec.dictionary
        for link, given in spec.links.items():
            texts[f"{role.value}.{link}"] = given.fact
        if spec.fact:
            texts[f"{role.value}.fact"] = spec.fact
    return texts


def ask(texts: dict[str, str], *, theory: Theory, language: str, glossary: dict[str, str],
        objections: dict[str, str], translator: str, host: str) -> dict[str, str]:  # fmt: skip
    """Translate a set of texts. The same Portuguese text always gets the same translation."""
    unique = {text: f"t{index}" for index, text in enumerate(dict.fromkeys(texts.values()))}
    name = LANGUAGE_NAME[language]
    terms = "".join(f'- "{pt}" is "{there}"\n' for pt, there in glossary.items() if pt != "")
    glossary_text = f"The situation, already translated: {glossary['']}\n\n" if "" in glossary else ""
    glossary_text += f"Terms already translated:\n{terms}\n" if terms else ""
    refused = {text: why for key, why in objections.items() if (text := texts.get(key))}
    listed = "\n".join(
        f'"{key}": {json.dumps(text, ensure_ascii=False)}'
        + (f"   (a previous translation was refused: {refused[text]})" if text in refused else "")
        for text, key in unique.items()
    )
    prompt = TRANSLATE.format(
        language=name, title=theory.title, rules=RULES.format(language=name), glossary=glossary_text, texts=listed
    )
    answer = chat(translator, prompt, host)

    def tidy(text: str) -> str:
        return " ".join(text.split()).replace("(1 = sim, 0 = não)", YES_NO[language])

    return {key: tidy(str(answer.get(unique[text]) or "")) for key, text in texts.items()}


def check(texts: dict[str, str], done: dict[str, str], *, language: str, judge: str, host: str) -> dict[str, str]:
    """Have the second model compare each translation with its original. Returns the objections by key."""
    verdicts: dict[tuple[str, str], str | None] = {}
    refused = {}
    for key, original in texts.items():
        pair = (original, done[key])
        if pair not in verdicts:
            if not done[key]:
                verdicts[pair] = "no translation came back"
            else:
                # One pair per call: with several at once, a small model compares across pairs.
                prompt = JUDGE.format(language=LANGUAGE_NAME[language], original=original, translation=done[key])
                verdict = chat(judge, prompt, host)
                same = verdict.get("same") is True
                verdicts[pair] = None if same else str(verdict.get("problem") or "the checker gave no verdict")
        if verdicts[pair] is not None:
            refused[key] = verdicts[pair]
    return refused


def translate_card(theory: Theory, language: str, *, translator: str, judge: str, host: str) -> tuple[dict, dict]:
    """Translate a whole card. The work goes in phases, so that the two models are not swapped at every call."""
    groups = {"frame": frame_of(theory)}
    groups.update({name: texts_of_variable(theory, name) for name in theory.variables})
    settings = {"theory": theory, "language": language, "translator": translator, "host": host}

    def glossary_from(frame: dict[str, str]) -> dict[str, str]:
        return {
            "": frame["context"],
            theory.treatment.label: frame["treatment.label"],
            theory.outcome.label: frame["outcome.label"],
            **{variable.label: frame[f"label.{name}"] for name, variable in theory.variables.items()},
        }

    done = {"frame": ask(groups["frame"], glossary={}, objections={}, **settings)}
    glossary = glossary_from(done["frame"])
    for name in theory.variables:
        done[name] = ask(groups[name], glossary=glossary, objections={}, **settings)
    print("  translated", flush=True)

    objections = {
        group: check(texts, done[group], language=language, judge=judge, host=host) for group, texts in groups.items()
    }
    print(f"  checked: {sum(map(len, objections.values()))} refused", flush=True)

    for group, refused in objections.items():
        if refused:
            again = {key: groups[group][key] for key in refused}
            fixed = ask(again, glossary={} if group == "frame" else glossary, objections=refused, **settings)
            done[group].update({key: text for key, text in fixed.items() if text})
    glossary = glossary_from(done["frame"])
    problems = {}
    for group, refused in objections.items():
        if refused:
            again = {key: groups[group][key] for key in refused}
            still = check(again, done[group], language=language, judge=judge, host=host)
            problems.update({f"{group}.{key}": why for key, why in still.items()})
    print(f"  checked again: {len(problems)} still refused", flush=True)

    frame = done["frame"]
    variables = {}
    for name, variable in theory.variables.items():
        words = done[name]
        entry: dict = {"label": frame[f"label.{name}"]}
        if variable.hidden_fact:
            entry["hidden_fact"] = words["hidden_fact"]
        entry["roles"] = {}
        for role, spec in variable.roles.items():
            said = {"dictionary": words[f"{role.value}.dictionary"]}
            said.update({link: words[f"{role.value}.{link}"] for link in spec.links})
            if spec.fact:
                said["fact"] = words[f"{role.value}.fact"]
            entry["roles"][role.value] = said
        variables[name] = entry

    card = {
        "language": language,
        "status": "rascunho",
        "title": frame["title"],
        "context": frame["context"],
        "randomized": frame["randomized"],
        "closing": frame["closing"],
        "treatment": {"label": frame["treatment.label"], "dictionary": frame["treatment.dictionary"]},
        "outcome": {"label": frame["outcome.label"], "dictionary": frame["outcome.dictionary"]},
        "variables": variables,
    }
    return card, problems


def structural_problems(theory: Theory, card: dict) -> list[str]:
    """What no checker model is needed for: role words, and sentences that would collide in a story."""
    translated = translate_theory(theory, card)
    found = []
    sentences: dict[str, str] = {}
    for name, variable in translated.variables.items():
        for role, spec in variable.roles.items():
            for text in [link.fact for link in spec.links.values()] + ([spec.fact] if spec.fact else []):
                sentences.setdefault(text, f"{name}.{role.value}")
        if variable.hidden_fact:
            sentences.setdefault(variable.hidden_fact, f"{name}.hidden_fact")
    original = {
        link.fact
        for variable in theory.variables.values()
        for spec in variable.roles.values()
        for link in spec.links.values()
    }
    if len(sentences) < len(original):
        found.append("two different sentences of the card got the same translation")
    everything = [*sentences, translated.context, translated.closing, translated.randomized]
    for text, where in sentences.items():
        if any(text in other and text != other for other in everything):
            found.append(f"{where}: the sentence is contained in another one")
    shown = " ".join(
        [*everything, *(spec.dictionary for v in translated.variables.values() for spec in v.roles.values())]
    ).lower()
    found += [f"the word {word!r} gives a role away" for word in ROLE_WORDS if word in shown]
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--theory", nargs="+", required=True)
    parser.add_argument("--language", nargs="+", required=True, choices=sorted(LANGUAGE_NAME))
    parser.add_argument("--translator", default="qwen3.5:35b")
    parser.add_argument("--judge", default="granite4.1:30b")
    parser.add_argument("--host", default="http://localhost:11434")
    args = parser.parse_args()

    for language in args.language:
        for theory_id in args.theory:
            theory = load_theory(theory_id)
            print(f"{theory_id} -> {language}", flush=True)
            card, problems = translate_card(
                theory, language, translator=args.translator, judge=args.judge, host=args.host
            )
            try:
                problems.update({f"structure.{i}": why for i, why in enumerate(structural_problems(theory, card))})
            except Exception as error:  # a text that never came back: the file is written for a person to finish
                problems["structure"] = f"{type(error).__name__}: {error}"

            folder = THEORIES_DIR / "i18n" / language
            folder.mkdir(parents=True, exist_ok=True)
            header = (
                f"# Tradução da ficha de teoria {theory_id!r} para o {LANGUAGE_NAME_PT[language]}.\n"
                f"#\n"
                f"# Feita por um modelo aberto ({args.translator}) e conferida por outro ({args.judge}),\n"
                f"# em {date.today().isoformat()}, com scripts/translate_theory.py. A ficha em português,\n"
                f"# theories/{theory_id}.yaml, é a que vale: este arquivo só traz as palavras, e a sua\n"
                f"# estrutura tem de espelhar a da ficha.\n"
            )
            if problems:
                header += "#\n# FRASES QUE NÃO PASSARAM NA CONFERÊNCIA (corrigir à mão):\n"
                header += "".join(f"#   {where}: {why}\n" for where, why in problems.items())
            text = header + "\n" + yaml.safe_dump(card, allow_unicode=True, sort_keys=False, width=100)
            (folder / f"{theory_id}.yaml").write_text(text, encoding="utf-8")
            print(f"  written, {len(problems)} problems", flush=True)
            for where, why in problems.items():
                print(f"    {where}: {why}", flush=True)


if __name__ == "__main__":
    main()
