# Causalista

**English** · [Português](README.pt-BR.md)

[![tests](https://github.com/coppead/causalista/actions/workflows/tests.yml/badge.svg)](https://github.com/coppead/causalista/actions/workflows/tests.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Model](https://img.shields.io/badge/%F0%9F%A4%97%20Model-coppead%2Fcausalista--4b-yellow)](https://huggingface.co/coppead/causalista-4b)
[![GGUF](https://img.shields.io/badge/%F0%9F%A4%97%20GGUF-coppead%2Fcausalista--4b--GGUF-yellow)](https://huggingface.co/coppead/causalista-4b-GGUF)
[![Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Dataset-coppead%2Fcausalista--worlds-yellow)](https://huggingface.co/datasets/coppead/causalista-worlds)

A small, local, honest causal analyst. You hand it a table, say which column is the intervention and which is the outcome, and tell it what you know about how the data were generated. Causalista decides which columns to adjust for, a separate runner estimates the effect with a confidence interval, and when the data cannot answer it says **not identifiable** and explains what is missing.

It is a 4B-parameter model, a fine-tune of Qwen3-4B that runs on a laptop, trained on synthetic worlds with a known answer and scored by a verifier that knows the true causal graph. Release 0.1.0 (2026-10-24), from COPPEAD/UFRJ, Apache 2.0.

## Results

Final measurement: 505 never-seen worlds in each of three languages (1,515 in all), eight management themes, of which two themes and one language (Spanish) never appeared in training. Score: +1 for a valid adjustment set or a right abstention, −1 for a confident error, −0.5 for an undue abstention.

| Responder | Score | Accuracy | pt | en | es | Two unseen themes |
|---|---|---|---|---|---|---|
| Adjust for every column | −0.66 | 17% | 17% | 17% | 17% | 18% |
| Adjust for nothing (naive difference) | −0.95 | 2% | 2% | 2% | 2% | 2% |
| Qwen3-4B, untrained | −0.05 | 47% | 46% | 46% | 47% | 47% |
| **Causalista 4B (this release)** | **+0.98** | **99%** | 100% | 99% | 98% | 96% |
| 27B open model with reasoning, sample of 152 | +0.99 | 99% | 100% | 100% | 98% | 100% |

On 48 frozen cases that simulate text written by people, Causalista reaches 69% and the 27B model 96%: reading what a person writes is where the small model still fails. The protocol, every number and what is **not** claimed (no frontier model was measured; the human-like text is simulated; every number is on synthetic data with a known answer) are in the [model card](docs/cards/model-card.md).

## Quickstart

**With Ollama, no GPU needed.** Pull the 2.5 GB quantized model from the Hub once with [Ollama](https://ollama.com); the harness then runs it on five written cases, prints the scoreboard and records every answer under `outputs/runs/quickstart/`.

```bash
ollama pull hf.co/coppead/causalista-4b-GGUF
git clone https://github.com/coppead/causalista && cd causalista
uv sync --no-group train
uv run --no-sync python scripts/run_models.py --cases cases/fase0.yaml --name quickstart \
    --model ollama:hf.co/coppead/causalista-4b-GGUF:nothink
```

The scoreboard prints in Portuguese, the project's working language: `nota` is the score, `acerto` the accuracy, `erro confiante` a confident error, `abstenção indevida` an undue abstention. `--no-sync` keeps the light environment: without it, `uv run` installs the training group, torch included, because the project installs it by default for its own training.

**With transformers, on a GPU** (requires transformers 5.0 or later):

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from causalista.task import build_prompt, parse_answer

tok = AutoTokenizer.from_pretrained("coppead/causalista-4b")
model = AutoModelForCausalLM.from_pretrained("coppead/causalista-4b", dtype="bfloat16", device_map="auto")
prompt = build_prompt(task)   # a Task: question, story, column cards (see src/causalista/task/prompt.py)
text = tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False,
                               add_generation_prompt=True, enable_thinking=False)
out = model.generate(**tok(text, return_tensors="pt").to(model.device), max_new_tokens=2048, do_sample=False)
answer = parse_answer(tok.decode(out[0], skip_special_tokens=True).split(prompt)[-1], task)
```

**On your own table.** The model never sees the rows. Describe the table the way the written cases in [cases/](cases/) do (question, story of how the data were generated, one card per column), run the model, and hand the columns it chose to the runner in `causalista.estimator`, which reports the effect, its interval, the naive difference for contrast and the assumptions. The model was trained on one prompt format and on eight management themes; outside them, nothing here says how often it is right.

## How it works

1. **Verifier** ([src/causalista/verifier/](src/causalista/verifier/)): given the true causal graph, says whether a set of columns is a valid adjustment set, or that no set is. Two independent engines (adjustment criterion and path analysis) check each other; 24 textbook cases and a net of planted errors guard it.
2. **World factory** ([src/causalista/worlds/](src/causalista/worlds/)): from a reviewed theory sheet per theme ([theories/](theories/)), draws variables and their roles, generates the numbers and the true effect, and writes the story, one fact per sentence in Portuguese, English or Spanish, or in prose written by open models.
3. **Task** ([src/causalista/task/](src/causalista/task/)): the prompt the model sees, the JSON answer, the score, and the ideal answer derived from the verifier's key.
4. **Estimator** ([src/causalista/estimator/](src/causalista/estimator/)): a doubly robust estimator with cross-fitting (DoubleML) that turns the chosen columns into an effect and an interval.
5. **Harness** ([src/causalista/harness/](src/causalista/harness/)): runs any model (Hugging Face, Ollama, an API) over saved worlds or written cases and records every answer. The pages in [src/causalista/viz/](src/causalista/viz/) are generated from those records, never drawn by hand.
6. **Training** ([scripts/](scripts/)): supervised LoRA fine-tuning on 22,906 examples (Unsloth + TRL), then a short GRPO step whose only reward is the verifier's score on 208 cases that simulate text written by people. The choice between training arms followed a rule written before the results.

## Repository map

| Path | What it is |
|---|---|
| [ESPECIFICACAO.md](ESPECIFICACAO.md) | The specification: what is being built, in what order, and the record of each phase gate (Portuguese) |
| [src/causalista/](src/causalista/) | The package: verifier, worlds, estimator, task, harness, viz. Each folder opens with a README (Portuguese) |
| [theories/](theories/) | One theory sheet per theme, in YAML; translations under `theories/i18n/` |
| [cases/](cases/) | Written cases with the diagram's arrows and the answer checked by the verifier; `cases/simulados/` holds the 48 frozen measurement cases |
| [configs/](configs/) | Candidate base models, the train/test split of themes and seeds, the showcase worlds |
| [scripts/](scripts/) | World generation, training data, training, model runs, GGUF conversion, publication, reading material |
| [tests/](tests/) | Tests, mirroring `src/` |
| [docs/](docs/) | Project status and full account of decisions, neighbouring work, the Hugging Face cards ([docs/cards/](docs/cards/)) |
| `outputs/` | Everything generated (worlds, runs, weights, pages); not in git. The world sets, cases, training examples and recorded answers that the cards rely on are published in the dataset |

## Reproduce

Everything in the cards can be regenerated from this repository and the dataset. A plain `uv sync` installs the training stack too (CUDA GPU, about 7 GB); the training scripts are documented in [scripts/README-treino.md](scripts/README-treino.md) (Portuguese).

```bash
hf download coppead/causalista-worlds --repo-type dataset --include "worlds/placar-v3/*" --local-dir outputs   # a saved world set
uv run python scripts/run_models.py --worlds placar-v3 --every 20 --model hf:coppead/causalista-4b:nothink  # measure the released model on it
uv run python scripts/make_worlds.py --name my-set --pairs 13 --first-seed 50000                          # or generate new worlds
uv run python scripts/make_training_data.py --name sft-v1 --themes telecom varejo --pairs 2000 --languages pt en
uv run python scripts/train_sft.py --data outputs/train/data/sft-v1.jsonl --base Qwen/Qwen3-4B
uv run python scripts/train_grpo.py --base <merged supervised model> \
    --cases cases/treino-simulados/pt-0[1-9].yaml cases/treino-simulados/pt-1[0-6].yaml cases/treino-simulados/en-0[1-9].yaml cases/treino-simulados/en-10.yaml   # the 26 files used; pt-17, pt-18, en-11, en-12 were held out
uv run python -m causalista.viz.scoreboard --set placar-v3                                                 # the scoreboard page from the records
```

Seeds have reserved ranges per use (table in `scripts/make_worlds.py`); training never uses a seed below 100,000, and the frozen cases never enter training.

## Data and provenance

- Training targets always come from the verifier, never from a language model.
- The sentences of the training stories come from eight theory sheets written by a large language model from management theory, reviewed sentence by sentence by independent instances of the same model; prose stories were written by open models and kept only when two other open models agreed they were faithful. The human-like cases were written and reviewed by instances of a large language model. The cards record who wrote what.
- The author made the design decisions: the family of worlds and its ranges, the themes, the score weights, the base model, the training size and the measurement protocol. The project was built by the author with an AI coding assistant.
- Code, names and docstrings are in English; the specification, the status, the READMEs of the packages and the output of the scripts are in Portuguese, the working language of the project. Data files (`theories/`, `cases/`) and some scripts carry Portuguese names, following the specification's vocabulary.

## Documentation

- [ESPECIFICACAO.md](ESPECIFICACAO.md): the specification and the gate record (Portuguese).
- [docs/status.md](docs/status.md): the full account of what was done, measured and decided, day by day (Portuguese).
- [docs/trabalhos-vizinhos.md](docs/trabalhos-vizinhos.md): neighbouring work in the literature (Portuguese).
- [docs/cards/](docs/cards/): the model, GGUF and dataset cards (English, with a Portuguese opening).
- [CHANGELOG.md](CHANGELOG.md), [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md).

## Development

```bash
uv sync --no-group train               # runtime and tests, no torch
uv run --no-sync pytest                # the everyday suite (10 to 15 minutes: the worlds are tested on all eight themes)
uv run --no-sync pytest -m slow        # exhaustive: every graph of up to five variables (about 2 minutes)
```

Python 3.12. The pages need Graphviz (`sudo apt install graphviz`). Run the exhaustive suite after any change under `src/causalista/verifier/`. Work from a clone: the package reads `theories/` and `cases/` from the repository checkout, so the wheel alone serves only the verifier, the estimator and the task format.

## Citation

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

[CITATION.cff](CITATION.cff) carries the same data in the format GitHub reads.

## License

Apache 2.0 ([LICENSE](LICENSE)), like the base model Qwen3-4B.

## Acknowledgements

The Qwen team for the base model; Unsloth, TRL, PEFT and transformers for the training stack; DoubleML for the estimator; llama.cpp and Ollama for local inference; the Hugging Face Hub for hosting. Built by André Fonseca (COPPEAD/UFRJ) with an AI coding assistant.
