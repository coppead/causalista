"""Tell the worlds of a saved set again: in another language, or as running prose.

    uv run python scripts/tell_worlds.py --set teste-final --language en            # level 1, in English
    uv run python scripts/tell_worlds.py --set teste-final --language pt --prose    # level 2, in Portuguese

A new telling is saved beside the original (same world, same table, same answer key;
only the words change). Prose is written by one open model and checked by two others: a
prose that does not say what the world says is thrown away, and the log keeps why.

Measured on 24 worlds of the eight themes (2026-10-04), with one writing and up to two
revisions: granite4.1:30b writing and qwen3.5:9b plus qwen3:14b reading kept 17 stories,
at about 50 seconds a world; qwen3:14b writing and qwen3.5:9b plus granite4.1:30b
reading kept 16, at about 30 seconds a world.
"""

from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from causalista.llm import OpenModel
from causalista.worlds import load_theory, read_world, retell, save_world
from causalista.worlds.prose import tell_in_prose

ROOT = Path(__file__).resolve().parents[1]


def save_beside(world, original: Path, folder: Path) -> None:
    """Save a telling, sharing the table file with the original instead of copying it."""
    home = save_world(world, folder)
    table = home / "visible" / "table.csv"
    table.unlink()
    os.link(original / "visible" / "table.csv", table)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", required=True, help="name of a set under outputs/worlds")
    parser.add_argument("--language", required=True)
    parser.add_argument("--prose", action="store_true", help="also rewrite the story as running prose (level 2)")
    parser.add_argument("--every", type=int, default=1, help="only one world in every N")
    parser.add_argument("--writer", default="granite4.1:30b")
    parser.add_argument("--readers", nargs="+", default=["qwen3.5:9b", "qwen3:14b"])
    parser.add_argument("--attempts", type=int, default=3, help="one writing and up to two revisions")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    folder = ROOT / "outputs" / "worlds" / args.set
    originals = sorted(
        home for home in folder.iterdir()
        if (home / "hidden").is_dir() and "." not in home.name  # the tellings have a dot in their name
    )[:: args.every]  # fmt: skip
    theories: dict[tuple[str, str], object] = {}

    def theory_of(theory_id: str, language: str):
        if (theory_id, language) not in theories:
            theories[(theory_id, language)] = load_theory(theory_id, language)
        return theories[(theory_id, language)]

    writer = OpenModel(args.writer, temperature=0.7, max_tokens=1200)
    readers = [OpenModel(name, json_mode=True, max_tokens=800) for name in args.readers]
    log = folder / f"prose-{args.language}.jsonl"

    def one(home: Path) -> str:
        theory_id = json.loads((home / "hidden" / "answer_key.json").read_text(encoding="utf-8"))["theory"]
        world = read_world(home, theory_of(theory_id, "pt"))
        theory = theory_of(theory_id, args.language)
        if args.language != "pt":
            world = retell(world, theory)
            if not (folder / world.name).exists():
                save_beside(world, home, folder)
        if not args.prose:
            return "told"
        if (folder / f"{world.id}.{args.language}2").exists():
            return "already there"
        telling = tell_in_prose(world, theory, writer=writer, readers=readers, attempts=args.attempts)
        with log.open("a", encoding="utf-8") as file:
            entry = {"world": world.name, "kept": telling.world is not None, "attempts": telling.attempts,
                     "problems": list(telling.problems)}  # fmt: skip
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if telling.world is None:
            return "refused"
        save_beside(telling.world, home, folder)
        return "kept"

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(one, originals))
    print({result: results.count(result) for result in sorted(set(results))})


if __name__ == "__main__":
    main()
