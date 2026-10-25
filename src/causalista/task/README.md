# Tarefa

Define a tarefa dada a um modelo: o que ele vê, como responde e como a resposta é pontuada. Especificação: seções 2 e 5.

## O que entra

Um mundo (ou uma tabela com o seu dicionário e a história de como os dados foram gerados).

## O que sai

- `task_of` e `build_prompt`: o texto mostrado ao modelo. Traz a pergunta, a história e, para cada coluna, o nome, o tipo, um resumo simples (média, mínimo e máximo, ou a fração de 1) e a descrição. O modelo nunca vê as linhas, o grafo nem o efeito verdadeiro. O mesmo texto vai para todos os modelos comparados.
- `parse_answer`: lê a resposta do modelo. O formato é um objeto JSON com quatro partes, nesta ordem: o papel de cada coluna com um motivo de uma linha, o veredito, o conjunto de ajuste (ou o que falta) e as suposições.
- `judge`: a nota. Quem decide se a resposta está certa é o verificador, no grafo verdadeiro.
- `ideal_answer`: a resposta ideal de um mundo, usada como alvo no treino supervisionado. Sai inteira do gabarito: o papel de cada coluna vem da estrutura, o veredito e o conjunto vêm do verificador, e o que falta vem das variáveis ocultas. Os motivos de uma linha dizem os fatos do grafo, no idioma da história.

## A nota

| Mundo | Resposta do modelo | Nota | Nome |
|---|---|---|---|
| Identificável | identificável, conjunto válido | +1 | acerto |
| Identificável | identificável, conjunto inválido | −1 | erro confiante |
| Identificável | não identificável | −0,5 | abstenção indevida |
| Não identificável | não identificável | +1 | acerto |
| Não identificável | identificável, qualquer conjunto | −1 | erro confiante |
| Qualquer | texto que o runner não consegue usar | −1 | resposta inválida |

A última linha não está na especificação. É uma proposta, e a decisão é do André: uma resposta sem veredito (um texto cortado, ou que não segue o formato) vale −1 e é contada à parte do erro confiante.

Uma resposta que afirma o efeito ajustando por algo que não é coluna da tabela (uma variável oculta, um nome que não existe) é erro confiante.

Cada nota vem com o motivo, nas palavras do verificador: que coluna não podia entrar no ajuste e por quê, que caminho ficou aberto, o que faltou na tabela.

## Decisões de desenho

- As instruções e os nomes dos papéis ficam em inglês, iguais para todos os idiomas. A história e as descrições das colunas ficam no idioma do mundo, e o modelo escreve os motivos nesse idioma.
- A leitura da resposta tolera a embalagem (um bloco de código, um trecho de raciocínio antes do JSON) e é rígida no que o runner precisa: o veredito e um conjunto feito de colunas da tabela.
- Só o veredito e o conjunto entram na nota. Os papéis, o que falta e as suposições são gravados, e `complete` diz se vieram todos.

## Como é testado

Em `tests/task/`: a tabela da nota, linha por linha; os motivos; respostas embrulhadas e respostas inutilizáveis; e a conferência de que o texto mostrado ao modelo não entrega nada do gabarito.
