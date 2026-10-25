# Status do projeto Causalista

<!-- The project's working log, kept in Portuguese. It records what was built, measured and decided, day by day, with every number; the Hugging Face cards (docs/cards/) and the English README summarise it. -->

Situação em 24 de outubro de 2026. O projeto foi construído em sessões de trabalho do André com um assistente de IA ("o assistente", neste documento), de 3 a 7 de outubro, fechado em 18 de outubro, gravado no repositório em 19 e enviado ao Hugging Face em 24.

## Em poucas palavras

O Causalista é um modelo pequeno, que roda na máquina da pessoa, treinado para uma decisão: diante de uma tabela e da história de como os dados foram gerados, dizer por quais colunas ajustar para medir o efeito de uma intervenção, ou dizer que não dá. Ele aprende em mundos sintéticos em que a resposta certa é conhecida.

- A fase 1 (o verificador, que dá o gabarito) está pronta e aprovada.
- A fase 2 (a fábrica de mundos e o estimador) tem os oito temas, com as fichas revisadas e aprovadas (o telecom pelo André, as outras sete por delegação).
- A fase 4 (treino supervisionado) produziu o modelo: na prova final, 99% de acerto em 1.515 mundos nunca vistos, nos três idiomas, inclusive em espanhol, que ele nunca treinou. Em texto que imita gente, 67% (69% depois do reforço), contra 96% de um modelo aberto de 27B.
- A fase 5 (reforço com a nota do verificador) foi feita: três treinos sobre mundos sintéticos não ensinaram nada; dois braços sobre casos tipo humano, em 18 de outubro, decidiram o modelo publicado pela regra escrita antes. O reforço mudou um caso em 32 e um em 48.
- **Em 18 de outubro o André decidiu fechar a 0.1 e publicar** (seção 35). **Em 24 de outubro os três repositórios subiram para a organização `coppead` no Hugging Face** (seção 36). Estão privados; abri-los ao público é decisão dele.

## Situação por fase

| Fase | O que é | Situação |
|---|---|---|
| 0 | Especificação, busca de literatura, cinco casos | Especificação na revisão 7. Busca de literatura feita. Os cinco casos foram escritos pelo assistente, a pedido do André, e aprovados por delegação depois de uma revisão independente. |
| 1 | Verificador | Aprovada: os testes passam e o André concordou com os 24 casos. |
| 2 | Mundos e estimador | Oito fichas revisadas, corrigidas e aprovadas (sete por delegação); dois atalhos fechados e a ordem das frases sorteada; estimador medido de novo nos oito temas (95,3%); temas de teste (e-mail e saúde) aprovados em 6 de outubro. |
| 3 | Harness e placar de base | Fechada em 18 de outubro por decisão do André, com duas pendências registradas: o modelo de fronteira não foi medido (sem chave de API) e os limiares do critério de pronto não foram fixados. |
| 4 | Treino supervisionado | Feita. Modelo final medido na prova final em 18 de outubro (seção 35): 99% em 1.515 mundos. |
| 5 | Treino por reforço (GRPO) | Feita. Três treinos sobre mundos sintéticos (7 de outubro) e dois braços sobre casos tipo humano (18 de outubro); o braço de reforço venceu pela regra e é o modelo publicado, com ganho de um caso em 32 e um em 48 (seção 35). |
| 6 | Publicação | Enviada em 24 de outubro para a organização `coppead` no Hugging Face: modelo, GGUF e dados, em três repositórios privados (seção 36). O código está público em `coppead/causalista` desde 24 de outubro; falta abrir os três repositórios do Hub. |

## O que foi feito em 3 de outubro

### 1. A especificação

O plano nasceu em uma conversa do André com o assistente. A partir dela foi escrita a especificação (`ESPECIFICACAO.md`), que hoje está na revisão 6. As decisões principais:

- **O modelo decide, o runner calcula.** O modelo não escreve código. Ele devolve o veredito e o conjunto de ajuste; um programa fixo faz a conta.
- **Treino em dois passos.** Primeiro o modelo estuda mundos com a resposta certa; depois treina por reforço, recebendo a nota do verificador.
- **Nota que valoriza a honestidade.** Acerto vale +1, erro confiante vale −1, abstenção indevida vale −0,5.
- **Mundos feitos para não serem decorados.** A mesma variável muda de papel de um mundo para outro, e os mundos saem em pares de gêmeos que diferem em um único fato.
- **Teoria de gestão como simulador.** Cada tema tem uma ficha de teoria que diz o que os mundos daquele tema podem conter.
- **Visualização em toda fase.** Cada fase entrega uma página que mostra o que foi feito a quem não lê código.

| Revisão | O que mudou |
|---|---|
| 1 | A ficha do produto da conversa original (nunca foi um arquivo). |
| 2 | Primeira versão escrita: o modelo decide e o runner calcula; entram o confundidor oculto, o papel variável, os gêmeos e oito temas. O reforço ficava para a versão 0.2. |
| 3 | O reforço volta para a 0.1, depois que o André mostrou a tese do projeto. Entram as fichas de teoria e a lista do que a 0.1 não prova. |
| 4 | Entra a seção de visualização. Granite 4.2 e Qwen3.5 passam a ser candidatas a base. |
| 5 | Cerca de 60% de mundos identificáveis, e não metade. Estimador definido. Entra o registro dos portões. |
| 6 | Novidade reescrita depois da busca de literatura. Entra o risco conhecido do passo de reforço. |

### 2. O verificador (fase 1)

É a peça que dá o gabarito. Recebe o grafo verdadeiro de um mundo e responde duas perguntas: se um conjunto de colunas é válido, e se existe algum conjunto válido com as colunas da tabela. Cada resposta vem com o motivo: que coluna não pode entrar no ajuste e por quê, que caminho fica aberto, que variável faltou na tabela.

Foi escrito com dois motores independentes, que se conferem a cada resposta. Se discordarem, o verificador recusa-se a responder.

| Conferência | Tamanho | Resultado |
|---|---|---|
| Casos de livro-texto, escritos à mão, com o motivo de cada erro | 24 casos | todos batem |
| Os dois motores e uma conta de regressão em modelos lineares | os 29.281 grafos de cinco variáveis, todos os conjuntos, mais grafos sorteados de seis a oito variáveis | concordam em tudo |
| dagitty, a implementação de referência | 400 problemas sorteados, 4.936 veredictos | nenhuma divergência |
| Erros plantados de propósito no verificador | 7 | todos pegos pelos testes |

Um episódio a registrar: a primeira comparação com o dagitty acusou diferenças em 167 dos 400 problemas. A causa não era erro do verificador. O dagitty lista também conjuntos com variáveis ocultas, e o verificador lista só colunas da tabela; no terreno comum, as listas são idênticas.

### 3. A página de casos

Uma página interativa com os 24 casos. A pessoa escolhe as colunas e vê no diagrama se o efeito sai certo, que caminho ficou aberto e por quê. Tudo o que a página mostra foi calculado pelo verificador; ela só consulta.

Foi conferida em um navegador de teste: as 129 escolhas possíveis e as 24 respostas batem com o verificador.

### 4. A ficha de teoria do telecom (fase 2)

Arquivo `theories/telecom.yaml`. Parte da teoria de custo de troca e lista 13 variáveis (antiguidade, renda, valor da fatura, reclamação, contato da retenção, e outras). Para cada uma diz os papéis possíveis, o sinal de cada efeito e a frase que entra na narrativa.

A ficha foi escrita pelo assistente e aprovada pelo André em 4 de outubro de 2026.

### 5. A fábrica de mundos

Para criar um mundo, o computador:

1. sorteia de 3 a 8 variáveis da ficha e um papel para cada uma;
2. sorteia a força de cada efeito, com o sinal que a ficha manda;
3. cria os clientes um a um, cada característica saindo das suas causas mais o acaso;
4. calcula o efeito verdadeiro, simulando os mesmos clientes com e sem a intervenção;
5. escreve a narrativa com as frases da ficha, sem dizer a resposta;
6. cria o gêmeo: o mesmo mundo com um fato trocado e outra resposta.

O gabarito vem sempre do verificador, nunca do rótulo do papel. O que o modelo vê e o que fica escondido são gravados em pastas separadas.

Medido em 3.000 sorteios: cerca de 40% dos mundos não são identificáveis, e em 3 de cada 4 pares de gêmeos o veredito muda de um para o outro.

### 6. O estimador

Faz a conta do runner: o efeito e o intervalo de confiança, dadas as colunas de ajuste. Usa um estimador duplamente robusto com validação cruzada, da biblioteca DoubleML.

| Medida, em mundos do tema telecom | Resultado |
|---|---|
| Intervalo com o ajuste certo contém o efeito verdadeiro | 95,3% de 465 mundos (o esperado é 95%) |
| Comparação simples contém o efeito verdadeiro, nos 429 mundos com confundidor | 24,0% |
| Comparação simples cai onde o mundo previa | 94,4% |
| Erro médio: ajuste certo e comparação simples | 1,2 e 4,3 pontos percentuais |

Uma versão mais simples do estimador, com modelos lineares, foi medida e descartada: o intervalo dela conteve o efeito verdadeiro em 85% de 182 mundos, e em só 71% nas tabelas de 50 mil linhas.

### 7. A página de mundos

A mesma página interativa, agora com 20 mundos gerados (10 pares de gêmeos). Além do diagrama, mostra as colunas da tabela, o mundo gêmeo e três números na mesma régua: o efeito verdadeiro, a comparação simples e a estimativa da escolha feita.

Um exemplo, o Mundo 1A: o efeito verdadeiro é −1,2 ponto percentual. A comparação simples dá +3,2 e faria concluir que a oferta aumenta o cancelamento. Ajustando por renda e satisfação, a estimativa é −1,4. Ajustando por todas as colunas, é −0,2, e a conclusão seria que a oferta não faz nada.

Os mundos mostrados seguem uma regra que olha só o tamanho: os primeiros pares com até 6 colunas e tabelas de 10 mil ou 20 mil linhas. A regra foi mudada uma vez, depois de se ver que tabelas de 2 mil linhas davam intervalos largos demais para mostrar.

Foi conferida em um navegador de teste: 192 estados batem com os dados. Em um dos 14 mundos identificáveis (o 5B), o intervalo com o ajuste certo deixa o efeito verdadeiro de fora, o que é esperado uma vez em vinte.

### 8. A busca de literatura

A frase "ninguém fez isso", que vinha da conversa original, não se sustenta. Já existe treino por reforço com recompensa verificável em tarefas causais, e um ambiente público que premia a decisão de identificação sobre grafos formais.

Não foi encontrado o que o Causalista propõe: treinar a decisão de ajuste a partir de texto comum, sem o grafo, com "não identificável" na recompensa, em modelo aberto de 3B a 4B. A formulação defensável está em `docs/trabalhos-vizinhos.md`.

A busca trouxe um risco para o passo de reforço: quando abster-se é uma resposta possível e o erro é penalizado, o treino pode derivar para recusar tudo. A decisão sobre isso fica para antes da fase 5.

### 9. O tamanho do que existia em 3 de outubro

| O quê | Quanto |
|---|---|
| Código do pacote | cerca de 2.600 linhas, em 19 arquivos |
| Testes | cerca de 1.600 linhas, em 20 arquivos |
| Testes do dia a dia | 1.905 passando, em cerca de 80 segundos |
| Teste exaustivo do verificador | 1, em cerca de 2 minutos |
| Casos de livro-texto | 24 |
| Fichas de teoria | 1 de 8, em rascunho |
| Páginas publicadas | 2 |

## O que foi feito em 4 de outubro

### 10. Aprovações do telecom

O André respondeu "ok" a três pedidos: aprovar a ficha de teoria do telecom, ler os 20 mundos do caderno (nenhum apontado como estranho) e confirmar os pesos da nota, os oito temas, os dois idiomas e as faixas de desenho dos mundos.

### 11. Os cinco casos escritos

O André pediu que o assistente escrevesse os cinco casos da fase 0. Estão em `cases/fase0.yaml`: um banco, uma operadora de saúde, dois de RH que são gêmeos (a avaliação de desempenho feita antes ou depois do programa) e uma campanha de e-mail enviada por sorteio. Um deles é não identificável, e em outro a resposta certa é não ajustar por nada.

