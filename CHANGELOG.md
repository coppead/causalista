# Changelog

*Em português: o registro das versões. A 0.1.0, de 24 de outubro de 2026, é a primeira; o relato completo do que foi feito está em [docs/status.md](docs/status.md).*

## [Unreleased]

## [0.1.0] — 2026-10-24

First release.

- **Verifier**: two independent engines (adjustment criterion and path analysis) that check each other and return a verdict with its reason; 24 textbook cases with a known answer; a safety net of planted errors.
- **World factory**: eight management themes (telecom churn, retail, bank credit, subscription software, HR, education, e-mail marketing, private health insurance), each with a reviewed theory sheet; stories told one fact per sentence in Portuguese, English and Spanish, and prose stories written by open models; the true effect and a doubly robust estimator with cross-fitting (95.3% interval coverage over 3,462 identifiable worlds).
- **Task and harness**: the prompt the model sees, the JSON answer format, the score (+1 valid set or right abstention, −1 confident error, −0.5 undue abstention, −1 unusable answer), and a harness that runs any model over saved worlds and records every answer.
- **Model**: Qwen3-4B with LoRA, supervised on 22,906 synthetic worlds, then a short GRPO step rewarded only by the verifier's score on 208 cases that simulate text written by people. Final measurement on 1,515 never-seen worlds: 99% accuracy (base model 47%); 98% in Spanish, never trained; 96% on two themes never trained. On 48 frozen human-like cases: 69%, against 96% for a 27B open model.
- **Release**: merged weights and both adapters (`coppead/causalista-4b`), GGUF Q4_K_M and Q8_0 with an Ollama Modelfile (`coppead/causalista-4b-GGUF`), and the dataset with the five world sets used for development and measurement, every written case, the training examples and every recorded answer on them (`coppead/causalista-worlds`). Apache 2.0.
- **Not claimed**: that the model beats frontier models, or recovers effects of real experiments. Every number is on synthetic data with a known answer; see the model card.

[Unreleased]: https://github.com/coppead/causalista/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/coppead/causalista/releases/tag/v0.1.0
