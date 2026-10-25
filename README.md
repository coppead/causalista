# Causalista

**English** · [Português](README.pt-BR.md)

[![tests](https://github.com/coppead/causalista/actions/workflows/tests.yml/badge.svg)](https://github.com/coppead/causalista/actions/workflows/tests.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](pyproject.toml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/coppead/causalista)](https://github.com/coppead/causalista/releases)
[![Model](https://img.shields.io/badge/%F0%9F%A4%97%20Model-coppead%2Fcausalista--4b-yellow)](https://huggingface.co/coppead/causalista-4b)
[![GGUF](https://img.shields.io/badge/%F0%9F%A4%97%20GGUF-coppead%2Fcausalista--4b--GGUF-yellow)](https://huggingface.co/coppead/causalista-4b-GGUF)
[![Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Dataset-coppead%2Fcausalista--worlds-yellow)](https://huggingface.co/datasets/coppead/causalista-worlds)

> **Working language.** Code, identifiers, this README and the Hugging Face cards are in English. The specification, the project log, the package READMEs, the data files and the scripts' console output are in Portuguese, the project's working language; [docs/README.md](docs/README.md) indexes them in English.

A small, local causal analyst that says when it cannot answer. You describe a table (its columns and how the data were generated) and name the intervention and the outcome columns. Causalista decides which columns to adjust for; a separate estimator then computes the effect with a confidence interval. When the data cannot answer the question, it says **not identifiable** and explains what is missing. The model never sees the rows.

It is a 4B-parameter fine-tune of Qwen3-4B that runs on a laptop, trained on synthetic worlds with known answers and scored by a verifier that knows the true causal graph. Model version 0.1.0 was released on 2026-10-25 by COPPEAD/UFRJ (the business school of the Federal University of Rio de Janeiro) under Apache 2.0; the code is at version 0.1.1 ([CHANGELOG](CHANGELOG.md)).

## Results

Final evaluation: 505 held-out worlds in each of three languages (1,515 in total) across eight management themes; two of the themes and one of the languages (Spanish) never appeared in training. Score per world: +1 for a valid adjustment set or a correct abstention, −1 for a confident error, −0.5 for an undue abstention; the table shows the mean. One training run (seed 0) and greedy decoding, so the evaluation is deterministic; at 99% accuracy on 1,515 worlds the binomial 95% interval is about ±0.5 points.

| System | Score | Accuracy | pt | en | es | Held-out themes (381) |
|---|---|---|---|---|---|---|
| Adjust for every column | −0.66 | 17% | 17% | 17% | 17% | 18% |
| Adjust for nothing (naive difference) | −0.95 | 2% | 2% | 2% | 2% | 2% |
| Qwen3-4B (base, no fine-tuning) | −0.05 | 47% | 46% | 46% | 47% | 47% |
| **Causalista 4B (this release)** | **+0.98** | **99%** | 100% | 99% | 98% | 96% |
| Qwen3.8 27B, reasoning on (`qwen3.8:27b` through Ollama), 152-world sample | +0.99 | 99% | 100% | 100% | 98% | 100% (37) |

On 48 frozen cases written to imitate human prose (e-mails, chat messages, meeting notes), Causalista scores 69% and the 27B model 96%: reading free text is where the small model still falls short. The protocol, every number and what is **not** claimed (no frontier model was measured; the human-like text is simulated; every number is on synthetic data with a known answer) are in the [model card](docs/cards/model-card.md). Every answer behind every number is recorded in the [dataset](https://huggingface.co/datasets/coppead/causalista-worlds), under `runs/`.

## Quickstart

**With Ollama, no GPU needed.** Pull the 2.5 GB quantized model once from the Hub with [Ollama](https://ollama.com); the harness then runs it on five written cases, prints the scoreboard and records every answer under `outputs/runs/quickstart/`.

```bash
ollama pull hf.co/coppead/causalista-4b-GGUF
git clone https://github.com/coppead/causalista && cd causalista
uv sync --no-group train
uv run --no-sync python scripts/run_models.py --cases cases/fase0.yaml --name quickstart \
    --model ollama:hf.co/coppead/causalista-4b-GGUF:nothink
```

The scoreboard prints in English (in Portuguese when your locale is `pt`): score, accuracy, confident errors, undue abstentions, invalid answers, and how many cases were answered. The responder label ends in `(sem raciocínio)`, "without reasoning", the mode the model was trained in. Keep `--no-sync`: without it, `uv run` would install the training group (torch included, about 7 GB), which the project enables by default for its own training runs. Prefer the harness or `scripts/ask.py` to `ollama run` for this model: Ollama's own `--think=false` does not close the thinking block for it (Ollama 0.32), so the model reasons for about a thousand tokens before answering; the harness sends the exact prompt the model was trained on (details in the [GGUF card](docs/cards/gguf-card.md)).

**On your own data.** `scripts/ask.py` builds the task from a CSV, a short story of how the data were generated and a one-sentence dictionary of the columns, asks the model, reads its answer and, when the effect is identifiable, runs the estimator on the rows:

```bash
uv run --no-sync python scripts/ask.py --csv campaign.csv --treatment email --outcome bought \
    --story story.txt --dictionary columns.yaml --model ollama:hf.co/coppead/causalista-4b-GGUF:nothink
```

```
Verdict: identifiable by adjustment
Adjust for: prior_purchases
Column roles:
  customer_id: neutral. It identifies only one customer.
  prior_purchases: confounder. It influences email and it influences bought.
  visited_site: mediator. It is a consequence of email and it influences bought: it is part of the effect.
Assumptions:
  - Nothing other than what was described influences both email and bought.
  - The story says correctly what came before and what came after email.
Adjusted effect: +0.1271  (95% interval [+0.0971, +0.1570]; 5000 rows; doubly robust with cross-fitting (5 folds, boosting learners))
Naive difference: +0.1998  (95% interval [+0.1754, +0.2242])
share of rows with near-certain treatment (overlap warning): 1.1%
```

The intervention column must hold 0 and 1; every column needs a description (`--dictionary` as YAML or JSON, or repeated `--column name="..."`); `--json record.json` saves the prompt, the raw answer and the estimate. The same thing from Python is `causalista.harness.ask(table, treatment, outcome, story, descriptions, responder)`. The model was trained on one prompt format and on six of the project's eight management themes; outside them, we make no claim about how often it is right.

**With transformers, on a GPU** (requires transformers 5.0 or later):

```python
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from causalista.harness import case_worlds
from causalista.task import build_prompt, parse_answer

task = case_worlds([Path("cases/fase0.yaml")])[0].task          # the first written case; or make_task(...) for your own
tok = AutoTokenizer.from_pretrained("coppead/causalista-4b")
model = AutoModelForCausalLM.from_pretrained("coppead/causalista-4b", dtype="bfloat16", device_map="auto")
prompt = build_prompt(task)
text = tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False,
                               add_generation_prompt=True, enable_thinking=False)
out = model.generate(**tok(text, return_tensors="pt").to(model.device), max_new_tokens=2048, do_sample=False)
answer = parse_answer(tok.decode(out[0], skip_special_tokens=True).split(prompt)[-1], task)
```

## How it works

1. **Verifier** ([src/causalista/verifier/](src/causalista/verifier/)): given the true causal graph, says whether a set of columns is a valid adjustment set, or that no set is. Two independent engines (the adjustment criterion and path analysis) cross-check each other; 24 textbook cases and a safety-net suite with planted errors guard it.
2. **World factory** ([src/causalista/worlds/](src/causalista/worlds/)): from a reviewed theory sheet per theme ([theories/](theories/)), samples variables and their causal roles, simulates the data and the true effect, and writes the story either one fact per sentence (in Portuguese, English or Spanish) or as prose written by open models.
3. **Task** ([src/causalista/task/](src/causalista/task/)): the prompt the model sees, the JSON answer, the score, and the reference answer derived from the verifier's answer key.
4. **Estimator** ([src/causalista/estimator/](src/causalista/estimator/)): a doubly robust estimator with cross-fitting (DoubleML) that turns the chosen columns into an effect estimate and a confidence interval.
5. **Harness** ([src/causalista/harness/](src/causalista/harness/)): runs any model (Hugging Face, Ollama, or an OpenAI-compatible API) over saved worlds or written cases and records every answer. The pages in [src/causalista/viz/](src/causalista/viz/) are generated from those records, never drawn by hand.
6. **Training** ([scripts/](scripts/)): supervised fine-tuning with LoRA (low-rank adapters) on 22,906 examples (Unsloth + TRL), then a short GRPO step (group relative policy optimization, a reinforcement-learning method) whose only reward is the verifier's score on 208 cases that simulate text written by people. The choice between the two training arms followed a rule fixed before the results were seen ([model card](docs/cards/model-card.md)).

## Repository layout

| Path | What it is |
|---|---|
| [ESPECIFICACAO.md](ESPECIFICACAO.md) | The specification: what is being built, in what order, and the record of each milestone check (Portuguese) |
| [src/causalista/](src/causalista/) | The package: verifier, worlds, estimator, task, harness, viz. Each folder opens with a README (Portuguese) |
| [theories/](theories/) | One theory sheet per theme, in YAML, with Portuguese file names; translations under `theories/i18n/` ([README](theories/README.md)) |
| [cases/](cases/) | Written cases with the diagram's arrows and the answer checked by the verifier; `cases/simulados/` holds the 48 frozen measurement cases ([README](cases/README.md)) |
| [configs/](configs/) | Candidate base models, the train/test split of themes and seeds, the showcase worlds ([README](configs/README.md)) |
| [scripts/](scripts/) | World generation, training data, training, model runs, `ask.py`, GGUF conversion, publication ([README](scripts/README.md)) |
| [tests/](tests/) | Tests, mirroring `src/` |
| [docs/](docs/) | Project log and the Hugging Face cards ([docs/cards/](docs/cards/)); index in [docs/README.md](docs/README.md) |
| `outputs/` | Everything generated (worlds, runs, weights, pages); not in git. The world sets, cases, training examples and recorded answers that the cards rely on are published in the dataset |

## Reproducing the results

Every number in the model and dataset cards can be regenerated from this repository and the dataset. A plain `uv sync` installs the training stack too (CUDA GPU, about 7 GB); the training scripts are documented in [scripts/README-treino.md](scripts/README-treino.md) (Portuguese). The `hf` command below comes from `huggingface_hub`, which is not in the light environment: run it with `uvx --from huggingface_hub hf ...`.

```bash
# the saved sets behind the tables (final test: teste-v3; development: placar-v3)
uvx --from huggingface_hub hf download coppead/causalista-worlds --repo-type dataset --include "worlds/teste-v3/*" --local-dir outputs

# the rows of the results table (hf: needs a GPU; the 27B comparator runs through Ollama, thinking on, 1 world in 10)
uv run python scripts/run_models.py --worlds teste-v3 --model rule:all --model rule:none \
    --model hf:Qwen/Qwen3-4B:nothink --model hf:coppead/causalista-4b:nothink
uv run python scripts/run_models.py --worlds teste-v3 --every 10 --model ollama:qwen3.8:27b
uv run python scripts/run_models.py --cases cases/simulados/*.yaml --name casos-simulados --model hf:coppead/causalista-4b:nothink
uv run python scripts/summarise_runs.py --set teste-v3 --markdown

# the published training run (the data file is examples/sft-final.jsonl in the dataset; seed 0; the exact
# arguments and versions are recorded in training/sft/run.json and training/grpo-c/run.json in the model repository)
uv run python scripts/train_sft.py --data outputs/train/data/sft-final.jsonl --base Qwen/Qwen3-4B --run-name sft-final-qwen3-4b --epochs 1
uv run python scripts/train_grpo.py --base <merged supervised model> \
    --cases cases/treino-simulados/pt-0[1-9].yaml cases/treino-simulados/pt-1[0-6].yaml cases/treino-simulados/en-0[1-9].yaml cases/treino-simulados/en-10.yaml

# new worlds and the pages
uv run python scripts/make_worlds.py --name my-set --pairs 13 --first-seed 50000
uv run python -m causalista.viz.scoreboard --set teste-v3
```

Each use (pages, estimator gate, baseline, final test, training) has its own reserved seed range (table in `scripts/make_worlds.py`); training never uses a seed below 100,000, and the frozen cases never enter training. No hyperparameter search was run: the training scripts' defaults were used.

## Data and provenance

- Training targets always come from the verifier, never from a language model.
- The sentences of the training stories come from eight theory sheets that a large language model wrote from the management literature and that independent instances of the same model reviewed sentence by sentence; prose stories were written by open models and kept only when two other open models agreed they were faithful. The human-like cases were written and reviewed by instances of a large language model. The cards record who wrote what.
- The author made the design decisions: the family of worlds and its ranges, the themes, the score weights, the base model, the training size and the measurement protocol. The project was built by the author with an AI coding assistant.
- Code, identifiers and docstrings are in English. The specification, the project log, the package READMEs, the data files (`theories/`, `cases/`, whose names follow the specification's vocabulary) and the scripts' Portuguese labels in the records are in Portuguese, the project's working language.

## Documentation

- [docs/README.md](docs/README.md): an index, in English, of every document and data folder.
- [ESPECIFICACAO.md](ESPECIFICACAO.md): the specification and the milestone record (Portuguese).
- [docs/status.md](docs/status.md): the project's working log, day by day (Portuguese); the cards summarise it.
- [docs/trabalhos-vizinhos.md](docs/trabalhos-vizinhos.md): neighbouring work in the literature (Portuguese).
- [docs/cards/](docs/cards/): the model, GGUF and dataset cards (English, with a Portuguese opening).
- [CHANGELOG.md](CHANGELOG.md), [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md).

## Development

```bash
uv sync --no-group train               # runtime and tests, no torch
uv run --no-sync pytest                # the default suite (10 to 15 minutes: the worlds are tested on all eight themes)
uv run --no-sync pytest -m slow        # exhaustive: every graph of up to five variables (about 2 minutes)
```

Python 3.12. The pages need Graphviz (`sudo apt install graphviz`). Run the exhaustive suite after any change under `src/causalista/verifier/`. Work from a clone: the package reads `theories/` and `cases/` from the repository checkout, so the wheel on its own provides only the verifier, the estimator and the task format. The package can also be installed with `pip install git+https://github.com/coppead/causalista`.

## Authors and contact

André Fonseca, COPPEAD Graduate School of Business, Federal University of Rio de Janeiro (UFRJ). Questions, problems and ideas: [open an issue](https://github.com/coppead/causalista/issues); security problems through the repository's [private reporting channel](SECURITY.md).

## Citation

```bibtex
@software{fonseca2026causalista,
  author    = {Fonseca, André},
  title     = {Causalista: a small, local model that decides what to adjust for and says when the data cannot answer},
  year      = {2026},
  version   = {0.1.1},
  publisher = {COPPEAD/UFRJ},
  url       = {https://github.com/coppead/causalista},
  note      = {Model: \url{https://huggingface.co/coppead/causalista-4b}}
}
```

[CITATION.cff](CITATION.cff) carries the same data in the format GitHub reads.

## License

Apache 2.0 ([LICENSE](LICENSE)), like the base model Qwen3-4B.

## Acknowledgements

The Qwen team for the base model; Unsloth, TRL, PEFT and transformers for the training stack; DoubleML for the estimator; llama.cpp and Ollama for local inference; the Hugging Face Hub for hosting. Built by André Fonseca (COPPEAD/UFRJ) with an AI coding assistant.
