"""A model run with Hugging Face transformers on the local GPU, with or without a LoRA adapter.

This is the same stack the training uses, so a base and its fine-tuned versions are
measured with the prompt they were trained on: the task as the single user message, in
the chat template of the base. Generation is greedy and batched.

torch, transformers and peft are imported only when a model is loaded, so that
``import causalista.harness`` works on a machine without them.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from causalista.harness.backends import Reply
from causalista.task import Task, build_prompt

OPEN_THINKING = "<think>"


def has_thinking_switch(tokenizer: Any) -> bool:
    """Whether the chat template of a tokenizer reacts to ``enable_thinking``."""
    probe = [{"role": "user", "content": "x"}]
    on, off = (
        tokenizer.apply_chat_template(probe, tokenize=False, add_generation_prompt=True, enable_thinking=flag)
        for flag in (True, False)
    )
    return on != off


def chat_prompt(tokenizer: Any, user_text: str, *, thinking: bool = False) -> str:
    """The text a model continues: one user message in the chat template, up to where the answer starts.

    The training builds its examples with this same function, so that a fine-tuned
    model is asked exactly as it was taught.
    """
    switch = {"enable_thinking": thinking} if has_thinking_switch(tokenizer) else {}
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": user_text}], tokenize=False, add_generation_prompt=True, **switch
    )


def by_length(lengths: list[int], batch_size: int) -> list[list[int]]:
    """Positions grouped in batches of similar length, the longest first.

    Similar lengths waste little padding, and the longest batch goes first so that a
    batch too large for the memory fails at once and not at the end of a long run.
    """
    order = sorted(range(len(lengths)), key=lambda position: -lengths[position])
    return [order[start : start + batch_size] for start in range(0, len(order), batch_size)]


def _adapter_name(adapter: str | Path) -> str:
    """The last two parts of the folder: the run and the point of the training."""
    return "/".join(Path(adapter).resolve().parts[-2:])


@dataclass
class HFModel:
    """A base from Hugging Face, loaded on the GPU, optionally with a LoRA adapter on top."""

    model: str
    """Repository id of the base."""
    adapter: str | Path | None = None
    """Folder of a LoRA adapter trained on this base."""
    thinking: bool = False
    """Switches the thinking mode of the chat template, where the template has one."""
    label: str = ""
    revision: str | None = None
    """Commit of the base; None takes the current one."""
    batch_size: int = 8
    max_new_tokens: int = 2048
    device: str = "cuda"
    tokenizer: Any = None
    """Loaded from the base when not given."""
    _model: Any = field(default=None, init=False, repr=False)
    _stops: tuple[int, ...] = field(default=(), init=False, repr=False)

    def __post_init__(self) -> None:
        if self.tokenizer is None:
            from transformers import AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(self.model, revision=self.revision)
        switch = has_thinking_switch(self.tokenizer)
        if self.thinking and not switch:
            raise ValueError(f"the chat template of {self.model} has no thinking mode to switch on")
        if not self.label:
            # A base with a single mode gets no suffix, like an Ollama model left in its default mode.
            suffix = {True: " (com raciocínio)", False: " (sem raciocínio)"}[self.thinking] if switch else ""
            name = self.model if self.adapter is None else f"{self.model} + {_adapter_name(self.adapter)}"
            self.label = name + suffix

    def prompt_of(self, task: Task) -> str:
        return chat_prompt(self.tokenizer, build_prompt(task), thinking=self.thinking)

    def load(self) -> Any:
        """Put the weights on the GPU. Done once, on the first answer."""
        if self._model is not None:
            return self._model
        import torch
        from transformers import AutoModelForCausalLM

        model = AutoModelForCausalLM.from_pretrained(
            self.model, revision=self.revision, dtype=torch.bfloat16, device_map={"": self.device}
        )
        if self.adapter is not None:
            model = _with_adapter(model, self.model, Path(self.adapter))
        model.eval()

        configured = model.generation_config.eos_token_id
        configured = [configured] if isinstance(configured, int) else list(configured or [])
        # The end of a turn is the tokenizer's end token; the model's own may be another one.
        self._stops = tuple(dict.fromkeys(t for t in [self.tokenizer.eos_token_id, *configured] if t is not None))
        self._model = model
        return model

    def __call__(self, task: Task) -> Reply:
        return self.many([task])[0]

    def many(self, tasks: list[Task]) -> list[Reply]:
        """Answer several tasks, in batches of similar length. Replies come in the order of the tasks.

        The seconds of a reply are its share of the time of its batch.
        """
        if not tasks:
            return []
        import torch

        model = self.load()
        prompts = [self.prompt_of(task) for task in tasks]
        # The template already wrote the special tokens.
        encoded = [self.tokenizer(prompt, add_special_tokens=False)["input_ids"] for prompt in prompts]
        pad = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else self._stops[0]

        replies: list[Reply | None] = [None] * len(tasks)
        for rows in by_length([len(ids) for ids in encoded], self.batch_size):
            width = len(encoded[rows[0]])
            input_ids = torch.full((len(rows), width), pad, dtype=torch.long)
            attention = torch.zeros((len(rows), width), dtype=torch.long)
            for row, position in enumerate(rows):  # padding on the left: the answer continues the prompt
                ids = encoded[position]
                input_ids[row, width - len(ids) :] = torch.tensor(ids)
                attention[row, width - len(ids) :] = 1

            started = time.time()
            with torch.inference_mode():
                output = model.generate(
                    input_ids=input_ids.to(model.device),
                    attention_mask=attention.to(model.device),
                    max_new_tokens=self.max_new_tokens,
                    do_sample=False,
                    temperature=None,
                    top_p=None,
                    top_k=None,
                    eos_token_id=list(self._stops),
                    pad_token_id=pad,
                )
            seconds = (time.time() - started) / len(rows)

            for row, position in enumerate(rows):
                new = output[row, width:].tolist()
                end = next((index for index, token in enumerate(new) if token in self._stops), None)
                text = self.tokenizer.decode(new if end is None else new[:end], skip_special_tokens=True)
                if prompts[position].rstrip().endswith(OPEN_THINKING):
                    # The template opened the reasoning; the record keeps the tag it was opened with.
                    text = f"{OPEN_THINKING}\n{text}"
                replies[position] = Reply(text, seconds, len(new) if end is None else end + 1)
        return replies  # type: ignore[return-value]


def _with_adapter(model: Any, base: str, adapter: Path) -> Any:
    """Put a LoRA adapter on a base, refusing one that was trained on another base or does not fit."""
    from peft import PeftModel
    from peft.utils import get_peft_model_state_dict, load_peft_weights

    trained_on = json.loads((adapter / "adapter_config.json").read_text(encoding="utf-8"))["base_model_name_or_path"]
    if str(trained_on).lower() != base.lower():
        raise ValueError(f"the adapter in {adapter} was trained on {trained_on}, not on {base}")
    model = PeftModel.from_pretrained(model, str(adapter))
    # peft only warns when weights of the adapter find no place in the model, and the
    # model then answers as the plain base. Here that is an error.
    saved = set(load_peft_weights(str(adapter), device="cpu"))
    placed = set(get_peft_model_state_dict(model))
    if saved != placed:
        lost = sorted(saved - placed)[:3] + sorted(placed - saved)[:3]
        raise ValueError(f"the adapter in {adapter} does not fit {base}: {len(saved ^ placed)} weights differ, e.g. {lost}")
    return model
