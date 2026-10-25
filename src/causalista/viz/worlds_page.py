"""The worlds page: generated worlds, with the number each choice of columns produces.

It uses the same template as the case gallery and adds what a generated world has and
a textbook case does not: the dictionary of the table, the twin world, and three
numbers on one scale (the true effect, the simple comparison, and the estimate for the
columns the reader picks).

    uv run python -m causalista.viz.worlds_page            # writes outputs/viz/mundos.html
    uv run python -m causalista.viz.worlds_page --fragment # the form used for publishing

Estimating the effect for every choice of columns takes a few minutes; the result is
kept in ``outputs/viz/mundos_dados.json`` and reused while nothing it depends on changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path

from threadpoolctl import threadpool_limits

from causalista.estimator import estimate_effect
from causalista.viz.gallery import (
    PageText,
    choices,
    page_payload,
    problem_payload,
    render_page,
    set_key,
)
from causalista.worlds import Theory, World, generate_pair, load_theory
from causalista.worlds.theory import THEORIES_DIR, Kind

DEFAULT_OUTPUT = Path("outputs/viz/mundos.html")
CACHE = Path("outputs/viz/mundos_dados.json")
PAIRS = 10
FIRST_SEED = 1
# The page stores one estimate per choice of columns, so it shows worlds with few
# columns; and it shows tables large enough for the intervals to be narrow.
MAX_COLUMNS = 6
ROWS_SHOWN = (10_000, 20_000)
TICK_STEPS = (0.5, 1, 2, 5, 10, 20, 50, 100)


def worlds_text(theory: Theory) -> PageText:
    return PageText(
        title="Mundos do Causalista",
        eyebrow=f"Causalista · mundos gerados · tema {theory.id}",
        heading="O que cada escolha faz com o número",
        lede=(
            "Cada mundo foi gerado a partir da ficha de teoria do tema. Leia a história, escolha "
            "as colunas e compare a estimativa com o efeito verdadeiro, que aqui é conhecido."
        ),
        item="Mundo",
        items="Mundos",
    )


def showcase_seeds(theory: Theory, pairs: int = PAIRS, first_seed: int = FIRST_SEED) -> list[int]:
    """The first seeds, in order, whose pair is small enough for the page.

    The rule is fixed in advance so that the worlds shown are not hand-picked.
    """
    seeds = []
    seed = first_seed
    while len(seeds) < pairs:
        world, twin = generate_pair(theory, seed)
        if twin is not None and all(
            len(w.problem.observed_covariates) <= MAX_COLUMNS and len(w.table) in ROWS_SHOWN
            for w in (world, twin)
        ):
            seeds.append(seed)
        seed += 1
    return seeds


def _estimates_of_world(job: tuple[str, int, int]) -> tuple[str, dict[str, dict[str, float]]]:
    """Worker: the estimate for every choice of columns in one world of a pair."""
    theory_id, seed, which = job
    with threadpool_limits(limits=1):
        world = generate_pair(load_theory(theory_id), seed)[which]
        treatment, outcome = world.problem.treatment, world.problem.outcome
        estimates = {}
        for choice in choices(sorted(world.problem.observed_covariates)):
            estimate = estimate_effect(world.table, treatment, outcome, choice, seed=seed)
            estimates[set_key(choice)] = {
                "effect": estimate.effect,
                "low": estimate.low,
                "high": estimate.high,
            }
    return world.id, estimates


def scale_and_ticks(values: list[float], factor: float) -> tuple[list[float], list[float]]:
    """A domain that holds every value, and round ticks for it, in the outcome's own units."""
    low, high = min(values) * factor, max(values) * factor
    padding = 0.04 * (high - low or 1.0)
    low, high = low - padding, high + padding
    step = next((s for s in TICK_STEPS if (high - low) / s <= 7), TICK_STEPS[-1])
    first, last = math.floor(low / step) * step, math.ceil(high / step) * step
    ticks = [first + i * step for i in range(round((last - first) / step) + 1)]
    return [first / factor, last / factor], [tick / factor for tick in ticks]


def _difference(theory: Theory, world: World, twin: World) -> str:
    """One sentence on what the twin changes, without giving the answer away."""
    for here, there in zip(world.structure.pieces, twin.structure.pieces, strict=True):
        if here == there:
            continue
        label = theory.variables[here.variable].label
        if here.hidden != there.hidden:
            return f"Nele, {label} {'está' if here.hidden else 'não está'} na tabela."
        return f"Nele, muda o que se sabe sobre {label}."
    raise ValueError("the two worlds are identical")


