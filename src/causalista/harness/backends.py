"""Ways of getting an answer to a task: a local model, a model behind an API, or a fixed rule.

Every responder takes a task and returns the text of an answer, so that models and
naive strategies go through the same reading and the same scoring.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol

from causalista.task import Answer, Task, build_prompt, render_answer

TIMEOUT = 900


@dataclass(frozen=True)
class Reply:
    text: str
    seconds: float
    output_tokens: int | None = None


class Responder(Protocol):
    label: str

    def __call__(self, task: Task) -> Reply: ...


def _post(url: str, body: dict, headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


@dataclass(frozen=True)
class OllamaModel:
    """A model served by a local Ollama."""

    model: str
    label: str = ""
    think: bool | None = None
    """None leaves the model in its default mode."""
    host: str = "http://localhost:11434"
    max_tokens: int = 4096
    context: int = 8192

    def __post_init__(self) -> None:
        if not self.label:
            suffix = {None: "", True: " (com raciocínio)", False: " (sem raciocínio)"}[self.think]
            object.__setattr__(self, "label", self.model + suffix)

    def __call__(self, task: Task) -> Reply:
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": build_prompt(task)}],
            "stream": False,
            "options": {"temperature": 0, "seed": 0, "num_predict": self.max_tokens, "num_ctx": self.context},
        }
        if self.think is not None:
            body["think"] = self.think
        started = time.time()
        reply = _post(f"{self.host}/api/chat", body)
        return Reply(reply["message"]["content"], time.time() - started, reply.get("eval_count"))


@dataclass(frozen=True)
class OpenAIModel:
    """A model behind an API that speaks the OpenAI chat format (the key comes from the environment)."""

    model: str
    label: str = ""
    base_url: str = "https://api.openai.com/v1"
    key_variable: str = "OPENAI_API_KEY"
    max_tokens: int = 4096
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.label:
            object.__setattr__(self, "label", self.model)

    def __call__(self, task: Task) -> Reply:
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": build_prompt(task)}],
            "max_completion_tokens": self.max_tokens,
            **self.extra,
        }
        started = time.time()
        reply = _post(
            f"{self.base_url}/chat/completions",
            body,
            {"Authorization": f"Bearer {os.environ[self.key_variable]}"},
        )
        usage = reply.get("usage", {})
        return Reply(
            reply["choices"][0]["message"]["content"] or "",
            time.time() - started,
            usage.get("completion_tokens"),
        )


@dataclass(frozen=True)
class Rule:
    """A fixed strategy that needs no model: it answers from the list of columns alone."""

    label: str
    everything: bool

    def __call__(self, task: Task) -> Reply:
        chosen = frozenset(task.covariates) if self.everything else frozenset()
        answer = Answer(True, chosen, (), (), (), complete=False)
        return Reply(render_answer(answer), 0.0)


ADJUST_FOR_EVERYTHING = Rule("ajusta tudo", everything=True)
ADJUST_FOR_NOTHING = Rule("ajusta nada", everything=False)
