# Causalista 0.1 — especificação

Revisão 7 · 2026-10-05

**Em uma frase:** transformar o julgamento causal em tarefa verificável, para que um modelo pequeno aprenda, por reforço, a tomar as decisões de identificação certas e a saber quando não pode.

Regra de escopo: nada entra na 0.1 depois deste documento. O que surgir vai para a lista da 0.2 (seção 10).

## 1. O que é

Um analista causal pequeno, local e honesto. A pessoa entrega uma tabela, diz qual coluna é a intervenção e qual é o resultado, e conta o que sabe sobre como os dados foram gerados. O Causalista decide por quais colunas ajustar, calcula o efeito médio com intervalo de confiança, lista as suposições e, quando os dados não permitem concluir, diz "não identificável" e explica o que falta.

A pessoa entra com a estrutura (o que sabe sobre como os dados nasceram); o modelo entra com a disciplina.

Divisão de trabalho da 0.1: **o modelo decide, o runner calcula.**

- O modelo (um modelo aberto de 3B a 4B com ajuste fino) faz o julgamento que nenhuma biblioteca faz: ler a história e decidir pelo que ajustar, ou que não dá.
- O runner (Python comum, com bibliotecas padrão) faz a conta. O modelo não escreve código na 0.1, então não há sandbox, e as linhas da tabela nunca passam pelo modelo.

## 2. Contrato da tarefa

**O modelo vê**

- a pergunta: qual o efeito médio da intervenção T sobre o resultado Y;
- a narrativa: texto livre sobre como os dados foram gerados (quem recebe a intervenção e por quê, o que é medido antes e depois dela, mecanismos conhecidos, o que se sabe que não está na tabela);
- o dicionário da tabela: nome, tipo e descrição de cada coluna, com um resumo estatístico simples.

**O modelo não vê**: o grafo, as equações, o efeito verdadeiro, as linhas da tabela.

**O modelo responde**, nesta ordem, em formato estruturado:

1. o papel de cada coluna (confundidor, mediador, colisor ou neutra), com um motivo de uma linha;
2. o veredito: identificável por ajuste, ou não identificável com estas colunas;
3. o conjunto de ajuste (se identificável) ou o que falta (se não);
4. as suposições que está assumindo.

**O runner** então estima o efeito com o conjunto escolhido e monta o relatório: efeito, intervalo, diferença ingênua para contraste, suposições e avisos. Se o veredito for "não identificável", o relatório diz por quê e que dado resolveria.

A conta é sempre a mesma: um estimador duplamente robusto com validação cruzada (o modelo de regressão interativa do DoubleML), que não supõe uma forma particular para como as colunas agem sobre a intervenção ou sobre o resultado.

## 3. Família de mundos

Um mundo = estrutura + tema + parâmetros. Dele saem a narrativa, a tabela e o gabarito.

**Estrutura.** Um grafo com T (binária), Y e de 3 a 8 covariáveis, montado com cinco peças:

| Peça | O que é | Resposta certa |
|---|---|---|
| Confundidor observado | causa T e Y, está na tabela | ajustar |
| Confundidor oculto | causa T e Y, citado na narrativa, fora da tabela | não identificável |
| Mediador | T → M → Y | não ajustar |
| Colisor | efeito de T e de Y (ou de uma causa de Y) | não ajustar |
| Neutra | causa só de Y, causa só de T, ou ruído | indiferente |
| Ausência inofensiva | causa só de Y ou só de T, citada na narrativa, fora da tabela | indiferente: o efeito continua identificável |

O gabarito nunca vem do rótulo da peça: é calculado pelo verificador a partir do grafo.

**O que falta na tabela não entrega a resposta** (revisão 7). Um mundo tem no máximo duas variáveis citadas na narrativa e ausentes da tabela, e cada uma pode ser um confundidor (o efeito deixa de ser identificável) ou uma ausência inofensiva. Assim, a frase "isto não está na tabela" e a contagem dessas frases não bastam para acertar: é preciso ler o papel da variável que falta. Medido em 2026-10-05 nos oito temas: com uma ausência, 47% dos mundos são identificáveis; com duas, 28%; sem nenhuma, todos.

