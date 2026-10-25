# Causalista

[English](README.md) · **Português**

[![tests](https://github.com/coppead/causalista/actions/workflows/tests.yml/badge.svg)](https://github.com/coppead/causalista/actions/workflows/tests.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Model](https://img.shields.io/badge/%F0%9F%A4%97%20Model-coppead%2Fcausalista--4b-yellow)](https://huggingface.co/coppead/causalista-4b)
[![GGUF](https://img.shields.io/badge/%F0%9F%A4%97%20GGUF-coppead%2Fcausalista--4b--GGUF-yellow)](https://huggingface.co/coppead/causalista-4b-GGUF)
[![Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Dataset-coppead%2Fcausalista--worlds-yellow)](https://huggingface.co/datasets/coppead/causalista-worlds)

Um analista causal pequeno, local e honesto. Você entrega uma tabela, diz qual coluna é a intervenção e qual é o resultado, e conta o que sabe sobre como os dados foram gerados. O Causalista decide por quais colunas ajustar, um programa separado calcula o efeito com intervalo de confiança e, quando os dados não permitem concluir, ele diz **não identificável** e explica o que falta.

É um modelo de 4 bilhões de parâmetros, um ajuste fino do Qwen3-4B que roda em um notebook, treinado em mundos sintéticos de resposta conhecida e avaliado por um verificador que conhece o grafo causal verdadeiro. Versão 0.1.0 (24 de outubro de 2026), da COPPEAD/UFRJ, licença Apache 2.0.

## Resultados

Medição final: 505 mundos nunca vistos em cada um de três idiomas (1.515 no total), oito temas de gestão, dos quais dois temas e um idioma (espanhol) nunca apareceram no treino. Nota: +1 por um conjunto de ajuste válido ou uma abstenção certa, −1 por um erro confiante, −0,5 por uma abstenção indevida.

| Quem respondeu | Nota | Acerto | pt | en | es | Dois temas não vistos |
|---|---|---|---|---|---|---|
| Ajustar por todas as colunas | −0,66 | 17% | 17% | 17% | 17% | 18% |
| Ajustar por nada (diferença simples) | −0,95 | 2% | 2% | 2% | 2% | 2% |
| Qwen3-4B sem treino | −0,05 | 47% | 46% | 46% | 47% | 47% |
| **Causalista 4B (esta versão)** | **+0,98** | **99%** | 100% | 99% | 98% | 96% |
| Modelo aberto de 27B com raciocínio, amostra de 152 | +0,99 | 99% | 100% | 100% | 98% | 100% |

Em 48 casos congelados que simulam texto escrito por pessoas, o Causalista chega a 69% e o modelo de 27B a 96%: ler o que uma pessoa escreve é onde o modelo pequeno ainda falha. O protocolo, cada número e o que **não** se afirma (nenhum modelo de fronteira foi medido; o texto tipo humano é simulado; cada número é sobre dados sintéticos de resposta conhecida) estão no [cartão do modelo](docs/cards/model-card.md).

## Começo rápido

**Com o Ollama, sem GPU.** Baixe uma vez o modelo quantizado de 2,5 GB com o [Ollama](https://ollama.com); o harness então o roda em cinco casos escritos, imprime o placar e grava cada resposta em `outputs/runs/quickstart/`.

```bash
ollama pull hf.co/coppead/causalista-4b-GGUF
git clone https://github.com/coppead/causalista && cd causalista
uv sync --no-group train
uv run --no-sync python scripts/run_models.py --cases cases/fase0.yaml --name quickstart \
    --model ollama:hf.co/coppead/causalista-4b-GGUF:nothink
```

O `--no-sync` mantém o ambiente leve: sem ele, `uv run` instala o grupo de treino, torch incluído, porque o projeto o instala por padrão para o próprio treino.

**Com o transformers, em uma GPU** (exige transformers 5.0 ou mais novo):

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from causalista.task import build_prompt, parse_answer

tok = AutoTokenizer.from_pretrained("coppead/causalista-4b")
model = AutoModelForCausalLM.from_pretrained("coppead/causalista-4b", dtype="bfloat16", device_map="auto")
prompt = build_prompt(task)   # um Task: pergunta, história, fichas das colunas (ver src/causalista/task/prompt.py)
text = tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False,
                               add_generation_prompt=True, enable_thinking=False)
out = model.generate(**tok(text, return_tensors="pt").to(model.device), max_new_tokens=2048, do_sample=False)
answer = parse_answer(tok.decode(out[0], skip_special_tokens=True).split(prompt)[-1], task)
```

**Na sua própria tabela.** O modelo nunca vê as linhas. Descreva a tabela como os casos escritos em [cases/](cases/) fazem (pergunta, história de como os dados foram gerados, uma ficha por coluna), rode o modelo e entregue as colunas que ele escolheu ao runner em `causalista.estimator`, que devolve o efeito, o intervalo, a diferença simples para contraste e as hipóteses. O modelo foi treinado em um formato de pergunta só e em oito temas de gestão; fora deles, nada aqui diz com que frequência ele acerta.

## Como funciona

1. **Verificador** ([src/causalista/verifier/](src/causalista/verifier/)): dado o grafo causal verdadeiro, diz se um conjunto de colunas é um conjunto de ajuste válido, ou que nenhum é. Dois motores independentes (critério de ajuste e análise de caminhos) se conferem; 24 casos de livro-texto e uma rede de erros plantados o protegem.
2. **Fábrica de mundos** ([src/causalista/worlds/](src/causalista/worlds/)): a partir de uma ficha de teoria revisada por tema ([theories/](theories/)), sorteia variáveis e papéis, gera os números e o efeito verdadeiro, e escreve a história, um fato por frase em português, inglês ou espanhol, ou em prosa escrita por modelos abertos.
3. **Tarefa** ([src/causalista/task/](src/causalista/task/)): o que o modelo vê, a resposta em JSON, a nota e a resposta ideal derivada do gabarito do verificador.
4. **Estimador** ([src/causalista/estimator/](src/causalista/estimator/)): um estimador duplamente robusto com validação cruzada (DoubleML) que transforma as colunas escolhidas em efeito e intervalo.
5. **Harness** ([src/causalista/harness/](src/causalista/harness/)): roda qualquer modelo (Hugging Face, Ollama, uma API) sobre mundos gravados ou casos escritos e grava cada resposta. As páginas em [src/causalista/viz/](src/causalista/viz/) são geradas a partir desses registros, nunca desenhadas à mão.
6. **Treino** ([scripts/](scripts/)): ajuste fino supervisionado com LoRA em 22.906 exemplos (Unsloth + TRL), depois um passo curto de GRPO cuja única recompensa é a nota do verificador em 208 casos que simulam texto de pessoas. A escolha entre os braços de treino seguiu uma regra escrita antes dos resultados.

## Mapa do repositório

| Caminho | O que é |
|---|---|
| [ESPECIFICACAO.md](ESPECIFICACAO.md) | A especificação: o que está sendo construído, em que ordem, e o registro dos portões de cada fase |
| [src/causalista/](src/causalista/) | O pacote: verifier, worlds, estimator, task, harness, viz. Cada pasta abre com um README |
| [theories/](theories/) | Uma ficha de teoria por tema, em YAML; traduções em `theories/i18n/` |
| [cases/](cases/) | Casos escritos, com as setas do diagrama e a resposta conferida pelo verificador; `cases/simulados/` guarda os 48 casos congelados da medição |
| [configs/](configs/) | Bases candidatas, a divisão de temas e sementes entre treino e teste, os mundos-vitrine |
| [scripts/](scripts/) | Geração de mundos, dados de treino, treino, rodadas de modelos, conversão para GGUF, publicação, material de leitura |
| [tests/](tests/) | Testes, espelhando `src/` |
| [docs/](docs/) | Status do projeto e relato completo das decisões, trabalhos vizinhos, os cartões do Hugging Face ([docs/cards/](docs/cards/)) |
| `outputs/` | Tudo o que é gerado (mundos, rodadas, pesos, páginas); fora do git. Os conjuntos de mundos, casos, exemplos de treino e respostas gravadas em que os cartões se apoiam estão publicados no conjunto de dados |

## Reproduzir

Tudo o que está nos cartões pode ser regenerado a partir deste repositório e do conjunto de dados. Um `uv sync` simples instala também a pilha de treino (GPU CUDA, cerca de 7 GB); os scripts de treino estão documentados em [scripts/README-treino.md](scripts/README-treino.md).

```bash
hf download coppead/causalista-worlds --repo-type dataset --include "worlds/placar-v3/*" --local-dir outputs   # um conjunto de mundos gravado
uv run python scripts/run_models.py --worlds placar-v3 --every 20 --model hf:coppead/causalista-4b:nothink  # medir o modelo publicado nele
uv run python scripts/make_worlds.py --name meu-conjunto --pairs 13 --first-seed 50000                    # ou gerar mundos novos
uv run python scripts/make_training_data.py --name sft-v1 --themes telecom varejo --pairs 2000 --languages pt en
uv run python scripts/train_sft.py --data outputs/train/data/sft-v1.jsonl --base Qwen/Qwen3-4B
uv run python scripts/train_grpo.py --base <modelo supervisionado fundido> \
    --cases cases/treino-simulados/pt-0[1-9].yaml cases/treino-simulados/pt-1[0-6].yaml cases/treino-simulados/en-0[1-9].yaml cases/treino-simulados/en-10.yaml   # os 26 arquivos usados; pt-17, pt-18, en-11, en-12 ficaram guardados
uv run python -m causalista.viz.scoreboard --set placar-v3                                                 # a página do placar a partir dos registros
```

As sementes têm faixas reservadas por uso (tabela em `scripts/make_worlds.py`); o treino nunca usa semente abaixo de 100.000, e os casos congelados nunca entram no treino.

## Dados e procedência

- As respostas-alvo do treino vêm sempre do verificador, nunca de um modelo de linguagem.
- As frases das histórias de treino vêm de oito fichas de teoria escritas por um modelo de linguagem a partir da teoria de gestão, revisadas frase a frase por instâncias independentes do mesmo modelo; as histórias em prosa foram escritas por modelos abertos e mantidas só quando dois outros modelos abertos concordaram que eram fiéis. Os casos tipo humano foram escritos e revisados por instâncias de um modelo de linguagem. Os cartões dizem quem escreveu o quê.
- O autor tomou as decisões de desenho: a família de mundos e suas faixas, os temas, os pesos da nota, o modelo-base, o tamanho do treino e o protocolo de medição. O projeto foi construído pelo autor com um assistente de programação por IA.
- Código, nomes e docstrings estão em inglês; a especificação, o status, os READMEs dos pacotes e a saída dos scripts estão em português, a língua de trabalho do projeto. Os arquivos de dados (`theories/`, `cases/`) e alguns scripts têm nomes em português, seguindo o vocabulário da especificação.

## Documentação

- [ESPECIFICACAO.md](ESPECIFICACAO.md): a especificação e o registro dos portões.
- [docs/status.md](docs/status.md): o relato completo do que foi feito, medido e decidido, dia a dia.
- [docs/trabalhos-vizinhos.md](docs/trabalhos-vizinhos.md): os trabalhos vizinhos na literatura.
- [docs/cards/](docs/cards/): os cartões do modelo, do GGUF e dos dados (em inglês, com abertura em português).
- [CHANGELOG.md](CHANGELOG.md), [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md).

## Desenvolvimento

```bash
uv sync --no-group train               # execução e testes, sem torch
uv run --no-sync pytest                # a bateria do dia a dia (10 a 15 minutos: os mundos são testados nos oito temas)
uv run --no-sync pytest -m slow        # exaustiva: todos os grafos de até cinco variáveis (cerca de 2 minutos)
```

Python 3.12. As páginas precisam do Graphviz (`sudo apt install graphviz`). Rode a bateria exaustiva depois de qualquer mudança em `src/causalista/verifier/`. Trabalhe a partir de um clone: o pacote lê `theories/` e `cases/` do repositório, então o wheel sozinho serve só ao verificador, ao estimador e ao formato da tarefa.

## Como citar

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

O arquivo [CITATION.cff](CITATION.cff) traz os mesmos dados no formato que o GitHub lê.

## Licença

Apache 2.0 ([LICENSE](LICENSE)), como o modelo-base Qwen3-4B.

## Agradecimentos

À equipe Qwen pelo modelo-base; a Unsloth, TRL, PEFT e transformers pela pilha de treino; ao DoubleML pelo estimador; ao llama.cpp e ao Ollama pela inferência local; ao Hugging Face Hub pela hospedagem. Construído por André Fonseca (COPPEAD/UFRJ) com um assistente de programação por IA.
