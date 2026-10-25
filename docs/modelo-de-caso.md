# Modelo para os casos escritos à mão

Entrega da fase 0: cinco casos, escritos pelo assistente a pedido do André e aprovados por delegação depois de revisão independente (`cases/fase0.yaml`). Copie o modelo abaixo, um por caso.

As setas são opcionais. Sem elas, o assistente propõe as setas a partir da história e o André confirma. Com elas, o verificador confere se a resposta bate.

Sugestão para os cinco: variar os temas e incluir pelo menos um caso não identificável e um em que a mesma coluna muda de papel por ser medida antes ou depois da intervenção.

## Modelo

```text
CASO 1

Tema:
  (um dos oito temas, ou outro que você queira)

Pergunta:
  Qual o efeito de [intervenção] sobre [resultado]?

Colunas da tabela:
  - [nome]: o que é, e se é medida antes ou depois da intervenção
  - ...

O que influencia a história mas NÃO está na tabela:
  (ou "nada")

História (um parágrafo):
  Quem recebe a intervenção e por quê. O que influencia o resultado.
  O que acontece depois da intervenção.

Resposta que você considera certa:
  Veredito: identificável / não identificável
  Ajustar por:
  Não ajustar por (com o motivo em uma linha):
  Se não identificável, o que falta:

Setas, se quiser (opcional): "causa -> efeito", uma por linha
```

## Um exemplo preenchido

```text
Tema:
  Varejo

Pergunta:
  Qual o efeito do cupom de desconto sobre a recompra em 60 dias?

Colunas da tabela:
  - cupom: 1 se o cliente recebeu o cupom (intervenção)
  - recompra: 1 se comprou de novo em até 60 dias (resultado)
  - gasto_12m: quanto gastou nos 12 meses ANTES do cupom
  - abriu_app: se abriu o aplicativo na semana DEPOIS do cupom
  - regiao: região do cliente

O que influencia a história mas NÃO está na tabela:
  nada

História:
  A loja enviou o cupom com mais frequência a quem gastou mais nos
  últimos 12 meses. Quem gasta mais já recompra mais, com ou sem cupom.
  Quem recebe o cupom abre mais o aplicativo na semana seguinte, e quem
  abre o aplicativo compra mais. A região não influenciou quem recebeu
  o cupom, mas em algumas regiões os clientes recompram mais.

Resposta que você considera certa:
  Veredito: identificável
  Ajustar por: gasto_12m
  Não ajustar por: abriu_app (é consequência do cupom; faz parte do efeito)
  Se não identificável, o que falta: —

Setas:
  gasto_12m -> cupom
  gasto_12m -> recompra
  cupom -> abriu_app
  abriu_app -> recompra
  cupom -> recompra
  regiao -> recompra
```
