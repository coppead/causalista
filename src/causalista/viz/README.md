# Visualização

Gera as páginas que mostram o projeto a quem não lê código. Especificação: seção 8.

## As três páginas

| Página | O que mostra | Estado |
|---|---|---|
| Casos | o tipo de decisão: a história, o diagrama causal, a escolha de colunas e o caminho que ela abre ou fecha | pronta, com os casos de livro-texto |
| Mundos | a mesma página com mundos gerados, mais o dicionário da tabela, o mundo gêmeo e três números na mesma régua: efeito verdadeiro, comparação simples e estimativa da escolha | pronta, com 20 mundos do tema telecom |
| Placar | onde está cada modelo e cada referência: acertos, abstenções indevidas, erros confiantes e respostas inválidas | pronta e publicada; mostra o que já rodou no placar de base |
| Aprendizado | o andamento do treino e o antes e depois em mundos fixos | fases 4 e 5 |

## Página de casos

**O que entra:** os casos de `src/causalista/verifier/textbook_cases.yaml`.

**O que sai:** um único arquivo HTML. Para cada caso, o verificador julga todas as escolhas possíveis de colunas, e a página mostra o veredito da escolha que a pessoa fizer. A página não decide nada: só consulta o que o verificador respondeu.

```bash
uv run python -m causalista.viz.gallery              # outputs/viz/casos.html, para abrir no navegador
uv run python -m causalista.viz.gallery --fragment   # a forma usada para publicar
```

Como ler o diagrama:

- seta azul: caminho causal, o efeito que se quer medir;
- faixa vermelha: caminho não causal aberto, que distorce o efeito;
- caixa amarela: coluna ajustada (clique na coluna para ajustar);
- contorno tracejado: variável fora da tabela.

## Página de mundos

**O que entra:** uma ficha de teoria. Os mundos mostrados são os primeiros pares de gêmeos, a partir da semente 1, com até 6 colunas e tabelas de 10 mil ou 20 mil linhas. A regra olha só o tamanho do mundo, nunca os resultados.

**O que sai:** um único arquivo HTML. Para cada mundo, o verificador julga todas as escolhas de colunas e o estimador calcula o efeito de cada uma. Isso leva alguns minutos na primeira vez; o resultado fica guardado em `outputs/viz/mundos_dados.json` e é reaproveitado enquanto a ficha, o gerador e o estimador não mudarem.

```bash
uv run python -m causalista.viz.worlds_page              # outputs/viz/mundos.html
uv run python -m causalista.viz.worlds_page --fragment   # a forma usada para publicar
```

## Página do placar

**O que entra:** os registros de uma rodada do harness, em `outputs/runs/<conjunto>/`.

**O que sai:** um único arquivo HTML. Uma barra por modelo mostra o que aconteceu com as respostas, e uma tabela traz todos os números. Os filtros (mundos identificáveis ou não, tema, idioma, nível da narrativa) refazem as contas a partir dos mesmos registros.

```bash
uv run python -m causalista.viz.scoreboard --set placar-base              # outputs/viz/placar.html
uv run python -m causalista.viz.scoreboard --set placar-base --fragment   # a forma usada para publicar
```

As quatro cores das barras foram conferidas como conjunto (separação para daltônicos e contraste) no fundo claro e no escuro.

## Organização

| Arquivo | O que faz |
|---|---|
| `layout.py` | pede ao Graphviz a posição de cada variável e a curva de cada seta |
| `gallery.py` | monta os dados da página de casos a partir do verificador |
| `worlds_page.py` | monta os dados da página de mundos: verificador mais estimador |
| `gallery.html` | o molde das duas páginas: estilo, estrutura e interação |
| `scoreboard.py` | monta os dados da página do placar a partir dos registros do harness |
| `scoreboard.html` | o molde da página do placar |

Requer o Graphviz instalado (`sudo apt install graphviz`). Os testes em `tests/viz/` conferem que a página carrega exatamente os veredictos do verificador.
