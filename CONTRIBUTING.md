# Contributing

*Em português: este guia diz como preparar o ambiente, rodar os testes e propor mudanças. A especificação ([ESPECIFICACAO.md](ESPECIFICACAO.md)) é a fonte da verdade do escopo e está em português; o código, os nomes e as docstrings ficam em inglês.*

## Read first

- [ESPECIFICACAO.md](ESPECIFICACAO.md) (Portuguese): what is being built, in what order, and the record of each phase gate. Nothing goes into a release that is not in it.
- [docs/status.md](docs/status.md) (Portuguese): the full account of what was done and decided.
- The README of each package under `src/causalista/` (Portuguese): what it does, what goes in, what comes out.
- The model and dataset cards in `docs/cards/` (English, with a Portuguese opening).

## Set up

```bash
uv sync                      # everything, including the training libraries (needs a CUDA GPU to be useful; about 7 GB)
uv sync --no-group train     # runtime and tests only, no torch
```

The training group is installed by default (`[tool.uv] default-groups` in `pyproject.toml`), so after `uv sync --no-group train` run commands with `uv run --no-sync`; a plain `uv run` would install the training group again.

Python 3.12. R with the `dagitty` package is only needed to regenerate the reference answers under `tests/verifier/reference/`.

## Tests

```bash
uv run --no-sync pytest                # the default suite (10 to 15 minutes: the worlds are tested on all eight themes)
uv run --no-sync pytest -m slow        # exhaustive: every graph of up to five variables (~2 min)
```

Run the slow suite after any change under `src/causalista/verifier/`. If the verifier is wrong, everything downstream is wrong, so changes there must keep all four test layers green and `test_safety_net.py` must still catch the planted errors.

## Non-negotiable rules

- **Targets come from the verifier, never from a model.** Every training answer is derived from the true graph.
- **Frozen cases never enter training.** `cases/simulados/` (48 cases, frozen on 2026-10-06) and the world set `teste-v3` are for final measurement only. Seeds have reserved ranges (table in `scripts/make_worlds.py`); training never uses a seed below 100,000.
- **Say only what is measured.** The release does not claim to beat frontier models or to recover effects of real experiments.
- **Vocabulary** in Portuguese prose: "ajustar por" (not "controlar"), "intervenção", "resultado", "coluna", "não identificável".

## Proposing changes

Open an issue first for anything that changes the verifier, the world design, the score or the task format: those are design decisions recorded in the specification. Keep pull requests small, one piece of the project per commit. Commit messages in English or Portuguese are both welcome; the maintainer keeps the project's own history in Portuguese. Pages under `src/causalista/viz/` are generated from records, never drawn by hand.

Ideas outside the current release go to the list in section 10 of the specification.