Cada caso traz as setas do diagrama causal, e o verificador confere a resposta declarada. Respostas erradas plantadas de propósito são pegas pelos testes. Os casos não foram escritos por pessoa: não contam para a prova de casos humanos e não entram em treino.

### 12. As fichas dos outros sete temas

| Tema | Intervenção → resultado | Teoria proposta |
|---|---|---|
| Varejo | cupom → recompra | utilidade de transação |
| Banco | aumento de limite → inadimplência | assimetria de informação no crédito |
| Software por assinatura | treinamento de implantação → renovação | expectativa e confirmação na continuidade de uso |
| RH | programa de capacitação → saída voluntária | capital humano e imersão no trabalho |
| Educação | monitoria → nota final | tempo de aprendizagem |
| Saúde suplementar | programa de acompanhamento → internação | modelo comportamental de uso de serviços de saúde |
| E-mail marketing | campanha → compra | hierarquia de efeitos |

Cada ficha tem de 13 a 14 variáveis e segue o formato da ficha do telecom. A teoria e as duas referências de cada tema foram propostas pelo assistente; as fichas foram escritas por sete agentes do assistente em paralelo, cada um com o seu tema, e passaram nos testes da fábrica de mundos. São rascunhos: só valem quando o André aprovar. Os pontos de cada ficha que pedem o olhar dele estão em `docs/fichas-para-aprovar.md`.

Educação é o único tema em que o resultado não é sim ou não: é uma nota de 0 a 10.

### 13. Um defeito corrigido na fábrica de mundos

Os agentes que escreveram as fichas acharam um defeito: uma variável que só pode ser mediador (ou só colisor) furava o limite de dois por mundo. No telecom isso acontecia em 72 de 20 mil sorteios. Corrigido: nesse caso o sorteio troca a variável por outra. A correção muda 107 de 20 mil mundos do telecom, e nenhum dos 20 mundos que o André leu. Um teste novo confere o limite em 8 mil sorteios por tema.

### 14. O estimador nos oito temas

Medido com 400 sementes por tema (`scripts/check_estimator.py`).

| Tema | Mundos identificáveis | Intervalo contém o efeito verdadeiro | Comparação simples contém, com confundidor | Comparação simples cai onde o mundo previa |
|---|---|---|---|---|
| Telecom | 475 | 95,4% | 26,0% | 95,2% |
| Varejo | 473 | 95,8% | 19,4% | 94,9% |
| Banco | 469 | 96,6% | 27,9% | 94,7% |
| Software por assinatura | 493 | 94,9% | 18,8% | 94,7% |
| RH | 462 | 95,5% | 27,6% | 92,9% |
| Educação | 474 | 97,5% | 14,3% | 96,8% |
| Saúde suplementar | 468 | 94,4% | 27,9% | 95,3% |
| E-mail marketing | 461 | 93,5% | 18,6% | 93,1% |
| Os oito temas | 3.775 | 95,4% | 22,5% | 94,7% |

Por tamanho de tabela, juntando os temas: 96,0% com 2 mil linhas, 96,2% com 5 mil, 95,6% com 10 mil, 95,3% com 20 mil e 94,1% com 50 mil.

O telecom foi medido de novo por causa da correção acima. Os números de 3 de outubro eram 465 mundos, 95,3%, 24,0% e 94,4%. A diferença no número de mundos não vem da correção: o código de antes daria cerca de 477 nas mesmas sementes. A causa não foi identificada.

### 15. A tarefa e a nota (fase 3)

Em `src/causalista/task/`. O modelo recebe a pergunta, a história e, para cada coluna, o nome, o tipo, um resumo simples e a descrição. Responde com um objeto JSON: o papel de cada coluna com um motivo de uma linha, o veredito, o conjunto de ajuste (ou o que falta) e as suposições. A nota é a da seção 5 da especificação, e quem decide é o verificador.

Decisões de desenho tomadas pelo assistente, que o André pode mudar:

- as instruções ficam em inglês, iguais para todos os idiomas; a história e as descrições das colunas ficam no idioma do mundo;
- uma resposta que o runner não consegue usar (sem veredito, ou citando coluna que não existe) vale −1 e é contada à parte do erro confiante.

### 16. O harness e o placar (fase 3)

O harness roda modelos e estratégias ingênuas sobre mundos gravados e grava cada resposta com a nota, o motivo dado pelo verificador e a conta do runner. A página do placar é gerada só desses registros.

O conjunto do placar de base tem 197 mundos dos oito temas, 59% identificáveis, com a narrativa de um fato por frase, em português.

| Quem responde | Nota | Acerto | Abstenção indevida | Erro confiante | Resposta inválida | Acerto nos mundos identificáveis | Acerto nos não identificáveis |
|---|---|---|---|---|---|---|---|
| Qwen3.8 de 27B, modelo aberto maior, com raciocínio | +1,00 | 100% | 0% | 0% | 0% | 100% | 100% |
| Qwen3.5-4B, sem raciocínio | +0,17 | 58% | 2% | 26% | 14% | 78% | 30% |
| Qwen3-4B, sem raciocínio | +0,10 | 54% | 4% | 41% | 1% | 88% | 6% |
| Granite 4.2 de 3B, sem raciocínio | −0,19 | 41% | 0% | 44% | 15% | 68% | 1% |
| Ajusta tudo | −0,70 | 15% | 0% | 85% | 0% | 26% | 0% |
| Ajusta nada | −0,92 | 4% | 0% | 96% | 0% | 7% | 0% |

"Ajusta tudo" é o que as bibliotecas de estimação fazem quando recebem todas as colunas.

O que esses números dizem:

- **Um modelo aberto maior acerta tudo.** O Qwen3.8 de 27 bilhões de parâmetros, rodando nesta máquina no seu modo padrão (com raciocínio, cerca de 1.400 tokens por resposta e 13 segundos por mundo), acertou os 197 mundos e o papel de todas as colunas. Isso diz três coisas. Primeiro: as narrativas de um fato por frase não são ambíguas, porque um modelo que lê com cuidado não erra nenhuma. Segundo: o teto de +1 é alcançável. Terceiro, e é um limite: este conjunto não separa modelos grandes entre si. Um modelo de fronteira só pode empatar com o de 27B aqui. Para comparar modelos grandes é preciso um teste mais difícil: a prosa corrida e os casos escritos por pessoas.
- **Há distância entre a base e o teto.** A melhor base tira +0,17, e o modelo maior tira +1. Essa é uma das condições do portão da fase 3. O que o treino precisa mostrar é que um modelo de 4B, que roda em uma máquina comum, chega perto do que hoje só o de 27B faz.
- **As bases quase nunca dizem "não identificável".** Nos mundos em que o efeito não pode ser medido, a Qwen3-4B acerta 6% e a Granite 1%; a Qwen3.5-4B acerta 30%. Nos mundos identificáveis elas vão bem melhor (de 68% a 88%). O espaço para o treino está justamente na honestidade, que é a tese do projeto.
- **As duas Qwen empatam.** A diferença entre elas é de 0,06, com margem de erro de 0,14. As duas ficam acima da Granite por cerca de 0,3, e essa diferença é segura.
- **Resposta inválida, aqui, é texto cortado.** Sem o modo de raciocínio, a Qwen3.5-4B e a Granite às vezes raciocinam dentro do campo do motivo, entram em repetição e estouram o limite de 2 mil tokens antes de dar o veredito.
- **A Qwen3.5-4B é a mais lenta** nesta máquina: cerca de 11 segundos por mundo, contra 2 da Qwen3-4B, porque uma parte da sua arquitetura roda por um caminho lento nas bibliotecas instaladas.

A especificação diz que fica a melhor base. Com as duas Qwen empatadas, a escolha ainda não está clara: falta a medição com raciocínio, e a Qwen3.5-4B tem duas desvantagens práticas (a lentidão e o fato de o ajuste fino comum alcançar só parte das suas camadas de atenção).

A primeira tentativa de medir as bases com raciocínio falhou por falta de memória na placa de vídeo, e o harness gravou as 197 falhas como respostas inválidas. Esses registros foram apagados antes de aparecer em qualquer página. O harness foi corrigido: uma falha de máquina não gera registro, e depois de cinco falhas a rodada para com erro. A medição com raciocínio será refeita com lotes menores.

A medição usou os modelos do Hugging Face carregados na placa de vídeo, o mesmo caminho do treino, nas revisões registradas em `configs/bases.yaml`. Os registros ficam em `outputs/runs/placar-base/`, e a página do placar é refeita com `uv run python -m causalista.viz.scoreboard --set placar-base`.

Durante a medição a leitura das respostas mudou em um ponto: afirmar um efeito ajustando por algo que não é coluna da tabela passou a contar como erro confiante, e não como resposta inválida. As respostas gravadas foram pontuadas de novo (`scripts/rescore.py`), sem rodar os modelos outra vez; sete respostas da Granite mudaram de categoria, e nenhuma nota mudou.

### 17. Idiomas

O André perguntou se vale treinar em vários idiomas, para o projeto ser o mais genérico possível. A proposta do assistente é usar o mesmo desenho dos temas: treinar em português, inglês e espanhol e reservar francês e alemão só para teste. A decisão é do André, e a especificação continua dizendo português e inglês.

O que já foi construído vale para qualquer lista de idiomas:

- uma ficha pode ser lida em outro idioma, a partir de uma tradução que só troca as palavras;
- o mesmo mundo pode ser contado em outro idioma sem mudar nada do gabarito;
- a tradução é feita por um modelo aberto e conferida, frase a frase, por outro modelo aberto de outra família (`scripts/translate_theory.py`).

Os nomes das colunas não são traduzidos: em qualquer idioma, a tabela tem as colunas da ficha.

As oito fichas foram traduzidas para o inglês (`theories/i18n/en/`) pelo modelo qwen3.5:35b e conferidas pelo granite4.1:30b, os dois abertos, com licença Apache 2.0. São 588 textos. O modelo conferente recusou 37; o assistente leu os 37: a maior parte era alarme falso, e 17 foram corrigidos à mão. Depois o assistente leu as oito traduções por inteiro e corrigiu mais 28 textos: alguns erros de sentido que a conferência automática deixou passar (por exemplo, "combina um plano de cuidado" traduzido como "combines") e vários de gramática. As correções estão listadas no cabeçalho de cada arquivo.

As traduções continuam marcadas como rascunho até o André ler, e o programa que gera os dados de treino recusa todas enquanto isso.

Espanhol, francês e alemão não foram traduzidos: esperam a decisão sobre os idiomas. Um teste mostrou que os modelos abertos médios traduzem mal para o alemão; para esses idiomas é preciso o modelo maior, que leva cerca de dez minutos por ficha e por idioma.

### 18. A narrativa em prosa corrida

O programa está escrito (`src/causalista/worlds/prose.py`) e foi calibrado com modelos de verdade. Um modelo aberto reescreve a narrativa de um fato por frase como uma pessoa contaria. Dois outros modelos abertos leem a prosa e respondem, frase por frase, se o texto diz cada fato do mundo e se diz algum fato que não é dele (os fatos dos outros papéis das mesmas variáveis: a reclamação registrada depois da oferta, em vez de antes). A prosa só fica se os dois leitores concordarem que ela diz todos os fatos do mundo e nenhum dos outros. Se não, o escritor é avisado do que faltou ou sobrou e reescreve, até duas vezes.

O primeiro desenho da conferência não funcionou, e a calibração mostrou isso. Ele pedia ao leitor uma tabela com o que cada variável influencia e o que a muda. Em histórias fiéis, os leitores só acertavam a tabela em 7 a 13 de 32 mundos: a conferência descartaria a maior parte das histórias boas. O desenho atual foi medido nas mesmas 32 histórias:

| Modelo leitor | Aceita a história fiel | Vê que um fato foi retirado | Vê que um papel foi trocado |
|---|---|---|---|
| qwen3.5:9b | 30 de 32 | 28 de 32 | 13 de 13 |
| qwen3:14b | 29 de 32 | 30 de 32 | 13 de 13 |
| granite4.1:30b | 26 de 32 | 29 de 32 | 13 de 13 |

A troca de papel é o erro que mudaria o gabarito, e nenhum leitor deixou passar. Um leitor sozinho deixa passar um fato retirado em 6% a 12% dos casos; por isso são dois.