def world_payload(
    theory: Theory,
    world: World,
    twin: World,
    estimates: dict[str, dict[str, float]],
    *,
    group: str,
    title: str,
    twin_title: str,
) -> dict:
    payload = problem_payload(world.problem, id=world.id, group=group, title=title, story=world.narrative)
    payload["dictionary"] = [asdict(entry) for entry in world.dictionary]
    payload["twin"] = {"id": twin.id, "title": twin_title, "difference": _difference(theory, world, twin)}

    binary = theory.outcome.kind is Kind.BINARY
    factor = 100.0 if binary else 1.0
    spread = [world.truth.true_effect]
    spread += [bound for estimate in estimates.values() for bound in (estimate["low"], estimate["high"])]
    domain, ticks = scale_and_ticks(spread, factor)
    payload["numbers"] = {
        "truth": world.truth.true_effect,
        "estimates": estimates,
        "scale": factor,
        "unit": "pp" if binary else "",
        "unitLong": "pontos percentuais" if binary else "na unidade do resultado",
        "domain": domain,
        "ticks": ticks,
        "rows": len(world.table),
    }
    return payload


def _fingerprint(theory: Theory, seeds: list[int]) -> str:
    """Changes whenever something the estimates depend on changes."""
    digest = hashlib.sha256(json.dumps([theory.id, seeds, MAX_COLUMNS, ROWS_SHOWN]).encode())
    package = Path(__file__).resolve().parents[1]
    sources = [THEORIES_DIR / f"{theory.id}.yaml"]
    sources += sorted((package / "worlds").glob("*.py")) + sorted((package / "estimator").glob("*.py"))
    for source in sources:
        digest.update(source.read_bytes())
    return digest.hexdigest()


def worlds_payload(theory: Theory, *, pairs: int = PAIRS, workers: int | None = None) -> dict:
    """The data of the page. Reuses the stored estimates when nothing they depend on changed."""
    seeds = showcase_seeds(theory, pairs)
    fingerprint = _fingerprint(theory, seeds)
    colophon = (
        f"{2 * len(seeds)} mundos do tema {theory.id}, em {len(seeds)} pares de gêmeos: os "
        f"primeiros pares, a partir da semente {FIRST_SEED}, com até {MAX_COLUMNS} colunas e "
        "tabelas de 10 mil ou 20 mil linhas. A regra olha só o tamanho do mundo, nunca os "
        "resultados. Os veredictos vêm do verificador; as estimativas, do estimador do runner."
    )
    if CACHE.exists():
        stored = json.loads(CACHE.read_text(encoding="utf-8"))
        if stored.get("fingerprint") == fingerprint:
            return page_payload(stored["cases"], colophon)

    jobs = [(theory.id, seed, which) for seed in seeds for which in (0, 1)]
    workers = workers or max(1, min(len(jobs), (os.cpu_count() or 2) - 2))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        by_world = dict(pool.map(_estimates_of_world, jobs))

    cases = []
    for number, seed in enumerate(seeds, 1):
        world, twin = generate_pair(theory, seed)
        group = f"Par {number}"
        titles = {world.id: f"Mundo {number}A", twin.id: f"Mundo {number}B"}
        for here, there in ((world, twin), (twin, world)):
            cases.append(
                world_payload(
                    theory,
                    here,
                    there,
                    by_world[here.id],
                    group=group,
                    title=titles[here.id],
                    twin_title=titles[there.id],
                )
            )
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(
        json.dumps({"fingerprint": fingerprint, "cases": cases}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return page_payload(cases, colophon)


def render_worlds(theory_id: str = "telecom", *, standalone: bool = True, pairs: int = PAIRS) -> str:
    theory = load_theory(theory_id)
    return render_page(worlds_payload(theory, pairs=pairs), worlds_text(theory), standalone=standalone)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the page of generated worlds.")
    parser.add_argument("--theory", default="telecom")
    parser.add_argument("--pairs", type=int, default=PAIRS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fragment", action="store_true", help="write the form used for publishing")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        render_worlds(args.theory, standalone=not args.fragment, pairs=args.pairs), encoding="utf-8"
    )
    print(f"wrote {args.out} ({args.out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
