"""Run models and naive strategies over a saved set of worlds, and print the scoreboard.

    uv run python scripts/run_models.py --worlds placar-base --model rule:tudo --model rule:nada \\
        --model ollama:qwen3.5:4b:nothink --model ollama:qwen3.5:4b:think

A model can also be loaded from Hugging Face on the local GPU, with the stack used in
the training: `--model hf:Qwen/Qwen3.5-4B:nothink` (or `:think`; no thinking when omitted).

Every answer is recorded in outputs/runs/<set>/<model>.jsonl; a run that stops can be
started again and continues where it was.
"""

from __future__ import annotations

import os

# The runner's estimates run in a few threads at once; each must not grab every core.
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")

import argparse
import json
import re
from pathlib import Path

from causalista.harness.specs import responder_of
from causalista.harness import (
    case_worlds,
    load_worlds,
    run,
    summarise,
)

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--worlds", help="name of a set under outputs/worlds")
    parser.add_argument("--cases", nargs="*", type=Path, help="files of written cases, answered instead of a set of worlds")
    parser.add_argument("--name", help="name of the folder under outputs/runs (default: the set, or \"casos\")")
    parser.add_argument(
        "--model", action="append", required=True,
        help="a responder, repeatable: rule:tudo, rule:nada, ollama:<model>[:nothink], hf:<repository>[:nothink], openai:<model>",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--every", type=int, default=1, help="only one world in every N, across the whole set")
    parser.add_argument("--batch", type=int, default=32, help="worlds answered together by a model on the GPU")
    parser.add_argument("--level", type=int, help="only the worlds told at this level (1: one fact per sentence; 2: prose)")
    parser.add_argument(
        "--think-tokens",
        type=int,
        default=4096,
        help="longest answer of a GPU model that reasons; with --batch it sets the memory needed "
        "(8 worlds of 8 thousand tokens did not fit in 24 GB)",
    )
    parser.add_argument(
        "--adapter",
        type=Path,
        help="folder of a trained LoRA adapter, put on top of every hf: model of this call",
    )
    args = parser.parse_args()

    if bool(args.worlds) == bool(args.cases):
        raise SystemExit("give --worlds <set> or --cases <files>, not both")
    if args.cases:
        worlds = case_worlds(args.cases)  # the runner has no table to estimate from: records carry no estimate
        estimate = False
    else:
        worlds = load_worlds(ROOT / "outputs" / "worlds" / args.worlds)
        estimate = True
    if args.level is not None:
        worlds = [world for world in worlds if world.level == args.level]
    worlds = worlds[:: args.every]
    out = ROOT / "outputs" / "runs" / (args.name or args.worlds or "casos")
    for spec in args.model:
        responder = responder_of(spec, args.host, args.think_tokens, args.adapter)
        if hasattr(responder, "load"):
            responder.load()  # a model that does not load stops here, before any record is written
        file = out / (re.sub(r"[^a-z0-9.]+", "-", responder.label.lower()).strip("-") + ".jsonl")
        unit = ("casos" if args.cases else "mundos") if os.environ.get("LANG", "").startswith("pt") else ("cases" if args.cases else "worlds")
        print(f"{responder.label}: {len(worlds)} {unit} -> {file}", flush=True)
        records = run(responder, worlds, file, workers=args.workers, batch=args.batch, estimate=estimate)
        if len(records) < len(worlds):
            print(f"{responder.label}: only {len(records)} of {len(worlds)} worlds have an answer; run again to finish")
        numbers = summarise(records)
        pt = os.environ.get("LANG", "").startswith("pt")
        labels = ("nota", "acerto", "erro confiante", "abstenção indevida", "inválida") if pt else ("score", "accuracy", "confident error", "undue abstention", "invalid")
        print(
            f"{responder.label:34s} {labels[0]} {numbers['score']:+.2f} | {labels[1]} {numbers['correct']:.0%} | "
            f"{labels[2]} {numbers['confident_error']:.0%} | {labels[3]} {numbers['undue_abstention']:.0%} | "
            f"{labels[4]} {numbers['invalid']:.0%} | {unit} {numbers['worlds']}"
        )
        (out / "summary.json").write_text(
            json.dumps(
                {**(json.loads((out / "summary.json").read_text()) if (out / "summary.json").exists() else {}),
                 responder.label: numbers},
                ensure_ascii=False, indent=1,
            ) + "\n",
            encoding="utf-8",
        )
    print(f"{'registros em' if os.environ.get('LANG', '').startswith('pt') else 'records in'} {out}")


if __name__ == "__main__":
    main()
