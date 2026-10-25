"""Merge a LoRA adapter into its base and save the result as a plain model folder.

    uv run python scripts/merge_adapter.py --base Qwen/Qwen3-4B \\
        --adapter outputs/train/sft-final-qwen3-4b/adapter --out outputs/train/merged/sft-final-qwen3-4b

The merged folder is what the second arm of the reinforcement step starts from
(`scripts/train_grpo.py --base <folder>`), and what gets published at the end. The merge
runs on the processor by default, so it does not need the graphics card.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASES = ROOT / "configs" / "bases.yaml"


def pinned_revision(repo: str) -> str | None:
    listed = yaml.safe_load(BASES.read_text(encoding="utf-8"))["bases"] if BASES.exists() else []
    return next((base["revision"] for base in listed if base["repo"] == repo), None)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="cpu", help="cpu (default) or cuda")
    args = parser.parse_args()

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    revision = pinned_revision(args.base)
    model = AutoModelForCausalLM.from_pretrained(args.base, revision=revision, dtype=torch.bfloat16, device_map={"": args.device})
    model = PeftModel.from_pretrained(model, str(args.adapter))
    model = model.merge_and_unload()
    args.out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(args.out), safe_serialization=True)
    AutoTokenizer.from_pretrained(args.base, revision=revision).save_pretrained(str(args.out))
    (args.out / "merged_from.json").write_text(
        json.dumps(
            {
                "base": {"repo": args.base, "revision": revision},
                "adapter": str(args.adapter),
                "merged_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"merged model written to {args.out}")


if __name__ == "__main__":
    main()
