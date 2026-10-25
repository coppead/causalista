# Causalista

[English](README.md) · **Português**

[![tests](https://github.com/coppead/causalista/actions/workflows/tests.yml/badge.svg)](https://github.com/coppead/causalista/actions/workflows/tests.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](pyproject.toml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/coppead/causalista)](https://github.com/coppead/causalista/releases)
[![Model](https://img.shields.io/badge/%F0%9F%A4%97%20Model-coppead%2Fcausalista--4b-yellow)](https://huggingface.co/coppead/causalista-4b)
[![GGUF](https://img.shields.io/badge/%F0%9F%A4%97%20GGUF-coppead%2Fcausalista--4b--GGUF-yellow)](https://huggingface.co/coppead/causalista-4b-GGUF)
[![Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Dataset-coppead%2Fcausalista--worlds-yellow)](https://huggingface.co/datasets/coppead/causalista-worlds)

> **Língua de trabalho.** Código, identificadores, o README em inglês e os cartões do Hugging Face estão em inglês. A especificação, o diário do projeto, os READMEs dos pacotes, os arquivos de dados e a saída dos scripts estão em português; [docs/README.md](docs/README.md) indexa tudo em inglês.

Um analista causal pequeno e local, que diz quando não pode responder. Você descreve uma tabela (as colunas e como os dados foram gerados) e diz qual coluna é a intervenção e qual é o resultado. O Causalista decide por quais colunas ajustar; um estimador separado calcula então o efeito com intervalo de confiança. Quando os dados não respondem à pergunta, ele diz **não identificável** e explica o que falta. O modelo nunca vê as linhas.

É um ajuste fino de 4 bilhões de parâmetros do Qwen3-4B, que roda em um notebook, treinado em mundos sintéticos de resposta conhecida e avaliado por um verificador que conhece o grafo causal verdadeiro. A versão 0.1.0 do modelo foi publicada em 25 de outubro de 2026 pela COPPEAD/UFRJ, sob a licença Apache 2.0; o código está na versão 0.1.1 ([CHANGELOG](CHANGELOG.md)).

## Resultados

Avaliação final: 505 mundos nunca vistos em cada um de três idiomas (1.515 no total), em oito temas de gestão; dois dos temas e um dos idiomas (espanhol) nunca apareceram no treino. Nota por mundo: +1 por um conjunto de ajuste válido ou uma abstenção correta, −1 por um erro confiante, −0,5 por uma abstenção indevida; a tabela mostra a média. Um treino só (semente 0) e decodificação gulosa, então a avaliação é determinística; com 99% de acerto em 1.515 mundos, o intervalo binomial de 95% é de cerca de ±0,5 ponto.

| Sistema | Nota | Acerto | pt | en | es | Temas reservados (381) |
|---|---|---|---|---|---|---|
| Ajustar por todas as colunas | −0,66 | 17% | 17% | 17% | 17% | 18% |
| Ajustar por nada (diferença simples) | −0,95 | 2% | 2% | 2% | 2% | 2% |
| Qwen3-4B (base, sem ajuste fino) | −0,05 | 47% | 46% | 46% | 47% | 47% |
| **Causalista 4B (esta versão)** | **+0,98** | **99%** | 100% | 99% | 98% | 96% |
| Qwen3.8 27B com raciocínio (`qwen3.8:27b` pelo Ollama), amostra de 152 | +0,99 | 99% | 100% | 100% | 98% | 100% (37) |

Em 48 casos congelados escritos para imitar texto de pessoas (e-mails, mensagens de chat, atas), o Causalista faz 69% e o modelo de 27B, 96%: ler texto livre é onde o modelo pequeno ainda fica aquém. O protocolo, cada número e o que **não** se afirma (nenhum modelo de fronteira foi medido; o texto tipo humano é simulado; cada número é sobre dados sintéticos de resposta conhecida) estão no [cartão do modelo](docs/cards/model-card.md). Cada resposta por trás de cada número está gravada no [conjunto de dados](https://huggingface.co/datasets/coppead/causalista-worlds), em `runs/`.

## Começo rápido

**Com o Ollama, sem GPU.** Baixe uma vez o modelo quantizado de 2,5 GB com o [Ollama](https://ollama.com); o harness então o roda em cinco casos escritos, imprime o placar e grava cada resposta em `outputs/runs/quickstart/`.

```bash
ollama pull hf.co/coppead/causalista-4b-GGUF
git clone https://github.com/coppead/causalista && cd causalista
uv sync --no-group train
uv run --no-sync python scripts/run_models.py --cases cases/fase0.yaml --name quickstart \
    --model ollama:hf.co/coppead/causalista-4b-GGUF:nothink
```

O placar sai em português quando o seu sistema está em português (em inglês nos demais): nota, acerto, erros confiantes, abstenções indevidas, respostas inválidas e quantos casos foram respondidos. O rótulo do respondedor termina em `(sem raciocínio)`, o modo em que o modelo foi treinado. Mantenha o `--no-sync`: sem ele, `uv run` instalaria o grupo de treino (torch incluído, cerca de 7 GB), que o projeto liga por padrão para os próprios treinos. Prefira o harness ou o `scripts/ask.py` ao `ollama run` para este modelo: o `--think=false` do Ollama não fecha o bloco de pensamento para ele (Ollama 0.32), e o modelo raciocina por cerca de mil tokens antes de responder; o harness manda exatamente o prompt em que o modelo foi treinado (detalhes no [cartão do GGUF](docs/cards/gguf-card.md)).

**Nos seus próprios dados.** O `scripts/ask.py` monta a tarefa a partir de um CSV, de uma história curta de como os dados foram gerados e de um dicionário com uma frase por coluna, pergunta ao modelo, lê a resposta e, quando o efeito é identificável, roda o estimador nas linhas:

```bash
uv run --no-sync python scripts/ask.py --csv campanha.csv --treatment email --outcome comprou \
    --story historia.txt --dictionary colunas.yaml --model ollama:hf.co/coppead/causalista-4b-GGUF:nothink --lang pt
```

A coluna da intervenção precisa valer 0 ou 1; cada coluna precisa de uma descrição (`--dictionary` em YAML ou JSON, ou `--column nome="..."` repetido); `--json registro.json` guarda a pergunta, a resposta crua e a estimativa. A mesma coisa em Python é `causalista.harness.ask(tabela, intervencao, resultado, historia, descricoes, respondedor)`. O modelo foi treinado em um formato de pergunta só e em seis dos oito temas de gestão do projeto; fora deles, não afirmamos nada sobre com que frequência ele acerta.

**Com o transformers, em uma GPU** (exige transformers 5.0 ou mais novo): o trecho de código está no [README em inglês](README.md#quickstart) e no [cartão do modelo](docs/cards/model-card.md).

## Como funciona

1. **Verificador** ([src/causalista/verifier/](src/causalista/verifier/)): dado o grafo causal verdadeiro, diz se um conjunto de colunas é um conjunto de ajuste válido, ou que nenhum é. Dois motores independentes (o critério de ajuste e a análise de caminhos) se conferem; 24 casos de livro-texto e uma rede de erros plantados o protegem.
2. **Fábrica de mundos** ([src/causalista/worlds/](src/causalista/worlds/)): a partir de uma ficha de teoria revisada por tema ([theories/](theories/)), sorteia variáveis e papéis causais, simula os dados e o efeito verdadeiro, e escreve a história, um fato por frase (em português, inglês ou espanhol) ou em prosa escrita por modelos abertos.
3. **Tarefa** ([src/causalista/task/](src/causalista/task/)): o que o modelo vê, a resposta em JSON, a nota e a resposta de referência derivada do gabarito do verificador.
4. **Estimador** ([src/causalista/estimator/](src/causalista/estimator/)): um estimador duplamente robusto com validação cruzada (DoubleML) que transforma as colunas escolhidas em efeito e intervalo de confiança.
5. **Harness** ([src/causalista/harness/](src/causalista/harness/)): roda qualquer modelo (Hugging Face, Ollama ou uma API compatível com a da OpenAI) sobre mundos gravados ou casos escritos e grava cada resposta. As páginas em [src/causalista/viz/](src/causalista/viz/) são geradas a partir desses registros, nunca desenhadas à mão.
6. **Treino** ([scripts/](scripts/)): ajuste fino supervisionado com LoRA em 22.906 exemplos (Unsloth + TRL), depois um passo curto de GRPO (reforço) cuja única recompensa é a nota do verificador em 208 casos que simulam texto de pessoas. A escolha entre os dois braços de treino seguiu uma regra fixada antes de ver os resultados ([cartão do modelo](docs/cards/model-card.md)).

## Mapa do repositório

| Caminho | O que é |
|---|---|
| [ESPECIFICACAO.md](ESPECIFICACAO.md) | A especificação: o que está sendo construído, em que ordem, e o registro dos portões de cada fase |
| [src/causalista/](src/causalista/) | O pacote: verifier, worlds, estimator, task, harness, viz. Cada pasta abre com um README |
| [theories/](theories/) | Uma ficha de teoria por tema, em YAML; traduções em `theories/i18n/` ([README](theories/README.md)) |
| [cases/](cases/) | Casos escritos, com as setas do diagrama e a resposta conferida pelo verificador; `cases/simulados/` guarda os 48 casos congelados da medição ([README](cases/README.md)) |
| [configs/](configs/) | Bases candidatas, a divisão de temas e sementes entre treino e teste, os mundos-vitrine ([README](configs/README.md)) |
| [scripts/](scripts/) | Geração de mundos, dados de treino, treino, rodadas de modelos, `ask.py`, conversão para GGUF, publicação ([README](scripts/README.md)) |
| [tests/](tests/) | Testes, espelhando `src/` |
| [docs/](docs/) | Diário do projeto e os cartões do Hugging Face ([docs/cards/](docs/cards/)); índice em [docs/README.md](docs/README.md) |
| `outputs/` | Tudo o que é gerado (mundos, rodadas, pesos, páginas); fora do git. Os conjuntos de mundos, casos, exemplos de treino e respostas gravadas em que os cartões se apoiam estão publicados no conjunto de dados |

## Reproduzir os resultados

Cada número dos cartões pode ser regenerado a partir deste repositório e do conjunto de dados. Um `uv sync` simples instala também a pilha de treino (GPU CUDA, cerca de 7 GB); os scripts de treino estão documentados em [scripts/README-treino.md](scripts/README-treino.md). O comando `hf` abaixo vem do `huggingface_hub`, que não está no ambiente leve: rode-o com `uvx --from huggingface_hub hf ...`.

```bash
# os conjuntos gravados por trás das tabelas (prova final: teste-v3; desenvolvimento: placar-v3)
uvx --from huggingface_hub hf download coppead/causalista-worlds --repo-type dataset --include "worlds/teste-v3/*" --local-dir outputs

# as linhas da tabela de resultados (hf: precisa de GPU; o 27B roda pelo Ollama, com raciocínio, 1 mundo em 10)
uv run python scripts/run_models.py --worlds teste-v3 --model rule:all --model rule:none \
    --model hf:Qwen/Qwen3-4B:nothink --model hf:coppead/causalista-4b:nothink
uv run python scripts/run_models.py --worlds teste-v3 --every 10 --model ollama:qwen3.8:27b
uv run python scripts/run_models.py --cases cases/simulados/*.yaml --name casos-simulados --model hf:coppead/causalista-4b:nothink
uv run python scripts/summarise_runs.py --set teste-v3 --markdown

# o treino publicado (o arquivo de dados é examples/sft-final.jsonl no conjunto de dados; semente 0; os argumentos
# e versões exatos estão em training/sft/run.json e training/grpo-c/run.json no repositório do modelo)
uv run python scripts/train_sft.py --data outputs/train/data/sft-final.jsonl --base Qwen/Qwen3-4B --run-name sft-final-qwen3-4b --epochs 1
uv run python scripts/train_grpo.py --base <modelo supervisionado fundido> \
    --cases cases/treino-simulados/pt-0[1-9].yaml cases/treino-simulados/pt-1[0-6].yaml cases/treino-simulados/en-0[1-9].yaml cases/treino-simulados/en-10.yaml

# mundos novos e as páginas
uv run python scripts/make_worlds.py --name meu-conjunto --pairs 13 --first-seed 50000
uv run python -m causalista.viz.scoreboard --set teste-v3
```

Cada uso (páginas, portão do estimador, placar de base, prova final, treino) tem a sua faixa de sementes (tabela em `scripts/make_worlds.py`); o treino nunca usa semente abaixo de 100.000, e os casos congelados nunca entram no treino. Não houve busca de hiperparâmetros: valem os padrões dos scripts.

## Dados e procedência

- As respostas-alvo do treino vêm sempre do verificador, nunca de um modelo de linguagem.
- As frases das histórias de treino vêm de oito fichas de teoria que um modelo de linguagem escreveu a partir da literatura de gestão e que instâncias independentes do mesmo modelo revisaram frase a frase; as histórias em prosa foram escritas por modelos abertos e mantidas só quando dois outros modelos abertos concordaram que eram fiéis. Os casos tipo humano foram escritos e revisados por instâncias de um modelo de linguagem. Os cartões dizem quem escreveu o quê.
- O autor tomou as decisões de desenho: a família de mundos e suas faixas, os temas, os pesos da nota, o modelo-base, o tamanho do treino e o protocolo de medição. O projeto foi construído pelo autor com um assistente de programação por IA.
- Código, identificadores e docstrings estão em inglês. A especificação, o diário, os READMEs dos pacotes e os arquivos de dados (`theories/`, `cases/`, com nomes que seguem o vocabulário da especificação) estão em português, a língua de trabalho do projeto.

## Documentação

- [docs/README.md](docs/README.md): índice, em inglês, de cada documento e pasta de dados.
- [ESPECIFICACAO.md](ESPECIFICACAO.md): a especificação e o registro dos portões.
- [docs/status.md](docs/status.md): o diário do projeto, dia a dia; os cartões o resumem.
- [docs/trabalhos-vizinhos.md](docs/trabalhos-vizinhos.md): os trabalhos vizinhos na literatura.
- [docs/cards/](docs/cards/): os cartões do modelo, do GGUF e dos dados (em inglês, com abertura em português).
- [CHANGELOG.md](CHANGELOG.md), [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md).

## Desenvolvimento

```bash
uv sync --no-group train               # execução e testes, sem torch
uv run --no-sync pytest                # a bateria padrão (10 a 15 minutos: os mundos são testados nos oito temas)
uv run --no-sync pytest -m slow        # exaustiva: todos os grafos de até cinco variáveis (cerca de 2 minutos)
```

Python 3.12. As páginas precisam do Graphviz (`sudo apt install graphviz`). Rode a bateria exaustiva depois de qualquer mudança em `src/causalista/verifier/`. Trabalhe a partir de um clone: o pacote lê `theories/` e `cases/` do repositório, então o wheel sozinho oferece só o verificador, o estimador e o formato da tarefa. O pacote também se instala com `pip install git+https://github.com/coppead/causalista`.

## Autores e contato

André Fonseca, COPPEAD, Instituto de Pós-Graduação e Pesquisa em Administração da Universidade Federal do Rio de Janeiro (UFRJ). Perguntas, problemas e ideias: [abra uma issue](https://github.com/coppead/causalista/issues); problemas de segurança pelo [canal privado](SECURITY.md) do repositório.

## Como citar

```bibtex
@software{fonseca2026causalista,
  author    = {Fonseca, André},
  title     = {Causalista: a small, local model that decides what to adjust for and says when the data cannot answer},
  year      = {2026},
  version   = {0.1.1},
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
