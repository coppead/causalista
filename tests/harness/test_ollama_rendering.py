"""With thinking off, the harness renders the Qwen3 chat format itself and sends it raw to Ollama."""

from pathlib import Path

import pytest

from causalista.harness import OllamaModel, case_worlds, chatml_prompt
from causalista.harness import backends


def test_the_closed_thinking_block_matches_the_transformers_template():
    transformers = pytest.importorskip("transformers")
    tok = transformers.AutoTokenizer.from_pretrained("Qwen/Qwen3-4B", revision="1cfa9a7208912126459214e8b04321603b3df60c")
    prompt = "What is the average effect of x on y?"
    expected = tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    assert chatml_prompt(prompt, thinking=False) == expected


def test_thinking_off_goes_raw_through_generate_and_thinking_on_through_chat(monkeypatch):
    calls = []

    def fake_post(url, body, headers=None):
        calls.append((url, body))
        return {"response": "{}", "message": {"content": "{}"}, "eval_count": 1}

    monkeypatch.setattr(backends, "_post", fake_post)
    task = case_worlds([Path("cases/fase0.yaml")])[0].task
    OllamaModel("m", think=False)(task)
    OllamaModel("m", think=True)(task)
    OllamaModel("m")(task)
    assert calls[0][0].endswith("/api/generate") and calls[0][1]["raw"] is True
    assert calls[0][1]["prompt"].endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n")
    assert calls[1][0].endswith("/api/chat") and calls[1][1]["think"] is True
    assert calls[2][0].endswith("/api/chat") and "think" not in calls[2][1]
