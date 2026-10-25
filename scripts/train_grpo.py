"""Reinforcement with a verifiable reward (GRPO): the model answers saved worlds, the verifier grades.

    uv run python scripts/train_grpo.py --worlds treino-prosa-v1 --base Qwen/Qwen3-4B --thinking \\
        --keep-out placar-v3 teste-v3 --max-steps 200

Each step takes a few worlds, has the model write several answers to each, grades every
answer with the score of the specification (+1 right, -1 confident error, -0.5 undue
abstention, -1 unusable) and pushes the model towards the answers that scored above the
others of the same world. No answer key is shown to the model: the only signal is the
grade. With --thinking the model may reason in writing before the JSON answer, and only
the answer is graded.

Two arms are meant to be compared on the same tests: this script on the raw base
(reinforcement alone) and this script on a base merged with the supervised adapter.

The guard André asked for (2026-10-06): if the model starts to say "not identifiable"
where the effect can be measured, in more than --guard-abstention of the identifiable
worlds of the last --guard-window answers, the run stops and run.json says so; the
checkpoints before the stop are kept.

The run folder gets run.json (settings, versions, result), checkpoint-<step>/, adapter/,
log.json (the trainer's log) and grades.jsonl (every graded answer: world, outcome, score).

Written for TRL 0.24.0 and Unsloth 2026.9.14 as installed; TRL's availability flags are
tuples under transformers 5.5, which this script fixes before importing the trainer.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from collections import deque
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASES = ROOT / "configs" / "bases.yaml"
TARGET_MODULES = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")
LIBRARIES = ("torch", "transformers", "peft", "trl", "unsloth", "unsloth_zoo", "datasets", "accelerate")

os.environ.setdefault("UNSLOTH_COMPILE_LOCATION", str(ROOT / "outputs" / "train" / ".unsloth_compiled_cache"))



def is_identifiable(world) -> bool:
    """Whether the effect is identifiable in a world; asked to the verifier, because a written case has no answer key."""
    from causalista.verifier import identify

    found = identify(world.problem)
    return bool(found["identifiable"] if isinstance(found, dict) else found.identifiable)


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--worlds", nargs="*", default=[], help="saved sets under outputs/worlds (training seeds only)")
    parser.add_argument("--cases", nargs="*", type=Path, default=[], help="files of written cases to train on (never the frozen test files)")
    parser.add_argument("--level", type=int, nargs="*", help="only the tellings at these levels (default: all)")
    parser.add_argument("--languages", nargs="*", default=["pt", "en"])
    parser.add_argument("--keep-out", nargs="*", default=[], help="saved sets whose structures must not be trained on")
    parser.add_argument("--base", required=True, help="repository id, or a local folder with a merged model")
    parser.add_argument("--revision", help="commit of the base (default: the one in configs/bases.yaml)")
    parser.add_argument("--thinking", action="store_true", help="let the model reason in writing before the answer")
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--alpha", type=int, default=16)
    parser.add_argument("--target-modules", nargs="+", default=list(TARGET_MODULES))
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--generations", type=int, default=8, help="answers written for each world at every step")
    parser.add_argument("--prompts-per-step", type=int, default=2, help="worlds answered at every optimizer step")
    parser.add_argument("--max-prompt-length", type=int, default=2048)
    parser.add_argument("--max-completion-length", type=int, help="default: 1536 with --thinking, 512 without")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=0.0, help="weight of the KL term towards the starting model")
    parser.add_argument("--scale-rewards", default="none", choices=["group", "batch", "none"], help="Dr. GRPO: no division by the group spread (Unsloth forces this anyway)")
    parser.add_argument("--loss-type", default="dr_grpo")
    parser.add_argument("--guard-abstention", type=float, default=0.10, help="undue abstention share that stops the run")
    parser.add_argument("--guard-window", type=int, default=200, help="graded answers the guard looks back on")
    parser.add_argument("--guard-after", type=int, default=20, help="steps before the guard starts to act")
    parser.add_argument("--save-steps", type=int, default=25)
    parser.add_argument("--logging-steps", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--run-name")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.max_completion_length is None:
        args.max_completion_length = 1536 if args.thinking else 512
    if args.run_name is None:
        args.run_name = args.out.name if args.out else (
            f"grpo-{Path(args.base).name.lower()}-{'think' if args.thinking else 'direct'}-{datetime.now().astimezone():%Y%m%d-%H%M%S}"
        )
    if args.out is None:
        args.out = ROOT / "outputs" / "train" / args.run_name
    return args


def gpu_free_gib() -> float | None:
    tool = shutil.which("nvidia-smi") or "/usr/lib/wsl/lib/nvidia-smi"
    try:
        asked = subprocess.run(
            [tool, "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True,
        )  # fmt: skip
    except (OSError, subprocess.CalledProcessError):
        return None
    total, used = (float(number) for number in asked.stdout.splitlines()[0].split(","))
    return round((total - used) / 1024, 2)


def pinned_revision(repo: str) -> str | None:
    listed = yaml.safe_load(BASES.read_text(encoding="utf-8"))["bases"] if BASES.exists() else []
    return next((base["revision"] for base in listed if base["repo"] == repo), None)


def fix_trl_flags() -> None:
    """TRL 0.24 reads transformers' package flags as booleans; transformers 5.5 returns tuples."""
    import trl.import_utils as flags

    for name, value in list(vars(flags).items()):
        if name.endswith("_available") and isinstance(value, tuple):
            setattr(flags, name, value[0])


