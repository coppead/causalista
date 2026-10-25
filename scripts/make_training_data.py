"""Build the examples of the supervised step: for each world, the prompt and the ideal answer.

    uv run python scripts/make_training_data.py --name sft-v1 --pairs 2000 \\
        --themes telecom varejo banco software rh educacao --languages pt en

Each line of outputs/train/data/<name>.jsonl is one world: what a model is shown (the
prompt) and what the answer key says (the ideal answer). Only the story, the dictionary
and a summary of each column are used; the tables are not kept.

Training worlds use seeds from 100 000 up, so that none of them is a world of a test.
A structure that appears in a test set given with --keep-out is also left out, whatever
its seed.

With --told, the stories in running prose (level 2) of a saved set of training worlds
are added: the set is made by scripts/make_worlds.py with training seeds and told by
scripts/tell_worlds.py --prose.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from causalista.task import build_prompt, ideal_answer, render_answer, task_of
from causalista.worlds import generate_pair, load_theory, read_world, retell
from causalista.worlds.split import FIRST_TRAINING_SEED, kept_out, signature_of

ROOT = Path(__file__).resolve().parents[1]


def language_of(world_id: str, languages: list[str]) -> str:
    """Each world is told in one language, picked by its name: the same world always gets the same one."""
    digest = hashlib.sha256(world_id.encode("utf-8")).digest()
    return languages[int.from_bytes(digest[:4], "big") % len(languages)]


def one_pair(job: tuple[str, int, list[str], frozenset[str]]) -> list[dict]:
    theory_id, seed, languages, forbidden = job
    theory = load_theory(theory_id)
    lines = []
    for world in generate_pair(theory, seed):
        if world is None or signature_of(theory_id, world.structure) in forbidden:
            continue
        language = language_of(world.id, languages)
        told_by = theory if language == theory.language else load_theory(theory_id, language)
        told = world if language == theory.language else retell(world, told_by)
        lines.append(
            {
                "world": told.name,
                "theory": theory_id,
                "language": told.language,
                "level": told.level,
                "identifiable": told.truth.identifiable,
                "prompt": build_prompt(task_of(told)),
                "answer": render_answer(ideal_answer(told, told_by)),
            }
        )
    return lines


def told_examples(folder: str, themes: list[str], languages: list[str], forbidden: frozenset[str]) -> list[dict]:
    """The examples of the prose tellings saved in a set of training worlds."""
    lines = []
    for home in sorted((ROOT / "outputs" / "worlds" / folder).iterdir()):
        if not (home / "hidden" / "answer_key.json").exists():
            continue
        about = json.loads((home / "visible" / "about.json").read_text(encoding="utf-8"))
        key = json.loads((home / "hidden" / "answer_key.json").read_text(encoding="utf-8"))
        if about["level"] != 2 or about["language"] not in languages or key["theory"] not in themes:
            continue
        if key["parameters"]["seed"] < FIRST_TRAINING_SEED:
            raise SystemExit(f"{folder}/{home.name} is not a training world: its seed is below {FIRST_TRAINING_SEED}")
        theory = load_theory(key["theory"], about["language"])
        world = read_world(home, theory)
        if signature_of(world.theory_id, world.structure) in forbidden:
            continue
        lines.append(
            {
                "world": world.name,
                "theory": world.theory_id,
                "language": world.language,
                "level": world.level,
                "identifiable": world.truth.identifiable,
                "prompt": build_prompt(task_of(world)),
                "answer": render_answer(ideal_answer(world, theory)),
            }
        )
    return lines


def case_examples(files: list[Path], languages: list[str]) -> list[dict]:
    """Examples from written cases: the question as the model sees it, and the verifier's answer."""
    from causalista.harness import case_worlds
    from causalista.task.ideal import ideal_answer_for_case
    from causalista.written_cases import load_written_cases

    lines = []
    for file in files:
        if "simulados" in file.parts and "treino-simulados" not in file.parts:
            raise SystemExit(f"{file} is a frozen test file: it is never trained on")
        cases = {case.id: case for case in load_written_cases(file)}
        for world in case_worlds([file]):
            if world.language not in languages:
                continue
            lines.append(
                {
                    "world": world.id,
                    "theory": world.theory,
                    "language": world.language,
                    "level": world.level,
                    "identifiable": cases[world.id].identifiable,
                    "prompt": build_prompt(world.task),
                    "answer": render_answer(ideal_answer_for_case(cases[world.id])),
                }
            )
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", required=True)
    parser.add_argument("--themes", nargs="+", required=True, help="the training themes (never the held-out ones)")
    parser.add_argument("--pairs", type=int, required=True, help="pairs of twin worlds per theme")
    parser.add_argument("--languages", nargs="+", default=["pt"])
    parser.add_argument("--first-seed", type=int, default=FIRST_TRAINING_SEED)
    parser.add_argument("--keep-out", nargs="*", default=[], help="saved sets whose structures must not be trained on")
    parser.add_argument("--told", nargs="*", default=[], help="saved sets of training worlds whose prose stories are added")
    parser.add_argument("--cases", nargs="*", type=Path, default=[], help="files of written cases added as examples (never the frozen test files)")
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument(
        "--allow-drafts",
        action="store_true",
        help="build examples from cards that André has not approved yet (for trials only, never for a real training)",
    )
    args = parser.parse_args()
    if args.first_seed < FIRST_TRAINING_SEED:
        raise SystemExit(f"training seeds start at {FIRST_TRAINING_SEED}")
    drafts = [
        theme if language == "pt" else f"{theme} ({language})"
        for theme in args.themes
        for language in args.languages
        if not load_theory(theme, language).approved
    ]
    if drafts and not args.allow_drafts:
        raise SystemExit(
            f"these cards are still drafts: {', '.join(drafts)}. A card only counts when its status is "
            '"aprovada", and a translation when its status is "revisada". Use --allow-drafts for a trial.'
        )

    forbidden = frozenset(kept_out(args.keep_out))
    jobs = [
        (theme, args.first_seed + index, args.languages, forbidden)
        for theme in args.themes
        for index in range(args.pairs)
    ]
    out = ROOT / "outputs" / "train" / "data" / f"{args.name}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter = Counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool, out.open("w", encoding="utf-8") as file:
        for lines in pool.map(one_pair, jobs, chunksize=4):
            for line in lines:
                file.write(json.dumps(line, ensure_ascii=False) + "\n")
                counts[(line["theory"], line["language"], line["identifiable"])] += 1
        prose = 0
        for folder in args.told:
            for line in told_examples(folder, args.themes, args.languages, forbidden):
                file.write(json.dumps(line, ensure_ascii=False) + "\n")
                counts[(line["theory"], line["language"], line["identifiable"])] += 1
                prose += 1
        written = 0
        for line in case_examples(args.cases, args.languages):
            file.write(json.dumps(line, ensure_ascii=False) + "\n")
            counts[(line["theory"], line["language"], line["identifiable"])] += 1
            written += 1

    total = sum(counts.values())
    summary = {
        "name": args.name,
        "examples": total,
        "identifiable_share": sum(n for (_, _, ok), n in counts.items() if ok) / total,
        "by_theme": {t: sum(n for (theme, _, _), n in counts.items() if theme == t) for t in [*args.themes, "caso escrito"]},
        "by_language": {x: sum(n for (_, lang, _), n in counts.items() if lang == x) for x in args.languages},
        "first_seed": args.first_seed,
        "pairs_per_theme": args.pairs,
        "kept_out_sets": args.keep_out,
        "kept_out_structures": len(forbidden),
        "told_sets": args.told,
        "prose_examples": prose,
        "case_files": [str(f) for f in args.cases],
        "case_examples": written,
        "draft_cards": drafts,
    }
    out.with_suffix(".json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
