"""Fix the showcase worlds: the test worlds answered at every point of the training.

    uv run python scripts/pick_showcase.py

The rule is in configs/split.yaml and looks only at the size of a world, never at any
result: for each held-out theme, the first pairs of twins (by seed) with few columns and
a table of middling size. The choice is written to configs/showcase.yaml, which is kept
in git, so that the "before and after" shown to colleagues is fixed before training.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    split = yaml.safe_load((ROOT / "configs" / "split.yaml").read_text(encoding="utf-8"))
    rule = split["showcase"]
    manifest = json.loads((ROOT / "outputs" / "worlds" / rule["set"] / "manifest.json").read_text(encoding="utf-8"))
    by_seed: dict[tuple[str, int], list[dict]] = {}
    for entry in manifest:
        by_seed.setdefault((entry["theory"], entry["seed"]), []).append(entry)

    chosen = []
    for theme in split["themes"]["test"]:
        pairs = 0
        for (theory, _seed), worlds in sorted(by_seed.items()):
            small = all(
                world["columns"] - 2 <= rule["max_columns"] and world["rows"] in rule["rows"] for world in worlds
            )
            if theory == theme and len(worlds) == 2 and small:
                chosen += sorted(world["world"] for world in worlds)
                pairs += 1
                if pairs == rule["pairs_per_theme"]:
                    break

    text = (
        "# Mundos-vitrine: fixados antes do treino, pela regra de configs/split.yaml.\n"
        "# Gerado por scripts/pick_showcase.py. Vale para a divisão de temas em vigor; se os\n"
        "# temas de teste mudarem, este arquivo é refeito antes de qualquer treino.\n\n"
        + yaml.safe_dump({"set": rule["set"], "status": split["status"], "worlds": chosen}, sort_keys=False)
    )
    (ROOT / "configs" / "showcase.yaml").write_text(text, encoding="utf-8")
    print(f"{len(chosen)} showcase worlds written to configs/showcase.yaml")


if __name__ == "__main__":
    main()
