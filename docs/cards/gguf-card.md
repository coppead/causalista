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

| File | Size | Use |
|---|---|---|
| `causalista-4b-Q4_K_M.gguf` | 2.5 GB | default: fits a laptop or an 8 GB GPU |
| `causalista-4b-Q8_0.gguf` | 4.3 GB | closer to the full-precision model |

Made with llama.cpp (clone of 2026-10-18): the merged safetensors model converted to f16, then quantized with `llama-quantize`. The script is `scripts/make_gguf.sh` in the code repository.

**Check.** The Q4_K_M file, served by Ollama, answered 35 worlds of the development set (one in forty, three languages, one-fact-per-sentence and prose) with exactly the same outcome as the full-precision model: 35 correct of 35. The records are under `runs/gguf-check/` in the dataset.

## Running with Ollama

Straight from the Hub (Ollama picks the Q4_K_M file by default):

```bash
ollama run hf.co/coppead/causalista-4b-GGUF --think=false
```

The `params` file in this repository sets temperature 0 and a context of 8,192 tokens for that path. **Turn thinking off**: Ollama detects the thinking capability of the Qwen3 family and enables it by default, but the model was trained and measured answering directly, without a written reasoning step. In the API, send `"think": false`; in the interactive prompt, `/set nothink`.

Or download the Q4_K_M file and the `Modelfile`, which carry the same settings, and build a local model:

```bash
ollama create causalista:0.1 -f Modelfile
```

## Running with llama.cpp

The GGUF headers carry the sampling defaults of the base model at conversion time (temperature 0.6, top-k 20, top-p 0.95; `general.sampling.*`), and `llama-cli` and `llama-server` use them as defaults. The model was measured with greedy decoding, so pass `--temp 0` to reproduce it. The Ollama paths above are not affected: `params` and the `Modelfile` set the temperature to 0. The name embedded in the files (`general.name`) is the name of the training run, not of the model.

## The prompt

The model was trained on one prompt format: English instructions, then the question, the story of how the data were generated, and the column dictionary with a simple summary of each column, in the user's language. The answer is structured: the role of each column with a one-line reason, the verdict (identifiable by adjustment, or not identifiable with these columns), the adjustment set or what is missing, and the assumptions. The exact format, the parser and the scorer are in `src/causalista/task/` of the code repository, and `scripts/run_models.py --model ollama:causalista:0.1:nothink` (or `ollama:hf.co/coppead/causalista-4b-GGUF:nothink`) runs the model through the same harness used for every number in the model card.

The rows of the table never go to the model: a separate runner estimates the effect with the columns the model chose.

## What it is for

Deciding which columns to adjust for, or saying that the data cannot answer, in tables of the kind described by management theory: customer, employee, student or client records with an intervention and an outcome. It is not a general assistant and it was not measured on anything else.