def write_run(folder: Path, run: dict) -> None:
    (folder / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    args = parse()
    args.out.mkdir(parents=True, exist_ok=True)

    from causalista.harness import load_worlds
    from causalista.harness.hf import chat_prompt
    from causalista.task import Outcome, build_prompt, judge, parse_answer
    from causalista.task.answer import InvalidAnswer
    from causalista.worlds.split import FIRST_TRAINING_SEED, kept_out, signature

    # -- the worlds ------------------------------------------------------------------
    forbidden = frozenset(kept_out(args.keep_out))
    worlds = []
    for name in args.worlds:
        for world in load_worlds(ROOT / "outputs" / "worlds" / name):
            key = json.loads((world.folder / "hidden" / "answer_key.json").read_text(encoding="utf-8"))
            if key["parameters"]["seed"] < FIRST_TRAINING_SEED:
                raise SystemExit(f"{name}/{world.id} is not a training world: its seed is below {FIRST_TRAINING_SEED}")
            pieces = [(p["variable"], p["role"], p["hidden"]) for p in key["structure"]["pieces"]]
            if signature(key["theory"], pieces, key["structure"]["direct_effect"]) in forbidden:
                continue
            if args.level and world.level not in args.level:
                continue
            if world.language not in args.languages:
                continue
            worlds.append(world)
    if args.cases:
        from causalista.harness import case_worlds

        for file in args.cases:
            if "simulados" in file.parts and "treino-simulados" not in file.parts:
                raise SystemExit(f"{file} is a frozen test file: it is never trained on")
        worlds += [world for world in case_worlds(args.cases) if world.language in args.languages]
    if not worlds:
        raise SystemExit("no worlds to train on")
    by_world = {world.id if world.level == 1 else f"{world.id}.{world.language}{world.level}": world for world in worlds}

    # Unsloth must be imported before transformers and trl, which it patches.
    import unsloth  # noqa: F401, I001
    from unsloth import FastLanguageModel
    import torch
    from datasets import Dataset
    from transformers import TrainerCallback

    fix_trl_flags()
    from trl import GRPOConfig, GRPOTrainer

    args.revision = revision = args.revision or pinned_revision(args.base)
    run = {
        "run_name": args.run_name,
        "status": "running",
        "started": datetime.now().astimezone().isoformat(timespec="seconds"),
        "command": " ".join(sys.argv),
        "settings": {name: ([str(v) for v in value] if isinstance(value, list) and value and isinstance(value[0], Path)
                            else str(value) if isinstance(value, Path) else value) for name, value in vars(args).items()},
        "base": {"repo": args.base, "revision": revision},
        "data": {
            "sets": args.worlds,
            "case_files": [str(f) for f in args.cases],
            "worlds": len(worlds),
            "by_level": {str(level): sum(w.level == level for w in worlds) for level in sorted({w.level for w in worlds})},
            "by_language": {lang: sum(w.language == lang for w in worlds) for lang in sorted({w.language for w in worlds})},
            "identifiable_share": round(sum(is_identifiable(w) for w in worlds) / len(worlds), 3),
            "kept_out_structures": len(forbidden),
        },
        "libraries": {name: version(name) for name in LIBRARIES} | {"python": platform.python_version()},
        "gpu": {"name": torch.cuda.get_device_name(0), "cuda": torch.version.cuda, "free_gib_at_start": gpu_free_gib()},
    }
    write_run(args.out, run)

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base,
        revision=revision,
        max_seq_length=args.max_prompt_length + args.max_completion_length,
        load_in_4bit=False,
        use_exact_model_name=True,
        text_only=True,
    )
    tokenizer = getattr(tokenizer, "tokenizer", tokenizer)
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.rank,
        lora_alpha=args.alpha,
        lora_dropout=0.0,
        target_modules=args.target_modules,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=args.seed,
    )

    # The prompt is rendered here, with the same function the harness uses, so that the
    # thinking switch of the chat template is set the way the model will be evaluated.
    rows = [
        {"prompt": chat_prompt(tokenizer, build_prompt(world.task), thinking=args.thinking), "world": name}
        for name, world in by_world.items()
    ]
    dataset = Dataset.from_list(rows).shuffle(seed=args.seed)

    # -- the reward: the verifier's grade, and nothing else -----------------------------
    grades = (args.out / "grades.jsonl").open("a", encoding="utf-8")
    recent: deque[tuple[bool, str]] = deque(maxlen=args.guard_window)
    counts = {outcome.value: 0 for outcome in Outcome}

    def verifier_reward(prompts, completions, world, trainer_state=None, **_) -> list[float]:
        rewards = []
        step = trainer_state.global_step if trainer_state is not None else None
        for text, name in zip(completions, world):
            saved = by_world[name]
            try:
                answer, invalid = parse_answer(text, saved.task), None
            except InvalidAnswer as error:
                answer, invalid = None, str(error)
            judgement = judge(saved.problem, answer, invalid=invalid)
            rewards.append(float(judgement.score))
            counts[judgement.outcome.value] += 1
            recent.append((judgement.world_identifiable, judgement.outcome.value))
            grades.write(json.dumps({
                "step": step, "world": name, "level": saved.level, "language": saved.language,
                "identifiable": judgement.world_identifiable, "outcome": judgement.outcome.value,
                "score": judgement.score, "tokens": len(tokenizer(text, add_special_tokens=False)["input_ids"]),
            }, ensure_ascii=False) + "\n")  # fmt: skip
        grades.flush()
        return rewards

    class AbstentionGuard(TrainerCallback):
        """Stops the run when the model abstains too often where the effect is identifiable."""

        tripped: dict | None = None

        def on_step_end(self, trainer_args, state, control, **kwargs):
            if state.global_step < args.guard_after or len(recent) < args.guard_window // 2:
                return control
            identifiable = [outcome for ok, outcome in recent if ok]
            if not identifiable:
                return control
            share = sum(outcome == Outcome.UNDUE_ABSTENTION.value for outcome in identifiable) / len(identifiable)
            if share > args.guard_abstention:
                AbstentionGuard.tripped = {"step": state.global_step, "undue_abstention_share": round(share, 3)}
                control.should_training_stop = True
                control.should_save = True
            return control

    config = GRPOConfig(
        output_dir=str(args.out),
        per_device_train_batch_size=args.generations,
        gradient_accumulation_steps=args.prompts_per_step,
        num_generations=args.generations,
        max_prompt_length=args.max_prompt_length,
        max_completion_length=args.max_completion_length,
        temperature=args.temperature,
        beta=args.beta,
        scale_rewards=args.scale_rewards,
        loss_type=args.loss_type,
        mask_truncated_completions=True,
        learning_rate=args.lr,
        max_steps=args.max_steps,
        lr_scheduler_type="constant",
        warmup_steps=0,
        optim="adamw_torch",
        logging_steps=args.logging_steps,
        save_strategy="steps",
        save_steps=args.save_steps,
        seed=args.seed,
        report_to="none",
        log_completions=False,
        use_vllm=False,
    )
    trainer = GRPOTrainer(
        model=model,
        reward_funcs=verifier_reward,
        args=config,
        train_dataset=dataset,
        processing_class=tokenizer,
        callbacks=[AbstentionGuard()],
    )

    torch.cuda.reset_peak_memory_stats()
    started = time.time()
    result = trainer.train(resume_from_checkpoint=args.resume or None)
    seconds = time.time() - started
    grades.close()

    model.save_pretrained(str(args.out / "adapter"))
    (args.out / "log.json").write_text(json.dumps(trainer.state.log_history, indent=1) + "\n", encoding="utf-8")
    steps = trainer.state.global_step
    graded = sum(counts.values())
    run |= {
        "status": "stopped by the abstention guard" if AbstentionGuard.tripped else "finished",
        "finished": datetime.now().astimezone().isoformat(timespec="seconds"),
        "result": {
            "steps": steps,
            "train_loss": result.training_loss,
            "seconds": round(seconds, 1),
            "seconds_per_step": round(seconds / max(steps, 1), 1),
            "graded_answers": graded,
            "outcome_shares": {name: round(n / max(graded, 1), 3) for name, n in counts.items()},
            "guard": AbstentionGuard.tripped,
            "peak_vram_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
            "gpu_free_gib_at_end": gpu_free_gib(),
            "adapter": str(args.out / "adapter"),
        },
    }
    write_run(args.out, run)
    print(json.dumps(run["result"], indent=1))


if __name__ == "__main__":
    main()
