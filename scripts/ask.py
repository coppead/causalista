"""Ask Causalista about a table of your own.

    uv run --no-sync python scripts/ask.py --csv table.csv --treatment email --outcome bought \\
        --story story.txt --dictionary columns.yaml --model ollama:hf.co/coppead/causalista-4b-GGUF:nothink

The table is a CSV with one row per unit; the intervention column holds 0 and 1. The story is a text
(or a file) saying how the data were generated: who received the intervention and why, what was
measured before and after it, what is known not to be in the table. The dictionary gives one plain
sentence per column (a YAML or JSON mapping, or repeated --column NAME="description"). The model names
the columns to adjust for, or says the effect is not identifiable; when it asserts an effect, the
estimator computes it from the rows. Output in English, or in Portuguese with --lang pt.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import yaml

from causalista.harness.ask import ask, format_consultation
from causalista.harness.specs import responder_of


def text_or_file(value: str) -> str:
    path = Path(value)
    return path.read_text(encoding="utf-8").strip() if path.is_file() else value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    parser.add_argument("--csv", required=True, type=Path, help="the table, one row per unit")
    parser.add_argument("--treatment", required=True, help="the intervention column (0/1)")
    parser.add_argument("--outcome", required=True, help="the outcome column")
    parser.add_argument("--story", required=True, help="how the data were generated: a text, or a file with it")
    parser.add_argument("--dictionary", type=Path, help="YAML or JSON mapping each column to a one-sentence description")
    parser.add_argument("--column", action="append", default=[], metavar="NAME=DESCRIPTION", help="a column description, repeatable")
    parser.add_argument("--question", help='default: "What is the average effect of <treatment> on <outcome>?"')
    parser.add_argument("--model", default="ollama:hf.co/coppead/causalista-4b-GGUF:nothink", help="responder spec: ollama:<model>[:nothink], hf:<repository>[:nothink], rule:tudo, rule:nada")
    parser.add_argument("--host", default="http://localhost:11434", help="the Ollama server")
    parser.add_argument("--lang", default="pt" if os.environ.get("LANG", "").startswith("pt") else "en", help="language of the report: en or pt")
    parser.add_argument("--json", type=Path, help="also write the full record (task, raw answer, estimate) to this file")
    args = parser.parse_args()

    table = pd.read_csv(args.csv)
    descriptions = {}
    if args.dictionary:
        descriptions.update(yaml.safe_load(args.dictionary.read_text(encoding="utf-8")) or {})
    for item in args.column:
        name, _, description = item.partition("=")
        descriptions[name.strip()] = description.strip()
    try:
        result = ask(table, args.treatment, args.outcome, text_or_file(args.story), descriptions, responder_of(args.model, host=args.host), question=args.question)
    except ValueError as problem:
        sys.exit(f"cannot build the task: {problem}")
    print(format_consultation(result, args.lang))
    if args.json:
        record = {
            "prompt": __import__("causalista.task", fromlist=["build_prompt"]).build_prompt(result.task),
            "raw_answer": result.reply.text,
            "answer": asdict(result.answer) if result.answer else None,
            "error": result.error,
            "estimate": asdict(result.estimate) if result.estimate else None,
            "naive": asdict(result.naive) if result.naive else None,
            "ignored": list(result.ignored),
            "seconds": result.reply.seconds,
        }
        args.json.write_text(json.dumps(record, ensure_ascii=False, indent=1, default=list) + "\n", encoding="utf-8")
        print(f"record written to {args.json}")


if __name__ == "__main__":
    main()