Escrita, medida em 24 mundos dos oito temas:

| Escritor | Leitores | Histórias mantidas | Tempo por mundo |
|---|---|---|---|
| granite4.1:30b | qwen3.5:9b e qwen3:14b | 17 de 24 | cerca de 50 segundos |
| qwen3:14b | qwen3.5:9b e granite4.1:30b | 16 de 24 | cerca de 30 segundos |

As recusas que sobram são, na maioria, alarmes falsos dos leitores, que erram para o lado seguro: recusam prosa boa. O assistente leu por inteiro algumas histórias mantidas e todas diziam os fatos do mundo sem trocar papéis. Com esses tempos, a prosa serve para os conjuntos de teste e para alguns milhares de mundos de treino, não para dezenas de milhares.

Limites: as amostras são pequenas (32 e 24 mundos), só em português, e a leitura humana das histórias mantidas foi de poucos casos.

**Os mundos do placar em prosa.** Dos 197 mundos do placar de base, 134 ganharam uma versão em prosa (68%), em 2 horas e 42 minutos. Por tema, de 11 em 24 (e-mail) a 20 em 23 (software). As três bases foram medidas nos mesmos 134 mundos, contados dos dois jeitos:

| Base, sem raciocínio | Nota com um fato por frase | Nota em prosa | Diferença |
|---|---|---|---|
| Qwen3.5-4B | +0,18 | +0,36 | +0,18, com margem de erro de 0,19 |
| Qwen3-4B | +0,08 | +0,09 | +0,01, com margem de erro de 0,10 |
| Granite 4.2 de 3B | −0,21 | −0,19 | +0,01, com margem de erro de 0,15 |

A prosa não ficou mais difícil para as bases; nenhuma diferença é segura. Faz sentido: a conferência exige que a prosa diga todos os fatos, então ela acaba sendo uma reescrita fiel, com outra ordem e outras palavras. Ela serve para o modelo treinado não depender das frases exatas das fichas. Ela não serve como o teste mais difícil para modelos grandes; para isso sobram os casos escritos por pessoas, ou um tipo de história em que os fatos fiquem implícitos, que hoje não existe no projeto.

### 19. Treino e teste separados

- `configs/split.yaml` (proposta): seis temas no treino; e-mail e saúde reservados para teste.
- O conjunto do teste final está gerado: 512 mundos dos dois temas reservados, 62% identificáveis.
- Os 20 mundos-vitrine foram escolhidos por uma regra que olha só o tamanho do mundo (`configs/showcase.yaml`).
- Cada uso tem a sua faixa de sementes, para que nenhum mundo de teste seja mundo de treino.
- `scripts/make_training_data.py` gera os exemplos do treino supervisionado: o texto mostrado ao modelo e a resposta ideal, tirada do gabarito.

Se o André escolher outros temas de teste, o conjunto do teste final e os mundos-vitrine são refeitos.

### 20. O ambiente de treino

As bibliotecas de treino estão instaladas no mesmo ambiente do projeto, como um grupo de dependências à parte: o pacote publicado continua sem precisar delas. As versões e o que foi conferido em cada biblioteca estão em `scripts/README-treino.md`.

As três bases candidatas existem no Hugging Face com os nomes da especificação, são públicas, têm licença Apache 2.0 conferida nos metadados e foram baixadas (`configs/bases.yaml`).

| Base | Repositório | Parâmetros |
|---|---|---|
| Qwen3.5-4B | `Qwen/Qwen3.5-4B` | 4,2 bilhões na parte de texto |
| Granite 4.2 de 3B | `ibm-granite/granite-4.2-3b` | 3,7 bilhões |
| Qwen3-4B | `Qwen/Qwen3-4B` | 4,0 bilhões |

O programa do treino supervisionado está escrito (`scripts/train_sft.py`), e o harness ganhou um caminho que carrega os modelos direto na placa de vídeo, o mesmo usado no treino (`src/causalista/harness/hf.py`).

Um teste de fumaça treina dez passos em cada base e gera respostas com o adaptador. Ele não mede qualidade: só confirma que as ferramentas carregam a base.

| Base | Carrega na ferramenta de treino | Dez passos de treino | Geração com o adaptador | Memória no treino |
|---|---|---|---|---|
| Qwen3-4B | sim | sim | sim | 8,4 GB |
| Granite 4.2 de 3B | sim | sim | sim | 8,3 GB |
| Qwen3.5-4B | sim | sim | sim | 8,8 GB |

A Granite 4.2 era a dúvida registrada em 3 de outubro: ela carrega e treina. As três cabem com folga nos 24 GB da placa de vídeo. Os tempos por passo medidos nesse teste não valem, porque a placa estava ocupada com outros trabalhos.

O que a conferência das bibliotecas mostrou, para as fases 4 e 5:

- a ferramenta de treino (Unsloth) troca o repositório pedido por uma cópia própria se não for instruída a usar o nome exato; o programa usa o nome exato e a revisão registrada;
- nenhuma das três bases marca, no seu modelo de conversa, onde começa a resposta; o programa calcula essa marca por conta própria e aborta se a perda não cair só sobre a resposta;
- nas três bases o raciocínio vem ligado por padrão e é desligado no modelo de conversa;
- para o treino por reforço, o comprimento máximo do texto de entrada na ferramenta é de 512 tokens por padrão, e as nossas perguntas têm cerca de mil; e a normalização da recompensa por grupo, que é o risco descrito na seção 6 da especificação, é o padrão e pode ser trocada.

### 21. O relatório executivo

Um relatório para colegas e gestores, com a natureza e o status do projeto, publicado como página privada que o André compartilha quando quer.

### 22. O tamanho do que existe em 4 de outubro

| O quê | Quanto |
|---|---|
| Código do pacote | cerca de 4.500 linhas, em 33 arquivos |
| Programas de apoio (`scripts/`) | cerca de 2.300 linhas |
| Testes | cerca de 2.700 linhas, em 34 arquivos |
| Testes do dia a dia | 4.472 passando, em cerca de 8 minutos (os mundos são testados nos oito temas) |
| Casos de livro-texto | 24, aprovados |
| Casos escritos | 5, à espera de aprovação |
| Fichas de teoria | 8: uma aprovada e sete em rascunho |
| Traduções das fichas | 8 para o inglês, em rascunho |
| Mundos gravados | 197 do placar de base, 134 deles também em prosa, e 512 do teste final |
| Páginas publicadas | 3: casos, mundos e placar |

## O que foi feito em 5 de outubro

### 23. A decisão do André e a revisão independente

Em 5 de outubro o André escreveu que não vai validar um a um o que o assistente gera, porque não há tempo, e que a saída é considerar que o trabalho está sendo feito corretamente: na prática, usar dados produzidos por um modelo de fronteira para treinar um modelo pequeno, como as empresas fazem. Pediu que o assistente revisasse tudo mais uma vez, em especial todas as fichas, e que, estando tudo certo, começassem os testes de treino. Pediu também explicações bem simples do que está sendo feito.

Três consequências, registradas na especificação (revisão 7):

- **Aprovação por delegação.** As sete fichas novas e os cinco casos escritos deixaram de esperar a leitura do André. Passaram por uma revisão independente e ficaram aprovados por delegação.
- **Procedência.** As frases das fichas, escritas pelo assistente, entram nas histórias de treino. As respostas-alvo continuam vindo só do verificador.
- **Como o assistente informa.** Explicação curta e simples na conversa; o detalhe fica neste documento.

**Como foi a revisão.** Cada ficha foi lida por um leitor separado (outra instância do assistente, sem acesso ao raciocínio de quem escreveu a ficha e sem poder alterar arquivos), com uma lista de oito coisas a conferir em cada frase: o sinal, o antes e o depois, se a frase afirma uma ligação que o mundo não tem, se a moldura já entrega a resposta, se a frase sobre o que falta na tabela combina com as outras, se cada frase se sustenta sozinha, o vocabulário e a plausibilidade. Um nono leitor fez o mesmo com os cinco casos escritos.

| Ficha | Erros | Dúvidas | Trocas de texto aplicadas |
|---|---|---|---|
| Telecom (já aprovada pelo André) | 5 | 9 | 16 |
| Software | ver nota | ver nota | 10 |
| Educação | 1 | 8 | 11 |
| Saúde | 1 | 5 | 9 |
| Banco | 0 | 7 | 11 |
| RH | 0 | 7 | 17 |
| Varejo | 0 | 8 | 5, e um número |
| E-mail | 0 | 6 | 8 |
| Cinco casos escritos | 0 | 10 | 9 |

Nota: a contagem de erros e dúvidas do software não ficou registrada; foram aplicadas as seis correções que o leitor pediu e mais quatro de redação comum a todas as fichas.

"Erro" quer dizer que um leitor atento tiraria da história um desenho causal diferente do que o mundo tem. Nenhum erro mudava o gabarito: eram frases que diziam mais do que deviam. Os tipos mais comuns:

- **A frase escolhia por uma informação que a organização não tinha.** No telecom, uma frase dizia que a operadora fez a oferta a quem tinha proposta de concorrente, e outra dizia que a operadora não sabe quem recebeu proposta. Passou a ser o cliente quem chega à oferta.
- **A frase citava outra coluna.** Na educação, "alunos que trabalham têm menos tempo para estudar" ligava duas colunas que o mundo não liga (trabalho e horas de estudo). Virou "chegam mais cansados às provas".
- **A frase dava uma regra geral em vez de um fato.** Na saúde, "a operadora procurou primeiro os beneficiários de maior risco" fazia toda coluna de risco parecer causa da inscrição. A explicação saiu.
- **A frase valia para todos, e a tabela não.** "A equipe liga para quem cancelou" contradiz uma coluna em que só parte recebeu ligação. Virou "liga com mais frequência", em todas as fichas.
- **Datas sem âncora.** No RH o programa dura três meses, e "depois do programa" podia ser depois do início ou do fim. Todas as descrições passaram a dizer "início" ou "fim".

Ficaram como estão, por serem escolhas de desenho e não defeitos de frase: a coluna do mediador é medida dentro da janela do resultado (a ficha do telecom, aprovada, já era assim); a variável sem relação com nada do varejo é o mês de aniversário; e a pesquisa de satisfação do varejo como causa só do cupom.

As trocas de frases na ficha do telecom mudam o texto das histórias, não a estrutura nem os números. Já a regra nova da seção 24 muda a maior parte dos mundos, inclusive os 20 que o André leu: em muitos deles uma informação inofensiva saiu da tabela.

As traduções para o inglês ficaram desatualizadas nas frases trocadas. A lista das trocas está em `theories/i18n/pendentes-2026-10-05.json`.

### 24. Dois atalhos fechados na fábrica de mundos

Na revisão, o assistente procurou regras de uma linha que acertassem a resposta sem raciocinar. Achou duas.

**"A história diz que algo não está na tabela, logo não dá para concluir."** Acertava 100% dos vereditos em 6.255 mundos, porque tudo o que ficava fora da tabela era um confundidor. Um aluno que decorasse essa frase tiraria nota máxima na parte mais importante da prova, sem entender nada. Correção: uma informação pode faltar na tabela sem fazer mal (uma causa só do resultado, ou só da intervenção). Entrou também um novo tipo de par de gêmeos: a mesma informação falta nos dois mundos; em um ela é causa só do resultado, no outro é confundidor.

**"Faltam duas coisas, logo não dá para concluir."** Depois da primeira correção, essa contagem ainda acertava sempre. Correção: um mundo pode ter duas ausências inofensivas, e nenhum mundo tem mais de duas ausências.

Medido depois das duas correções, nos oito temas: sem nada faltando, todos os mundos são identificáveis (isto é o raciocínio certo, não um atalho); com uma ausência, 47%; com duas, 28%. A melhor regra que só conta as ausências acerta 69% dos vereditos; quem lê o papel de cada variável acerta 100%. No conjunto, 54% dos mundos são identificáveis. Os dois limites estão em testes (`tests/worlds/test_structure.py`).

Isto é uma mudança no desenho dos mundos, que é decisão do André. Foi feita dentro da delegação, está na seção 3 da especificação, e pode ser desfeita.

### 25. O estimador, medido de novo

Como as fichas e a fábrica mudaram, a medição da fase 2 foi refeita, com 400 sementes por tema.

