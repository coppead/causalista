"""The gate of phase 2, measured: does the estimator recover the true effect?

For many identifiable worlds, estimate the effect with the smallest valid set and see
how often the 95% interval contains the true effect (it should be about 95%). Also
check the simple comparison: with a confounder in the world it should miss the truth,
and it should land where the world says it would with infinitely many rows.

    uv run python scripts/check_estimator.py --worlds 300 --learner boosting
"""

from __future__ import annotations

import os

# One thread per process: the worlds already run in parallel.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from causalista.estimator import estimate_effect, naive_difference
from causalista.worlds import Role, generate_pair, load_theory

ROOT = Path(__file__).resolve().parents[1]


def one_seed(args: tuple[str, int, str]) -> list[dict]:
    theory_id, seed, learner = args
    theory = load_theory(theory_id)
    rows = []
    for world in generate_pair(theory, seed):
        if world is None or not world.truth.identifiable:
            continue
        treatment, outcome = world.problem.treatment, world.problem.outcome
        started = time.time()
        adjusted = estimate_effect(
            world.table, treatment, outcome, world.truth.adjustment_set, seed=seed, learner=learner
        )
        seconds = time.time() - started
        naive = naive_difference(world.table, treatment, outcome)
        rows.append(
            {
                "world": world.id,
                "rows": len(world.table),
                "set_size": len(world.truth.adjustment_set),
                "confounders": world.structure.count(Role.CONFOUNDER),
                "truth": world.truth.true_effect,
                "expected_naive": world.truth.expected_naive,
                "adjusted": adjusted.effect,
                "adjusted_se": adjusted.standard_error,
                "adjusted_covers": adjusted.covers(world.truth.true_effect),
                "clipped_share": adjusted.clipped_share,
                "naive": naive.effect,
                "naive_se": naive.standard_error,
                "naive_covers": naive.covers(world.truth.true_effect),
                "naive_covers_expected": naive.covers(world.truth.expected_naive),
                "seconds": seconds,
            }
        )
    return rows


def summarise(rows: list[dict]) -> dict:
    def share(values) -> float:
        values = list(values)
        return float(np.mean(values)) if values else float("nan")

    confounded = [row for row in rows if row["confounders"] > 0]
    unconfounded = [row for row in rows if row["confounders"] == 0]
    z = [(row["adjusted"] - row["truth"]) / row["adjusted_se"] for row in rows]
    by_rows = {}
    for size in sorted({row["rows"] for row in rows}):
        group = [row for row in rows if row["rows"] == size]
        by_rows[size] = {"worlds": len(group), "coverage": share(r["adjusted_covers"] for r in group)}
    return {
        "worlds": len(rows),
        "coverage": share(row["adjusted_covers"] for row in rows),
        "coverage_by_rows": by_rows,
        "mean_z": float(np.mean(z)),
        "sd_z": float(np.std(z)),
        "mean_abs_error": share(abs(row["adjusted"] - row["truth"]) for row in rows),
        "worlds_with_confounder": len(confounded),
        "naive_coverage_with_confounder": share(row["naive_covers"] for row in confounded),
        "naive_lands_where_expected": share(row["naive_covers_expected"] for row in rows),
        "naive_mean_abs_error_with_confounder": share(abs(r["naive"] - r["truth"]) for r in confounded),
        "worlds_without_confounder": len(unconfounded),
        "naive_coverage_without_confounder": share(row["naive_covers"] for row in unconfounded),
        "max_clipped_share": max(row["clipped_share"] for row in rows),
        "median_seconds": float(np.median([row["seconds"] for row in rows])),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--theory", default="telecom")
    parser.add_argument("--worlds", type=int, default=300, help="number of seeds (pairs of worlds)")
    parser.add_argument("--first-seed", type=int, default=10_000)
    parser.add_argument("--learner", default="boosting")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 4))
    args = parser.parse_args()

    jobs = [(args.theory, args.first_seed + i, args.learner) for i in range(args.worlds)]
    started = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = [row for batch in pool.map(one_seed, jobs, chunksize=2) for row in batch]
    summary = summarise(rows)
    summary["learner"] = args.learner
    summary["minutes"] = (time.time() - started) / 60

    out = ROOT / "outputs" / "gates"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"estimator_{args.theory}_{args.learner}.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
