# Casos que simulam texto de pessoa

Quarenta e oito casos escritos como uma pessoa escreveria (e-mail ao chefe, mensagem de chat, ata de reunião, trecho de relatório, pergunta em fórum), em português, inglês e espanhol, em temas dentro e fora dos oito do projeto. São a prova mais difícil do modelo: texto que ele nunca viu, com a estrutura causal dita do jeito que gente diz.

**Por que existem.** A especificação (seção 7) pede 30 casos escritos por pessoas. Em 6 de outubro de 2026 o André disse que não há como pôr uma etapa humana no fluxo e pediu que o assistente simulasse esse texto "no limite da sua capacidade". É isso que estes arquivos são: não são texto de pessoas de verdade, e o relatório do projeto não pode dizer que são.

**Como foram feitos.** Seis instâncias do assistente escreveram oito casos cada, cada uma no papel de pessoas definidas (gerente, analista, professora...), sem acesso às fichas de teoria. Cada caso declara o diagrama causal e a resposta; o verificador confere a resposta contra o diagrama (`scripts/check_cases.py`). Depois, outras seis instâncias revisaram os arquivos, um cada: se o texto implica exatamente o diagrama, se a informação que falta é inferível, se há "dicas" que um modelo raso exploraria (a mesma frase em todo caso não identificável, a frase decisiva sempre no mesmo lugar), se alguma frase ecoa as fichas. As revisões mudaram texto em quase todos os casos e corrigiram erros de tempo e de inferência em vários. A sobreposição de palavras com as fichas, medida em sequências de cinco palavras, ficou abaixo de 1,5% em todos os casos.

**Congelados em 6 de outubro de 2026**, antes de qualquer modelo responder. Nunca entram em treino nem servem para ajustar nada. Em 24 de outubro de 2026 mudaram, em cada arquivo, só o comentário do cabeçalho e o rótulo `author` (de um nome próprio para `ai`); história, colunas, setas e resposta de cada caso são os de 6 de outubro, conferidos linha a linha contra a etiqueta `v0.1.0`. As somas de verificação dos arquivos atuais:

| Arquivo | Casos | Não identificáveis | Idioma | SHA-256 |
|---|---|---|---|---|
| `en-1.yaml` | 8 | 3 | en | `4b1ea39d3db88ffebbc44e66e1bd9f196aacdc676ce163bb26eac46e49228d1a` |
| `en-2.yaml` | 8 | 3 | en | `e44fff50b42b1089fc67bb797af236b2b685cee80a5a0b31853be5f14ed6e714` |
| `es-1.yaml` | 8 | 4 | es | `587eaed728a7a249c9738fdb1adb012bc3583cdcbe40d9e8d68e5e997efdc159` |
| `pt-1.yaml` | 8 | 3 | pt | `3339215943bcfeed370250b57f511b427604ecbc5e160a3444a454f2c5a606df` |
| `pt-2.yaml` | 8 | 4 | pt | `58212c290b444fc084cea0ec35527ea75a7c87896fcc98477924d1548c527755` |
| `pt-3.yaml` | 8 | 4 | pt | `51018afbf45dae6fa3d6616cc4352e82f86183540b944587f6ba3a75a4c68cfa` |

Estilos usados: e-mail longo (3), e-mail to the data team (2), one-page memo (2), notes from a call with a consultant (2), short internal wiki page (2), chat message (2), meeting notes (2), mensaje de chat (2), fragmento de informe (2), pregunta en un foro (2), mensagem de Slack para o time de dados (2), pergunta em um fórum de analytics (2), e-mail para o chefe (2), trecho de relatório interno (2), transcrição de um áudio informal (2), e-mail com anexo descrito (2), mensagem de WhatsApp (2), Slack message (1), forum post (1), quarterly report excerpt (1), question to a consultant (1), acta de reunión (1), correo al jefe (1), ata de reunião (1), trecho de relatório trimestral (1), nota curta para o chefe (1), pergunta em fórum (1), tópicos de reunião (1), briefing para uma consultoria (1), trecho de dissertação de mestrado (1).

**Como o modelo os responde.** `scripts/run_models.py --cases cases/simulados/*.yaml --name casos-simulados --model ...`. Como um caso não tem tabela, o resumo de cada coluna (média, fração de 1) é inventado a partir da descrição da coluna (`src/causalista/harness/cases.py`); história, colunas, diagrama e resposta são os do autor.
