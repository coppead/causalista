"""Score again the answers already recorded for a set of worlds.

    uv run python scripts/rescore.py --worlds placar-base

The records keep every answer as it was given, so a change in how answers are read or
scored does not need the models to run again: each recorded text is read and judged
anew, and the record is rewritten. Nothing is asked of any model.
"""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")

import argparse
import json
from collections import Counter
from pathlib import Path

from causalista.harness import Reply, load_worlds, record_of, summarise

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--worlds", required=True, help="name of a set under outputs/worlds")
    args = parser.parse_args()

    worlds = {world.id: world for world in load_worlds(ROOT / "outputs" / "worlds" / args.worlds)}
    folder = ROOT / "outputs" / "runs" / args.worlds
    summary = {}
    for file in sorted(folder.glob("*.jsonl")):
        old = [json.loads(line) for line in file.read_text(encoding="utf-8").splitlines() if line.strip()]
        new = [
            record_of(
                worlds[record["world"]],
                record["model"],
                record["checkpoint"],
                Reply(record["raw"], record["seconds"], record["output_tokens"]),
            )
            for record in old
        ]
        for before, after in zip(old, new, strict=True):
            after["seconds"] = before["seconds"]
        moved = Counter((b["outcome"], a["outcome"]) for b, a in zip(old, new, strict=True) if b["outcome"] != a["outcome"])
        file.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in new), encoding="utf-8")
        label = new[0]["model"]
        summary[label] = summarise(new)
        print(f"{label:44s} nota {summary[label]['score']:+.2f} | mudaram: {dict(moved) or 'nenhuma'}")
    (folder / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
