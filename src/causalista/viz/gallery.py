"""The case gallery: an interactive page built from the textbook cases.

For every case, the verifier judges every possible choice of columns, and the page
shows the verdict for whatever the reader picks. Nothing on the page is decided by
the page itself: it only looks up what the verifier answered.

    uv run python -m causalista.viz.gallery            # writes outputs/viz/casos.html
    uv run python -m causalista.viz.gallery --fragment # the form used for publishing

The same page template also shows generated worlds; see ``worlds_page.py``.
"""

from __future__ import annotations

import argparse
import html
import json
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from itertools import chain, combinations
from pathlib import Path

from causalista.verifier import (
    CausalProblem,
    adjustment,
    check_adjustment_set,
    identify,
    valid_adjustment_sets,
)
from causalista.verifier.textbook import TextbookCase, load_textbook_cases
from causalista.viz.layout import layout_graph, node_size

DEFAULT_OUTPUT = Path("outputs/viz/casos.html")
# One verdict is stored per choice of columns, so the page grows as 2 ** columns.
MAX_COLUMNS = 8

_STANDALONE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>body{{margin:0}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
</head>
<body>
{fragment}
</body>
</html>
"""


@dataclass(frozen=True)
class PageText:
    """The words around the cases: they differ between the two pages built from the template."""

    title: str
    eyebrow: str
    heading: str
    lede: str
    item: str
    items: str


CASES_TEXT = PageText(
    title="Casos do Causalista",
    eyebrow="Causalista · casos de livro-texto",
    heading="Por quais colunas ajustar?",
    lede=(
        "Cada caso é um pequeno mundo em que a resposta certa é conhecida. Escolha as colunas "
        "e veja no diagrama se o efeito sai certo, e por quê."
    ),
    item="Caso",
    items="Casos",
)


def set_key(variables: frozenset[str] | tuple[str, ...]) -> str:
    """How a choice of columns is named in the page data: sorted names joined by commas."""
    return ",".join(sorted(variables))


def choices(columns: list[str]) -> chain[tuple[str, ...]]:
    """Every choice of columns, smallest first."""
    return chain.from_iterable(combinations(columns, size) for size in range(len(columns) + 1))


def problem_payload(
    problem: CausalProblem,
    *,
    id: str,
    group: str,
    title: str,
    story: str,
    note: str | None = None,
    why: Mapping[str, str] | None = None,
) -> dict:
    """Everything the page needs to show one causal problem: drawing, verdicts and answer."""
    columns = sorted(problem.observed_covariates)
    if len(columns) > MAX_COLUMNS:
        raise ValueError(f"{id}: {len(columns)} columns is too many for the page")

    endpoints = {problem.treatment, problem.outcome}
    sizes = {name: node_size(name, with_role=name in endpoints) for name in problem.nodes}
    layout = layout_graph(problem.graph, sizes)

    on_causal_path = adjustment.causal_nodes(problem)
    causal_edges = {
        (source, target)
        for source, target in problem.graph.edges
        if source in on_causal_path | {problem.treatment} and target in on_causal_path
    }

    verdicts = {}
    for choice in choices(columns):
        verdict = check_adjustment_set(problem, choice)
        verdicts[set_key(choice)] = {
            "valid": verdict.valid,
            "forbidden": {name: reason.value for name, reason in verdict.forbidden.items()},
            "open": [
                {
                    "nodes": list(path.nodes),
                    "text": path.text,
                    "opened": {
                        collider: sorted(members)
                        for collider, members in path.opened_colliders.items()
                    },
                }
                for path in verdict.open_paths
            ],
        }

    answer = identify(problem)
    return {
        "id": id,
        "group": group,
        "title": title,
        "story": story,
        "note": note,
        "treatment": problem.treatment,
        "outcome": problem.outcome,
        "columns": columns,
        "width": layout.width,
        "height": layout.height,
        "nodes": [
            {
                "name": box.name,
                "x": box.x,
                "y": box.y,
                "w": box.width,
                "h": box.height,
                "role": (
                    "treatment"
                    if box.name == problem.treatment
                    else "outcome" if box.name == problem.outcome else "covariate"
                ),
                "hidden": box.name in problem.unobserved,
            }
            for box in sorted(layout.nodes.values(), key=lambda box: box.name)
        ],
        "edges": [
            {
                "from": edge.source,
                "to": edge.target,
                "d": edge.path,
                "causal": (edge.source, edge.target) in causal_edges,
            }
            for edge in layout.edges
        ],
        "verdicts": verdicts,
        "why": dict(why or {}),
        "answer": {
            "identifiable": answer.identifiable,
            "smallest": None if answer.adjustment_set is None else sorted(answer.adjustment_set),
            "validCount": len(valid_adjustment_sets(problem)),
            "missing": None if answer.missing is None else sorted(answer.missing),
        },
    }


def case_payload(case: TextbookCase) -> dict:
    """Everything the page needs to show one textbook case."""
    return problem_payload(
        case.problem,
        id=case.id,
        group=case.group,
        title=case.title,
        story=case.story,
        note=case.note,
        why={set_key(invalid.variables): invalid.why for invalid in case.invalid_sets},
    )


def page_payload(cases: list[dict], colophon: str) -> dict:
    groups: list[str] = []
    for case in cases:
        if case["group"] not in groups:
            groups.append(case["group"])
    return {"groups": groups, "cases": cases, "colophon": colophon}


def gallery_payload(cases: list[TextbookCase]) -> dict:
    return page_payload(
        [case_payload(case) for case in cases],
        f"{len(cases)} casos. Todos os veredictos desta página foram calculados pelo verificador "
        "do Causalista; a página apenas consulta o que ele respondeu.",
    )


def render_page(payload: dict, text: PageText, *, standalone: bool = True) -> str:
    """Fill the page template. ``standalone`` wraps it so that a browser can open the file."""
    template = resources.files("causalista.viz").joinpath("gallery.html").read_text(encoding="utf-8")
    words = {
        "__TITLE__": text.title,
        "__EYEBROW__": text.eyebrow,
        "__HEADING__": text.heading,
        "__LEDE__": text.lede,
        "__ITEMS__": text.items,
        "__ITEM__": text.item,
    }
    for marker, value in words.items():
        if template.count(marker) != 1:
            raise RuntimeError(f"gallery.html must contain {marker} exactly once")
        template = template.replace(marker, html.escape(value))

    # "</" must not appear inside a <script> block; "<\/" means the same in JSON.
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    marker = "/*__CASES__*/"
    if template.count(marker) != 1:
        raise RuntimeError("gallery.html must contain the data marker exactly once")
    fragment = template.replace(marker, data)
    return _STANDALONE.format(fragment=fragment) if standalone else fragment


def render(cases: list[TextbookCase] | None = None, *, standalone: bool = True) -> str:
    """Build the page of textbook cases."""
    payload = gallery_payload(load_textbook_cases() if cases is None else cases)
    return render_page(payload, CASES_TEXT, standalone=standalone)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the case gallery page.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--fragment",
        action="store_true",
        help="write the page without the <html> wrapper (the form used for publishing)",
    )
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(standalone=not args.fragment), encoding="utf-8")
    print(f"wrote {args.out} ({args.out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