**Papel variável (regra central).** A mesma variável muda de papel conforme os fatos da narrativa. No tema telecom: reclamação registrada antes da oferta é confundidor; depois da oferta, é mediador. Contato da retenção antes da oferta é causa da oferta; depois, é colisor. O nome da coluna nunca basta para acertar.

**Mundos gêmeos.** Os mundos são gerados em pares que diferem em um único fato causal e têm respostas diferentes (o confundidor está ou não na tabela; a reclamação vem antes ou depois da oferta; a informação que falta na tabela é causa só do resultado ou é confundidor). No conjunto, cerca de 55% dos mundos são identificáveis. Não chega a metade a metade porque gêmeos precisam ter respostas diferentes, e dois mundos não identificáveis nunca formam par.

**Temas como fichas de teoria.** Cada tema parte de uma teoria de gestão, registrada em uma ficha que diz quais relações existem e com que sinal. No tema telecom a teoria é a de custo de troca: a antiguidade aumenta o custo de troca e reduz o cancelamento; a oferta de fidelização aumenta o custo de troca. As estruturas são sorteadas dentro do que a ficha permite, e os sinais dos efeitos seguem a teoria. O André define a teoria de cada tema e aprova a ficha. São oito temas: seis entram no treino e dois ficam reservados para teste.

| Tema | Intervenção → resultado |
|---|---|
| Telecom | oferta de fidelização → cancelamento |
| Varejo | cupom → recompra |
| Banco | aumento de limite → inadimplência |
| Software por assinatura | treinamento de implantação → renovação |
| RH | programa de capacitação → rotatividade |
| Educação | monitoria → nota |
| Saúde suplementar | programa de acompanhamento → internação |
| E-mail marketing | campanha → compra |

**Narrativas**, em três níveis:

1. fatos diretos, um por frase, gerados por molde;
2. prosa corrida escrita por um modelo aberto a partir da ficha de fatos, em português ou inglês, com conferência de ida e volta (um segundo passe extrai os fatos do texto e compara com a ficha; se divergir, o mundo é descartado);
3. casos escritos por pessoas, usados só em teste.

**Dados.** T binária, gerada por regressão logística nos pais; Y contínuo ou binário; covariáveis contínuas, binárias ou de contagem; de 2 mil a 50 mil linhas. O efeito verdadeiro é calculado simulando do(T=1) e do(T=0) no próprio mundo. Parte dos mundos tem efeito nulo ou de sinal oposto ao da diferença ingênua.

## 4. Verificador

Definição de acerto: o critério de ajuste (Shpitser, VanderWeele e Robins, 2010). Dado o grafo, T, Y e as colunas observadas, o verificador responde duas perguntas:

- existe conjunto de ajuste válido entre as colunas observadas?
- o conjunto proposto é válido?

Cada resposta vem com o motivo: quais colunas nunca podem entrar no ajuste e por quê, quais caminhos não causais ficam abertos e, quando o efeito não é identificável, que variável faltou na tabela. O mesmo motivo alimenta a nota, as respostas ideais do treino e as páginas de visualização.

Quatro camadas de teste:

1. casos de livro-texto com resposta conhecida, lidos e aprovados pelo André;
2. força bruta: em todos os grafos de até cinco variáveis, a implementação rápida comparada com a definição por caminhos, para todo conjunto;
3. modelos lineares: nos mesmos grafos, todo conjunto dito válido tem de recuperar o efeito verdadeiro em uma regressão calculada com infinitas linhas, e os inválidos não;
4. segunda opinião externa: as respostas do dagitty, a implementação de referência do critério, em grafos sorteados.

## 5. Nota

| Mundo | Resposta do modelo | Nota |
|---|---|---|
| Identificável | identificável, conjunto válido | +1 |
| Identificável | identificável, conjunto inválido | −1 |
| Identificável | não identificável | −0,5 |
| Não identificável | não identificável | +1 |
| Não identificável | identificável, qualquer conjunto | −1 |

