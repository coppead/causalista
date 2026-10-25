# Verificador

Decide, olhando o grafo verdadeiro de um mundo, se uma escolha de colunas dá o efeito certo. É a peça que dá o gabarito de todo o projeto: a nota do modelo, as respostas ideais do treino e as páginas de visualização saem daqui. Especificação: seção 4.

## O que entra

Um problema causal (`CausalProblem`):

- o grafo, escrito como uma lista de `"causa -> efeito"`;
- a intervenção e o resultado;
- as variáveis que não estão na tabela.

## O que sai

Duas respostas, cada uma com o motivo.

**`check_adjustment_set(problema, colunas)`**: este conjunto é válido?

- `valid`: se o ajuste dá o efeito certo;
- `forbidden`: colunas que nunca podem entrar no ajuste, e por quê (mediador, consequência de mediador, consequência do resultado);
- `open_paths`: caminhos não causais que ficam abertos, e qual coluna abriu cada um;
- `not_in_table`: colunas pedidas que não existem na tabela.

**`identify(problema)`**: dá para identificar o efeito com esta tabela?

- `identifiable`: sim ou não;
- `adjustment_set`: o menor conjunto válido;
- `open_paths`: se não dá, o caminho que nenhuma coluna fecha;
- `missing`: se não dá, a variável que faltou na tabela.

"Válido" quer dizer "não enviesa o efeito". Um conjunto válido pode conter uma coluna inútil.

## Como está organizado

| Arquivo | O que faz |
|---|---|
| `graph.py` | o problema causal e a validação da entrada |
| `adjustment.py` | o motor rápido: critério de ajuste pelo grafo de porta dos fundos |
| `paths.py` | o motor por definição: enumera os caminhos um a um |
| `check.py` | as duas respostas com os motivos; consulta os dois motores e recusa-se a responder se discordarem |
| `textbook_cases.yaml` | os casos de livro-texto, escritos para serem lidos por uma pessoa |
| `textbook.py` | leitura dos casos |

Os dois motores não compartilham código de propósito: cada um confere o outro.

## Como é testado

Quatro camadas independentes, todas em `tests/verifier/`:

1. **Casos de livro-texto.** 24 grafos pequenos com a resposta escrita à mão em `textbook_cases.yaml`, incluindo o motivo de cada erro.
2. **Força bruta.** Em todos os 29.281 grafos de cinco variáveis (e nos menores), para todo conjunto, o motor rápido e a definição por caminhos têm de concordar.
3. **Modelos lineares.** Nos mesmos grafos, todo conjunto dito válido tem de recuperar o efeito verdadeiro em uma regressão calculada com infinitas linhas, e os inválidos não. Esta camada não usa teoria de grafos: é uma conta.
4. **Segunda opinião externa.** 400 problemas sorteados, com as respostas do dagitty (a implementação de referência do critério) guardadas em `tests/verifier/reference/`.

Além disso, `test_safety_net.py` planta erros de propósito no verificador e confirma que os testes os pegam.

```bash
uv run pytest tests/verifier            # dia a dia, alguns segundos
uv run pytest -m slow                   # todos os grafos de cinco variáveis, cerca de dois minutos
```

Para refazer as respostas do dagitty é preciso R com os pacotes `dagitty` e `jsonlite`:

```bash
uv run python tests/verifier/reference/make_dagitty_reference.py
```