| Tema | Mundos | O intervalo conteve o efeito verdadeiro |
|---|---|---|
| Telecom | 440 | 96,4% |
| Varejo | 442 | 94,8% |
| Banco | 427 | 95,8% |
| Software | 448 | 94,0% |
| RH | 429 | 95,3% |
| Educação | 434 | 97,2% |
| Saúde | 422 | 94,5% |
| E-mail | 420 | 94,8% |
| **Os oito** | **3.462** | **95,3%** |

Nas tabelas de 50 mil linhas: 94,6% (686 mundos; na saúde, 90,7% em cerca de 85 mundos, o ponto mais baixo). Nos mundos com confundidor, a comparação simples só conteve o efeito verdadeiro em 23,7%. A medição anterior está guardada em `outputs/gates/antes-da-revisao-2026-10-05/`.

### 26. O primeiro teste de treino

**O que foi treinado.** A base Qwen3-4B (uma das duas melhores no placar de base, e cinco vezes mais rápida de treinar que a outra), com 4.673 exemplos em português dos seis temas de treino: a pergunta como o modelo a vê e a resposta ideal dada pelo verificador. Histórias de um fato por frase. Uma passada pelos exemplos, 293 passos, 26 minutos na placa desta máquina, com pico de 9 GB de memória. Nenhuma estrutura dos conjuntos de teste está entre os exemplos.

**A prova.** Um conjunto novo de 384 mundos dos oito temas (`placar-v2`, sementes 50.000 em diante), gerado depois das correções das seções 23 e 24. Os conjuntos anteriores (`placar-base` e `teste-final`) são da fábrica antiga e ficam só como histórico.

| Quem respondeu | Nota | Acerto | Erro confiante | Acerto quando a resposta é "não identificável" | Pares de gêmeos com os dois certos |
|---|---|---|---|---|---|
| "Ajusta nada" | −0,93 | 4% | 96% | nunca se abstém | |
| "Ajusta tudo" | −0,77 | 11% | 89% | nunca se abstém | |
| Qwen3-4B sem treino | +0,03 | 51% | 47% | 9% | 12% |
| Qwen3-4B treinado | +1,00 | 100% | 0% | 100% | 100% |

O modelo treinado acertou os 384 mundos, inclusive os 97 dos dois temas que nunca viu (e-mail e saúde).

**A checagem: ele entendeu ou decorou o formato?** Uma nota perfeita logo na primeira tentativa pede desconfiança. Três sondagens, todas com o mesmo modelo treinado:

| Sondagem | Sem treino | Treinado | Modelo aberto de 27B |
|---|---|---|---|
| As mesmas histórias, com as frases em outra ordem (192 mundos) | 37% | 65% | não medido |
| Histórias em prosa corrida (134 mundos da fábrica antiga) | 54% | 75% | 100% |
| Os cinco casos escritos (com resumos de coluna inventados) | 4 de 5 | 2 de 5 | não medido |

O modelo treinado se apoiou no formato dos exercícios. Em todas as histórias de treino, as frases sobre uma mesma variável vinham juntas e na mesma ordem (primeiro a ligação com a intervenção, depois a ligação com o resultado). Com as frases fora dessa ordem ele cai de 100% para 65%. Na prosa corrida o treino ajuda (de 54% para 75%), mas fica longe do modelo grande. Nos cinco casos escritos ele ficou pior do que a base sem treino; são só cinco casos, e as colunas levaram resumos inventados, então isto é um sinal e não uma medida.

Em uma frase: o treino funciona como máquina (roda, converge, e o modelo passa a reconhecer quando falta um confundidor), mas com exercícios todos arrumados do mesmo jeito o aluno aprende a arrumação.

### 27. O segundo treino: frases em ordem sorteada

**A correção.** A fábrica passou a sortear a ordem das frases da história. Em cerca de metade dos mundos as frases de uma mesma variável ficam juntas, em qualquer ordem; na outra metade, todas as frases se espalham pela história. Vale para os exercícios e para a prova. As histórias de dois mundos gêmeos continuam diferindo só no fato que mudou. É o terceiro atalho fechado no dia, e também está em teste (`tests/worlds/test_world.py`).

**O treino.** Mesma base, mesmos mundos e mesmo tamanho do primeiro (4.673 exemplos, 293 passos, 32 minutos); só a ordem das frases mudou.

**A prova.** `placar-v3`: os mesmos 384 mundos do `placar-v2`, contados com a ordem sorteada.

| Medida | Sem treino | Primeiro treino | Segundo treino |
|---|---|---|---|
| `placar-v2`: 384 mundos, frases na ordem antiga | 51% | 100% | não medido |
| `placar-v3`: os mesmos mundos, frases em ordem sorteada | 47% (nota −0,04) | 70% (nota +0,41) | 98% (nota +0,96) |
| As histórias do formato antigo, com as frases embaralhadas (192 mundos) | 37% | 65% | 99% |
| Histórias em prosa corrida (134 mundos da fábrica antiga) | 54% | 75% | 90% |
| Os cinco casos escritos | 4 de 5 | 2 de 5 | 2 de 5 |

No `placar-v3` o segundo treino acertou 375 de 384 (94 de 97 nos dois temas que nunca viu; 175 de 184 pares de gêmeos com os dois certos). Os 9 erros: 3 vezes afirmou um efeito sem poder, e 6 vezes disse "não identificável" quando dava para medir.

**O que isto mostra.**

- Sortear a ordem resolveu a dependência da ordem (de 65% para 99%) e, sem ver nenhuma prosa no treino, levou a prosa de 75% para 90%.
- A prova com ordem sorteada já não é gabaritada: sobra espaço para medir melhora.
- Os cinco casos escritos continuam em 2 de 5, com os mesmos erros. Neles o texto junta dois fatos em uma frase ("os gestores indicaram mais quem tinha mais tempo de casa e quem tinha se mostrado mais engajado") e diz de outro jeito que algo ficou fora da tabela ("ficou só no prontuário"). O modelo treinado ainda lê as frases das fichas, não qualquer frase. São só cinco casos: é um sinal, não uma medida.

**O passo seguinte, já em andamento.** Pôr prosa corrida no treino, escrita por um modelo aberto e conferida por dois outros (o nível 2 da especificação), e fazer uma prova em prosa escrita por um modelo diferente do que escreveu a do treino. Depois vem o terceiro treino.

Como foi:

- **Prosa da prova: pronta às 14h28.** Um modelo aberto (Granite 4.1 de 30B) reescreveu metade dos mundos do `placar-v3`, e dois outros conferiram frase por frase. De 192 histórias, 113 passaram na conferência e foram guardadas; 79 foram recusadas. Levou três horas. Nenhum modelo respondeu ainda a essa prova.
- **Prosa do treino: pronta às 21h26.** 876 mundos de treino reescritos por outro modelo (Qwen3 de 14B), para que a prova em prosa não tenha o mesmo "sotaque" dos exercícios: 719 histórias passaram na conferência e 157 foram recusadas, a cerca de meio minuto por história.
- **Depois:** o terceiro treino, na seção 28.

**A prova nova pode ser resolvida por leitura.** O modelo aberto de 27B, com raciocínio, respondeu um em cada quatro mundos do `placar-v3` (96 mundos, 49 deles não identificáveis) e acertou os 96. As mudanças do dia na fábrica (ausências inofensivas, ordem sorteada) não deixaram as histórias ambíguas para um leitor forte.

**O placar do `placar-v3`, completo.** "Ajusta nada" −0,93; "ajusta tudo" −0,77; a base sem treino −0,04 (acerta 13 dos 176 mundos não identificáveis, e os dois gêmeos em 16 de 184 pares); o primeiro treino +0,41 (85 de 184 pares); o segundo treino +0,96 (173 de 176 não identificáveis, 175 de 184 pares); o modelo de 27B, em 96 mundos, +1,00.

### 28. O terceiro treino: prosa corrida nos exercícios

**Os exemplos.** Os mesmos 4.673 de um fato por frase, mais 710 histórias em prosa corrida de mundos de treino (seção 27), escritas por um modelo aberto (Qwen3 de 14B) e aprovadas pelos dois leitores. 5.383 exemplos; 337 passos; 29 minutos.

**A prova em prosa.** 113 mundos do `placar-v3` reescritos por outro modelo aberto (Granite 4.1 de 30B), para que a prova não tenha o mesmo "sotaque" dos exercícios. Nenhum modelo tinha visto essas histórias.

| Medida | Sem treino | Segundo treino (sem prosa) | Terceiro treino (com prosa) |
|---|---|---|---|
| `placar-v3`, um fato por frase, 384 mundos | 47% (−0,04) | 98% (+0,96) | 99% (+0,99) |
| `placar-v3` em prosa corrida, 113 mundos, escrita por outro modelo | 39% (−0,22) | 81% (+0,64) | 93% (+0,87); o modelo de 27B, em 57 deles, 100% |
| Prosa da fábrica antiga, 134 mundos | 54% | 90% | 96% |
| As mesmas frases em outra ordem, 192 mundos | 37% | 99% | 100% |
| Os cinco casos escritos à mão | 4 de 5 | 2 de 5 | 4 de 5 |

Na prosa nova, o terceiro treino acerta 59 dos 62 mundos não identificáveis e 20 dos 24 dos dois temas que nunca viu. Os 10 erros dele nas duas provas: 5 vezes afirmou um efeito sem poder (em prosa), 4 vezes se absteve sem precisar, 1 resposta sem veredito.

Nos casos escritos à mão voltou a acertar 4 de 5: os três que o segundo treino errava passaram a sair certos, e o erro que ficou é o mesmo da base sem treino (o caso da saúde, em que a informação que falta é contada de um jeito que nenhuma ficha usa: "ficou só no prontuário").

**O que isto mostra.** Prosa nos exercícios é o que faltava para o modelo ler além das frases das fichas: de 81% para 93% em prosa de outro modelo, e de 2 para 4 nos casos à mão, sem perder nada na prova de um fato por frase. O modelo aberto de 27B, com raciocínio, acertou os 57 mundos da prova em prosa que respondeu (29 deles não identificáveis): a prova em prosa pode ser resolvida por leitura, e a distância do modelo pequeno treinado para o teto é de 7 pontos. O que ainda não foi medido: outros idiomas, e textos escritos por pessoas em quantidade (os 30 casos humanos da seção 7).

### 29. O tamanho do que existe em 5 de outubro

| O quê | Quanto |
|---|---|
| Testes do dia a dia | 4.508 passando, em cerca de 11 minutos |
| Fichas de teoria | 8, todas aprovadas (uma pelo André, sete por delegação) |
| Casos escritos | 5, aprovados por delegação |
| Traduções das fichas para o inglês | 8, em rascunho e desatualizadas nas frases trocadas |
| Mundos gravados | `placar-v3` (384, o placar atual), `teste-v3` (505, guardado para a medição final), `treino-prosa-v1` (876, para a prosa do treino); `placar-v2` é o `placar-v3` com as frases na ordem antiga; `placar-base` e `teste-final` são histórico |
| Exemplos de treino | `sft-pt-v1` e `sft-pt-v2`, 4.673 cada; `sft-pt-v3`, 5.383 (710 em prosa) |
| Histórias em prosa corrida | 113 na prova (`placar-v3`) e 719 nos mundos de treino (`treino-prosa-v1`) |
| Modelos treinados | três adaptadores de teste, em `outputs/train/` |

## O que foi decidido em 6 de outubro

### 30. O desenho do treino de verdade

O assistente apresentou sete decisões e o André aprovou as seis primeiras como propostas ("vamos fazer tudo o que você propõe"), deixando a sétima para o fim:

1. **Tamanho.** Cerca de 20 mil exercícios de um fato por frase e cerca de 3 mil histórias em prosa corrida. O gargalo é escrever a prosa: de um a dois dias de placa de vídeo.
2. **Prosa.** Perto de 25% dos exercícios, escrita por dois ou três modelos abertos diferentes; um modelo (Granite 4.1 de 30B) fica reservado para escrever só a prova.
3. **Idiomas.** Treino em português e inglês; espanhol só como prova, para medir a generalização para uma língua nunca vista. Francês e alemão ficam para uma versão futura.
4. **Temas de prova.** E-mail marketing e saúde suplementar seguem fora do treino.
5. **Base.** Qwen3-4B. Empatou com a Qwen3.5-4B no placar de base e é cinco vezes mais rápida de treinar; o empate foi decidido pela praticidade.
6. **Reforço (fase 5).** Uma rodada curta, só com prosa e casos difíceis, mantida apenas se superar o supervisionado nas provas de prosa e de texto humano. Trava contra o colapso para a recusa: abstenção indevida acima de 10% para a rodada, e volta-se ao modelo anterior.
7. **Casos escritos por pessoas.** Adiado para o fim. O André disse que não há como pôr uma etapa humana no fluxo; pediu que o assistente simule texto humano "no limite da sua capacidade", pensando com profundidade em cada etapa para não esquecer detalhes nem enviesar o processo.

O André pediu também que o reforço com recompensa verificável, a tese do projeto, entrasse logo no plano. Resposta do assistente, incorporada ao plano: o reforço só ensina onde o aluno ainda erra, e por isso terá dois braços comparados na mesma prova: (a) reforço puro, a partir do modelo cru, com raciocínio escrito antes da resposta e nota só pelo resultado, dada pelo verificador; (b) supervisionado seguido de reforço em prosa e casos difíceis. A comparação dos dois com o supervisionado puro, em prosa e nos casos tipo humano, é o resultado a publicar.

**Como o texto humano será simulado.** Casos escritos por instâncias separadas do assistente, cada uma no papel de uma pessoa (gestor, analista, aluno), em registros variados (e-mail, ata de reunião, mensagem curta, trecho de relatório), em três idiomas, em temas dentro e fora dos oito, sem acesso às fichas de teoria; cada caso declara o diagrama e a resposta, o verificador confere a resposta, e um revisor independente confere se o texto implica exatamente o diagrama. O conjunto fica congelado antes de qualquer modelo responder e nunca entra no treino.

### 31. O protocolo da medição final, escrito antes dos resultados

Para que o resultado final não seja escolhido depois de visto, fica registrado aqui, antes de qualquer treino de verdade, como ele será medido.

**O que é medido uma única vez, no fim**, com o modelo escolhido e com as referências (as duas estratégias ingênuas, a base sem treino e o modelo aberto de 27B em amostra):

1. `teste-v3`, um fato por frase, em português e em inglês (505 mundos em cada idioma, oito temas; e-mail e saúde nunca treinados).
2. `teste-v3` em espanhol, um fato por frase (idioma nunca treinado).
3. A prosa corrida do `placar-v3` em português e em inglês, escrita pelo modelo reservado para a prova (Granite 4.1 de 30B), que não escreve nenhuma prosa de treino.
4. Os 48 casos que simulam texto de pessoa (`cases/simulados/`), em três idiomas, congelados em 6 de outubro depois da revisão independente e nunca usados em treino nem em ajuste.

**O que serve para desenvolver** (e pode ser olhado quantas vezes for preciso): `placar-v3` um fato por frase em português e inglês, a prosa antiga do `placar-base`, as sondagens de frases embaralhadas, e os cinco casos escritos da fase 0.

**Como se escolhe o modelo.** Entre o supervisionado final, o reforço puro (braço A) e o supervisionado seguido de reforço (braço B), fica o que tiver a maior nota na prosa do `placar-v3` em português, desde que não perca mais de 2 pontos de acerto na prova de um fato por frase. A escolha é feita só com os conjuntos de desenvolvimento; os casos simulados e o `teste-v3` só são abertos depois.

**Emenda de 7 de outubro, escrita antes de medir os braços novos.** Os dois braços da seção 33 não tiveram o que ensinar (seção 35), e o reforço passou a mirar texto tipo humano. Para isso foram escritos 240 casos de treino (`cases/treino-simulados/`), separados dos 48 congelados. Quatro arquivos deles (`pt-17`, `pt-18`, `en-11`, `en-12`: 32 casos) ficam fora de qualquer treino e servem de prova de desenvolvimento para texto tipo humano. A regra de escolha passa a ser: entre o supervisionado final e os braços treinados nos casos (reforço e supervisionado, braços C e D), fica o de maior nota nesses 32 casos de desenvolvimento, desde que não perca mais de 2 pontos de acerto na prosa do `placar-v3` em português nem na prova de um fato por frase. Os 48 casos congelados continuam reservados para a medição final.

**O que não se afirma com estes números** (seção 7 da especificação): que o modelo supera a fronteira; que lê texto de pessoas de verdade (os casos são simulados pelo assistente); que recupera efeitos de experimentos reais.

**O que está sendo produzido agora** (6 de outubro, de madrugada): as oito fichas traduzidas para o inglês (corrigidas) e para o espanhol (novas), lidas por inteiro por instâncias separadas do assistente; 48 casos tipo humano, escritos por seis instâncias e revisados por outras seis; cerca de 20 mil exemplos de um fato por frase em português e inglês; perto de 3 mil histórias em prosa para o treino, por dois modelos abertos, e a prosa em inglês da prova; o programa do treino por reforço, com a trava de abstenção, testado em dois passos.

### 32. O que ficou pronto na madrugada de 6 de outubro

- **Traduções.** Oito instâncias do assistente, uma por ficha, leram a tradução inglesa inteira contra a ficha em português e a corrigiram; escreveram a espanhola do zero. O inglês feito por modelo aberto em 4 de outubro tinha de 12 a 17 erros de sentido por ficha (frases que não diziam a mesma coisa: agente trocado, "com mais frequência" perdido, tempo errado), além das frases que a revisão de 5 de outubro mudou. As dezesseis traduções estão com `status: revisada`, por delegação, e os testes de tradução passam nas três línguas.
- **Casos tipo humano.** 48 casos em `cases/simulados/` (24 em português, 16 em inglês, 8 em espanhol), escritos por seis instâncias no papel de pessoas e revisados por outras seis. A revisão mudou texto em quase todos: erros de tempo (uma coluna medida no meio da janela do resultado), fatores ausentes só meio inferíveis, frases que ecoavam as fichas, e "dicas" (a mesma frase em todo caso não identificável; a pergunta final só nos não identificáveis). A sobreposição de palavras com as fichas ficou abaixo de 1,5%. Congelados, com soma de verificação em `cases/simulados/README.md`.
- **Exemplos de um fato por frase.** 19.814 (9.719 em português, 10.095 em inglês), seis temas de treino, 888 estruturas dos conjuntos de teste excluídas.
- **Prosa de treino.** Em português, pronta na noite de 6 de outubro: 1.167 histórias guardadas das 1.408 escritas pelo Qwen3 de 14B (83%) e 785 das 945 escritas pelo Gemma 4 de 26B (83%). Em inglês, em produção na manhã de 7 de outubro: 620 guardadas até as 5h; faltam o resto do conjunto do Gemma, um terço do conjunto do Qwen e a prosa em inglês da prova, escrita pelo Granite (reservado para provas). A fila deve terminar por volta do meio-dia de 7 de outubro; depois dela, começam sozinhos o treino supervisionado final, as medições de desenvolvimento e os dois braços do reforço (seção 33).
- **Programa do reforço** (`scripts/train_grpo.py`): roda sobre mundos gravados, nota do verificador como única recompensa, raciocínio escrito opcional, trava de abstenção. Testado em dois passos. Encontrou e contornou uma incompatibilidade entre duas bibliotecas instaladas.
- **Apoio.** Casos escritos passam a ser conjunto de teste do harness (`run_models.py --cases`), com resumo de colunas inventado a partir da descrição; `scripts/check_cases.py`; `scripts/merge_adapter.py` para fundir o adaptador supervisionado na base antes do braço B do reforço.

### 33. A fila automática dos treinos (escrita antes de rodar)

Quando a prosa terminar, roda sem intervenção, nesta ordem, com registro em `outputs/train/`:

1. Montar os exemplos finais: os 19.814 de um fato por frase mais todas as histórias em prosa dos dois conjuntos de treino (português e inglês).
2. Treino supervisionado final (`sft-final-qwen3-4b`): uma passada, mesmos ajustes dos testes.
3. Medições de desenvolvimento: o modelo final e a base no `placar-v3` inteiro (um fato por frase em três idiomas; prosa em português e inglês) e nos 48 casos simulados, com as duas estratégias ingênuas e o modelo de 27B nos casos.
4. Fusão do adaptador na base, para o braço B.
5. Braço B do reforço: parte do modelo supervisionado fundido, responde direto (sem raciocínio escrito), 200 passos, mundos de treino de um fato por frase e em prosa (`treino-prosa-v1`, nunca usados no supervisionado final).
6. Braço A do reforço: parte do modelo cru, com raciocínio escrito antes da resposta, 200 passos, os mesmos mundos.

Em cada passo do reforço o modelo escreve oito respostas para cada um de dois mundos; o verificador dá a nota de cada resposta (+1, −1, −0,5 ou −1 por resposta inutilizável), e o modelo é empurrado na direção das respostas que ficaram acima da média do seu grupo. Nenhuma resposta certa é mostrada. A trava: se, nos últimos 200 mundos identificáveis, mais de 10% das respostas forem "não identificável", a rodada para e guarda o ponto anterior.

O que vem depois disso é manual: medir os dois braços nos conjuntos de desenvolvimento, escolher pelo protocolo da seção 31 e só então abrir o `teste-v3` e os casos simulados para a medição final.

### 34. O treino supervisionado final e as medições de desenvolvimento (7 de outubro)

**Exemplos.** 22.906: os 19.814 de um fato por frase (metade em português, metade em inglês) mais 3.092 histórias em prosa dos dois conjuntos de treino (1.943 em português, escritas pelo Qwen3 de 14B e pelo Gemma 4 de 26B; 1.149 em inglês). A prosa é 13,5% do total, menos que os 25% planejados, porque a escrita em inglês foi cortada para caber no prazo da placa. O treino levou 2h22 (1.432 passos). Nenhum exemplo é de um tema de prova nem de uma estrutura dos conjuntos de prova.

**No `placar-v3` (desenvolvimento), por idioma e tipo de história**, acerto do modelo final e, entre parênteses, da base sem treino:

| História | Português | Inglês | Espanhol (idioma nunca treinado) |
|---|---|---|---|
| Um fato por frase, 384 mundos | 100% (47%) | 98% (47%) | 98% (46%) |
| Prosa corrida, escrita pelo modelo reservado | 96% (39%), 113 mundos | 97% (35%), 116 mundos | não há |

Nota geral do modelo final nos 1.381 mundos: +0,97; da base, −0,09. Nos dois temas nunca vistos, 97 de 97 em português e 90 de 97 em inglês, um fato por frase.

**Nos 48 casos que simulam texto de pessoa** (ver a nota de protocolo abaixo):

| Quem respondeu | Nota | Acerto | Português (24) | Inglês (16) | Espanhol (8) |
|---|---|---|---|---|---|
| "Ajusta tudo" | −1,00 | 0% | 0% | 0% | 0% |
| "Ajusta nada" | −0,75 | 12% | 12% | 12% | 12% |
| Base sem treino | +0,05 | 52% | 50% | 56% | 50% |
| Modelo supervisionado final | +0,36 | 67% | 75% | 56% | 62% |
| Modelo aberto de 27B, com raciocínio | +0,92 | 96% | 100% | 94% | 88% |

"Ajusta tudo" erra os 48: todo caso tem uma coluna medida depois da intervenção, como na vida real. Os 16 erros do modelo final: 8 vezes deixou de fora um fator de confusão dito de forma indireta; 5 vezes afirmou um efeito em caso não identificável (nenhuma em português: acertou os 11 não identificáveis em português, e errou 2 de 6 em inglês e 3 de 4 em espanhol); 3 vezes se absteve sem precisar.

**O que isto diz.** Em mundos sintéticos, mesmo em prosa de outro modelo e em idioma nunca visto, o modelo pequeno está a 2 ou 3 pontos do teto. Em texto que imita gente, está a 29 pontos do modelo de 27B. A fronteira do projeto é essa: ler o que uma pessoa escreve. É exatamente onde o reforço (seção 33) tem o que ensinar, e é o que os dois braços vão tentar.