**Erro confiante** é afirmar um efeito causal com conjunto inválido ou em mundo não identificável. É a métrica principal do projeto. Os pesos −1 e −0,5 são decisão de pesquisa do André.

## 6. Treino

**Passo 1: ajuste fino supervisionado com gabarito.** O gerador conhece a resposta certa de cada mundo, então produz pares de entrada e resposta ideal em qualquer quantidade; os motivos de uma linha saem dos fatos do grafo. LoRA sobre a base, na RTX 4090 local, com dezenas de milhares de mundos. Para treinar bastam narrativa e dicionário; a tabela só é necessária na avaliação. Este passo garante um modelo antes de qualquer RL.

**Passo 2: GRPO**, com a nota da seção 5 como recompensa, em episódios de uma pergunta e uma resposta. É onde a nota assimétrica entra no treino: o passo 1 imita o gabarito; o passo 2 aprende quando abster-se rende mais que arriscar. Prazo fechado de duas semanas. O ponto de partida (o modelo do passo 1 ou um aquecimento só de formato) é escolhido depois da avaliação do passo 1.

Risco conhecido do passo 2: quando abster-se é uma resposta possível e o erro é penalizado, o treino por reforço pode derivar para recusar tudo, e a normalização por grupo do GRPO pode apagar a diferença entre as penalidades (Che e outros, 2026). Antes da fase 5 o André decide entre manter a abstenção como resposta, acompanhando de perto a fração de mundos respondidos, ou fazer o modelo informar sempre a sua confiança e decidir a abstenção por um limiar na hora do uso.

**Base.** Três candidatas abertas, todas com licença Apache 2.0: Qwen3.5-4B, IBM Granite 4.2 de 3B e Qwen3-4B. O placar de base da fase 3 mede as três nos mesmos mundos, e fica a melhor. O nome final do modelo segue o tamanho da base escolhida.

**Procedência** (revisão 7; decisão do André em 2026-10-05). As respostas-alvo vêm sempre do verificador, e os números vêm do gerador. As frases das fichas de teoria, com as quais o gerador monta as histórias de um fato por frase, foram escritas pelo assistente de IA com que o André construiu o projeto (um modelo comercial, chamado "o assistente" neste documento) e revisadas por leituras independentes do próprio assistente; o André aceitou esse uso e decidiu não ler o material um a um. A prosa corrida é escrita por modelo aberto. Nenhuma resposta de modelo comercial entra como resposta-alvo. O cartão do modelo diz quem escreveu o quê. Até a revisão 6 a regra era "nenhuma saída de API comercial vira dado de treino".

## 7. Avaliação e critério de pronto

Duas provas, relatadas em separado:

1. **Mundos nunca vistos**: temas e estruturas fora do treino, 500 mundos com tabela, avaliados de ponta a ponta.
2. **Casos humanos**: 30 narrativas escritas pelo André, com o grafo declarado por ele e os dados gerados a partir do grafo.

Comparadores, com o mesmo prompt e o mesmo runner:

- a base sem ajuste fino;
- um modelo aberto maior;
- um modelo de fronteira via API;
- "ajusta tudo" (o que as bibliotecas de estimação fazem quando recebem todas as colunas);
- "ajusta nada" (a diferença ingênua).

Métricas: nota média, taxa de erro confiante, taxa de abstenção indevida, cobertura do intervalo e erro do efeito nos casos respondidos.

**Pronto para publicar** quando o modelo supera a base e o "ajusta tudo" com folga nas duas provas e a taxa de erro confiante fica abaixo do limiar. Os limiares numéricos são fixados depois do placar de base e antes do treino. Publica-se o melhor dos dois modelos (supervisionado, ou supervisionado mais GRPO), e o relatório mostra os dois lado a lado. Se nenhum passar, o ambiente e o placar saem mesmo assim, com o resultado negativo descrito.

**O que a 0.1 não prova**: que o modelo supera a fronteira (o placar mede; não se promete), que recupera efeitos de experimentos reais, e onde ele discorda da prática de especialistas. Dados reais entram só como exemplo de uso no cartão do modelo.

