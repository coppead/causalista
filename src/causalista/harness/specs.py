"""Model specifications on the command line, shared by the scripts.

A responder is named by a short spec:

- ``rule:all`` and ``rule:none`` (or ``rule:tudo`` and ``rule:nada``): the two naive strategies (adjust for every
  column; adjust for nothing);
- ``ollama:<model>[:think|:nothink]``: a model served by a local Ollama, for example
  ``ollama:hf.co/coppead/causalista-4b-GGUF:nothink``;
- ``hf:<repository>[:think|:nothink]``: a model loaded from the Hugging Face Hub on the local GPU
  (needs the ``train`` dependency group), for example ``hf:coppead/causalista-4b:nothink``;
- ``openai:<model>``: a model behind an OpenAI-compatible API (the key comes from the environment).

``nothink`` is the mode the published model was trained and measured in.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from causalista.harness.backends import ADJUST_FOR_EVERYTHING, ADJUST_FOR_NOTHING, OllamaModel, OpenAIModel, Responder

ROOT = Path(__file__).resolve().parents[3]
THINK = {"think": True, "nothink": False}
BASES = ROOT / "configs" / "bases.yaml"


def pinned_revision(repo: str) -> str | None:
    """The commit recorded for a base in configs/bases.yaml; None for a repository that is not there."""
    listed = yaml.safe_load(BASES.read_text(encoding="utf-8"))["bases"] if BASES.exists() else []
    return next((base["revision"] for base in listed if base["repo"] == repo), None)


def responder_of(spec: str, host: str = "http://localhost:11434", think_tokens: int = 4096, adapter: Path | None = None) -> Responder:
    """The responder named by a spec (see the module docstring)."""
    kind, _, rest = spec.partition(":")
    if kind == "rule":
        rules = {"tudo": ADJUST_FOR_EVERYTHING, "all": ADJUST_FOR_EVERYTHING, "nada": ADJUST_FOR_NOTHING, "none": ADJUST_FOR_NOTHING}
        if rest not in rules:
            raise SystemExit(f"unknown rule {rest!r}: use rule:all (rule:tudo) or rule:none (rule:nada)")
        return rules[rest]
    if kind == "ollama":
        model, _, mode = rest.rpartition(":")
        if mode not in THINK:
            model, mode = rest, None
        budget = {"max_tokens": 8192, "context": 16384} if mode != "nothink" else {}
        return OllamaModel(model, think=THINK.get(mode), host=host, **budget)
    if kind == "hf":
        from causalista.harness.hf import HFModel  # needs torch and transformers

        model, _, mode = rest.rpartition(":")
        if mode not in THINK:
            model, mode = rest, "nothink"
        budget = {"max_new_tokens": think_tokens} if THINK[mode] else {}
        return HFModel(model, adapter=adapter, thinking=THINK[mode], revision=pinned_revision(model), **budget)
    if kind == "openai":
        return OpenAIModel(rest)
    raise SystemExit(f"unknown kind of model in {spec!r}: use rule:, ollama:, hf: or openai:")
