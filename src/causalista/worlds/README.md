# Mundos

Fabrica mundos sintéticos: cada mundo tem uma história, uma tabela e uma resposta certa conhecida. É o material de treino e de prova do modelo. Especificação: seção 3.

## O que entra

Uma ficha de teoria (`theories/<tema>.yaml`), que diz o que a teoria afirma sobre o tema: quais variáveis existem, quais papéis cada uma pode ter e com que sinal ela age. A do telecom foi aprovada pelo André; as outras sete foram escritas pelo assistente e aprovadas por delegação dele em 5 de outubro de 2026, depois de uma revisão independente. Há uma ficha para cada um dos oito temas.

As fichas são escritas em português. Para contar um mundo em outro idioma, `load_theory(tema, idioma)` lê a tradução em `theories/i18n/<idioma>/<tema>.yaml`. A tradução só traz palavras (rótulos, descrições das colunas e frases); sinais, tipos, tamanhos e nomes das colunas vêm sempre da ficha.

## O que sai

Um mundo (`World`), sempre em duas partes:

| Parte | Conteúdo | Quem vê |
|---|---|---|
| visível | a pergunta, a narrativa, o dicionário das colunas e a tabela | o modelo e o analista |
| escondida | o grafo, os papéis, os tamanhos dos efeitos, o efeito verdadeiro e o gabarito | só a avaliação |

`save_world` grava cada parte em uma pasta (`visible/` e `hidden/`).

Os mundos saem em pares de gêmeos (`generate_pair`): dois mundos que diferem em um único fato e têm respostas diferentes. O fato é uma coluna estar ou não na tabela, ou o papel de uma variável (a reclamação registrada antes ou depois da oferta). A mesma semente sempre gera o mesmo par.

## Como um mundo é feito

1. **Estrutura** (`structure.py`). Sorteia de 3 a 8 variáveis da ficha e um papel para cada uma, entre os que a ficha permite. O grafo sai daí. O gabarito é calculado pelo verificador, nunca pelos rótulos dos papéis.
2. **Números** (`mechanism.py`). Cada variável recebe seu valor das suas causas mais o acaso. Os sinais vêm da ficha; os tamanhos são sorteados dentro das faixas abaixo.
3. **Efeito verdadeiro.** Os mesmos clientes são simulados duas vezes, uma com todos recebendo a intervenção e outra com ninguém recebendo. A diferença é o efeito verdadeiro.
4. **Narrativa e dicionário** (`narrative.py`). As frases da ficha, uma por fato, em ordem sorteada: em cerca de metade dos mundos as frases de uma mesma variável ficam juntas (em qualquer ordem), e na outra metade todas as frases se espalham pela história. Antes de 5 de outubro de 2026 as frases de uma variável vinham sempre juntas e na mesma ordem, e um modelo treinado nessas histórias se apoiava nisso (seção 26 de `docs/status.md`). As histórias de dois mundos gêmeos continuam diferindo só no fato que mudou. A narrativa nunca diz o papel de uma variável nem o efeito que se pergunta. É o nível 1 da especificação.
5. **Outro idioma** (`retell`, em `world.py`). O mesmo mundo contado com as frases da tradução da ficha. Nada do mundo muda: só as palavras.
6. **Prosa corrida** (`prose.py`). É o nível 2: um modelo aberto reescreve a narrativa de nível 1 do jeito que uma pessoa contaria. Dois outros modelos leem a prosa e respondem, frase por frase, se o texto diz cada fato do mundo e se diz algum fato dos outros papéis das mesmas variáveis. A prosa só fica se os dois concordarem que ela diz todos os fatos do mundo e nenhum dos outros; se não, o escritor é avisado e reescreve, até duas vezes. A calibração está em `docs/status.md`.

## Decisões de desenho que são do André

Estes números estão no código como propostas e podem mudar.

| O quê | Valor proposto | Onde |
|---|---|---|
| Variáveis por mundo | de 3 a 8 | `structure.py` |
| Mediadores e colisores por mundo | no máximo 2 de cada | `structure.py` |
| Mundos com confundidor fora da tabela | 65% dos sorteios; com os gêmeos, cerca de 45% dos mundos não são identificáveis | `structure.py` |
| Informação que falta na tabela sem fazer mal (causa só do resultado, ou só da intervenção) | na maior parte dos mundos; no máximo duas ausências por mundo, contando os confundidores | `structure.py` |
| Gêmeo por mudança de tabela ou por mudança de papel | cerca de 3 pares em 4 mudam o veredito; os demais mudam só o conjunto | `structure.py` |
| Mundos em que a intervenção não tem efeito próprio | 15% (30% quando há mediador) | `structure.py` |
| Tamanho dos efeitos | faixas em `STRENGTH` | `mechanism.py` |
| Linhas por tabela | 2 mil, 5 mil, 10 mil, 20 mil ou 50 mil | `mechanism.py` |
| Sobreposição mínima | ninguém com menos de 2% ou mais de 98% de chance de receber a intervenção, nos percentis 1 e 99 | `mechanism.py` |

Por que não é metade a metade: gêmeos precisam ter respostas diferentes, então dois mundos não identificáveis nunca formam par.

## Traduções das fichas

`scripts/translate_theory.py` traduz uma ficha com um modelo aberto e pede a um segundo modelo aberto, de outra família, que compare cada frase com a original: mesmo sujeito, mesma direção (mais ou menos), mesmo momento (antes ou depois). Uma frase recusada é traduzida de novo com a objeção; se for recusada duas vezes, fica listada no cabeçalho do arquivo para ser corrigida à mão.

Os nomes das colunas não são traduzidos: em qualquer idioma, a tabela tem as colunas da ficha.

## Sementes

Cada uso tem a sua faixa de sementes, para que nenhum mundo de teste seja mundo de treino. A tabela está em `scripts/make_worlds.py`.

## Como é testado

Em `tests/worlds/`:

- a ficha é recusada se estiver incompleta ou incoerente, ou se um mediador levar o efeito no sentido contrário ao da teoria;
- os limites de mediadores e colisores valem em milhares de sorteios (uma variável que só pode ser mediador furava o limite uma vez em cada 300 mundos; corrigido em 4 de outubro de 2026);
- a prosa fiel é mantida e a prosa infiel é descartada (com modelos de mentira, sem placa de vídeo);
- toda estrutura sorteada contém só o que a ficha permite;
- o verificador concorda com o que os papéis implicam (nesta família, o efeito é identificável exatamente quando nenhum confundidor está oculto);
- os gêmeos diferem em um fato e na resposta, e compartilham todos os números em comum;
- as taxas batem com os alvos, os grupos se sobrepõem e o efeito verdadeiro tem o sinal que a teoria diz;
- a narrativa conta todos os fatos e não entrega a resposta;
- o que é gravado como visível não contém nada do gabarito.

Os testes rodam uma vez para cada ficha da pasta `theories/`.

```bash
uv run pytest tests/worlds              # todos os temas
uv run pytest tests/worlds -k varejo    # um tema só
```
