# Scripts

Command-line entry points; every one has a docstring and `--help` in English. Run them with `uv run python scripts/<name>.py` (or `uv run --no-sync` in an environment installed without the training group).

| Script | What it does |
|---|---|
| `ask.py` | Asks the model about a table of your own (CSV, story, column dictionary) and runs the estimator on its answer |
| `run_models.py` | Runs responders (naive rules, Ollama, Hugging Face, OpenAI-compatible APIs) over a saved set of worlds or over written cases, records every answer under `outputs/runs/<set>/` and prints the scoreboard |
| `summarise_runs.py` | Prints the scoreboard of a saved set of runs, by language and kind of story |
| `make_worlds.py` | Generates a set of synthetic worlds (the seed ranges of each use are in its table) |
| `tell_worlds.py` | Tells saved worlds again, in another language or as prose written by an open model, keeping a prose story only when two other open models accept it |
| `make_training_data.py` | Builds the supervised training examples from worlds and their reference answers |
| `train_sft.py`, `train_grpo.py`, `merge_adapter.py`, `smoke_train.py` | Supervised fine-tuning, the reinforcement step, merging adapters into the base, and a short smoke test of the training stack (CUDA GPU) |
| `check_estimator.py` | Measures the estimator's interval coverage on worlds of one theme (the gate of phase 2) |
| `check_cases.py` | Checks written cases against the verifier |
| `translate_theory.py` | Translates a theory sheet with open models and checks the translation |
| `pick_showcase.py` | Picks the showcase worlds by the rule in `configs/split.yaml` |
| `rescore.py` | Re-scores recorded answers after a change in the scorer |
| `make_gguf.sh` | Converts the merged model to GGUF and quantizes it (needs llama.cpp) |
| `publish_hf.py` | Uploads model, GGUF and dataset to the Hugging Face Hub (dry run unless `--upload`) |
| `reading_pack.py` | Builds the author's reading pack (PDFs and pages, Portuguese) from the repository |

`README-treino.md` (Portuguese) documents the training environment and the commands used.