**O que se pode dizer de novo.** Treinar modelos com reforço e recompensa verificável em tarefas causais já foi feito, e existe ambiente público que premia a escolha do método de identificação sobre grafos formais. A formulação defensável da novidade, com os trabalhos vizinhos, está em `docs/trabalhos-vizinhos.md`.

## 8. Visualização

O projeto precisa ser mostrado a quem não lê código. São três páginas, geradas sempre a partir dos mesmos registros usados na avaliação, nunca desenhadas à mão.

| Página | O que mostra | Quando fica disponível |
|---|---|---|
| Casos e mundos | o tipo de decisão: a história, o diagrama causal, a escolha de colunas e, no diagrama, o caminho que a escolha abre ou fecha. É a mesma página em duas versões: casos de livro-texto e mundos gerados | fase 1, com os casos de livro-texto; fase 2, com mundos gerados e os três números (efeito verdadeiro, comparação simples, efeito ajustado); fase 3, com a escolha de cada modelo |
| Placar | onde está cada modelo e cada referência: acertos, abstenções indevidas e erros confiantes | fase 3 |
| Aprendizado | o andamento do treino: a nota e os três tipos de resposta ao longo do tempo, por tipo de armadilha, e o antes e depois em mundos fixos | fases 4 e 5 |

Regras:

- **Tudo vem de registros.** Cada resposta de cada modelo é gravada com o mundo, o ponto do treino, a resposta, a nota e o motivo dado pelo verificador. As páginas só leem esses registros.
- **Mundos-vitrine escolhidos antes do treino.** Cerca de vinte mundos de teste são fixados na fase 3 e respondidos a cada ponto do treino. O "antes e depois" mostrado aos colegas sai deles, e não de exemplos escolhidos depois de ver o resultado.
- **Uma página, um arquivo.** Cada página é um HTML único, que abre em qualquer navegador, pode ser projetado em aula e publicado para compartilhar.

## 9. O que se publica

- Modelo: `COPPEAD/causalista-4b` no Hugging Face (ou `-3b`, conforme a base), em safetensors e GGUF, Apache 2.0.
- Pacote: `pip install causalista` (nome a confirmar), o runner local, para GPU de 8 GB ou CPU.
- Ambiente: gerador, verificador e os mundos de teste, como dataset.
- Harness de avaliação e relatório técnico curto com o placar.
- As três páginas de visualização.

A licença do código ainda não foi escolhida; a sugestão é Apache 2.0, igual à do modelo.

*Nota de 2026-10-24, no fechamento da 0.1:* a organização é `coppead` (modelo `coppead/causalista-4b`, GGUF em `coppead/causalista-4b-GGUF`, dados em `coppead/causalista-worlds`); o pacote não foi ao PyPI e instala-se do repositório; são cinco páginas, não três; o relatório técnico curto foi dispensado em favor dos cartões; a licença do código é Apache 2.0. O registro está na seção 13.

## 10. Fora da 0.1 (lista da 0.2)

- exploração dos dados com código escrito pelo modelo, com o sandbox e o treino em vários passos que isso exige;
- variável instrumental, diferenças em diferenças, painel;
- efeito por subgrupo ("para quem");
- viés-M e variáveis proxy;
- provas externas com gabarito real: ACIC, Jobs, experimentos de marketing;
- prova externa em benchmarks de terceiros (CausalDS, CausalReasoningBenchmark);
- prova humana: alunos resolvem os mesmos mundos de teste que o modelo;
- comparação com a prática de especialistas.

## 11. Ordem de construção

