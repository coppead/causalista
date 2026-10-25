"""Publish the 0.1 release to the Hugging Face Hub: model, GGUF files and the dataset.

    uv run python scripts/publish_hf.py --org coppead                 # dry run: prints what would go where
    uv run python scripts/publish_hf.py --org coppead --upload        # sends it (needs `hf auth login` or HF_TOKEN)
    uv run python scripts/publish_hf.py --org coppead --upload --only dataset

Three repositories:

- <org>/causalista-4b: the merged model (base + supervised adapter + reinforcement adapter) in
  safetensors, the two LoRA adapters under adapter/, the training records, and the model card
  (docs/cards/model-card.md);
- <org>/causalista-4b-GGUF: the GGUF files made by scripts/make_gguf.sh, an Ollama Modelfile, the `params`
  file Ollama reads when pulling straight from the Hub, and their card (docs/cards/gguf-card.md);
- <org>/causalista-worlds (dataset): the saved world sets used for development and for the final
  measurement, the prose training sets, the written cases, the training examples, every recorded
  answer of every model, the pages, and the dataset card (docs/cards/dataset-card.md).

Nothing is uploaded without --upload. Repositories are created private unless --public is given.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "docs" / "cards"

WORLD_SETS = ["placar-v3", "teste-v3", "treino-prosa-v1", "treino-prosa-v2a", "treino-prosa-v2b"]
RUN_SETS = ["placar-v3", "teste-v3", "casos-simulados", "casos-dev", "gguf-check"]
PAGES = ["casos.html", "mundos.html", "placar.html", "placar-final.html", "placar-casos.html"]


@dataclass
class Upload:
    repo: str
    repo_type: str  # "model" or "dataset"
    source: Path
    path_in_repo: str  # "" for the repository root
    allow: list[str] = field(default_factory=list)
    ignore: list[str] = field(default_factory=list)

    @property
    def is_file(self) -> bool:
        return self.source.is_file()

    def size(self) -> int:
        if self.is_file:
            return self.source.stat().st_size
        return sum(f.stat().st_size for f in self.source.rglob("*") if f.is_file() and self.wanted(f))

    def wanted(self, file: Path) -> bool:
        """Whether a file of the folder goes up, by the same patterns the upload uses."""
        from fnmatch import fnmatch

        name = str(file.relative_to(self.source))
        if self.allow and not any(fnmatch(name, pat) or fnmatch(file.name, pat) for pat in self.allow):
            return False
        return not any(fnmatch(name, pat) or fnmatch(file.name, pat) for pat in self.ignore)


def plan(args: argparse.Namespace) -> list[Upload]:
    model = f"{args.org}/{args.model_name}"
    gguf = f"{args.org}/{args.model_name}-GGUF"
    dataset = f"{args.org}/{args.dataset_name}"
    uploads: list[Upload] = []

    if "model" in args.only:
        uploads += [
            Upload(model, "model", args.merged, "", allow=["*.safetensors", "*.json", "*.jinja"]),
            # The adapters go without PEFT's boilerplate README: it is an empty form, and the reinforcement one
            # names a local path as base_model, which the Hub rejects. The model card explains both.
            Upload(model, "model", args.adapter, "adapter/sft", ignore=["README.md"]),
            Upload(model, "model", args.adapter.parent / "run.json", "training/sft/run.json"),
            Upload(model, "model", args.adapter.parent / "log.json", "training/sft/log.json"),
            Upload(model, "model", args.rl_adapter, "adapter/grpo-c", ignore=["README.md"]),
            Upload(model, "model", args.rl_adapter.parent / "run.json", "training/grpo-c/run.json"),
            Upload(model, "model", args.rl_adapter.parent / "log.json", "training/grpo-c/log.json"),
            Upload(model, "model", args.rl_adapter.parent / "grades.jsonl", "training/grpo-c/grades.jsonl"),
            Upload(model, "model", ROOT / "outputs/train/escolha-2026-10-18.json", "training/escolha-2026-10-18.json"),
            Upload(model, "model", CARDS / "model-card.md", "README.md"),
            Upload(model, "model", ROOT / "LICENSE", "LICENSE"),
        ]
    if "gguf" in args.only:
        uploads += [
            Upload(gguf, "model", args.gguf_dir, "", allow=["*-Q4_K_M.gguf", "*-Q8_0.gguf", "Modelfile", "params"]),
            Upload(gguf, "model", CARDS / "gguf-card.md", "README.md"),
            Upload(gguf, "model", ROOT / "LICENSE", "LICENSE"),
        ]
    if "dataset" in args.only:
        for name in WORLD_SETS:
            uploads.append(Upload(dataset, "dataset", ROOT / "outputs" / "worlds" / name, f"worlds/{name}"))
        uploads.append(Upload(dataset, "dataset", ROOT / "cases", "cases", ignore=["**/__pycache__/*"]))
        for name in ("sft-final.jsonl", "sft-final-l1.json", "sft-final-prosa.json"):
            uploads.append(Upload(dataset, "dataset", ROOT / "outputs" / "train" / "data" / name, f"examples/{name}"))
        for name in RUN_SETS:
            folder = ROOT / "outputs" / "runs" / name
            if folder.exists():
                uploads.append(Upload(dataset, "dataset", folder, f"runs/{name}"))
        for page in PAGES:
            uploads.append(Upload(dataset, "dataset", ROOT / "outputs" / "viz" / page, f"pages/{page}"))
        uploads += [
            Upload(dataset, "dataset", ROOT / "theories", "theories"),
            Upload(dataset, "dataset", ROOT / "configs", "configs"),
            Upload(dataset, "dataset", CARDS / "dataset-card.md", "README.md"),
            Upload(dataset, "dataset", ROOT / "LICENSE", "LICENSE"),
        ]
    return uploads


def human(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TiB"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--org", required=True, help="organisation (or user) on the Hub")
    parser.add_argument("--model-name", default="causalista-4b")
    parser.add_argument("--dataset-name", default="causalista-worlds")
    parser.add_argument("--merged", type=Path, default=ROOT / "outputs/train/merged/grpo-c-sft-cases", help="base + both adapters, merged")
    parser.add_argument("--adapter", type=Path, default=ROOT / "outputs/train/sft-final-qwen3-4b/adapter", help="the supervised adapter")
    parser.add_argument("--rl-adapter", type=Path, default=ROOT / "outputs/train/grpo-c-sft-cases/adapter", help="the reinforcement adapter, on top of the supervised model")
    parser.add_argument("--gguf-dir", type=Path, default=ROOT / "outputs/publish/gguf")
    parser.add_argument("--only", nargs="*", default=["model", "gguf", "dataset"], choices=["model", "gguf", "dataset"])
    parser.add_argument("--public", action="store_true", help="create the repositories public (default: private)")
    parser.add_argument("--upload", action="store_true", help="actually upload; without it, only print the plan")
    args = parser.parse_args()

    uploads = plan(args)
    missing = [u for u in uploads if not u.source.exists()]
    for u in uploads:
        flag = "FALTA " if not u.source.exists() else ""
        size = human(u.size()) if u.source.exists() else "-"
        print(f"{flag}{u.repo_type:7} {u.repo:40} {u.path_in_repo or '/':32} {size:>9}  <- {u.source.relative_to(ROOT) if u.source.is_relative_to(ROOT) else u.source}")
    if missing:
        print(f"\n{len(missing)} fonte(s) faltando; nada enviado.")
        sys.exit(1)
    if not args.upload:
        print("\nDry run: nada foi enviado. Repita com --upload para enviar.")
        return

    from huggingface_hub import HfApi

    api = HfApi()
    for repo, repo_type in sorted({(u.repo, u.repo_type) for u in uploads}):
        api.create_repo(repo, repo_type=repo_type, private=not args.public, exist_ok=True)
        print(f"repositório pronto: {repo} ({repo_type}, {'público' if args.public else 'privado'})")
    for u in uploads:
        print(f"enviando {u.source.name} -> {u.repo}:{u.path_in_repo or '/'} ...", flush=True)
        if u.is_file:
            api.upload_file(path_or_fileobj=str(u.source), path_in_repo=u.path_in_repo, repo_id=u.repo, repo_type=u.repo_type,
                            commit_message=f"Causalista 0.1: {u.path_in_repo}")
        else:
            api.upload_folder(folder_path=str(u.source), path_in_repo=u.path_in_repo or None, repo_id=u.repo, repo_type=u.repo_type,
                              allow_patterns=u.allow or None, ignore_patterns=u.ignore or None,
                              commit_message=f"Causalista 0.1: {u.path_in_repo or 'model files'}")
    print("pronto.")


if __name__ == "__main__":
    main()