**Nota de protocolo.** A fila automática (seção 33) foi escrita antes do protocolo da seção 31 ficar fechado e incluiu os casos simulados nas medições de desenvolvimento do modelo supervisionado, da base e do modelo de 27B. Isso contraria o protocolo, que reservava os casos para a medição final. O que fica garantido: a escolha entre os braços do reforço segue a regra mecânica da seção 31 (nota na prosa do `placar-v3` em português, sem perder mais de 2 pontos em um fato por frase), e os braços não serão medidos nos casos antes dessa escolha. Nada foi nem será ajustado olhando os casos.

## O que foi feito em 18 de outubro

### 35. O fechamento da 0.1

**A decisão.** Depois de onze dias sem sessões, o André pediu uma avaliação honesta do estado do projeto. O diagnóstico do assistente: a tarefa é resolvida por um modelo aberto de 27B (100% nos mundos sintéticos, 96% nos casos tipo humano); o supervisionado chegou a 99% e esvaziou o reforço; o texto "humano" é simulado. A sugestão: fechar em dois ou três dias, sem mais treinos, e publicar modelo, GGUF, dados e código numa organização do COPPEAD no Hugging Face; não começar outro projeto grande de RLVR agora; se quiser uma linha nova, um piloto de uma semana com critério de morte. O André mandou fechar ("terminar tudo o que seja caminho crítico para postar uma primeira versão"). À tarde perguntou se o reforço faria sentido em tese; a resposta foi que sim, porque reforço só ensina onde o aluno erra às vezes, e no texto tipo humano o modelo erra um terço. Ele mandou rodar ("se a GPU estiver desocupada, rode o RLVR").

**O que rodou, em uma fila só, das 12h25 às 19h59.** Os testes do projeto (4.685 passam; a bateria exaustiva passa). As referências ingênuas na prova final. O braço C: reforço com a nota do verificador sobre 208 casos tipo humano (`cases/treino-simulados/`, 26 arquivos), partindo do supervisionado fundido, 8 respostas por caso, 2 casos por passo. O braço D: supervisionado sobre os mesmos 208 casos, 3 passadas. Medições de desenvolvimento dos dois nos 32 casos guardados (`pt-17`, `pt-18`, `en-11`, `en-12`) e no `placar-v3` inteiro. A escolha pela regra da emenda de 7 de outubro, feita por programa e gravada em `outputs/train/escolha-2026-10-18.json`. A prova final (`teste-v3`, aberta uma vez) para o supervisionado, a base, o vencedor e uma amostra de 1 em 10 do modelo de 27B. O vencedor nos 48 casos congelados. Dois consertos no caminho: o script de reforço não aceitava casos escritos no lugar de mundos gravados (dois detalhes de registro), e o script supervisionado não aceitava partir de um modelo fundido local; os dois foram testados em dois passos antes da fila.

**O braço C parou no passo 20**, pela trava de abstenção (16% de abstenções indevidas na janela), em 14 minutos. **Nos 32 casos guardados:** supervisionado +0,48 (23 acertos); C +0,56 (24); D +0,91 (30). **No `placar-v3`:** C não perdeu nada (100% em um fato por frase em português, 96% na prosa); D caiu para 95% e 94%. **Pela regra** (maior nota nos 32 casos sem perder mais de 2 pontos no `placar-v3`), D ficou de fora e C venceu o supervisionado por um caso.

**A prova final** (`teste-v3`: 505 mundos em cada idioma, oito temas, um fato por frase; e-mail e saúde nunca treinados; espanhol nunca treinado):

| Quem respondeu | Nota | Acerto (1.515) | pt | en | es | Dois temas nunca vistos (381) |
|---|---|---|---|---|---|---|
| "Ajusta tudo" | −0,66 | 17% | 17% | 17% | 17% | 18% |
| "Ajusta nada" | −0,95 | 2% | 2% | 2% | 2% | 2% |
| Base sem treino | −0,05 | 47% | 46% | 46% | 47% | 47% |
| Supervisionado | +0,98 | 99% | 100% | 98% | 98% | 96% |
| **Supervisionado + reforço (publicado)** | +0,98 | 99% | 100% | 99% | 98% | 96% |
| Modelo aberto de 27B com raciocínio, 152 mundos | +0,99 | 99% | 100% | 100% | 98% | 100% (37) |

Nos mundos não identificáveis, o supervisionado e o publicado acertam 100%; a base, 4%. **Nos 48 casos congelados:** supervisionado +0,36 (67%: 75% pt, 56% en, 62% es); publicado +0,41 (69%: 75% pt, 62% en, 62% es); modelo de 27B +0,92 (96%). O reforço consertou um caso em inglês.

**O que isto diz.** O modelo pequeno empata com o de 27B nos mundos sintéticos, em idioma e temas que nunca viu, e fica 27 pontos abaixo dele em texto que imita gente. O reforço, que é a tese do projeto, mudou um caso em 32 e um em 48, e parou cedo pela trava. O braço D mostrou que 208 casos ensinam muito sobre esse texto (94% nos 32 guardados), ao custo de 5 pontos nos mundos sintéticos: o próximo passo natural é um treino supervisionado que misture os dois tipos de história, não mais reforço com este sinal. Fica registrado para a 0.2.

**Nota de protocolo.** A prova final foi aberta uma vez, para todos os respondedores da tabela na mesma rodada. O braço C só foi medido nos 48 casos depois de escolhido pela regra; o supervisionado, a base e as referências já tinham sido medidos neles em 7 de outubro (seção 34). A rodada das referências ingênuas foi interrompida e retomada com mais trabalhadores, sem efeito nos registros.

**O pacote de publicação.** Modelo fundido (base + adaptador supervisionado + adaptador do reforço), os dois adaptadores, GGUF em Q4_K_M (2,5 GB) e Q8_0 (4,3 GB) com Modelfile para o Ollama, cartão do modelo, cartão dos dados e cartão do GGUF (`docs/cards/`, em inglês com abertura em português), licença Apache 2.0 no repositório, o script de envio (`scripts/publish_hf.py`, que lista tudo sem enviar até receber `--upload`), o script da conversão (`scripts/make_gguf.sh`) e o resumo por idioma (`scripts/summarise_runs.py`). Páginas regeneradas: casos, mundos, placar de desenvolvimento, placar da prova final e placar dos casos. O conjunto de dados a publicar tem cerca de 3,3 GB: os cinco conjuntos de mundos que valem, os casos, os exemplos de treino, todos os registros de resposta, as fichas e as páginas. Instalado nesta máquina: o llama.cpp em `~/.local/opt/llama.cpp`, só com o quantizador compilado. A versão Q4_K_M, servida pelo Ollama, respondeu 35 mundos do `placar-v3` (1 em 40, três idiomas, um fato por frase e prosa) com o mesmo desfecho do modelo completo, 35 acertos em 35. O ensaio de envio lista 17,4 GiB, sem nada faltando. O material de leitura foi refeito e copiado para o Drive às 20h05.

**Ficou de fora, de propósito:** o modelo de fronteira no placar (sem chave de API), o relatório técnico longo (os cartões cumprem o papel), os casos escritos por pessoas de verdade, e a instalação limpa em outra máquina.

## O que foi feito em 24 de outubro

### 36. A publicação no Hugging Face

**A organização.** O André criou a organização `coppead` no Hugging Face em 24 de outubro, a partir da sua conta `aladaf`, que ficou como administradora. O nome estava livre.

**O envio.** Feito com `scripts/publish_hf.py --org coppead --upload`, em duas tentativas. A primeira subiu o modelo fundido e o adaptador supervisionado e parou no adaptador do reforço: o PEFT grava dentro de cada adaptador um README automático, um formulário vazio, e no do reforço o campo `base_model` aponta para a pasta local do modelo supervisionado fundido, que o Hub recusa. Correção: o script deixou de enviar esses dois READMEs, o que já havia subido foi apagado do repositório, e o cartão do modelo ganhou um parágrafo que explica que o adaptador do reforço vai por cima do modelo supervisionado, não da base, com o código para carregar os dois. A segunda tentativa terminou sem erro; o modelo de 8,0 GB (7,5 GiB) não foi reenviado, porque o Hub reconhece o arquivo pelo conteúdo. Os registros estão em `outputs/publish/upload-2026-10-24.log` e `upload-2026-10-24-b.log`.

**O que está lá**, tudo privado:

| Repositório | Conteúdo | Arquivos | Tamanho |
|---|---|---|---|
| `coppead/causalista-4b` | modelo fundido, dois adaptadores, registros dos treinos e da escolha do braço, cartão, licença | 20 | 7,75 GiB |
| `coppead/causalista-4b-GGUF` | Q4_K_M, Q8_0, Modelfile para o Ollama, cartão, licença | 7 | 6,31 GiB |
| `coppead/causalista-worlds` (dados) | cinco conjuntos de mundos, casos, exemplos de treino, todas as respostas gravadas, fichas, configurações, cinco páginas, cartão, licença | 71.181 | 3,34 GiB |

Os três cartões no Hub foram comparados byte a byte com os arquivos de `docs/cards/` e são iguais. O código não está no Hugging Face: os cartões apontam para o GitHub, público desde a noite de 24 de outubro.

**A casa pública do código.** Na mesma tarde o André propôs um repositório público, organizado no padrão usual do ecossistema, e criou a organização `coppead` no GitHub (21h44). O assistente recomendou transferir `aladaf/causalista` para ela, em vez de recomeçar, porque o histórico de 22 commits é parte da procedência e foi varrido sem achar tokens, chaves ou arquivos de senha; o GitHub redireciona o endereço antigo. Acabamento feito, sem depender da decisão: `CITATION.cff` (válido pelo esquema 1.2.0), `CHANGELOG.md` com a 0.1.0, `CONTRIBUTING.md` (ambiente, testes, regras que não se negociam), o fluxo `.github/workflows/tests.yml` (bateria rápida a cada push, sem torch, com Graphviz; a exaustiva sob demanda), `pyproject.toml` na versão 0.1.0 com licença, palavras-chave e os links para o GitHub e o Hugging Face, e `.gitignore` com as pastas do editor e do linter. Os três cartões passaram a apontar para `github.com/coppead/causalista` e foram reenviados ao Hub. O fluxo foi ensaiado nesta máquina num ambiente só com as dependências de execução e teste (`uv sync --no-group train`): 4.683 testes passam, 134 são pulados por não haver torch, em 10 min 25 s. **Decisões que ficaram com o André:** transferir ou criar do zero; README da raiz em inglês; o que fazer com os trechos pessoais deste status (seção 35) antes de abrir.