| Fase | Entrega | Peça visual | Portão para seguir |
|---|---|---|---|
| 0 | Especificação fechada; 5 casos escritos à mão pelo André; busca de trabalhos vizinhos na literatura | | André aprova este documento |
| 1 | Verificador com as quatro camadas de teste | página de casos, com os casos de livro-texto | testes passam; André leu e concordou com os casos de resposta conhecida |
| 2 | Fichas de teoria, gerador (estruturas, narrativas, dados) e estimador do runner | casos com mundos gerados e os três números | André aprova as fichas; com conjunto válido, o intervalo cobre a verdade em cerca de 95% dos mundos; a diferença ingênua erra como previsto; André lê 20 mundos e os acha plausíveis |
| 3 | Harness e placar de base em 200 mundos | placar; casos com a escolha de cada modelo; mundos-vitrine fixados | há distância entre a base e o teto; os erros do modelo de fronteira não vêm de narrativa ambígua; limiares fixados |
| 4 | Treino supervisionado e avaliação nas duas provas | aprendizado do treino supervisionado | o modelo supera a base e o "ajusta tudo" |
| 5 | GRPO, com prazo fechado de duas semanas | aprendizado do GRPO, com antes e depois | supera o supervisionado nas provas, ou o prazo acaba |
| 6 | Pacote, GGUF, cartões, relatório, publicação | as três páginas em versão pública | critério de pronto da seção 7; instalação limpa em outra máquina reproduz um caso |

Hábito fixo desde a fase 3: respostas do modelo gravadas, e o André lê umas dez por sessão.

## 12. O que mudou em relação à ficha original

- **O modelo decide, o runner calcula.** Antes o modelo explorava os dados escrevendo código. Isso exigia sandbox e treino de agente em vários passos, as duas partes mais lentas e menos conhecidas do plano.
- **Treino supervisionado antes do GRPO.** O gabarito garante um modelo; o GRPO vem em seguida, com prazo fechado. Na revisão 2 o GRPO estava na 0.2. Voltou na revisão 3 porque o reforço com recompensa verificável é a tese do projeto e, sem código gerado pelo modelo, o episódio é de uma pergunta e uma resposta.
- **Entrou o confundidor oculto.** Com as três armadilhas originais, nenhum mundo era "não identificável".
- **Papel variável e mundos gêmeos.** Com um grafo fixo, a resposta certa era a mesma em todos os mundos e podia ser decorada.
- **Oito temas em vez de um**, cada um com sua ficha de teoria, dois reservados para teste.
- **Saíram da 0.1**: efeito por subgrupo, variável instrumental, diferenças em diferenças, painel e as provas com dados reais.
- **Visualização planejada desde o início** (revisão 4). O verificador devolve o motivo de cada veredito, tudo é gravado, e cada fase entrega a sua página.
- **Granite e Qwen3.5 como candidatas a base** (revisão 4), ao lado do Qwen3-4B, decididas pelo placar.
- **Cerca de 60% de mundos identificáveis, e não metade** (revisão 5), pela razão dada na seção 3.
- **Novidade reescrita depois da busca de literatura** (revisão 6): seção 7 e `docs/trabalhos-vizinhos.md`. Entrou o risco conhecido do passo de reforço na seção 6.
- **Ausência inofensiva e limite de duas ausências** (revisão 7): até a revisão 6, toda variável citada e ausente da tabela era um confundidor, e a regra de uma linha "a história diz que algo não está na tabela, logo não identificável" acertava 100% dos vereditos. Ver a seção 3.
- **Procedência e aprovação por delegação** (revisão 7): em 2026-10-05 o André decidiu não validar um a um o que o assistente escreve, aceitou frases escritas pelo assistente nos dados de treino e pediu uma revisão independente de todas as fichas. Ver as seções 6 e 13.
- **Estimador do runner definido** (revisão 5): duplamente robusto com validação cruzada. A versão com modelos lineares simples foi medida e descartada: seu intervalo conteve o efeito verdadeiro em só 71% dos mundos com tabelas de 50 mil linhas.

## 13. Registro dos portões

