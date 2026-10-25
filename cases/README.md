# Written cases

Cases written by hand, in the shape a person would describe a table: a story of how the data were generated, the column dictionary, the arrows of the causal diagram the author has in mind, and the answer, which the verifier checks against those arrows. Each case carries `author: ai` (written by a large language model) or `author: andre`. Comments inside the files are in Portuguese; the stories are in the language of the case.

| Folder or file | Cases | Role |
|---|---|---|
| `fase0.yaml` | 5 | the first cases of the project, in Portuguese; the quickstart runs them |
| `simulados/` | 48 (24 pt, 16 en, 8 es) | **frozen on 2026-10-06** and used only for the final measurement; never in training. `simulados/README.md` lists the SHA-256 of each file |
| `treino-simulados/` | 240 (30 files) | the same kind of case, written on 2026-10-07 for training; 26 files (208 cases) trained the published model's reinforcement step, and `pt-17`, `pt-18`, `en-11`, `en-12` were held out as the development test |

`docs/modelo-de-caso.md` (Portuguese) is the template; `src/causalista/written_cases.py` reads and checks the files; `scripts/check_cases.py` checks them from the command line.
