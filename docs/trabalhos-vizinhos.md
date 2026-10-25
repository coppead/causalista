# Trabalhos vizinhos do Causalista

Busca feita em 3 de outubro de 2026. Entrega da fase 0 da especificação.

## Em poucas palavras

A frase "ninguém fez isso" não se sustenta. Já existem trabalhos que treinam modelos de linguagem com reforço e recompensa verificável em tarefas causais, e pelo menos um ambiente público em que o modelo é premiado por escolher o método de identificação e o conjunto de variáveis certos.

O que a busca não encontrou é a combinação que o Causalista propõe: decidir o ajuste a partir de uma descrição em linguagem comum, sem o grafo na mão, com o veredito "não identificável" dentro da recompensa, em um modelo aberto pequeno.

## O que já foi feito

**Reforço com recompensa verificável em tarefas causais.**

- Lu e colegas (2025) comparam ajuste supervisionado e reforço em modelos Qwen2.5 de 3B a 32B. A tarefa é calcular probabilidades sobre grafos causais dados, não escolher ajuste. O reforço generalizou melhor, mas só quando o modelo já tinha alguma competência inicial.
- Chen, Chen e Lu (2026, CauGym) comparam cinco formas de pós-treino, inclusive GRPO, em sete tarefas causais. O modelo deles de 14B chegou a 93,5% em um benchmark em que o o3 da OpenAI fez 55,4%. A saída é um número, não uma decisão de ajuste.

**Reforço com verificador para a decisão de identificação.**

- CausalReasoningEnv (Jamil, março de 2026) é um ambiente público no hub da Prime Intellect. O modelo recebe um grafo formal e declara o método (porta dos fundos, porta da frente ou variável instrumental) e o conjunto de nós. O autor treinou um Qwen3 de 30B por 200 passos. Não é artigo revisado: é um repositório e um post.
- causal-gym (agosto de 2026) é outro ambiente no mesmo hub: o agente recebe uma tabela e um dicionário de dados e entrega o efeito com intervalo; o conjunto de ajuste vale parte da nota.

**Benchmarks em que o modelo decide a partir de texto e dados, sem treino.**

- CausalDS (Leban e Sun, julho de 2026) é o vizinho mais próximo do nosso gerador e do nosso placar: mundos sintéticos com grafo oculto, história em linguagem natural escrita por modelo, tabela, tarefas de conjunto de ajuste e abstenção pontuada quando o efeito não é identificável. É só avaliação; o código é aberto.
- CausalReasoningBenchmark (Sawarni, Tan e Syrgkanis, 2026) usa 174 perguntas sobre 139 bases de dados reais. Um modelo de fronteira acertou a estratégia geral em 81% dos casos, mas a especificação completa de identificação em só 38%.

**Abstenção.** Vários benchmarks pontuam a abstenção em perguntas causais. Fora do domínio causal, há treino por reforço com recompensa para "não sei" (TruthRL, 2025).

## O que parece não ter sido feito

A confiança é média em todos os itens: ambientes em hubs e posts são mal indexados, e a busca não cobriu bem os periódicos de marketing.

- Treinar a decisão de ajuste a partir de descrição em linguagem comum mais a lista de colunas, sem grafo fornecido. Os treinos encontrados usam grafo formal; os benchmarks com texto não treinam.
- Pôr o veredito "não identificável" na recompensa, com penalidade maior para o erro confiante. Os dois ambientes de identificação só geram problemas identificáveis.
- Fazer isso em um modelo aberto de 3B a 4B. A decisão de identificação foi treinada em um modelo de 30B, sem pesos publicados.
- Narrativas de negócio ancoradas em teorias de gestão.
- Publicar junto o modelo, o ambiente e o placar para essa decisão.

## Como escrever a novidade

Não escrever "primeiro a treinar um modelo com reforço em recompensa causal verificável", nem "primeiro ambiente causal". As duas frases têm contraexemplo.

Formulação defensável:

> Até onde encontramos, em busca de outubro de 2026, este é o primeiro trabalho a treinar um modelo aberto pequeno (3B a 4B), com ajuste supervisionado seguido de reforço, para decidir qual conjunto de ajuste usar ou declarar o efeito não identificável, a partir de uma descrição em linguagem natural de como os dados foram gerados e da lista de colunas, sem grafo fornecido. A recompensa vem de um verificador do critério de ajuste e penaliza mais o erro confiante do que a abstenção. Trabalhos anteriores treinam com reforço sobre grafos formais (Lu et al.; CauGym; CausalReasoningEnv) ou avaliam, sem treinar, decisões de identificação a partir de texto (CausalDS; CausalReasoningBenchmark).

## O que isso muda no projeto