**Revisão independente da estrutura (24 de outubro, à noite).** A pedido do André, uma instância separada do assistente, sem acesso às conclusões desta sessão, comparou o repositório com onze repositórios semelhantes (OLMo, OLMo-core, smollm, Qwen, Qwen3, gpt-neox, open-r1, simpleRL, Alpaca, PRIME, BERTimbau) e com os guias da PyPA, pyOpenSci, Scientific Python, uv, GitHub e Keep a Changelog. Veredito: **em grande parte sim**; a espinha dorsal (`src/` + `tests/` espelhados, `pyproject.toml` com hatchling, `uv.lock` e `.python-version` no git, licença, citação, changelog, contribuição, CI) está no padrão; nada grande, gerado ou secreto está rastreado (180 arquivos, 3,7 MB). Desvios apontados e **corrigidos em seguida**: actions atrasadas no fluxo de testes (agora `checkout@v7` e `setup-uv@v10`, `uv sync --locked`, `concurrency`, `permissions`, mais `.github/dependabot.yml`); versão em dois lugares (agora uma só, lida de `src/causalista/__init__.py`, e o pacote constrói como `causalista-0.1.0`); caminho do Google Drive do André no README, no arquivo de instruções do assistente e em `scripts/reading_pack.py` (virou placeholder); caminho local e endereço privado neste status (removidos); faltavam `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1, texto oficial) e `SECURITY.md` (criados); changelog no formato Keep a Changelog; BibTeX no README; `Issues` nos links do pacote; descrição e nove tópicos no repositório do GitHub. **Apontados e deixados como estão, por julgamento:** `ESPECIFICACAO.md` na raiz (é a fonte da verdade do projeto), dados em `theories/`, `cases/` e `configs/` na raiz (há precedente), cartões em `docs/cards/`, `default-groups` com torch, um job de lint (o ruff aponta 13 erros e 63 arquivos fora do formato; nasceria vermelho). **Resolvidos na mesma noite, depois das decisões do André:** README da raiz em inglês (o maior desvio visível: todos os onze comparadores publicam em inglês, inclusive times chineses e brasileiros), com `README.pt-BR.md` como tradução; trechos pessoais retirados da seção 35; repositório criado do zero na organização; etiqueta `v0.1.0` e Release; relato privado de vulnerabilidade ligado.

**Revisão independente dos repositórios no Hugging Face (24 de outubro, à noite).** Uma segunda instância, também sem as conclusões desta sessão, comparou os três repositórios com a documentação do Hub e com repositórios semelhantes (Qwen3-4B e seu GGUF, bartowski, unsloth, zephyr, smoltalk, open-llm-leaderboard), inspecionou o cabeçalho do GGUF e testou a carga do modelo e do conjunto em ambientes descartáveis. Veredito: modelo e GGUF **em grande parte** no padrão; conjunto de dados **parcialmente**. Achados certos (testados): o modelo só carrega no transformers 5 (no 4.57 o tokenizer falha e o `rope_theta` é lido errado, degradando a saída em silêncio); o Hub classificava o repositório como *adapter* do Qwen3-4B, não como *finetune*; o GGUF traz template de chat e tokenizer embutidos, então `ollama run hf.co/coppead/causalista-4b-GGUF` funciona, mas o Ollama liga o raciocínio por padrão e o cartão não dizia como desligar; no conjunto de dados, o visualizador e o `load_dataset` iam falhar ao abrir, porque a detecção automática escolhia `runs/casos-dev/` como partição "validation" e quebrava ao juntar arquivos de colunas diferentes; os links para o GitHub davam 404. **Corrigido em seguida, nos cartões e em arquivos pequenos:** `base_model_relation: finetune` e aviso "requer transformers ≥ 5" no cartão do modelo, mais seções de limitações, de computação e impacto ambiental, BibTeX e contato; `generation_config.json` determinístico (`do_sample: false`), como o cartão sempre disse; no GGUF, `base_model: coppead/causalista-4b` com `base_model_relation: quantized`, `quantized_by`, `pipeline_tag`, um arquivo `params` (temperatura 0, contexto 8.192) que o Ollama lê ao puxar direto do Hub, a instrução `--think=false`, e os links para o código e os dados; no conjunto, um bloco `configs` que faz o visualizador e o `load_dataset` mostrarem os 22.906 exemplos de treino, mais `task_categories`, `annotations_creators`, `language_creators`, a seção sobre dados pessoais (não há: tudo é sintético), BibTeX e contato. **Deixado para depois, por ser trabalho médio:** copiar os arquivos de tokenizer do Qwen3-4B e acrescentar `rope_theta` e `torch_dtype` ao `config.json` para o transformers 4.x (a revisora testou que funciona; esta sessão ainda não conferiu); reconverter o GGUF com nome legível (hoje o nome embutido é "Grpo C Sft Cases") e metadados de licença e base; tabelas parquet por conjunto para os mundos e as respostas gravadas; um Space estático para as páginas; renomear slugs com acento perdido. Nada disso quebra nada ao abrir.

**Gravado em 24 de outubro**, por peça, no ramo local `historico` (o histórico completo, que continua no repositório privado `aladaf/causalista`), e como um commit só no repositório público novo `coppead/causalista` (ver abaixo): o script de envio, os três cartões, o README em inglês e o `README.pt-BR.md`, `scripts/reading_pack.py`, `pyproject.toml`, `uv.lock`, `src/causalista/__init__.py`, `.gitignore`, os arquivos novos `CITATION.cff`, `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `.github/workflows/tests.yml` e `.github/dependabot.yml`, a seção 13 da especificação e este status.

**O repositório público e o primeiro fluxo.** O André escolheu criar o repositório do zero, e não transferir: `coppead/causalista` nasceu público às 22h18 com um commit só, "Causalista 0.1.0", a etiqueta `v0.1.0` e um Release com as notas do changelog e o pacote (`.whl` e `.tar.gz`); descrição, nove tópicos, página inicial apontando para o modelo no Hub e relato privado de vulnerabilidade ligado. A primeira rodada do fluxo de testes falhou em segundos: o `setup-uv` não publica etiqueta de versão maior a partir da v8, e `@v10` não resolvia. Correção: as duas actions fixadas pelo SHA da versão exata, com a versão em comentário, como a documentação do uv recomenda. A segunda rodada passou, em 16 minutos, sem torch e com Graphviz. Modelos de issue (problema ou resposta errada; ideia ou pergunta; link para o canal de segurança) e de pull request completam o perfil de comunidade do GitHub. No clone local, `main` acompanha o repositório público e o ramo `historico` guarda o histórico completo, que continua no repositório privado `aladaf/causalista` (ainda não enviado para lá: o André não pediu). Esse primeiro histórico público, de cinco commits, foi reescrito na madrugada de 25 (parágrafo das auditorias, abaixo).

**Referências ao assistente retiradas do repositório (24 de outubro, noite).** O André leu a cláusula dos termos de uso do serviço do assistente que proíbe treinar modelos de IA "concorrentes" e recusou a leitura de que um ajuste fino de um modelo de 4B, para uma decisão só, concorra com o serviço. Pediu que toda referência nominal ao assistente e ao seu fornecedor saísse da documentação e do código. Feito: a documentação passa a dizer "o assistente" (em português) e "a large language model" ou "an AI coding assistant" (em inglês); o fato de as fichas, os casos simulados e as revisões terem sido escritos por um modelo de linguagem continua dito em todos os cartões, porque é procedência dos dados; o rótulo de autor dos casos passou de um nome próprio para `ai`; o cliente da API desse fornecedor saiu do harness (fica o cliente compatível com a API da OpenAI, suficiente para a linha de fronteira que falta no placar); os links para as páginas privadas publicadas no serviço saíram deste status e do material de leitura; o arquivo de instruções do assistente saiu do repositório (continua na máquina, fora do git); e a pendência sobre os termos de uso foi encerrada por decisão dele. Os commits públicos anteriores a esta mudança traziam uma linha de coautoria com o nome do assistente, e a árvore da etiqueta `v0.1.0` ainda continha as referências; isso foi resolvido na madrugada de 25 com a reescrita do histórico público (parágrafo seguinte).

**Quatro auditorias independentes e o fechamento (noite de 24 para 25 de outubro).** O André pediu certeza, e quatro instâncias separadas, sem as conclusões desta sessão, auditaram: (1) um clone limpo do repositório público, com instalação, bateria completa (4.685 testes passam em 12 minutos), construção do pacote, começo rápido, perfil de comunidade (100%, contra 25% a 75% em seis repositórios comparáveis) e configurações do GitHub; (2) a consistência de toda a documentação, número a número, link a link e comando a comando, contra os registros primários (todas as tabelas de resultado batem com `outputs/runs/`); (3) a hospedagem no Hub, com integridade byte a byte (71.180 arquivos do conjunto, 19 do modelo, 6 do GGUF, todos iguais à fonte), carga do modelo baixado do Hub na GPU e comparação com as respostas gravadas em 11 mundos de três idiomas (texto idêntico, caractere por caractere), caminho PEFT dos dois adaptadores (idêntico), GGUF pelo Ollama (mesmos vereditos), `load_dataset` (22.906 linhas) e transformers 4.57 (falha como o cartão avisa); (4) a varredura de nomes em todos os arquivos, históricos, mensagens, pacotes do Release e cabeçalhos dos GGUF (zero ocorrências nos arquivos atuais; as que restavam estavam em histórico). **Achados corrigidos em seguida:** o começo rápido do README não baixava o modelo, porque o harness só chama o chat do Ollama (agora há `ollama pull` antes); `uv run` reinstalava o torch depois de `uv sync --no-group train`, pelos grupos padrão do projeto (os documentos passam a usar `uv run --no-sync`, com o motivo); `README.pt-BR.md` era o README antigo (agora tradução fiel do inglês); `scripts/README-treino.md` dizia que nenhum treino tinha rodado; o exemplo de código dos cartões chamava `parse_answer` sem o segundo argumento; as somas SHA-256 dos 48 casos congelados não batiam mais, porque a troca do rótulo de autor mudou os arquivos (somas refeitas, com a nota de que história, colunas, setas e resposta não mudaram, conferido linha a linha contra a etiqueta); `train_grpo.py --cases` com uma pasta em vez dos 26 arquivos no README; números e textos envelhecidos (prosa 1.943/1.149, modelo de 8,0 GB, tamanhos em GiB, 7 arquivos no GGUF, nove tópicos, célula da prosa em inglês no cartão, regras ingênuas medidas em 384 mundos, 27B em 153, duas abstenções indevidas na prova final, seções 28 e 29 trocadas, "GitHub segue privado", temas de teste, base, prosa e risco do reforço como pendências, nota na seção 9 da especificação); `make_gguf.sh` passou a apontar para o modelo publicado; caminhos absolutos nos `run.json` publicados viraram relativos; `summary.json` do `placar-v3` refeito para o 27B (153 mundos, não 57); o cartão do GGUF ganhou a instrução `--temp 0` para o llama.cpp, porque os arquivos trazem a amostragem do modelo-base gravada no cabeçalho (temperatura 0,6) e o llama.cpp a usa como padrão (o Ollama não é afetado). **Histórico público reescrito:** a etiqueta `v0.1.0`, os pacotes do Release e quatro mensagens de commit ainda carregavam o arquivo de instruções, as referências nominais e a linha de coautoria. Como o repositório tinha horas de vida, sem forks nem estrelas, o histórico de `main` foi reescrito em um commit só com a árvore final, a etiqueta e o Release foram refeitos sobre ele, e uma regra protege `main` contra apagamento e reescrita daqui em diante. No Hub, as revisões antigas dos cartões, casos e fichas ainda traziam os nomes: o histórico dos três repositórios foi achatado em um commit com a ferramenta do próprio Hub. Ligados no GitHub: varredura de segredos com proteção de push, atualizações de segurança do Dependabot (actions e `uv`); wiki e projects desligados. **Deixado para a 0.1.1:** regenerar os GGUF com amostragem gulosa e nome legível, compatibilidade com o transformers 4.x, matriz de Python no CI, rótulos do placar em inglês, assinatura de commits, tabelas parquet, Space das páginas.

