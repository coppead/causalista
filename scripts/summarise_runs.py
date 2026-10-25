"""Print the scoreboard of a saved set of runs, broken down by language and by kind of telling.

    uv run python scripts/summarise_runs.py --set teste-v3
    uv run python scripts/summarise_runs.py --set placar-v3 --markdown

Reads outputs/runs/<set>/*.jsonl, one file per responder, and applies the metrics of section 7
of the specification (causalista.harness.summarise) to the records of each language and level.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from causalista.harness import summarise
from causalista.viz.scoreboard import load_runs

ROOT = Path(__file__).resolve().parents[1]
LEVEL = {1: "um fato por frase", 2: "prosa"}
LANGUAGE = {"pt": "português", "en": "inglês", "es": "espanhol"}


def pct(x: float | None) -> str:
    return "-" if x is None else f"{100 * x:.0f}%"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", required=True, help="folder under outputs/runs")
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args()

    runs = load_runs(ROOT / "outputs" / "runs" / args.set)
    header = ("respondedor", "história", "idioma", "mundos", "nota", "acerto", "erro conf.", "abst. indevida", "inválida", "acerto nos não ident.")
    rows: list[tuple] = []
    for model, records in sorted(runs.items()):
        groups = sorted({(r["level"], r["language"]) for r in records})
        for level, language in groups:
            part = [r for r in records if r["level"] == level and r["language"] == language]
            s = summarise(part)
            rows.append((model, LEVEL.get(level, str(level)), LANGUAGE.get(language, language), s["worlds"], f"{s['score']:+.2f}",
                         pct(s["correct"]), pct(s["confident_error"]), pct(s["undue_abstention"]), pct(s["invalid"]),
                         pct(s["correct_when_not_identifiable"])))
        s = summarise(records)
        rows.append((model, "todas", "todos", s["worlds"], f"{s['score']:+.2f}", pct(s["correct"]), pct(s["confident_error"]),
                     pct(s["undue_abstention"]), pct(s["invalid"]), pct(s["correct_when_not_identifiable"])))
    if args.markdown:
        print("| " + " | ".join(header) + " |")
        print("|" + "---|" * len(header))
        for row in rows:
            print("| " + " | ".join(str(c) for c in row) + " |")
    else:
        widths = [max(len(str(x)) for x in col) for col in zip(header, *rows)]
        for row in (header, *rows):
            print("  ".join(str(c).ljust(w) for c, w in zip(row, widths)))


if __name__ == "__main__":
    main()
