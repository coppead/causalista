"""Smoke test of the training stack: every base takes ten steps of training and answers eight prompts.

    uv run python scripts/smoke_train.py                       # the three bases of configs/bases.yaml
    uv run python scripts/smoke_train.py --base Qwen/Qwen3-4B  # one of them

It checks that the tools can load each base, train a LoRA adapter on it and generate
with the adapter. It says nothing about quality: the data are 64 telecom worlds whose
answers carry only the verdict and the adjustment set, and the adapter is thrown away.
The worlds come from seeds 90 000 and up, a range no other use of the project touches.

The card is shared. Each stage waits until there is room for a base (--room, in GiB):
without room nothing fails, the stage just runs many times slower and slows the others.

Everything is written under outputs/train/smoke/; the table is in summary.json.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import yaml
from train_sft import gpu_free_gib

from causalista.task import Answer, build_prompt, render_answer, task_of
from causalista.worlds import World, generate_pair, load_theory

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "outputs" / "train" / "smoke"
FIRST_SEED = 90_000
EXAMPLES = 64
PROMPTS = 8


def worlds(count: int) -> list[World]:
    theory, made, seed = load_theory("telecom", "pt"), [], FIRST_SEED
    while len(made) < count:
        made += [world for world in generate_pair(theory, seed) if world is not None]
        seed += 1
    return made[:count]


def write_data(path: Path) -> None:
    lines = []
    for world in worlds(EXAMPLES):
        truth = world.truth
        answer = Answer(
            identifiable=truth.identifiable,
            adjustment_set=frozenset(truth.adjustment_set or ()),
            roles=(),
            missing=tuple(truth.missing or ()),
            assumptions=(),
            complete=False,
        )
        lines.append(
            {
                "world": world.name,
                "theory": world.theory_id,
                "language": world.language,
                "level": world.level,
                "prompt": build_prompt(task_of(world)),
                "answer": render_answer(answer),
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines), encoding="utf-8")


def wait_for_room(gib: float) -> None:
    """Hold on until the card has had this much memory free for a minute.

    One look is not enough: a server that swaps models leaves the card free for a few seconds.
    """
    told, calm = False, 0
    while calm < 4:
        free = gpu_free_gib()
        if free is None:
            return
        calm = calm + 1 if free >= gib else 0
        if calm == 0 and not told:
            print(f"waiting for the GPU: {free:.1f} GiB free, {gib:.0f} needed", flush=True)
            told = True
        time.sleep(20 if calm < 4 else 0)


def generate(base: str, revision: str, adapter: Path, out: Path) -> None:
    """One batch of eight prompts with the adapter, and the first of them alone for comparison."""
    import torch

    from causalista.harness.hf import HFModel

    tasks = [task_of(world) for world in worlds(PROMPTS)]
    model = HFModel(base, adapter=adapter, revision=revision, batch_size=PROMPTS, max_new_tokens=256)
    model.load()
    torch.cuda.reset_peak_memory_stats()
    started = time.time()
    replies = model.many(tasks)
    seconds = time.time() - started
    tokens = sum(reply.output_tokens for reply in replies)
    alone = model(tasks[0])
    same = next(
        (i for i, (a, b) in enumerate(zip(alone.text, replies[0].text)) if a != b),
        min(len(alone.text), len(replies[0].text)),
    )
    out.write_text(
        json.dumps(
            {
                "label": model.label,
                "prompts": len(tasks),
                "output_tokens": tokens,
                "seconds": round(seconds, 2),
                "tokens_per_second": round(tokens / seconds, 1),
                "peak_vram_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
                "gpu_free_gib_at_end": gpu_free_gib(),  # near zero: the card was full, the speed is not to be trusted
                "alone_and_in_batch_agree_up_to": f"{same} of {len(alone.text)} characters",
                "first_reply": replies[0].text,
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", action="append", help="repository id; default: every base of configs/bases.yaml")
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--room", type=float, default=12.0, help="free GPU memory a stage waits for, in GiB")
    parser.add_argument("--generate", nargs=4, metavar=("BASE", "REVISION", "ADAPTER", "OUT"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.generate:
        base, revision, adapter, out = args.generate
        return generate(base, revision, Path(adapter), Path(out))

    listed = {base["repo"]: base for base in yaml.safe_load((ROOT / "configs" / "bases.yaml").read_text())["bases"]}
    data = HOME / "data.jsonl"
    write_data(data)

    summary = {}
    for repo in args.base or list(listed):
        folder = HOME / repo.split("/")[-1].lower()
        row = summary[repo] = {"trains": False, "generates": False}
        # Each stage in its own process, so that the memory of one does not count in the next.
        wait_for_room(args.room)
        training = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "train_sft.py"), "--data", str(data), "--base", repo,
             "--max-steps", str(args.steps), "--batch-size", "2", "--grad-accum", "1", "--logging-steps", "1",
             "--save-steps", "1000", "--out", str(folder)],
            check=False,  # a base that fails is a result of the test, reported in the table
        )  # fmt: skip
        run = json.loads((folder / "run.json").read_text()) if (folder / "run.json").exists() else {}
        if training.returncode != 0 or run.get("status") != "finished":
            continue
        row |= {
            "trains": True,
            "revision": run["base"]["revision"],
            "train_peak_vram_gib": run["result"]["peak_vram_gib"],
            "train_gpu_free_gib_at_end": run["result"]["gpu_free_gib_at_end"],
            "seconds_per_step": run["result"]["seconds_per_step"],
            "train_loss": round(run["result"]["train_loss"], 4),
            "prompt_tokens_mean": run["data"]["prompt_tokens_mean"],
            "prompt_tokens_max": run["data"]["prompt_tokens_max"],
            "modules_with_lora": run["lora"]["modules_with_lora"],
        }
        wait_for_room(args.room)
        generation = subprocess.run(
            [sys.executable, __file__, "--generate", repo, run["base"]["revision"], str(folder / "adapter"),
             str(folder / "generation.json")],
            check=False,
        )  # fmt: skip
        if generation.returncode == 0:
            answers = json.loads((folder / "generation.json").read_text())
            row |= {
                "generates": True,
                "tokens_per_second": answers["tokens_per_second"],
                "generate_peak_vram_gib": answers["peak_vram_gib"],
                "generate_gpu_free_gib_at_end": answers["gpu_free_gib_at_end"],
                "alone_and_in_batch_agree_up_to": answers["alone_and_in_batch_agree_up_to"],
            }

    known = json.loads((HOME / "summary.json").read_text()) if (HOME / "summary.json").exists() else {}
    (HOME / "summary.json").write_text(json.dumps(known | summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