**Segunda rodada de auditorias, com Stanford como régua (25 de outubro, manhã).** Depois de o André executar a reescrita do histórico público e o achatamento do histórico no Hub, ele pediu nova checagem "de acordo com as melhores práticas dos melhores pesquisadores de Stanford", para que o repositório fosse familiar a pesquisadores e praticantes do mundo todo. Três instâncias independentes: (1) o repositório do GitHub contra Alpaca, HELM, DSPy, Levanter, pyvene, pyreft, Stanza, OLMo, open-r1 e gpt-neox, as listas de verificação de código do NeurIPS/Papers with Code e de Pineau, os indicadores do Foundation Model Transparency Index e o perfil de comunidade do GitHub; (2) os três repositórios do Hub contra os cartões de Stanford (BioMedLM, Alpaca, stanfordnlp), os artigos *Model Cards for Model Reporting* e *Datasheets for Datasets*, os modelos de cartão do Hub e repositórios GGUF de referência; (3) um praticante estrangeiro, sem português, que leu o repositório a frio, seguiu o começo rápido, recomputou todos os números da tabela a partir dos registros (bateram, em um minuto) e tentou usar o modelo numa tabela própria. **Veredito das três: "quase"**: a substância (protocolo pré-registrado, registros públicos de cada resposta, procedência, não-alegações, somas de verificação, CI, perfil de comunidade em 100% contra 12% a 75% das referências) está acima das referências; faltava forma. **Feito em seguida:** `scripts/ask.py` e `causalista.harness.ask`, o comando para usar o modelo numa tabela própria (CSV, história, dicionário) com o estimador no fim, testado de ponta a ponta com o modelo local (identifica confundidor e mediador, efeito ajustado +0,127 contra diferença simples +0,200 numa tabela de brinquedo); comandos exatos para reproduzir cada linha da tabela de resultados e o treino publicado; política de idioma no topo do README e índices em inglês para `docs/`, `theories/`, `cases/`, `configs/` e `scripts/`; README em português refeito como tradução; blocos de identificação (autor, afiliação, versão, data, licença, contato), seções de uso pretendido e fora de escopo, frase de incerteza (um treino, ±0,5 ponto), tabela dos modelos usados e seção de versões nos cartões; tabela de campos dos registros e de correspondência entre as linhas da tabela e os arquivos `.jsonl`, glossário dos nomes internos e códigos dos temas no cartão dos dados; comandos completos do llama.cpp com raciocínio desligado, procedência da conversão (commit `5aeac37`) e formato do prompt no cartão do GGUF; `Modelfile` com tokens de parada e comentários em inglês; `merged_from.json` apontando para a revisão da base; `training/README.md` no repositório do modelo; placar do harness em inglês fora de locale português, progresso e caminho dos registros; aliases `rule:all`/`rule:none`; `roles_right` nulo quando não há papéis a conferir (resumos de `casos-simulados` e `casos-dev` refeitos); `requires-python <3.14`; Dependabot agrupado e sem a pilha de treino; wheel/sdist sem ruído; titular na licença; regra em `main` com o fluxo de testes obrigatório; data de lançamento 2026-10-25 no CHANGELOG e na citação, com nota sobre a reescrita do histórico; cerca de sessenta frases de inglês reescritas. **Dependem do André:** abrir os três repositórios do Hub (as três auditorias apontam isto como a única lacuna crítica: badges, começo rápido e `hf download` morrem em 401 para quem não é membro); repetir o achatamento do histórico no Hub depois destes reenvios, se quiser um commit só; preencher o perfil da organização `coppead` no GitHub (nome, descrição, URL, local, e-mail); decidir se um e-mail institucional entra no README e nos cartões; DOI no Zenodo e PyPI, se quiser. **Para a 0.1.1:** GGUF reconvertidos com nome e metadados próprios, compatibilidade com o transformers 4.x, tabelas parquet, Space das páginas, matriz de Python, assinatura de commits, intervalos de confiança por célula, notebook de demonstração.

## O que falta

**Depende do André**

1. Abrir os três repositórios do Hugging Face ao público, na ordem: conjunto de dados, modelo, GGUF (o cartão do modelo aponta para o conjunto). Hoje só os membros da organização os veem. Quando ele disser, é um comando.
2. Preencher o perfil da organização `coppead` no GitHub (nome, descrição, URL da escola, local, e-mail): quem chega por `github.com/coppead` hoje não vê que é a COPPEAD.
3. Decidir se um e-mail institucional entra no README, no código de conduta e nos cartões como contato; hoje o contato é só pelas issues.
4. Repetir o achatamento do histórico nos três repositórios do Hub depois do reenvio dos cartões de 25 de outubro, se quiser manter um commit só (é um comando que o assistente não pode executar sozinho).
5. Fornecer uma chave de API de um modelo de fronteira, se quiser a linha que falta no placar.

**Trabalho de máquina, depois disso**

1. Abrir os repositórios do Hub e conferir as páginas abertas (visualizador do conjunto, árvore do modelo com a relação *finetune*, snippet do Ollama); rodar uma vez o começo rápido do README pelo `hf.co`, o único caminho que não pôde ser testado em privado.
2. Os itens médios da revisão do Hub: compatibilidade com o transformers 4.x, reconversão do GGUF, tabelas parquet, Space das páginas.

## Quem decidiu o quê

| Decisão | Situação |
|---|---|
| Organização do repositório (código em inglês, textos em português) | aprovada pelo André |
| Os 24 casos de resposta conhecida | aprovados pelo André ("concordo com todos") |
| O modelo decide, o runner calcula; treino em dois passos | escrito na especificação pelo assistente; o André mandou começar a implementação com ela |
| Ficha de teoria do telecom | rascunho do assistente; aprovada pelo André em 4 de outubro ("ok") |
| Os 20 mundos do caderno | lidos pelo André em 4 de outubro ("ok"); nenhum apontado como estranho |
| Faixas de desenho dos mundos (quantas variáveis, força dos efeitos, tamanho das tabelas) | proposta do assistente; confirmada pelo André em 4 de outubro |
| Pesos da nota (−1 e −0,5) | proposta do assistente; confirmada pelo André em 4 de outubro |
| Oito temas e dois idiomas | proposta do assistente; confirmada pelo André em 4 de outubro |
| Os cinco casos da fase 0 | o André pediu, em 4 de outubro, que o assistente os escrevesse; aprovados por delegação em 5 de outubro, depois de revisão independente |
| Teoria e referências dos sete temas novos; as sete fichas | proposta do assistente; aprovadas por delegação em 5 de outubro, depois de revisão independente |
| Temas reservados para teste (e-mail e saúde) | proposta do assistente; aprovada pelo André em 6 de outubro |
| Idiomas de treino e de teste | treino em português e inglês, espanhol como prova; aprovado pelo André em 6 de outubro |
| Resposta inválida vale −1; instruções em inglês | escolha do assistente ao escrever a tarefa; aceita de fato: a 0.1 foi publicada com ela |
| Estimador duplamente robusto | escolhido pela medição |
| Não validar um a um o que o assistente escreve; frases escritas pelo assistente nos dados de treino | decisão do André em 5 de outubro |
| Ausências inofensivas, limite de duas ausências por mundo e ordem sorteada das frases | mudanças do assistente no desenho dos mundos, em 5 de outubro, dentro da delegação; podem ser desfeitas |
| Base (Qwen3-4B) | escolha do assistente pelo empate no placar e pela praticidade; aprovada pelo André em 6 de outubro |
| Tamanho do treino, proporção de prosa, desenho da fase 5 e trava de 10% de abstenção | proposta do assistente; aprovada pelo André em 6 de outubro |
| Casos escritos por pessoas | adiados pelo André em 6 de outubro; no lugar, texto humano simulado pelo assistente |

## O que depende do André

A lista está na seção "O que falta". Além dela, para depois da publicação: escolher se a 0.2 existe e com que desenho (seção 35, "O que isto diz"), ou se a próxima linha é outra (a proposta de 18 de outubro, "o mercado como simulador", está registrada na conversa e na memória do assistente, não neste repositório).

## Próximos passos

1. **Abrir a 0.1 ao público no Hugging Face**, quando o André autorizar; o GitHub já está público em `coppead/causalista`.
2. **Depois, se houver 0.2:** treino supervisionado que misture mundos sintéticos e casos tipo humano (o braço D mostrou o ganho e o custo); casos escritos por pessoas de verdade; o modelo de fronteira no placar.

## Onde está cada coisa

**Repositório.** https://github.com/coppead/causalista, público, na organização criada pelo André em 24 de outubro; os cartões no Hugging Face apontam para ele. O repositório privado `aladaf/causalista` guarda o histórico completo de desenvolvimento até o fechamento.

**Hugging Face** (organização `coppead`; privados até o André abrir): o modelo em https://huggingface.co/coppead/causalista-4b, o GGUF em https://huggingface.co/coppead/causalista-4b-GGUF e os dados em https://huggingface.co/datasets/coppead/causalista-worlds.

| Pasta | Conteúdo |
|---|---|
| `ESPECIFICACAO.md` | o que estamos construindo, em que ordem, e o registro dos portões |
| `src/causalista/verifier/` | o verificador e os casos de livro-texto |
| `src/causalista/worlds/` | a fábrica de mundos |
| `src/causalista/estimator/` | o estimador |
| `src/causalista/task/` | a tarefa: o que o modelo vê, o formato da resposta, a nota e a resposta ideal |
| `src/causalista/harness/` | roda modelos sobre mundos gravados e grava cada resposta |
| `src/causalista/viz/` | as páginas: casos, mundos e placar |
| `theories/` | as fichas de teoria dos oito temas; em `theories/i18n/`, as traduções |
| `cases/` | os casos escritos, com as setas e a resposta conferida pelo verificador |
| `configs/` | as bases candidatas, a divisão entre treino e teste e os mundos-vitrine |
| `docs/` | este status, os trabalhos vizinhos, os pontos das fichas para aprovar e o modelo dos casos |
| `scripts/` | material de leitura, medição do estimador, geração de mundos e de exemplos de treino, rodada de modelos, tradução das fichas e treino |
| `tests/` | os testes |
| `outputs/` | tudo o que é gerado (mundos, registros, páginas, medições); fora do git |

**Pasta de leitura.** Gerada em `outputs/leitura` e copiada para o Drive, em `COPPEAD/Projetos/causalista`, quando ele está montado: o guia, os cadernos de casos e de mundos, a especificação, as fichas de teoria, os casos escritos, os pontos das fichas para aprovar, os trabalhos vizinhos, este status e as páginas interativas. São cópias; a versão que vale é a do repositório.

**Páginas interativas.** Geradas em `outputs/viz/` e publicadas na pasta `pages/` do conjunto de dados no Hugging Face. As cópias publicadas como páginas privadas (casos, mundos, placar e relatório executivo) são compartilhadas pelo André quando ele quer.

## Pontos de atenção

- **Aprovação por delegação.** Sete fichas e os cinco casos não foram lidos pelo André: passaram por uma revisão independente feita por outras instâncias do assistente. É uma segunda leitura de verdade, mas do mesmo modelo; erros que o assistente comete de forma sistemática podem ter passado pelas duas.
- **Conjuntos antigos.** `placar-base` e `teste-final` foram gerados antes das correções de 5 de outubro e ficam só como histórico. Os conjuntos atuais são `placar-v3` (desenvolvimento) e `teste-v3` (prova final, aberta uma vez em 18 de outubro).
- **O teste atual é fácil para modelos grandes.** Um modelo aberto de 27B acertou todos os mundos das amostras em que foi medido (153 no desenvolvimento, 152 na prova final). O conjunto mede bem a distância entre um modelo pequeno e um grande, mas não diz nada sobre modelos grandes entre si, e a frase "o julgamento que nenhuma biblioteca faz" precisa de cuidado: um modelo grande já faz esse julgamento quando a história é contada um fato por frase. A prosa corrida, do jeito que é gerada hoje, não é mais difícil que a narrativa de um fato por frase (medido nas três bases). O teste mais difícil que o plano prevê são os casos escritos por pessoas.
- **A escolha da base.** As duas Qwen empatavam no placar; a Qwen3-4B foi escolhida em 6 de outubro pela praticidade no treino (seção 30).
- **A narrativa em prosa é lenta de produzir.** Cerca de 30 a 50 segundos por mundo, com um terço das histórias recusado. Dá para os conjuntos de teste e para alguns milhares de mundos de treino. No treino final a prosa ficou em 13,5% dos exemplos (3.092 de 22.906), decisão de 6 de outubro.
- **Procedência das frases.** As frases das fichas foram escritas pelo assistente e entram nas histórias de treino, por decisão do André (seção 23).
- **Traduções feitas por modelo aberto.** A conferência automática pegou parte dos erros e deu muitos alarmes falsos; a leitura por inteiro achou erros que ela deixou passar. Para outros idiomas, que o assistente e o André leem pior, a conferência automática sozinha não basta.
- **Cobertura nas tabelas maiores.** Com 50 mil linhas, o intervalo conteve o efeito verdadeiro em 94,6% dos mundos na medição de 5 de outubro (94,1% na de 4 de outubro), um pouco abaixo dos 95% esperados. Está dentro da margem de erro, mas a tendência de queda com o tamanho da tabela merece ser acompanhada.
- **Tamanho dos efeitos.** Em alguns mundos o efeito é grande para a vida real (uma campanha de e-mail que vale 15 pontos percentuais). Vem das faixas da fábrica de mundos, que são decisão do André.
- **Risco do reforço.** O colapso para a recusa, descrito na literatura, foi tratado com a trava de 10% de abstenção indevida; ela parou dois dos treinos de 7 de outubro e o braço publicado de 18 de outubro (seções 33 e 35).
- **Números de terceiros.** Os números citados da literatura vêm de resumos e de uma busca automática. Antes de usar em artigo, é preciso abrir as fontes.
- **O segundo servidor de modelos foi encerrado.** Para um teste, o assistente tinha iniciado um segundo Ollama na porta 11435. Ele ficou parado, sem modelo carregado, até 5 de outubro, quando o André autorizou e o assistente o encerrou. O servidor principal (porta 11434) não foi tocado.
