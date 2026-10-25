"""Generate a set of worlds and save it, each world with its visible part and its answer key.

    uv run python scripts/make_worlds.py --name placar-base --pairs 13 --first-seed 50000

Seeds are kept apart by use, so that no world of a test is ever a world of training:

    1 to 9 999          pages and reading material
    10 000 to 19 999    the estimator gate
    50 000 to 59 999    the baseline scoreboard of phase 3
    60 000 to 69 999    the final test (worlds never seen)
    100 000 and up      training
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from causalista.worlds import generate_pair, load_theory, save_world
from causalista.worlds.theory import THEORIES_DIR

ROOT = Path(__file__).resolve().parents[1]


def one_pair(job: tuple[str, int, str, str]) -> list[dict]:
    theory_id, seed, language, folder = job
    theory = load_theory(theory_id, language)
    made = []
    for world in generate_pair(theory, seed):
        if world is None:
            continue
        save_world(world, Path(folder))
        made.append(
            {
                "world": world.name,
                "theory": theory_id,
                "seed": seed,
                "language": world.language,
                "level": world.level,
                "identifiable": world.truth.identifiable,
                "columns": len(world.table.columns),
                "rows": len(world.table),
            }
        )
    return made


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", required=True, help="name of the set: the folder under outputs/worlds")
    parser.add_argument("--themes", nargs="*", default=sorted(path.stem for path in THEORIES_DIR.glob("*.yaml")))
    parser.add_argument("--pairs", type=int, default=13, help="pairs of twin worlds per theme")
    parser.add_argument("--first-seed", type=int, required=True)
    parser.add_argument("--language", default="pt")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    folder = ROOT / "outputs" / "worlds" / args.name
    folder.mkdir(parents=True, exist_ok=True)
    jobs = [
        (theme, args.first_seed + index, args.language, str(folder))
        for theme in args.themes
        for index in range(args.pairs)
    ]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        made = [entry for batch in pool.map(one_pair, jobs) for entry in batch]

    manifest = folder / "manifest.json"
    known = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else []
    names = {entry["world"] for entry in made}
    manifest.write_text(
        json.dumps([e for e in known if e["world"] not in names] + made, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    share = sum(entry["identifiable"] for entry in made) / len(made)
    print(f"{len(made)} worlds in {folder} ({share:.0%} identifiable)")


if __name__ == "__main__":
    main()
