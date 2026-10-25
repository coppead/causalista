"""Talking to an open model served by a local Ollama.

Used where the project needs an open model to write or to read text (the prose stories
and their check, the translation of the theory cards). Models compared on the task go
through ``causalista.harness`` instead.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

HOST = "http://localhost:11434"


@dataclass(frozen=True)
class OpenModel:
    """A callable that sends one message to a local model and returns its reply."""

    model: str
    host: str = HOST
    temperature: float = 0.0
    json_mode: bool = False
    max_tokens: int = 2048
    context: int = 8192
    timeout: int = 900

    def __call__(self, prompt: str, *, seed: int = 0) -> str:
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
            "options": {
                "temperature": self.temperature,
                "seed": seed,
                "num_predict": self.max_tokens,
                "num_ctx": self.context,
            },
        }
        if self.json_mode:
            body["format"] = "json"
        request = urllib.request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            content = json.loads(response.read().decode("utf-8"))["message"]["content"]
        # A model that reasons aloud despite being told not to: keep what comes after.
        return content.rsplit("</think>", 1)[-1].strip()
