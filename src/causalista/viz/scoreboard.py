"""The scoreboard page: where each model and each reference stands.

The page is built from the records of the harness and from nothing else: every bar and
every number on it is a count over recorded answers.

    uv run python -m causalista.viz.scoreboard --set placar-base              # outputs/viz/placar.html
    uv run python -m causalista.viz.scoreboard --set placar-base --fragment   # the form used for publishing
"""

from __future__ import annotations

import argparse
import html
import json
from datetime import date
from importlib import resources
from pathlib import Path

from causalista.task import SCORE, Outcome
from causalista.viz.gallery import _STANDALONE
from causalista.worlds import Kind, load_theory
from causalista.worlds.theory import THEORIES_DIR

RUNS = Path("outputs/runs")
DEFAULT_OUTPUT = Path("outputs/viz/placar.html")
# The order of the segments of a bar, from good to bad; the page uses the same order.
OUTCOME_CODE = {
    Outcome.CORRECT.value: 0,
    Outcome.UNDUE_ABSTENTION.value: 1,
    Outcome.CONFIDENT_ERROR.value: 2,
    Outcome.INVALID.value: 3,
}
REFERENCES = ("ajusta tudo", "ajusta nada")
THEME_NAME = {
    "telecom": "Telecom",
    "varejo": "Varejo",
    "banco": "Banco",
    "software": "Software por assinatura",
    "rh": "RH",
    "educacao": "Educação",
    "saude": "Saúde suplementar",
    "email": "E-mail marketing",
}
LANGUAGE_NAME = {"pt": "português", "en": "inglês", "es": "espanhol", "fr": "francês", "de": "alemão"}
LEVEL_NAME = {1: "um fato por frase", 2: "prosa corrida", 3: "escrita por pessoa"}


def load_runs(folder: Path) -> dict[str, list[dict]]:
    """The records of every responder that ran on a set of worlds, by label."""
    runs: dict[str, list[dict]] = {}
    for file in sorted(folder.glob("*.jsonl")):
        records = [json.loads(line) for line in file.read_text(encoding="utf-8").splitlines() if line.strip()]
        if records:
            runs.setdefault(records[0]["model"], []).extend(records)
    return runs


def scoreboard_payload(runs: dict[str, list[dict]], *, source: str) -> dict:
    """Everything the page needs: the worlds, and for each model one short row per answer."""
    worlds: dict[str, list] = {}
    for records in runs.values():
        for record in records:
            worlds.setdefault(
                record["world"],
                [record["world"], record["theory"], record["language"], record["level"], record["world_identifiable"]],
            )
    index = {name: position for position, name in enumerate(sorted(worlds))}

    models = []
    for label, records in runs.items():
        rows = []
        for record in records:
            estimate = record["estimate"]
            covers = None if estimate is None else int(estimate["low"] <= record["true_effect"] <= estimate["high"])
            error = None if estimate is None else round(abs(estimate["effect"] - record["true_effect"]), 5)
            roles = None if record["roles_right"] is None else round(record["roles_right"], 3)
            rows.append([index[record["world"]], OUTCOME_CODE[record["outcome"]], covers, error, roles])
        # A base with an adapter on top is labelled "<base> + <run>/<point>" by the harness.
        models.append({"label": label, "reference": label in REFERENCES, "trained": " + " in label, "records": rows})

    themes = {}
    for theory_id in sorted({world[1] for world in worlds.values()}):
        if (THEORIES_DIR / f"{theory_id}.yaml").exists():
            binary = load_theory(theory_id).outcome.kind is Kind.BINARY
            themes[theory_id] = {"name": THEME_NAME.get(theory_id, theory_id), "unit": "pp" if binary else "nota"}
        else:  # written cases carry no theory card and no runner estimate
            themes[theory_id] = {"name": theory_id, "unit": "pp"}
    answers = sum(len(records) for records in runs.values())
    return {
        "worlds": [worlds[name] for name in sorted(worlds)],
        "models": models,
        "themes": themes,
        "languages": LANGUAGE_NAME,
        "levels": LEVEL_NAME,
        "scores": [SCORE[Outcome(name)] for name, _ in sorted(OUTCOME_CODE.items(), key=lambda item: item[1])],
        "colophon": (
            f"Gerado em {date.today().strftime('%d/%m/%Y')} a partir de {answers} respostas gravadas em {source}. "
            "A nota de cada resposta foi dada pelo verificador do Causalista, e o efeito foi calculado pelo runner."
        ),
    }


def render(set_name: str, *, standalone: bool = True) -> str:
    runs = load_runs(RUNS / set_name)
    if not runs:
        raise SystemExit(f"no records under {RUNS / set_name}")
    payload = scoreboard_payload(runs, source=str(RUNS / set_name))
    worlds = len({world[0].split(".")[0] for world in payload["worlds"]})  # tellings of a world count once
    words = {
        "__TITLE__": "Placar do Causalista",
        "__EYEBROW__": "Causalista · placar",
        "__HEADING__": "Onde está cada modelo?",
        "__LEDE__": (
            f"Cada modelo recebeu os mesmos {worlds} mundos, com a mesma pergunta: por quais colunas ajustar, "
            "ou dizer que os dados não permitem concluir. A barra mostra o que aconteceu com as respostas."
        ),
    }
    template = resources.files("causalista.viz").joinpath("scoreboard.html").read_text(encoding="utf-8")
    for marker, value in words.items():
        if template.count(marker) != 1:
            raise RuntimeError(f"scoreboard.html must contain {marker} exactly once")
        template = template.replace(marker, html.escape(value))
    # "</" must not appear inside a <script> block; "<\/" means the same in JSON.
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    if template.count("/*__DATA__*/") != 1:
        raise RuntimeError("scoreboard.html must contain the data marker exactly once")
    fragment = template.replace("/*__DATA__*/", data)
    return _STANDALONE.format(fragment=fragment) if standalone else fragment


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the scoreboard page.")
    parser.add_argument("--set", required=True, help="name of a set of worlds with records under outputs/runs")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fragment", action="store_true", help="write the page without the <html> wrapper")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(args.set, standalone=not args.fragment), encoding="utf-8")
    print(f"wrote {args.out} ({args.out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
