---
license: apache-2.0
language:
  - pt
  - en
  - es
pretty_name: Causalista worlds
source_datasets:
  - original
multilinguality:
  - multilingual
task_categories:
  - text-generation
annotations_creators:
  - machine-generated
language_creators:
  - machine-generated
configs:
  - config_name: default
    data_files:
      - split: train
        path: examples/sft-final.jsonl
tags:
  - causal-inference
  - synthetic
  - reinforcement-learning
  - verifiable-rewards
  - management
size_categories:
  - 10K<n<100K
---

# Causalista worlds

Synthetic "worlds" for one decision: given a table, the column that is the intervention, the column that is the outcome, and a story of how the data were generated, say which columns to adjust for to measure the average effect, or say that the effect is not identifiable with these columns. Every world has a known answer, computed by a verifier from the true causal graph, which the model never sees.

- **Curated by:** André Fonseca, COPPEAD Graduate School of Business, Federal University of Rio de Janeiro (UFRJ), with an AI coding assistant; funded by the author's own institution, on the author's own hardware
- **Version:** 0.1.0, released 2026-10-25 (files uploaded 2026-10-24)
- **Languages:** Portuguese, English, Spanish (stories); column names are Portuguese identifiers in all three
- **License:** Apache 2.0
- **Size:** 71,181 files, 3.3 GiB; 22,906 training examples in the viewer
- **Contact:** https://github.com/coppead/causalista/issues
- **Model trained on it:** [coppead/causalista-4b](https://huggingface.co/coppead/causalista-4b); code: [github.com/coppead/causalista](https://github.com/coppead/causalista)

The Dataset Viewer and `load_dataset("coppead/causalista-worlds")` show the training examples (`examples/sft-final.jsonl`: 22,906 rows of prompt and ideal answer). The rest of the repository is a tree of folders, one per world, described below; download it with `hf download coppead/causalista-worlds --repo-type dataset --local-dir <folder>`, or only one set with `--include "worlds/placar-v3/*"`. Quantized files of the model are in [coppead/causalista-4b-GGUF](https://huggingface.co/coppead/causalista-4b-GGUF).

*Em português: mundos sintéticos para uma decisão só, dizer por quais colunas ajustar para medir o efeito de uma intervenção, ou dizer que não dá. Cada mundo tem gabarito, calculado pelo verificador a partir do grafo verdadeiro. Este conjunto treinou e mediu o modelo [coppead/causalista-4b](https://huggingface.co/coppead/causalista-4b). O código que gera, confere e avalia está em [github.com/coppead/causalista](https://github.com/coppead/causalista).*

This dataset is the environment behind the model [coppead/causalista-4b](https://huggingface.co/coppead/causalista-4b). The generator, the verifier, the estimator and the evaluation harness are in the code repository, [github.com/coppead/causalista](https://github.com/coppead/causalista), with READMEs in Portuguese.

## What a world is

A world is drawn from a *theory sheet*: a YAML file for one management theme (telecom churn, retail, bank credit, subscription software, HR, education, e-mail marketing, private health insurance) that lists the variables the theory names, the causal roles each one may play (confounder, mediator, collider, neutral), the sign of each effect, and one sentence per fact in three languages. The generator samples 3 to 8 variables and their roles, builds the graph, simulates a table with the effect sizes drawn within fixed ranges, computes the true average effect by simulating everyone treated and everyone untreated, and tells the story one fact per sentence, in random order. Worlds come in twin pairs (`-a` and `-b`) that differ in a single fact and have different answers: a column present or absent from the table, or a variable measured before or after the intervention.

About 45% of worlds are not identifiable: a confounder named in the story is not in the table. In most worlds some other information is also missing without harm (a cause of the outcome only, or of the intervention only), so "something is missing, therefore not identifiable" is not a usable shortcut.

Each world folder contains:

| Path | Who sees it | Content |
|---|---|---|
| `visible/question.txt` | the model | the question: the effect of which column on which column |
| `visible/narrative.txt` | the model | the story of how the data were generated |
| `visible/dictionary.json` | the model | name, type, description and a simple summary of each column |
| `visible/table.csv` | the runner only | the rows (2k, 5k, 10k, 20k or 50k) |
| `visible/about.json` | both | theme, language, level, seed |
| `hidden/answer_key.json` | evaluation only | the graph, the roles, the true effect, and the verifier's verdict with its reason |
| `estimates.json` | evaluation only | the runner's estimate for each adjustment set some responder chose |

A world told in another language or as prose is a separate folder with a suffix: `<world>.en1` (English, one fact per sentence), `<world>.es1` (Spanish), `<world>.pt2` / `<world>.en2` (prose). Only the words change; graph, table and answer are the same.

## Uses

**Direct use.** Training or measuring a model on the decision the dataset encodes (which columns to adjust for, or abstain), with the verifier's answer key; studying abstention under a verifiable reward; comparing estimators on tables whose true effect is known.

**Out-of-scope use.** Training on `worlds/teste-v3` or on `cases/simulados/`: they exist to measure, and the published model never saw them. Treating the tables as records of real customers, employees or students: every row is simulated from a theory sheet. Presenting the simulated cases as text written by people: they were written by a language model to imitate people.

## The sets

| Set | Use | Level 1 (one fact per sentence) | Level 2 (prose) | Prose written by |
|---|---|---|---|---|
| `worlds/placar-v3` | development: inspected freely | 384 pt, 384 en, 384 es | 113 pt, 116 en | Granite 4.1 30B, reserved for tests |
| `worlds/teste-v3` | final measurement, opened once on 2026-10-18 | 505 pt, 505 en, 505 es | none | |
| `worlds/treino-prosa-v1` | reinforcement experiments of 2026-10-07 (not in the published model) | 876 pt | 719 pt | Qwen3 14B |
| `worlds/treino-prosa-v2a` | prose examples of the published model | 1,408 pt, 470 en | 1,167 pt, 383 en | Qwen3 14B |
| `worlds/treino-prosa-v2b` | prose examples of the published model | 943 pt, 943 en | 785 pt, 771 en | Gemma 4 26B |

Every set has a `manifest.json` with the seeds and the generator settings. The prose sets also keep `prose-<lang>.jsonl`, the log of every prose attempt, including the ones two reader models rejected for leaving a fact out or adding one.

Two of the eight themes, e-mail marketing and private health insurance, appear only in `placar-v3` and `teste-v3`: no training example comes from them. The 888 graph structures of the two test sets were also excluded from training, whatever the theme. Seeds are allocated by use (`scripts/make_worlds.py` in the code repository); no training seed is below 100,000.

## Written cases

`cases/` holds cases written by hand, in YAML: a story, the columns, the causal arrows and the answer, which the verifier checks against the arrows (`scripts/check_cases.py`).

- `cases/fase0.yaml`: 5 cases written by a language model at the author's request, in Portuguese.
- `cases/simulados/`: 48 cases that **simulate** text written by people (an e-mail to the boss, a chat message, meeting notes, a report excerpt, a forum question), in Portuguese (24), English (16) and Spanish (8), on themes inside and outside the eight. Six instances of a large language model wrote them in the role of managers, analysts and students, without access to the theory sheets; six other instances reviewed them. Frozen on 2026-10-06 with SHA-256 sums in `cases/simulados/README.md`, before any model answered them; never used in training. **They are not text written by people**, and nothing built on them may say so.
- `cases/treino-simulados/`: 240 cases of the same kind, written on 2026-10-07 for training. 208 of them (26 files) were the data of the published model's reinforcement step and of the supervised arm it was compared with; the four files `pt-17`, `pt-18`, `en-11` and `en-12` (32 cases) were held out as the development test that chose between the arms.

A case has no table, so when a model answers it the column summaries are synthesised from the column descriptions.

## Training examples

`examples/sft-final.jsonl` is the exact supervised training set of the published model: 22,906 lines, one JSON object each, with `world`, `theory`, `language`, `level`, `identifiable`, `prompt` (the text the model sees, in English instructions around the story in its language) and `answer` (the ideal structured answer, derived from the verifier's answer key). 19,814 are level 1 (9,719 pt, 10,095 en) from the six training themes, 1,700 twin pairs per theme; 3,092 are prose (1,943 pt, 1,149 en) from `treino-prosa-v2a` and `treino-prosa-v2b`. The two `.json` files next to it are the generation records.

**Data fields** of `examples/sft-final.jsonl` (one JSON object per line): `world` (the world's id, e.g. `telecom-100042-a`), `theory` (the theme), `language` (`pt` or `en`), `level` (1 = one fact per sentence, 2 = prose), `identifiable` (whether the effect is identifiable, from the answer key), `prompt` (the full text the model sees), `answer` (the reference answer, JSON in a string). Example, shortened:

```json
{"world": "telecom-100042-a", "theory": "telecom", "language": "pt", "level": 1, "identifiable": true,
 "prompt": "You are a careful analyst ... ## Story\nA operadora ...", "answer": "{\"roles\": [...], \"verdict\": \"identifiable\", \"adjustment_set\": [...], ...}"}
```

## Recorded answers

`runs/<set>/<responder>.jsonl` keeps every answer of every responder that was run on a set (`placar-v3` and `teste-v3` for worlds; `casos-simulados` for the 48 frozen cases; `casos-dev` for the 32 held-out cases; `gguf-check` for the quantized model on a sample): the world, theme, language and level; the responder and checkpoint; the raw and the parsed answer; the outcome (correct, confident error, undue abstention, invalid), the score and the verifier's reason; and, when an effect was asserted, the runner's estimate with its interval next to the true effect. `summary.json` in each folder aggregates them. The scoreboard page in `pages/` is rendered from these files and from nothing else.

**Record fields** (one JSON object per line): `world`, `theory`, `language`, `level` (1, 2, or 3 for a written case, whose column summaries are synthesised from the descriptions), `model` (the responder's label), `checkpoint`, `world_identifiable`, `outcome` (`correct`, `confident_error`, `undue_abstention` or `invalid`), `score` (+1, −1, −0.5, −1), `reason` (the verifier's reason, always in Portuguese), `answer` (the parsed answer: `identifiable`, `adjustment_set`, `roles`, `reasons`, `missing`, `assumptions`, `complete`), `roles_right` (share of column roles right; null for written cases), `estimate` (the estimator's effect, interval and overlap share when an effect was asserted), `true_effect`, `raw` (the model's text), `seconds`, `output_tokens`. `summary.json` in each folder aggregates these per responder with the metrics of `causalista.harness.summarise`.

**Which file is which responder** (the labels are the model paths as the harness saw them; `(sem raciocínio)` = thinking off):

| Row of the results tables | Label in `summary.json` | File |
|---|---|---|
| Adjust for every column | `ajusta tudo` | `ajusta-tudo.jsonl` |
| Adjust for nothing | `ajusta nada` | `ajusta-nada.jsonl` |
| Base, Qwen3-4B without fine-tuning | `Qwen/Qwen3-4B (sem raciocínio)` | `qwen-qwen3-4b-sem-racioc-nio.jsonl` |
| Supervised model only | `Qwen/Qwen3-4B + sft-final-qwen3-4b/adapter (sem raciocínio)` | `qwen-qwen3-4b-sft-final-qwen3-4b-adapter-sem-racioc-nio.jsonl` |
| **The published model** (supervised + reinforcement) | `outputs/train/merged/sft-final-qwen3-4b + grpo-c-sft-cases/adapter (sem raciocínio)` | `outputs-train-merged-sft-final-qwen3-4b-grpo-c-sft-cases-adapter-sem-racioc-nio.jsonl` |
| Qwen3.8 27B with reasoning | `qwen3.8:27b` | `qwen3.8-27b.jsonl` |

Other files under `runs/placar-v3/` are development arms named after their training run (`grpo-a2`, `grpo-b`, `sft-d-cases`, `sft-pt-v1/v2/v3`).

Responders in the records: the two naive strategies ("adjust for everything" and "adjust for nothing"), the base model Qwen3-4B without training, the supervised model, the published model (supervised plus the reinforcement step), the arms that were not published (earlier supervised tests, the reinforcement runs of 2026-10-07 that were measured, the supervised arm on cases), and a larger open model (Qwen3.8 27B with reasoning) on samples.

## Theory sheets and configuration

`theories/` holds the eight theory sheets in Portuguese and their English and Spanish translations under `theories/i18n/`. `configs/` holds the candidate base models with pinned revisions, the train/test split rule and the showcase worlds.

## Provenance

- **Answers** always come from the verifier, never from a language model. It has two engines that share no code and must agree: one applies the adjustment criterion on the back-door graph, the other enumerates every path by definition.
- **Theory sheets** were written by a large language model from management theory and references it proposed; the telecom card was approved by the author, the other seven were each read sentence by sentence by an independent instance of the same model, corrected, and approved by delegation. The sentences of the cards are the sentences of the level 1 stories.
- **Prose** was written by open models (Qwen3 14B and Gemma 4 26B for training; Granite 4.1 30B for the test set) and kept only when two other open models (Qwen3.5 9B with Granite 4.1 30B for the training prose; Qwen3.5 9B with Qwen3 14B for the test prose) agreed, sentence by sentence, that it states every fact of the world and none of the alternatives.
- **Translations** of the cards were first made by open models and then re-read in full and corrected by instances of a large language model.
- **Simulated cases** were written and reviewed by instances of a large language model, as described above.
- **No text in this dataset was written by a person**; the author's contribution is the design: ranges, themes and weights.

## Personal and sensitive information

None. Every table, story and name is synthetic, generated from theory sheets about management; no record describes a real person, company or event. The recorded answers are outputs of language models.

## Limitations

- Synthetic data from eight management themes; the effect sizes are sometimes larger than those typically found in practice.
- Themes are named by Portuguese codes in every file: `telecom`, `varejo` (retail), `banco` (bank credit), `software`, `rh` (HR), `educacao` (education), and the two held out of training, `email` (e-mail marketing) and `saude` (private health insurance). Set names: `placar-v3` (development; "placar" = scoreboard; v3 = third generation of the generator), `teste-v3` (final test), `treino-prosa-*` (training sets with prose), `casos-simulados` and `casos-dev` (runs over the 48 frozen and the 32 held-out cases), `gguf-check` (the quantized model against the full one).
- In this family of worlds the effect is not identifiable exactly when a named confounder is missing from the table; other reasons for non-identifiability (instruments, selection, M-bias, proxies) are not covered.
- Stories are one fact per sentence or model-written prose; text written by people is simulated, not real.
- A 27B open model answers almost every world correctly; the sets measure the distance between a small model and a larger one, not between large models.

## Versions and errata

| Version | Date | What |
|---|---|---|
| 0.1.0 | 2026-10-25 (files uploaded 2026-10-24) | first release |

The sets are frozen: a correction never edits a world in place. New versions get a new revision here, a new tag in the code repository and an entry in its `CHANGELOG.md`, where errata are listed. Maintained by the author; report problems through the issues of the code repository.

## Citation

```bibtex
@software{fonseca2026causalista,
  author    = {Fonseca, André},
  title     = {Causalista: a small, local model that decides what to adjust for and says when the data cannot answer},
  year      = {2026},
  version   = {0.1.0},
  publisher = {COPPEAD/UFRJ},
  url       = {https://github.com/coppead/causalista},
  note      = {Dataset: \url{https://huggingface.co/datasets/coppead/causalista-worlds}}
}
```

Questions and problems: open an issue at https://github.com/coppead/causalista/issues.
