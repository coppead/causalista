# Documentation index

Code, identifiers, the root README and the Hugging Face cards are in English. Everything else was written in Portuguese, the project's working language; this page says what each document is, so that a reader without Portuguese knows what to open and what to skip.

## Documents

| File | What it is | Read it if |
|---|---|---|
| [`../ESPECIFICACAO.md`](../ESPECIFICACAO.md) | The specification: scope of release 0.1, the task, the score, the phases and their gates, and section 13 with the measured record of each gate | you want the design decisions and the acceptance criteria |
| [`status.md`](status.md) | The project's working log, day by day: what was built, measured and decided, with every number and the protocol of the final measurement (section 31) | you want to audit a number or a decision; the cards summarise it |
| [`trabalhos-vizinhos.md`](trabalhos-vizinhos.md) | Neighbouring work in the literature and how the project phrases its novelty | you are writing about related work |
| [`fichas-para-aprovar.md`](fichas-para-aprovar.md) | Review notes on the eight theory sheets (approved on 2026-10-05) | you want to know what was checked in the sheets |
| [`modelo-de-caso.md`](modelo-de-caso.md) | The template of a written case | you want to write a case of your own |
| [`cards/model-card.md`](cards/model-card.md), [`cards/gguf-card.md`](cards/gguf-card.md), [`cards/dataset-card.md`](cards/dataset-card.md) | The Hugging Face cards, in English with a Portuguese opening; byte for byte the README of each Hub repository | you want the complete, self-contained description of the release |

## Data folders

| Folder | What it holds | Language |
|---|---|---|
| [`../theories/`](../theories/) | One theory sheet per management theme (what the theory says about the variables and their roles); `i18n/` has the English and Spanish translations | Portuguese (file names too: `banco` bank, `educacao` education, `email` e-mail marketing, `rh` HR, `saude` health insurance, `software`, `telecom`, `varejo` retail) |
| [`../cases/`](../cases/) | Written cases: `fase0.yaml` (5 textbook-style cases), `simulados/` (48 frozen cases that imitate human prose, for measurement only), `treino-simulados/` (240 cases of the same kind, for training) | stories in pt, en or es; comments in Portuguese |
| [`../configs/`](../configs/) | `bases.yaml` (candidate base models and their pinned revisions), `split.yaml` (which themes and languages are held out), `showcase.yaml` (a superseded proposal, kept as a record) | comments in Portuguese |
| [`../scripts/`](../scripts/) | The command-line entry points; `README-treino.md` documents the training environment | docstrings and `--help` in English |

## Glossary of internal names

| Name | Meaning |
|---|---|
| `placar-v3` | the development set ("placar" = scoreboard; v3 = third generation of the world factory; v1 and v2 were superseded and are not published) |
| `teste-v3` | the final test set, opened once on 2026-10-18 |
| `treino-prosa-v1`, `-v2a`, `-v2b` | the training sets whose stories are prose written by open models |
| `casos-simulados`, `casos-dev` | runs over the 48 frozen cases and over the 32 held-out development cases |
| `gguf-check` | the run that checked the quantized model against the full-precision one (35 of 35) |
| `(sem raciocínio)` | "without reasoning": the model answers directly, with the thinking step off |
| `ajusta tudo`, `ajusta nada` | the two naive strategies, "adjust for everything" and "adjust for nothing" (`rule:all`, `rule:none`) |
| level 1 / level 2 / level 3 | a story told one fact per sentence / in prose / a written case |