| Fase | Situação | O que foi verificado |
|---|---|---|
| 0 | busca de literatura feita em 2026-10-03; os 5 casos foram escritos em 2026-10-04 e aprovados por delegação em 2026-10-05 | "Ninguém fez isso" não se sustenta: há reforço com recompensa verificável em tarefas causais e um ambiente que premia a decisão de identificação sobre grafos formais. Não foi encontrado treino da decisão de ajuste a partir de texto, com abstenção na recompensa, em modelo pequeno. Ver `docs/trabalhos-vizinhos.md`. Em 2026-10-04 o André pediu que o assistente escrevesse os cinco casos (`cases/fase0.yaml`). A resposta de cada caso foi conferida pelo verificador. Não são casos escritos por pessoa: não contam para a prova de casos humanos da seção 7 e não entram em treino. Em 2026-10-05 o André decidiu não ler um a um o que o assistente escreve; um leitor independente conferiu se cada história conta exatamente o desenho declarado (nenhum erro, dez dúvidas de redação, nove ajustes feitos), e os casos ficaram aprovados por delegação. |
| 1 | aprovada em 2026-10-03 | As quatro camadas de teste do verificador passam. O André leu os 24 casos de resposta conhecida e concordou com todos. |
| 2 | medida nos oito temas; telecom aprovado pelo André, os outros sete por delegação (2026-10-05) | **Estimador, medido em 2026-10-04 com 400 sementes por tema:** em 3.775 mundos identificáveis dos oito temas, o intervalo com o ajuste certo conteve o efeito verdadeiro em 95,4% das vezes (entre 93,5% e 97,5% por tema; 94,1% nas tabelas de 50 mil linhas). Nos mundos com confundidor, a comparação simples só o conteve em 22,5%, e caiu onde o mundo previa em 94,7%. No telecom: 475 mundos, 95,4%, 26,0% e 95,2%. **Telecom aprovado:** em 2026-10-04 o André respondeu "ok" aos três pedidos da fase: aprovar a ficha de teoria do telecom; ler os 20 mundos do caderno, sem apontar nenhum como estranho; e confirmar os pesos da nota, os oito temas, os dois idiomas e as faixas de desenho dos mundos. **Sete fichas novas, em rascunho:** varejo, banco, software, RH, educação, saúde e e-mail, escritas pelo assistente em 2026-10-04 com teoria e referências propostas por ele; os pontos que pedem o olhar do André estão em `docs/fichas-para-aprovar.md`. **Defeito corrigido na fábrica de mundos:** uma variável que só pode ser mediador (ou só colisor) furava o limite de dois por mundo, cerca de uma vez em 300 mundos; os 20 mundos lidos pelo André não mudaram. Por isso o telecom foi medido de novo; os números de 2026-10-03 (465 mundos; 95,3%; 24,0%; 94,4%) ficam substituídos pelos de cima, e a diferença no número de mundos não vem dessa correção (causa não identificada). **Narrativa em prosa:** escrita por um modelo aberto e conferida por dois outros, frase por frase; em 32 histórias fiéis os leitores aceitaram de 81% a 94%, viram de 88% a 94% dos fatos retirados e todos os 13 papéis trocados; em 24 mundos, 16 a 17 histórias em prosa foram mantidas. **Revisão independente e aprovação por delegação (2026-10-05):** o André decidiu não validar um a um o que o assistente escreve e pediu a revisão de todas as fichas. Cada uma das oito foi lida por um leitor separado, frase por frase; em sete delas os leitores apontaram 7 erros (frases que diziam mais do que o mundo tem; nenhum mudava o gabarito) e 50 dúvidas (a contagem da oitava, software, não ficou registrada), e foram feitas 87 trocas de texto nas oito. As sete fichas novas ficaram aprovadas por delegação; a do telecom, já aprovada, também foi corrigida. **Dois atalhos fechados na fábrica de mundos:** a regra de uma linha "algo não está na tabela, logo não identificável" acertava 100% dos vereditos; agora uma informação pode faltar sem fazer mal, há no máximo duas ausências por mundo, e a melhor regra que só conta ausências acerta 69% (seção 3). **Estimador medido de novo em 2026-10-05**, com as fichas corrigidas e a fábrica nova, 400 sementes por tema: em 3.462 mundos identificáveis, o intervalo com o ajuste certo conteve o efeito verdadeiro em 95,3% das vezes (entre 94,0% e 97,2% por tema; 94,6% nas tabelas de 50 mil linhas); nos mundos com confundidor, a comparação simples só o conteve em 23,7%. Os números de 2026-10-04, acima, ficam como registro da versão anterior. **Temas de teste** (e-mail e saúde) aprovados pelo André em 2026-10-06; as frases trocadas foram retraduzidas e relidas por inteiro em 2026-10-06 (seção 32 de `docs/status.md`). |
| 3 | fechada em 2026-10-18 por decisão do André, com duas pendências | O formato da pergunta e da resposta, a nota (seção 5), o harness e a página do placar estão escritos e testados. O conjunto do placar de base tem 197 mundos dos oito temas (59% identificáveis), com a narrativa de um fato por frase, em português. Medido em 2026-10-04 nesse conjunto: "ajusta tudo" tira nota −0,70 (acerto em 15% dos mundos, erro confiante em 85%) e "ajusta nada" tira −0,92 (4% e 96%). As três bases, sem raciocínio: Qwen3.5-4B +0,17, Qwen3-4B +0,10 e Granite 4.2 de 3B −0,19. As duas Qwen empatam (diferença de 0,06, com margem de erro de 0,14). Nos mundos não identificáveis as bases quase nunca se abstêm: acertam 30%, 6% e 1%. Um modelo aberto maior, o Qwen3.8 de 27B com raciocínio, tira +1,00: acerta os 197 mundos. Há, portanto, distância entre a base e o teto, e as narrativas de um fato por frase não se mostraram ambíguas; mas o conjunto não separa modelos grandes entre si. Em 134 desses mundos contados também em prosa corrida, as três bases tiram praticamente a mesma nota que com um fato por frase (diferenças de +0,01 a +0,18, nenhuma segura): a prosa, como é gerada hoje, não é mais difícil. Faltam: as bases com raciocínio; um modelo de fronteira (depende de uma chave de API); fixar os limiares. Os mundos-vitrine foram escolhidos pela regra de `configs/split.yaml`, que ainda é uma proposta. **Conjunto novo (2026-10-05):** depois das correções da fase 2, o placar passou a usar `placar-v3` (384 mundos dos oito temas, 54% identificáveis, frases em ordem sorteada); `placar-base` e `teste-final` ficam como histórico, e o teste final novo é `teste-v3`, ainda não usado. No `placar-v3`: "ajusta tudo" −0,77 e "ajusta nada" −0,93. Os números das bases neste conjunto estão na linha da fase 4. **Fechamento (2026-10-18):** há distância entre a base e o teto (seção 35 de `docs/status.md`); o modelo de fronteira não foi medido, por falta de chave de API; os limiares não foram fixados. As duas pendências ficam registradas e a fase foi fechada por decisão do André. |
| 4 | aprovada pela medição final de 2026-10-18 | **Primeiro treino (2026-10-05):** Qwen3-4B com LoRA, 4.673 exemplos em português dos seis temas de treino, histórias de um fato por frase, uma passada (293 passos, 26 minutos). Em 384 mundos novos com as frases na ordem antiga (`placar-v2`): sem treino, nota +0,03 (acerto 51%; 9% nos mundos não identificáveis); treinado, +1,00 (384 de 384, inclusive os 97 dos dois temas não vistos). **Sondagens:** com as mesmas frases em outra ordem o treinado caiu para 65%; em 134 histórias em prosa corrida (fábrica antiga) fez 75%, contra 54% da base e 100% do modelo aberto de 27B; nos cinco casos escritos, 2 de 5 (a base, 4 de 5). Conclusão: o modelo se apoiou na ordem fixa das frases. **Correção:** a fábrica passou a sortear a ordem das frases (seção 3 do README da fábrica). **Segundo treino**, igual ao primeiro salvo a ordem: no `placar-v3`, nota +0,96 (375 de 384; 94 de 97 nos temas não vistos; os dois gêmeos certos em 175 de 184 pares); 99% nas histórias embaralhadas; 90% na prosa; 2 de 5 nos casos escritos. No mesmo `placar-v3`: a base sem treino tira −0,04 (acerto 47%; 13 de 176 nos mundos não identificáveis), o primeiro treino +0,41 (70%), e o modelo aberto de 27B com raciocínio, em uma amostra de 96 mundos, +1,00 (96 de 96), o que indica que a prova nova pode ser resolvida por leitura. **Terceiro treino (2026-10-05):** os mesmos exemplos mais 710 histórias em prosa corrida de mundos de treino, escritas por um modelo aberto e conferidas por dois outros (337 passos, 29 minutos). Em uma prova em prosa de 113 mundos do `placar-v3`, escrita por um modelo diferente do dos exercícios: base −0,22 (39%), segundo treino +0,64 (81%), terceiro +0,87 (93%; 59 de 62 nos não identificáveis); o modelo aberto de 27B, em 57 desses mundos, +1,00. No `placar-v3` de um fato por frase, +0,99 (99%); nas frases embaralhadas, 100%; nos cinco casos escritos, 4 de 5. Nenhum destes números é o da avaliação final: o `teste-v3` não foi usado, e faltam os casos escritos por pessoas (seção 7). **Decisões de 2026-10-06** (seção 30 de `docs/status.md`): cerca de 20 mil exemplos e 3 mil histórias em prosa; treino em português e inglês, espanhol só como prova; e-mail e saúde fora do treino; base Qwen3-4B; fase 5 com dois braços (reforço puro a partir do modelo cru, e supervisionado seguido de reforço), trava de 10% de abstenção indevida; os casos escritos por pessoas ficam para o fim e, no lugar deles, o assistente simula texto humano em casos revisados por instâncias independentes e congelados antes de qualquer medição. **Treino final e prova final (seção 35 de `docs/status.md`):** 22.906 exemplos em português e inglês, 2h22 de treino. Na prova final (`teste-v3`, 505 mundos por idioma, aberta uma vez em 2026-10-18): 99% de acerto, contra 47% da base, 17% do "ajusta tudo" e 2% do "ajusta nada"; 98% em espanhol, nunca treinado; 96% nos dois temas nunca treinados. O portão (supera a base e o "ajusta tudo") está passado. |
| 5 | feita; o braço de reforço venceu pela regra em 2026-10-18 | Três treinos sobre mundos sintéticos em 2026-10-07 não ensinaram nada (um não tinha o que aprender; dois pararam na trava de abstenção). Em 2026-10-18, dois braços sobre 208 casos tipo humano, partindo do supervisionado: C (reforço com a nota do verificador, parado pela trava no passo 20) e D (supervisionado). Pela regra escrita antes (emenda de 2026-10-07 à seção 31 de `docs/status.md`), D foi excluído por perder 5 pontos nos mundos sintéticos e C venceu o supervisionado por um caso em 32. Na prova final, C empata com o supervisionado (99%) e acerta um caso a mais nos 48 casos congelados (69% contra 67%). O portão ("supera o supervisionado nas provas") foi passado por margem de um caso; o cartão do modelo diz isso com essas palavras. |
| 6 | enviada ao Hugging Face em 2026-10-24, em três repositórios privados da organização `coppead`; abertura ao público depende do André | Modelo fundido, dois adaptadores, GGUF (Q4_K_M e Q8_0), cartões do modelo, dos dados e do GGUF, licença Apache 2.0, script de envio, cinco páginas. O critério de pronto da seção 7 vale para a prova de mundos; a prova de casos humanos foi substituída por casos simulados (decisão de 2026-10-06) e isso está dito nos cartões. **Envio (2026-10-24):** `coppead/causalista-4b` (7,75 GiB, 20 arquivos), `coppead/causalista-4b-GGUF` (6,31 GiB, 7 arquivos) e `coppead/causalista-worlds` (3,34 GiB, 71.181 arquivos); os três cartões no Hub conferidos byte a byte com `docs/cards/` (seção 36 de `docs/status.md`). Não feitos: relatório técnico longo, instalação limpa em outra máquina. Código público em `coppead/causalista` desde 2026-10-24; faltam abrir os três repositórios do Hub. |
