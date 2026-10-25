---
license: apache-2.0
base_model: Qwen/Qwen3-4B
base_model_relation: finetune
language:
  - pt
  - en
  - es
library_name: transformers
pipeline_tag: text-generation
datasets:
  - coppead/causalista-worlds
tags:
  - causal-inference
  - management
  - adjustment-set
  - abstention
  - synthetic-data
---

# Causalista 4B

A small, local model for one decision in causal analysis. Give it a table's column dictionary, say which column is the intervention and which is the outcome, and tell it how the data were generated. It answers which columns to adjust for to measure the average effect, or says that the effect is **not identifiable** with these columns and names what is missing. It never sees the rows: a separate runner, included in the code repository, estimates the effect with the columns the model chose.

*Em português: um modelo pequeno, que roda na máquina da pessoa, treinado para uma decisão só: diante do dicionário de uma tabela e da história de como os dados foram gerados, dizer por quais colunas ajustar para medir o efeito de uma intervenção, ou dizer que não dá e o que falta. A conta é feita por um programa separado. Código, dados e páginas: [github.com/coppead/causalista](https://github.com/coppead/causalista) e [coppead/causalista-worlds](https://huggingface.co/datasets/coppead/causalista-worlds).*

It is the 0.1 release of the Causalista project at COPPEAD/UFRJ: Qwen3-4B, fine-tuned with supervision on 22,906 synthetic worlds with a known answer, then pushed for a short reinforcement step in which the only reward was the verifier's score on cases that simulate text written by people. Everything about it is reproducible from the code repository ([github.com/coppead/causalista](https://github.com/coppead/causalista)) and the dataset ([coppead/causalista-worlds](https://huggingface.co/datasets/coppead/causalista-worlds)); quantized GGUF files are in [coppead/causalista-4b-GGUF](https://huggingface.co/coppead/causalista-4b-GGUF).

## The task

**The model sees**: the question (the average effect of column T on column Y), a story of how the data were generated (who received the intervention and why, what was measured before and after it, what is known not to be in the table), and the column dictionary with a simple summary of each column. Instructions are in English; story and dictionary are in the user's language (trained in Portuguese and English; Spanish was never trained and is reported as a transfer test).

**The model answers**, in JSON: the role of each column (confounder, mediator, collider or neutral) with a one-line reason; the verdict (`identifiable` by adjustment, or `not_identifiable` with these columns); the adjustment set, or what is missing; and the assumptions it relies on.

**The runner** then estimates the effect with the chosen columns, using a doubly robust estimator with cross-fitting (DoubleML's interactive regression model), and reports the effect, its interval, the naive difference for contrast, and the assumptions. When the verdict is "not identifiable", the report says why and what data would resolve it.

The prompt builder, the answer parser and the scorer are in `src/causalista/task/` of the code repository. An answer is scored by a verifier that knows the true causal graph: +1 when the adjustment set is valid (or when the abstention is right), −1 for a confident error (asserting an effect with a biased set, or when the effect is not identifiable), −0.5 for an undue abstention, −1 for an answer the runner cannot use.

## Training

| | |
|---|---|
| Base | [Qwen/Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B), revision `1cfa9a72` |
| Method | supervised fine-tuning with LoRA (rank 16, alpha 16, all linear projections), loss on the answer only |
| Examples | 22,906: 19,814 stories told one fact per sentence (9,719 pt, 10,095 en) and 3,092 in prose written by open models (1,943 pt, 1,149 en), from six management themes (telecom churn, retail, bank credit, subscription software, HR, education) |
| Targets | the ideal answer derived from the verifier's answer key; no answer was written by a language model |
| Schedule | 1 epoch, 1,432 steps, batch 16, learning rate 2e-4 linear with 5% warm-up, bf16, Unsloth + TRL |
| Hardware | one RTX 4090, 2 h 22 min |
| Reinforcement step | GRPO with the verifier's score as the only reward (Dr. GRPO loss, no KL term): 8 answers per case, 2 cases per step, learning rate 2e-5; stopped by the guard against collapsing into abstention at step 20, after 14 minutes |
| Reinforcement data | 208 cases that simulate text written by people (128 pt, 80 en), `cases/treino-simulados/` in the dataset; 32 more cases were held out as a development test |
| Published weights | the base with both adapters merged (safetensors); the two adapters under `adapter/sft` and `adapter/grpo-c`; the training records and the record of the model choice under `training/` |

Two themes, e-mail marketing and private health insurance, were held out of training entirely, as were the 888 graph structures of the two test sets. The exact training file is `examples/sft-final.jsonl` in the dataset.

**Reinforcement learning.** The plan was supervised training followed by reinforcement with the verifier's score as the only reward (GRPO). On 2026-10-07, three runs on synthetic worlds taught nothing: from the supervised model, 200 steps changed nothing measurable (it already answered the synthetic worlds almost perfectly); from the untrained base, with and without a written reasoning step, the runs were stopped by the guard against collapsing into "not identifiable" after 35 and 28 steps. Reinforcement only has something to teach where the model still errs, and that is text that imitates people (67% for the supervised model). So on 2026-10-18 two arms were trained on 208 such cases, starting from the supervised model: **C**, reinforcement with the verifier's score (this model), and **D**, supervised training on the same 208 cases with their ideal answers. The choice between the supervised model, C and D followed a rule written before the results: the highest score on 32 held-out cases, provided the arm loses no more than 2 points of accuracy on the synthetic development set. D reached 94% on the 32 cases but lost 5 points on the synthetic worlds and was excluded by the rule; C reached 75% against 72% for the supervised model, with no loss, and was chosen. The honest summary: the reinforcement step moved one case in 32 and, on the final measurement below, one case in 48, and it was stopped early by the guard. All runs are recorded in the repository.

## Compute and environmental impact

One RTX 4090 for the two published runs: 2 h 22 min of supervised training and 14 min of reinforcement, about 1.2 kWh at the card's rated power as an upper bound, not counting the exploratory runs recorded in the repository. Emissions depend on the local grid and were not estimated.

## Evaluation

All numbers come from the harness in the repository, with the same prompt and the same runner for every responder; every answer is recorded in the dataset under `runs/`. Comparators: "adjust for everything" (what estimation libraries do when given all columns), "adjust for nothing" (the naive difference), the base model without training, and a larger open model with reasoning (Qwen3.8 27B, through Ollama) on samples. A frontier model was not measured.

The measurement protocol was written before the results (section 31 of `docs/status.md` in the repository, amended on 2026-10-07 for the arms trained on cases). The development set `placar-v3` and the 32 held-out cases were looked at freely. The final test `teste-v3` was opened once, on 2026-10-18, for the table below. The 48 cases that simulate text written by people were frozen before any model answered them and never used for tuning; the supervised model, the base and the comparators had been measured on them once during development, against the protocol, and this model was measured on them only after being chosen by the rule.

### Final test: 505 worlds in each language, eight themes, one fact per sentence

Two of the eight themes never appeared in training; Spanish never appeared in training.

| Responder | Score | Accuracy, 1,515 worlds | Portuguese | English | Spanish (never trained) | Two themes never trained (381) | Not-identifiable worlds |
|---|---|---|---|---|---|---|---|
| Adjust for everything | −0.66 | 17% | 17% | 17% | 17% | 18% | 0% |
| Adjust for nothing | −0.95 | 2% | 2% | 2% | 2% | 2% | 0% |
| Base without training (Qwen3-4B) | −0.05 | 47% | 46% | 46% | 47% | 47% | 4% |
| Supervised model only | +0.98 | 99% | 100% | 98% | 98% | 96% | 100% |
| **This model** (supervised + reinforcement step) | +0.98 | 99% | 100% | 99% | 98% | 96% | 100% |
| Qwen3.8 27B with reasoning, 1 world in 10 (152) | +0.99 | 99% | 100% | 100% | 98% | 100% (37) | 100% |

This model made two undue abstentions (0.1%) and no invalid answer; its other 14 errors are confident errors in identifiable worlds. All 16 errors are in English and Spanish.

### Development set: 384 worlds in each language, plus prose

Accuracy of this model and, in parentheses, of the base without training:

| Story | Portuguese | English | Spanish (never trained) |
|---|---|---|---|
| One fact per sentence, 384 worlds | 100% (47%) | 98% (47%) | 98% (46%) |
| Prose written by a model reserved for tests | 96% (39%), 113 worlds | 98% (35%), 116 worlds | not available |

Mean score over the 1,381 worlds: +0.97 for the supervised model, −0.09 for the base; on the 384 Portuguese one-fact worlds, −0.77 for "adjust for everything" and −0.93 for "adjust for nothing". This model, after the reinforcement step: 98% over the 1,381 worlds, 100% in Portuguese one fact per sentence, 96% in Portuguese prose. The 27B open model with reasoning answered all 153 worlds of its sample correctly (96 one fact per sentence, 57 prose).

### 32 held-out cases that simulate text written by people (development)

| Responder | Score | Accuracy |
|---|---|---|
| Supervised model only | +0.48 | 72% |
| **This model** (arm C) | +0.56 | 75% |
| Arm D, supervised on the 208 cases | +0.91 | 94%, but 95% instead of 100% on the synthetic worlds: excluded by the rule |

### 48 cases that simulate text written by people

E-mails, chat messages, meeting notes and report excerpts, written by a large language model in the role of managers and analysts, on themes inside and outside the eight; 24 in Portuguese, 16 in English, 8 in Spanish. **They are not text written by people.**

| Responder | Score | Accuracy | pt | en | es |
|---|---|---|---|---|---|
| Adjust for everything | −1.00 | 0% | 0% | 0% | 0% |
| Adjust for nothing | −0.75 | 12% | 12% | 12% | 12% |
| Base without training | +0.05 | 52% | 50% | 56% | 50% |
| Supervised model only | +0.36 | 67% | 75% | 56% | 62% |
| **This model** (supervised + reinforcement step) | +0.41 | 69% | 75% | 62% | 62% |
| Qwen3.8 27B with reasoning | +0.92 | 96% | 100% | 94% | 88% |

The supervised model's 16 errors: 8 times it left out a confounder that was stated indirectly; 5 times it asserted an effect in a case that was not identifiable (none in Portuguese); 3 times it abstained without need. The reinforcement step fixed one English case.

### What the numbers say

In synthetic worlds, including two themes and a language it never saw, this 4B model matches a 27B open model and is far above the base and the naive strategies. In text that imitates people, it is 27 points below the 27B model: reading what a person writes is where it still fails, and that is the frontier of the project. The reinforcement step, the project's thesis, changed one case in 32 and one in 48; the supervised arm trained on the same cases learned far more about that text (94% on the 32 cases) at the cost of 5 points on the synthetic worlds, which suggests that the next step is supervised training that mixes both kinds of story, not more reinforcement on this signal.

### Bias, risks and limitations

The model gives a confident, structured answer to any table that fits the prompt format, including tables far from the eight management themes it was trained on; outside that family, nothing here says how often it is right. Its answer is a decision a person may act on, so the runner reports the assumptions with every estimate and the record of every measured answer is public. The stories it was trained on were written by language models from theory sheets, and the "human" text it was measured on is simulated; both carry the biases of the models that wrote them.

**What is not claimed:**

- That the model beats a frontier model: no frontier model was measured.
- That it reads real text written by people: the cases are simulated by a language model.
- That it recovers effects of real experiments: every number above is on synthetic data with a known answer.
- The task is not hard for large models: a 27B open model answers nearly every synthetic world. The result is about what a small local model can learn from a verifiable signal, not about the state of the art.

## How to use

The model expects the exact prompt format it was trained on. The simplest path is the harness in the code repository, which builds the prompt from a saved world or a written case and runs the model locally:

```bash
uv sync
hf download coppead/causalista-worlds --repo-type dataset --include "worlds/placar-v3/*" --local-dir outputs
uv run python scripts/run_models.py --worlds placar-v3 --every 20 --model hf:coppead/causalista-4b:nothink
```

With `transformers` directly, build the prompt with the package and decode greedily, with thinking turned off. **Requires transformers 5.0 or later**: the files were saved with 5.5; with 4.x the tokenizer does not load and `config.json` is read with the wrong `rope_theta`, which degrades the output silently.

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from causalista.task import build_prompt, parse_answer   # pip install git+https://github.com/coppead/causalista

tok = AutoTokenizer.from_pretrained("coppead/causalista-4b")
model = AutoModelForCausalLM.from_pretrained("coppead/causalista-4b", dtype="bfloat16", device_map="auto")
prompt = build_prompt(task)   # a Task: question, story, column cards (see src/causalista/task/prompt.py)
text = tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False,
                               add_generation_prompt=True, enable_thinking=False)
out = model.generate(**tok(text, return_tensors="pt").to(model.device), max_new_tokens=2048, do_sample=False)
answer = parse_answer(tok.decode(out[0], skip_special_tokens=True).split(prompt)[-1], task)
```

The rows of the table never go to the model. To get the effect, give the chosen columns to the runner (`causalista.estimator`).

**The adapters.** `adapter/sft` is a LoRA adapter on `Qwen/Qwen3-4B`. `adapter/grpo-c` is a LoRA adapter on the *supervised model*, that is, on the base with `adapter/sft` already merged; it is not an adapter on the bare base. Its `adapter_config.json` names the local folder where that merged model lived during training, so load it by passing the model object to PEFT instead of relying on that path:

```python
from peft import PeftModel
base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-4B", dtype="bfloat16", device_map="auto")
supervised = PeftModel.from_pretrained(base, "coppead/causalista-4b", subfolder="adapter/sft").merge_and_unload()
published = PeftModel.from_pretrained(supervised, "coppead/causalista-4b", subfolder="adapter/grpo-c")
```

The merged `model.safetensors` at the root of this repository is exactly that result, so most users need neither adapter.

## Provenance

- Answers used in training always come from the verifier, never from a language model.
- The sentences of the training stories come from eight theory cards written by a large language model from management theory; one was approved by the author, seven were reviewed sentence by sentence by independent instances of the same model and approved by delegation. Prose was written by open models (Qwen3 14B, Gemma 4 26B) and kept only when two other open models agreed it was faithful.
- The simulated human-like cases, both the 208 used in the reinforcement step and the 48 used for measurement, were written and reviewed by instances of a large language model.
- The author made the design decisions: the family of worlds and its ranges, the themes, the score weights, the base model, the training size and the measurement protocol.

Full history, decisions and every measurement: `docs/status.md` in the repository (in Portuguese).

## License and citation

Apache 2.0, like the base model.

```bibtex
@software{fonseca2026causalista,
  author    = {Fonseca, André},
  title     = {Causalista: a small, local model that decides what to adjust for, and says when the data cannot answer},
  year      = {2026},
  version   = {0.1.0},
  publisher = {COPPEAD/UFRJ},
  url       = {https://github.com/coppead/causalista},
  note      = {Model: \url{https://huggingface.co/coppead/causalista-4b}}
}
```

Questions and problems: open an issue at https://github.com/coppead/causalista/issues.