1. **A tese continua de pé, mais estreita.** A contribuição deixa de ser "reforço verificável para julgamento causal" em geral e passa a ser a decisão a partir de texto, com abstenção, em modelo pequeno, com teoria de gestão como simulador.
2. **Há indício de espaço acima da fronteira quando o grafo não é dado.** No CausalReasoningBenchmark, um modelo de fronteira acertou a especificação completa em 38% dos casos reais. Isso não vale automaticamente para os nossos mundos; o placar de base da fase 3 é que mede.
3. **O resultado do CauGym é animador para a aposta.** Um modelo de 14B com pós-treino dirigido superou um modelo de fronteira muito maior em tarefas causais.
4. **Risco conhecido no passo de reforço.** Che e colegas (julho de 2026) mostram que, quando abster-se é uma resposta possível e o erro é penalizado, o treino pode derivar para recusar tudo, com a curva de recompensa subindo enquanto o modelo para de responder. Mostram também que a normalização por grupo, que o GRPO usa, pode apagar a diferença entre as penalidades desenhadas. Isso toca diretamente a nossa nota assimétrica. Antes da fase 5 é preciso decidir se mantemos a abstenção como resposta ou se adotamos o conserto que eles propõem: o modelo sempre informa a confiança, e a abstenção é decidida por um limiar na hora do uso.
5. **Comparação externa disponível.** Avaliar o Causalista também no CausalDS ou no CausalReasoningBenchmark daria uma medida que não fomos nós que construímos. Fica proposto para a lista da 0.2.
6. **Nomes.** "CauGym" e "causal-gym" já estão em uso. "Causalista" não colide com nenhum trabalho encontrado.

## Referências principais

| Trabalho | Onde | O que é |
|---|---|---|
| Lu, Zhao, Sun, Peng e outros (2025). Generalization of RLVR Using Causal Reasoning as a Testbed | https://arxiv.org/abs/2512.20760 | reforço e ajuste supervisionado em consultas probabilísticas sobre grafos causais |
| Chen, Chen e Lu (2026). Can Post-Training Transform LLMs into Causal Reasoners? (CauGym) | https://arxiv.org/abs/2602.06337 | cinco formas de pós-treino em sete tarefas causais |
| Jamil (2026). CausalReasoningEnv | https://github.com/ijamil1/CausalReasoningEnv | ambiente de reforço para escolher método e conjunto de nós em grafos formais |
| ulcompute (2026). causal-gym | https://api.primeintellect.ai/api/v1/environmentshub/ulcompute/causal-gym/@latest | ambiente com tabela, dicionário e efeito a estimar |
| Leban e Sun (2026). CausalDS | https://arxiv.org/abs/2607.08093 | benchmark de mundos sintéticos com história, tabela, ajuste e abstenção |
| Sawarni, Tan e Syrgkanis (2026). CausalReasoningBenchmark | https://arxiv.org/abs/2602.20571 | identificação e estimação avaliadas em separado, em dados reais |
| Che, Yuan, Zhao e Yu (2026). Abstention as an Action Can Kill Both the Reward Gradient and the KL Anchor | https://arxiv.org/abs/2608.00301 | colapso para a recusa em reforço com penalidade de erro, e um conserto |
| Wei e outros (2025). TruthRL | https://arxiv.org/abs/2509.25760 | reforço com recompensa para acerto, abstenção e erro em perguntas factuais |
| Kirichenko, Ibrahim, Chaudhuri e Bell (2025). AbstentionBench | https://arxiv.org/abs/2506.09038 | modelos de raciocínio falham em perguntas sem resposta |
| Vaidya, Jerzak, Sprague, Yin e outros (2026). When Many Answers Are Valid, Voting Fails | https://arxiv.org/abs/2608.03506 | verificador simbólico para escolher entre respostas causais, sem treino |
| He, Huang, Sachan e Jin (2026). Uncovering Hidden Correctness in LLM Causal Reasoning via Symbolic Verification | https://arxiv.org/abs/2601.21210 | checagem simbólica de expressões causais geradas por modelo |
| Zhang, Correia, Parra e Xie (2026). CausalVerify | https://arxiv.org/abs/2609.07944 | verificação de ponta a ponta de análises causais feitas por modelo |
| Chen e outros (2024). Causal Evaluation of Language Models (CaLM) | https://arxiv.org/abs/2405.00622 | benchmark com tarefas de ajuste e identificabilidade sobre grafos dados |
| Jin e outros (2023). CLadder | NeurIPS 2023 (citado de memória; não reaberto nesta busca) | perguntas causais em linguagem natural com gabarito formal |

## O que foi e o que não foi conferido

A busca foi feita por um agente auxiliar, que abriu a página de cada trabalho citado. Depois eu conferi, por conta própria:

- que os 18 artigos do arXiv citados existem, com os títulos e autores indicados;
- os resumos de cinco deles (Lu et al., CauGym, CausalDS, CausalReasoningBenchmark e Che et al.), que batem com o que está escrito aqui;
- que os dois ambientes existem no hub e que o repositório do CausalReasoningEnv descreve o treino do Qwen3 de 30B.

Não conferi os demais detalhes: os números internos dos artigos, o que cada benchmark contém além do resumo, e as revistas de epidemiologia e marketing. Antes de citar qualquer número em artigo ou relatório, é preciso abrir a fonte.

A busca tentou, sem achar nada, consultas sobre treino por reforço para escolher conjunto de ajuste a partir de linguagem natural, no arXiv, OpenReview, GitHub, Hugging Face e em hubs de ambientes. O Google Scholar não foi consultado, e o Semantic Scholar respondeu a poucas consultas.
