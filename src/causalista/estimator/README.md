# Estimador

Faz a conta do runner: o efeito e o intervalo de confiança, depois que as colunas de ajuste foram escolhidas. O modelo decide; este módulo calcula, sempre do mesmo jeito.

## O que entra

- a tabela;
- o nome da coluna de intervenção (0 ou 1) e o da coluna de resultado;
- as colunas de ajuste (podem ser nenhuma).

## O que sai

Um `EffectEstimate`:

- `effect`: o efeito médio da intervenção sobre o resultado;
- `low` e `high`: o intervalo de 95% de confiança;
- `clipped_share`: a fração de linhas quase certas de receber, ou de não receber, a intervenção. Se for grande, os dois grupos quase não se sobrepõem e a estimativa se apoia em poucas linhas.

## Como calcula

- **Sem ajuste** (`naive_difference`): a média do resultado em quem recebeu menos a média em quem não recebeu. É a comparação simples.
- **Com ajuste** (`adjusted_effect`): estimador duplamente robusto com validação cruzada, o modelo de regressão interativa do DoubleML. Ele não supõe uma forma particular para como as colunas agem sobre a intervenção ou sobre o resultado.

O estimador não sabe se o conjunto de ajuste é válido. Com um conjunto inválido ele devolve um número com intervalo estreito e errado; evitar isso é o trabalho do modelo.

## Como é testado

- Em `tests/estimator/`: tabelas pequenas em que a resposta é conhecida por construção.
- `scripts/check_estimator.py`: o portão da fase 2. Em centenas de mundos identificáveis, mede quantas vezes o intervalo contém o efeito verdadeiro (deve ficar perto de 95%) e confere que a comparação simples erra onde há confundidor.

```bash
uv run pytest tests/estimator
uv run python scripts/check_estimator.py --worlds 400
```

## O que foi medido

Medição de 2026-10-03, tema telecom, sementes 20000 a 20399 (465 mundos identificáveis):

| Medida | Resultado |
|---|---|
| Intervalo com o ajuste certo contém o efeito verdadeiro | 95,3% (o esperado é 95%) |
| Por tamanho da tabela (2 mil, 5 mil, 10 mil, 20 mil, 50 mil linhas) | 97,6%, 93,3%, 94,8%, 96,6%, 94,4% |
| Comparação simples contém o efeito verdadeiro, nos 429 mundos com confundidor | 24,0% |
| Comparação simples cai onde o mundo previa | 94,4% |
| Erro médio: ajuste certo e comparação simples | 1,2 e 4,3 pontos percentuais |

O estimador usa árvores com reforço de gradiente para aprender como as colunas agem. A alternativa com modelos lineares simples (`learner="linear"`) foi medida em 182 mundos do mesmo desenho e descartada: seu intervalo conteve o efeito verdadeiro em 85% deles, e em só 71% com tabelas de 50 mil linhas. Ela fica no código apenas para refazer essa comparação.
