"""The Hugging Face responder, with a stand-in tokenizer and a stand-in model: no GPU, no download."""

from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from causalista.harness.hf import HFModel, by_length, chat_prompt, has_thinking_switch
from causalista.task import Task, build_prompt, make_task

END, PAD = 0, 1


class Tokenizer:
    """One token per character. The template opens the reasoning, or closes it empty."""

    eos_token_id = END
    pad_token_id = PAD

    def __init__(self, *, switch: bool = True) -> None:
        self.switch = switch

    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt, enable_thinking=True):
        assert not tokenize and add_generation_prompt and [m["role"] for m in messages] == ["user"]
        opening = "<think>\n" if enable_thinking else "<think></think>"
        return f"<user>{messages[0]['content']}<assistant>" + (opening if self.switch else "")

    def __call__(self, text: str, *, add_special_tokens: bool) -> dict:
        assert add_special_tokens is False
        return {"input_ids": [ord(character) for character in text]}

    def decode(self, ids: list[int], *, skip_special_tokens: bool) -> str:
        return "".join(chr(token) for token in ids)


class Model:
    """Answers each row with the number of tokens it was allowed to see, then ends the turn."""

    device = "cpu"
    generation_config = SimpleNamespace(eos_token_id=None)

    def __init__(self) -> None:
        self.shapes: list[tuple[int, int]] = []

    def generate(self, *, input_ids, attention_mask, max_new_tokens, **options):
        import torch

        assert options["do_sample"] is False and options["eos_token_id"] == [END]
        self.shapes.append(tuple(input_ids.shape))
        answers = []
        for ids, mask in zip(input_ids, attention_mask):
            assert (ids[mask == 0] == PAD).all() and mask.tolist() == sorted(mask.tolist())  # padding on the left
            answers.append([ord(character) for character in f"vi {int(mask.sum())}"] + [END])
        width = max(len(answer) for answer in answers)
        new = torch.tensor([answer + [PAD] * (width - len(answer)) for answer in answers])
        return torch.cat([input_ids, new], dim=1)


def _task(number: int) -> Task:
    table = pd.DataFrame({"oferta": [0, 1], "cancelou": [1, 0]})
    return make_task(
        world_id=f"mundo-{number}",
        question="Qual o efeito?",
        treatment="oferta",
        outcome="cancelou",
        narrative="x" * number,
        descriptions={"oferta": "a oferta", "cancelou": "o cancelamento"},
        table=table,
    )


def _model(**options) -> HFModel:
    model = HFModel("org/base", tokenizer=options.pop("tokenizer", Tokenizer()), **options)
    model._model, model._stops = Model(), (END,)
    return model


def test_batches_hold_similar_lengths_and_the_longest_come_first() -> None:
    assert by_length([5, 9, 1, 7, 3], 2) == [[1, 3], [0, 4], [2]]
    assert by_length([], 4) == []


def test_the_label_says_the_mode_that_was_used() -> None:
    assert _model().label == "org/base (sem raciocínio)"
    assert _model(thinking=True).label == "org/base (com raciocínio)"
    assert _model(label="outro nome").label == "outro nome"
    assert _model(adapter="/x/outputs/train/rodada-1/adapter").label == "org/base + rodada-1/adapter (sem raciocínio)"


def test_a_base_with_a_single_mode_gets_no_suffix_and_cannot_be_asked_to_think() -> None:
    plain = Tokenizer(switch=False)
    assert not has_thinking_switch(plain)
    assert _model(tokenizer=plain).label == "org/base"
    with pytest.raises(ValueError, match="no thinking mode"):
        _model(tokenizer=plain, thinking=True)


def test_the_prompt_is_the_task_as_the_single_user_message() -> None:
    task = _task(3)
    assert _model().prompt_of(task) == f"<user>{build_prompt(task)}<assistant><think></think>"
    assert _model(thinking=True).prompt_of(task).endswith("<assistant><think>\n")
    assert chat_prompt(Tokenizer(switch=False), "oi", thinking=False) == "<user>oi<assistant>"


def test_many_answers_in_batches_and_gives_the_replies_in_the_order_of_the_tasks() -> None:
    pytest.importorskip("torch")
    model = _model(batch_size=2)
    tasks = [_task(number) for number in (4, 30, 1, 17, 9)]

    replies = model.many(tasks)

    lengths = [len(model.prompt_of(task)) for task in tasks]
    assert [reply.text for reply in replies] == [f"vi {length}" for length in lengths]
    assert [reply.output_tokens for reply in replies] == [len(f"vi {length}") + 1 for length in lengths]
    assert [rows for rows, _ in model._model.shapes] == [2, 2, 1]
    assert [width for _, width in model._model.shapes] == sorted(lengths, reverse=True)[::2]
    assert model(tasks[1]).text == replies[1].text
    assert model.many([]) == []


def test_reasoning_opened_by_the_template_keeps_its_opening_tag_in_the_record() -> None:
    pytest.importorskip("torch")
    reply = _model(thinking=True)(_task(2))
    assert reply.text.startswith("<think>\nvi ")


def test_the_harness_is_imported_without_torch() -> None:
    code = "import sys, causalista.harness; print(sorted({'torch', 'transformers', 'peft'} & set(sys.modules)))"
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert done.stdout.strip() == "[]"
