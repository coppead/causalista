"""Positions for drawing a causal graph, computed by Graphviz.

Graphviz decides where each variable sits and how each arrow bends; the pages draw
the result themselves, so that they can colour paths and react to clicks. The ``dot``
program must be installed (``sudo apt install graphviz``).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass

import networkx as nx

# The pages write variable names in a monospace face at 13px, where every character
# is 0.6em wide. Sizes are given to Graphviz explicitly, so its own fonts do not matter.
CHAR_WIDTH = 7.8
SIDE_PADDING = 14.0
MIN_WIDTH = 64.0
HEIGHT = 34.0
HEIGHT_WITH_ROLE = 50.0
ROLE_LABEL_WIDTH = 96.0
MARGIN = 14.0
_POINTS_PER_INCH = 72.0


@dataclass(frozen=True)
class NodeBox:
    name: str
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class EdgeCurve:
    source: str
    target: str
    path: str
    """SVG path data, ending exactly at the border of the target."""


@dataclass(frozen=True)
class Layout:
    width: float
    height: float
    nodes: dict[str, NodeBox]
    edges: list[EdgeCurve]


class GraphvizMissing(RuntimeError):
    """The ``dot`` program is not installed."""


def node_size(name: str, *, with_role: bool) -> tuple[float, float]:
    """Width and height of the box for a variable; taller when it shows a role label."""
    width = max(MIN_WIDTH, len(name) * CHAR_WIDTH + 2 * SIDE_PADDING)
    if with_role:
        return max(width, ROLE_LABEL_WIDTH), HEIGHT_WITH_ROLE
    return width, HEIGHT


def _dot_source(graph: nx.DiGraph, sizes: dict[str, tuple[float, float]]) -> str:
    lines = [
        "digraph {",
        "  rankdir=LR; nodesep=0.42; ranksep=0.8; margin=0;",
        '  node [shape=box, fixedsize=true, label=""];',
        "  edge [arrowsize=0.7];",
    ]
    for name in sorted(graph.nodes):
        width, height = sizes[name]
        lines.append(
            f'  "{name}" [width={width / _POINTS_PER_INCH:.4f}, '
            f"height={height / _POINTS_PER_INCH:.4f}];"
        )
    for source, target in sorted(graph.edges):
        lines.append(f'  "{source}" -> "{target}";')
    lines.append("}")
    return "\n".join(lines)


def _edge_path(pos: str, flip: float) -> str:
    """Turn Graphviz's spline into SVG path data, extended to the tip of the arrow."""
    tip: tuple[float, float] | None = None
    points: list[tuple[float, float]] = []
    for token in pos.split():
        if token.startswith("e,"):
            x, y = token[2:].split(",")
            tip = (float(x), float(y))
        elif token.startswith("s,"):
            continue
        else:
            x, y = token.split(",")
            points.append((float(x), float(y)))

    def fmt(point: tuple[float, float]) -> str:
        return f"{point[0] + MARGIN:.1f} {flip - point[1] + MARGIN:.1f}"

    pieces = [f"M {fmt(points[0])}"]
    for i in range(1, len(points) - 2, 3):
        pieces.append(f"C {fmt(points[i])}, {fmt(points[i + 1])}, {fmt(points[i + 2])}")
    if tip is not None:
        pieces.append(f"L {fmt(tip)}")
    return " ".join(pieces)


def layout_graph(graph: nx.DiGraph, sizes: dict[str, tuple[float, float]]) -> Layout:
    """Lay the graph out left to right, causes before effects."""
    if shutil.which("dot") is None:
        raise GraphvizMissing("Graphviz is required to draw graphs: sudo apt install graphviz")
    result = subprocess.run(
        ["dot", "-Tjson0"],
        input=_dot_source(graph, sizes),
        capture_output=True,
        text=True,
        check=True,
    )
    drawing = json.loads(result.stdout)
    _, _, right, top = (float(value) for value in drawing["bb"].split(","))

    by_id: dict[int, str] = {}
    nodes: dict[str, NodeBox] = {}
    for item in drawing.get("objects", []):
        by_id[item["_gvid"]] = item["name"]
        x, y = (float(value) for value in item["pos"].split(","))
        width, height = sizes[item["name"]]
        nodes[item["name"]] = NodeBox(
            item["name"], round(x + MARGIN, 1), round(top - y + MARGIN, 1), width, height
        )

    edges = [
        EdgeCurve(by_id[item["tail"]], by_id[item["head"]], _edge_path(item["pos"], top))
        for item in drawing.get("edges", [])
    ]
    return Layout(
        width=round(right + 2 * MARGIN, 1),
        height=round(top + 2 * MARGIN, 1),
        nodes=nodes,
        edges=edges,
    )
