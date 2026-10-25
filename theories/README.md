# Theory sheets

One YAML file per management theme, in Portuguese: the variables the theory names, the roles each may play (cause, mediator, collider, neutral), the sign of each influence, and one sentence per fact that the world factory uses to tell a story. The sheets were drafted by a large language model from the management literature, reviewed sentence by sentence by independent instances of the same model, and approved by the author (telecom) or on the author's behalf (the other seven) on 2026-10-05. Only sheets with `status: aprovada` are used.

| File | Theme | Used for |
|---|---|---|
| `telecom.yaml` | telecom churn | training |
| `varejo.yaml` | retail | training |
| `banco.yaml` | bank credit | training |
| `software.yaml` | subscription software | training |
| `rh.yaml` | human resources | training |
| `educacao.yaml` | education | training |
| `email.yaml` | e-mail marketing | **held out**: final test only |
| `saude.yaml` | private health insurance | **held out**: final test only |

`i18n/en/` and `i18n/es/` hold the English and Spanish translations of every sentence, first made by open models (`qwen3.5:35b`, checked by `granite4.1:30b`) and then read in full and corrected by a large language model on 2026-10-06. `i18n/pendentes-2026-10-05.json` is the list of sentences that the review of 2026-10-05 changed in the Portuguese sheets, kept so that the translations can be traced to it. The Portuguese sheet is the one that counts; the translations only render it.
