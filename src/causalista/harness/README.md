# Harness de avaliação

Roda modelos e estratégias ingênuas sobre mundos gravados, grava cada resposta e soma os números do placar. Especificação: seções 7 e 8.

## O que entra

- Um conjunto de mundos gravados em `outputs/worlds/<conjunto>/`, cada um com a parte visível (pergunta, história, dicionário, tabela) e o gabarito. Quem gera é `scripts/make_worlds.py`.
- Um ou mais respondedores. Todos recebem a mesma tarefa e devolvem o texto de uma resposta:

| Respondedor | O que é |
|---|---|
| `OllamaModel` | um modelo servido pelo Ollama desta máquina |
| `HFModel` (em `hf.py`) | um modelo do Hugging Face carregado na placa de vídeo, com ou sem o adaptador treinado; é o mesmo caminho usado no treino |
| `OpenAIModel` | um modelo de fronteira via API compatível com a da OpenAI; a chave vem de uma variável de ambiente |
| `ADJUST_FOR_EVERYTHING` | "ajusta tudo": afirma o efeito ajustando por todas as colunas |
| `ADJUST_FOR_NOTHING` | "ajusta nada": afirma o efeito com a comparação simples |

## O que sai

Um registro por mundo e por respondedor, em `outputs/runs/<conjunto>/<respondedor>.jsonl`:

- o mundo, o tema, o idioma e o nível da narrativa;
- o modelo e, se houver, o ponto do treino;
- a resposta como veio e como foi lida;
- o tipo de desfecho (acerto, abstenção indevida, erro confiante, resposta inválida), a nota e o motivo dado pelo verificador;
- quando a resposta afirma um efeito, o efeito e o intervalo que o runner calcula com as colunas escolhidas, e o efeito verdadeiro do mundo.

As páginas de visualização só leem esses registros.

`summarise` soma os registros nas métricas da seção 7: nota média, taxa de erro confiante, taxa de abstenção indevida, cobertura do intervalo e erro do efeito nos casos respondidos.

## Como usar

```bash
uv run python scripts/make_worlds.py --name placar-base --pairs 13 --first-seed 50000
uv run python scripts/run_models.py --worlds placar-base --model rule:tudo --model rule:nada \
    --model ollama:qwen3.8:27b --model hf:Qwen/Qwen3-4B:nothink
uv run python -m causalista.viz.scoreboard --set placar-base
```

Uma rodada interrompida pode ser retomada: os mundos já respondidos não são refeitos.

Para medir um modelo treinado, `--adapter <pasta do adaptador>` põe o adaptador sobre os modelos `hf:` da chamada.

## Decisões de desenho

- **Sementes separadas por uso.** Mundos de página, do portão do estimador, do placar de base, do teste final e do treino usam faixas de sementes diferentes (a tabela está em `scripts/make_worlds.py`). Nenhum mundo de teste é mundo de treino.
- **Com e sem raciocínio.** Alguns modelos pequenos escrevem um raciocínio antes da resposta. O placar mostra os dois modos em linhas separadas. O modelo treinado responde direto, então a comparação justa com a base é a linha "sem raciocínio".
- **Resposta sem texto útil conta como inválida.** Um modelo que esgota o limite de texto sem dar o veredito fica registrado como resposta inválida, com o motivo.
- **Falha de máquina não é resposta.** Se o servidor do modelo falha (falta de memória na placa de vídeo, conexão que cai), nada é gravado para aquele mundo: ele fica para a próxima rodada. Depois de cinco falhas a rodada para com erro. Em 4 de outubro de 2026 uma rodada inteira falhou por falta de memória e foi gravada como 197 respostas inválidas; os registros foram apagados, e o harness passou a se comportar assim.
- **A conta do runner é guardada ao lado do mundo** (`estimates.json`), porque muitos respondedores escolhem os mesmos conjuntos.

## Como é testado

Em `tests/harness/`: um mundo gravado volta igual ao original; o gabarito tira nota +1 em todos os mundos; as estratégias ingênuas nunca se abstêm; uma rodada retomada não refaz nem perde respostas.
