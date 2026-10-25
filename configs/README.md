# Configuration

| File | What it fixes |
|---|---|
| `bases.yaml` | The candidate base models with the Hub revision each was pinned to (the published model was trained from `Qwen/Qwen3-4B` at `1cfa9a72`), their licences and sizes |
| `split.yaml` | What is held out of training: the themes `email` and `saude`, the language `es`, the seed ranges of each use, and the rule that picks the showcase worlds |
| `showcase.yaml` | A proposal of showcase worlds generated on 2026-10-04 for a set that was later superseded; kept as a record. The rule in force is `showcase:` in `split.yaml` |

Comments inside the files are in Portuguese.
