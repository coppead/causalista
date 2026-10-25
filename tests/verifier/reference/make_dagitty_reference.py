"""Regenerate dagitty_reference.json: the answers of dagitty to random problems.

dagitty is the R package by the authors of the algorithms the verifier follows
(Textor, van der Zander, Liśkiewicz and others). This script draws random problems,
asks dagitty about each one, and stores the problems together with its answers. The
test suite compares the verifier with the stored answers, so R is needed only to
regenerate the file, not to run the tests.

Usage, from the root of the repository:

    uv run python tests/verifier/reference/make_dagitty_reference.py

It needs R with the packages dagitty and jsonlite. If they are installed in a
project-local library, point R_LIBS_USER at it (the default below is ``.r-lib``).
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import tempfile
from itertools import chain, combinations
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[2]
OUTPUT = HERE / "dagitty_reference.json"
SEED = 20261003
PROBLEMS = 400


def draw_problem(rng: random.Random, number: int) -> dict:
    size = rng.randint(3, 7)
    covariates = [f"v{i}" for i in range(1, size - 1)]
    nodes = ["t", "y", *covariates]
    order = nodes[:]
    rng.shuffle(order)
    density = rng.choice([0.2, 0.35, 0.5, 0.65])
    edges = [[a, b] for a, b in combinations(order, 2) if rng.random() < density]
    latent = sorted(name for name in covariates if rng.random() < 0.3)
    sets = [
        list(subset)
        for subset in chain.from_iterable(
            combinations(covariates, n) for n in range(len(covariates) + 1)
        )
    ]
    return {
        "id": f"random-{number:03d}",
        "nodes": nodes,
        "edges": edges,
        "treatment": "t",
        "outcome": "y",
        "latent": latent,
        "sets": sets,
    }


def main() -> None:
    rng = random.Random(SEED)
    problems = [draw_problem(rng, number) for number in range(PROBLEMS)]

    env = dict(os.environ)
    env.setdefault("R_LIBS_USER", str(ROOT / ".r-lib"))
    with tempfile.TemporaryDirectory() as folder:
        questions = Path(folder) / "problems.json"
        answers = Path(folder) / "answers.json"
        questions.write_text(json.dumps(problems), encoding="utf-8")
        subprocess.run(
            ["Rscript", str(HERE / "dagitty_answers.R"), str(questions), str(answers)],
            check=True,
            env=env,
        )
        result = json.loads(answers.read_text(encoding="utf-8"))

    by_id = {answer["id"]: answer for answer in result["answers"]}
    for problem in problems:
        answer = by_id[problem["id"]]
        assert len(answer["valid"]) == len(problem["sets"]), problem["id"]
        problem["dagitty"] = {
            "valid": answer["valid"],
            "all_sets": answer["all_sets"],
            "identifiable": answer["identifiable"],
        }

    document = {"seed": SEED, "source": result["meta"], "problems": problems}
    OUTPUT.write_text(json.dumps(document, separators=(",", ":")) + "\n", encoding="utf-8")
    verdicts = sum(len(problem["sets"]) for problem in problems)
    print(f"wrote {OUTPUT.relative_to(ROOT)}: {len(problems)} problems, {verdicts} verdicts")


if __name__ == "__main__":
    main()
