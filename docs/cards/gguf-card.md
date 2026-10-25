---
license: apache-2.0
base_model: coppead/causalista-4b
base_model_relation: quantized
quantized_by: coppead
pipeline_tag: text-generation
language:
  - pt
  - en
  - es
tags:
  - gguf
  - llama.cpp
  - ollama
  - causal-inference
---

# Causalista 4B, GGUF

Quantized files of [coppead/causalista-4b](https://huggingface.co/coppead/causalista-4b) for llama.cpp and Ollama. Read that model card for what the model does, how it was trained and measured, and what it does not claim. Code: [github.com/coppead/causalista](https://github.com/coppead/causalista); data and every recorded answer: [coppead/causalista-worlds](https://huggingface.co/datasets/coppead/causalista-worlds).

*Em português: versões quantizadas do Causalista 4B para rodar no Ollama ou no llama.cpp, em qualquer máquina. O cartão do modelo explica o que ele faz e como foi medido.*

- **Quantized by:** coppead (André Fonseca, COPPEAD Graduate School of Business, UFRJ)
- **From:** [coppead/causalista-4b](https://huggingface.co/coppead/causalista-4b), version 0.1.0 (2026-10-25); base `Qwen/Qwen3-4B`
- **License:** Apache 2.0 · **Contact:** https://github.com/coppead/causalista/issues

| File | Quant | Size | Use |
|---|---|---|---|
| [`causalista-4b-Q4_K_M.gguf`](https://huggingface.co/coppead/causalista-4b-GGUF/blob/main/causalista-4b-Q4_K_M.gguf) | Q4_K_M | 2.5 GB | default: fits a laptop or an 8 GB GPU; verified against the full model (35 of 35, below) |
| [`causalista-4b-Q8_0.gguf`](https://huggingface.co/coppead/causalista-4b-GGUF/blob/main/causalista-4b-Q8_0.gguf) | Q8_0 | 4.3 GB | near-lossless, for machines with the memory |

Download one file: `uvx --from huggingface_hub hf download coppead/causalista-4b-GGUF --include "*Q4_K_M*" --local-dir .`

Made with llama.cpp at commit `5aeac37` (0.7.0-dev, checkout of 2026-10-18): the merged safetensors model converted to f16 with `convert_hf_to_gguf.py --outtype f16`, then quantized with `llama-quantize` to Q4_K_M and Q8_0, without an importance matrix. The script is `scripts/make_gguf.sh` in the code repository.

**Check.** The Q4_K_M file, served by Ollama, answered 35 worlds of the development set (one in forty, three languages, one-fact-per-sentence and prose) with exactly the same outcome as the full-precision model: 35 correct of 35. The records are under `runs/gguf-check/` in the dataset.

## Running with Ollama

Pull straight from the Hub (Ollama picks the Q4_K_M file by default; the `params` file in this repository sets temperature 0, a context of 8,192 tokens and the stop tokens for that path), then use the harness or `scripts/ask.py` from the code repository, which send the model exactly the prompt it was trained and measured on:

```bash
ollama pull hf.co/coppead/causalista-4b-GGUF
uv run --no-sync python scripts/run_models.py --cases cases/fase0.yaml --name quickstart --model ollama:hf.co/coppead/causalista-4b-GGUF:nothink
```

Checked on 2026-10-25 with Ollama 0.32.15, as an anonymous visitor: the five cases of the quickstart come back correct, 182 to 228 tokens each, with the same parsed answers as a local copy built from the `Modelfile`.

**Thinking must be off, and Ollama's `think: false` does not do it for this model.** The model was trained and measured answering directly, with the thinking block closed in the prompt (`<think>\n\n</think>\n\n` right after `<|im_start|>assistant`, which is what `enable_thinking=False` produces). In Ollama 0.32.15, `ollama run ... --think=false`, `/set nothink` and `"think": false` in `/api/chat` leave that block open or absent for this model (checked by counting prompt tokens: the prompt then ends at `<|im_start|>assistant` or at `<think>`); the model opens `<think>` by itself and writes about a thousand tokens of reasoning before the JSON. On the five quickstart cases the answers were still correct, but that is not the measured setting, and it is five to ten times slower. The harness and `scripts/ask.py` therefore render the prompt themselves and send it through `/api/generate` with `raw: true`. Do the same in your own code:

```python
import requests
prompt = f"<|im_start|>user\n{task_text}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
reply = requests.post("http://localhost:11434/api/generate", json={
    "model": "hf.co/coppead/causalista-4b-GGUF", "prompt": prompt, "raw": True, "stream": False,
    "options": {"temperature": 0, "num_ctx": 8192}}).json()["response"]
```

A `TEMPLATE` line in a Modelfile does not change this: Ollama prefers the chat template embedded in the GGUF when there is one (its log says `template selection ... selected=gguf_chat_template`). The `Modelfile` in this repository still builds a local copy with the same temperature, context and stop tokens (`ollama create causalista:0.1 -f Modelfile`); use it through the harness, as above.

## Running with llama.cpp

The GGUF headers carry the sampling defaults of the base model at conversion time (temperature 0.6, top-k 20, top-p 0.95; `general.sampling.*`), and `llama-cli` and `llama-server` use them as defaults. The model was measured with greedy decoding and thinking off, so pass both:

```bash
llama-cli -hf coppead/causalista-4b-GGUF:Q4_K_M --temp 0 --reasoning-budget 0
llama-server -hf coppead/causalista-4b-GGUF:Q4_K_M --temp 0 --chat-template-kwargs '{"enable_thinking": false}'
```

(flags as documented by llama.cpp; this project ran the quantized files through Ollama only). The Ollama paths above are not affected: `params` and the `Modelfile` set the temperature to 0 and the harness sends `think: false`. The name embedded in the files (`general.name`) is the name of the training run, not of the model.

## The prompt format

The chat template is Qwen3's (ChatML). With thinking off, the prompt the model was trained on ends like this:

```
<|im_start|>user
{the task: instructions, question, story, column dictionary}<|im_end|>
<|im_start|>assistant
<think>

</think>

```

## What goes into the prompt

The model was trained on one prompt format: English instructions, then the question, the story of how the data were generated, and the column dictionary with a simple summary of each column, in the user's language. The answer is structured: the role of each column with a one-line reason, the verdict (identifiable by adjustment, or not identifiable with these columns), the adjustment set or what is missing, and the assumptions. The exact format, the parser and the scorer are in `src/causalista/task/` of the code repository, and `scripts/run_models.py --model ollama:causalista:0.1:nothink` (or `ollama:hf.co/coppead/causalista-4b-GGUF:nothink`) runs the model through the same harness used for every number in the model card.

The rows of the table never go to the model: a separate runner estimates the effect with the columns the model chose.

## What it is for

Deciding which columns to adjust for, or saying that the data cannot answer, in tables of the kind described by management theory: customer, employee, student or client records with an intervention and an outcome. It is not a general assistant and it was not measured on anything else.
