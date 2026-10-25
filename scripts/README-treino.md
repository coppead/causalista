# Treino: ambiente, bases e comandos

Este arquivo descreve o ambiente de treino: o que foi instalado, as três bases candidatas, como testar se tudo funciona e como rodar o treino. Foi preparado e conferido em 2026-10-04, antes do primeiro treino; os treinos feitos depois (supervisionado e reforço, com números e decisões) estão em `docs/status.md` e nos cartões em `docs/cards/`. A seção "O que não foi verificado" registra o estado daquele dia.

## O que o modelo aprende

A tarefa é uma só. O modelo lê a história de como os dados foram gerados e o dicionário da tabela, e responde por quais colunas ajustar para medir o efeito da intervenção sobre o resultado, ou diz que o efeito é não identificável. O treino supervisionado mostra ao modelo a pergunta e a resposta ideal, e cobra só a resposta.

## O que foi instalado

As bibliotecas de treino entraram como um grupo de dependências chamado `train` no `pyproject.toml`. O grupo é instalado por padrão junto com o `dev` (`[tool.uv] default-groups`), então `uv sync` e `uv run` deixam tudo no mesmo ambiente (`.venv`). As dependências do pacote publicado (`[project] dependencies`) não mudaram: o runner continua sem precisar do torch. As versões de numpy (2.5.3), pandas (3.0.6), scikit-learn (1.9.1) e doubleml (0.11.4) ficaram como estavam.

| Biblioteca | Versão instalada |
|---|---|
| torch | 2.12.1+cu126 |
| transformers | 5.5.0 |
| peft | 0.21.2 |
| trl | 0.24.0 |
| unsloth | 2026.9.14 |
| unsloth-zoo | 2026.9.9 |
| datasets | 4.3.0 |
| accelerate | 1.15.0 |
| bitsandbytes | 0.50.2 |
| xformers | 0.0.35 |
| torchvision | 0.27.1+cu126 |

Dois pontos a saber:

- **Quem limita as versões é o Unsloth.** A versão atual dele exige torch abaixo de 2.13, transformers até 5.5.0, trl até 0.24.0 e datasets abaixo de 4.4. Por isso o ambiente não tem as últimas versões dessas bibliotecas (hoje: torch 2.14, transformers 5.18, trl 1.14).
- **O torch vem do índice do PyTorch, na versão para CUDA 12.6.** O torch do PyPI é compilado para CUDA 13, que pede um driver de vídeo mais novo do que o desta máquina (576.80, que vai até CUDA 12.9). O `pyproject.toml` aponta o torch e o torchvision para `https://download.pytorch.org/whl/cu126`. O torch do PyPI não chegou a ser testado aqui: a escolha veio do que o pacote e o driver declaram. Se o driver for atualizado, isso pode ser revisto.

Conferido depois de instalar: o torch enxerga a RTX 4090, e `uv run pytest tests/task tests/estimator -q` passa.

## As três bases

A especificação (seção 6) nomeia três bases, todas com licença Apache 2.0. As três existem no Hugging Face com esses nomes, nas organizações oficiais, são públicas e foram baixadas para o cache padrão (`~/.cache/huggingface/hub`). A licença foi conferida nos metadados de cada repositório. O registro completo está em `configs/bases.yaml`.

| Nome na especificação | Repositório | Revisão (commit) | Licença | Parâmetros |
|---|---|---|---|---|
| Qwen3.5-4B | `Qwen/Qwen3.5-4B` | `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` | Apache 2.0 | 4,66 bilhões no repositório; 4,21 bilhões na parte de texto |
| IBM Granite 4.2 de 3B | `ibm-granite/granite-4.2-3b` | `e459acceac81e5fe67c07d9cfc72329a332e7eb1` | Apache 2.0 | 3,66 bilhões |
| Qwen3-4B | `Qwen/Qwen3-4B` | `1cfa9a7208912126459214e8b04321603b3df60c` | Apache 2.0 | 4,02 bilhões |

O que cada uma tem de particular:

- **Qwen3.5-4B** também lê imagem e vídeo. Aqui só a parte de texto é carregada. É um modelo híbrido: de suas 32 camadas, 24 usam um tipo de atenção diferente (atenção linear) e só 8 usam a atenção comum. O LoRA com os alvos de costume alcança a parte de atenção só dessas 8 camadas (e a outra parte, a rede densa, das 32). Em princípio dá para incluir as outras 24 com `--target-modules`, somando os nomes das projeções dessas camadas (estão em `configs/bases.yaml`). Isso não foi testado, e se vale a pena é uma decisão a tomar com o placar na mão.
- **Granite 4.2** é só texto. O modelo de conversa dele sempre escreve um bloco de sistema, vazio quando não há mensagem de sistema.
- **Qwen3-4B** é a versão de abril de 2025, com os dois modos (com e sem raciocínio) no mesmo modelo. A Qwen publicou depois duas variantes separadas, `Qwen3-4B-Instruct-2507` e `Qwen3-4B-Thinking-2507`. São outros pesos e não foram baixadas.

Nas três, o raciocínio vem ligado por padrão e se desliga com `enable_thinking=False` no modelo de conversa. Nas três, a resposta termina com o mesmo marcador, `<|im_end|>`.

## Como rodar o teste de fumaça

O teste de fumaça não mede qualidade. Ele só confirma que as ferramentas conseguem carregar cada base, treinar um adaptador LoRA nela e gerar respostas com o adaptador.

```bash
uv run python scripts/smoke_train.py                         # as três bases
uv run python scripts/smoke_train.py --base Qwen/Qwen3-4B    # uma só
```

Para cada base ele faz 10 passos de treino com `scripts/train_sft.py` e depois gera, de uma vez, as respostas de 8 perguntas com o adaptador carregado. Os dados são 64 mundos do tema telecom (sementes de 90 000 em diante, que nenhum outro uso do projeto toca), com respostas que trazem só o veredito e o conjunto de ajuste. Tudo fica em `outputs/train/smoke/`, e a tabela em `summary.json`.

A placa de vídeo é dividida com outros trabalhos. Antes de cada etapa o teste espera até a placa ter 12 GiB livres por um minuto seguido (`--room`). Sem esse espaço quase nunca aparece um erro: o treino só fica dezenas de vezes mais lento e atrapalha os outros. A memória livre é perguntada ao driver (`nvidia-smi`). A conta do próprio torch, no WSL, não enxerga o que os outros programas ocupam: marcou 14,4 GiB livres quando o driver marcava 5,6.

### Resultado em 2026-10-04: incompleto

Enquanto o teste rodava, outros trabalhos ocupavam de 17 a 23 GB dos 24 GB da placa (um servidor Ollama, trocando de modelo). O teste rodou por inteiro em uma base, pela metade em outra, e não rodou na terceira. **Nenhum dos tempos abaixo vale como medida**: foram tomados com a placa cheia.

| | Qwen3.5-4B | Granite 4.2 (3B) | Qwen3-4B |
|---|---|---|---|
| O Unsloth carrega a base e põe o LoRA | sim (conferido à parte, fora do teste) | sim | sim |
| 10 passos de treino | **não rodou** | sim; a perda caiu de 0,50 para 0,02 | sim; a perda caiu de 1,24 para 0,03 |
| Pico de memória da placa no treino (lote de 2) | não medido | 8,28 GiB | 8,37 GiB |
| Segundos por passo | não medido | 12,2 (placa cheia; não vale) | 2,2 (placa cheia; pode estar inflado) |
| Camadas com LoRA | 128 (ver a observação da base) | 280 | 252 |
| Geração de 8 perguntas com o adaptador | **não rodou** | **não rodou** | sim; o adaptador encaixou, e a resposta saiu no formato treinado |
| Tokens por segundo na geração | não medido | não medido | 0,7 (placa cheia; não vale) |
| Pico de memória da placa na geração (lote de 8) | não medido | não medido | 10,36 GiB |
| Mesma resposta sozinha e dentro do lote | não medido | não medido | sim, idêntica |
| Tokens da pergunta: média e máximo | 963 e 1199 | 1025 e 1287 | 992 e 1257 |

Os tamanhos da pergunta foram medidos nas três bases, sem a placa, nos 64 mundos do teste (tema telecom, em português, já com o modelo de conversa e o raciocínio desligado).

O que aconteceu com o Qwen3.5-4B: a etapa de treino começou quando a placa estava cheia e parou antes de carregar qualquer coisa, com o erro "CUDA-capable device(s) is/are busy or unavailable". É um erro da placa ocupada, e não diz nada sobre a base. À parte, antes do teste, o Unsloth carregou o Qwen3.5-4B (inteiro e só a parte de texto) e pôs o LoRA sem problema.

Para completar, com a placa livre:

```bash
uv run python scripts/smoke_train.py     # as três bases, para ter os tempos limpos
```

ou só o que faltou:

```bash
uv run python scripts/smoke_train.py --base Qwen/Qwen3.5-4B --base ibm-granite/granite-4.2-3b
```

O `summary.json` traz, para cada etapa, a memória livre da placa no fim (`..._gpu_free_gib_at_end`), medida com o modelo ainda carregado. Perto de zero quer dizer que a placa estava cheia e que os tempos daquela etapa não valem.

## O treino de verdade

Os dados são um arquivo JSONL, uma linha por mundo:

```json
{"world": "...", "theory": "...", "language": "pt", "level": 1, "prompt": "...", "answer": "..."}
```

`prompt` é a mensagem do usuário (o texto de `causalista.task.build_prompt`) e `answer` é a resposta ideal, um texto JSON sem raciocínio.

```bash
uv run python scripts/train_sft.py \
    --data outputs/train/data/sft.jsonl \
    --base Qwen/Qwen3.5-4B \
    --rank 16 --alpha 16 --lr 2e-4 \
    --epochs 1 --max-seq-length 4096 \
    --batch-size 4 --grad-accum 4 \
    --seed 0 --save-steps 200 \
    --run-name sft-qwen3.5-4b-v1
```

Os valores acima eram os padrões do script em 4 de outubro, antes de qualquer treino; os valores do treino final estão em `docs/status.md` (seção 35) e em `training/sft/run.json` no repositório do modelo no Hugging Face. Outros argumentos: `--max-steps` (para por número de passos em vez de épocas), `--target-modules`, `--dropout`, `--warmup`, `--weight-decay`, `--scheduler`, `--load-in-4bit`, `--out`, `--resume` (continua do último ponto salvo) e `--revision`.

O que o script grava na pasta da rodada (`outputs/train/<nome da rodada>/`):

- `run.json`: todos os ajustes, as versões das bibliotecas, o repositório e a revisão da base, o resumo dos dados (quantos exemplos, tamanhos em tokens, quantos ficaram de fora por serem longos demais) e, no fim, o resultado (passos, perda, segundos por passo, pico de memória da placa);
- `checkpoint-<passo>/`: pontos do treino, no intervalo de `--save-steps`;
- `adapter/`: o adaptador LoRA final;
- `log.json`: a perda ao longo dos passos.

Para avaliar um adaptador com o harness:

```python
from causalista.harness.hf import HFModel
modelo = HFModel("Qwen/Qwen3.5-4B", adapter="outputs/train/sft-qwen3.5-4b-v1/adapter")
```

E para medir uma base sem ajuste fino, pelo script do placar:

```bash
uv run python scripts/run_models.py --worlds placar-base --model hf:Qwen/Qwen3.5-4B:nothink
```

O `scripts/run_models.py` carrega um adaptador com `--adapter <pasta>`, que vale para todos os modelos `hf:` da chamada:

```bash
uv run python scripts/run_models.py --worlds placar-v3 --model hf:Qwen/Qwen3-4B:nothink \
    --adapter outputs/train/sft-pt-v2-qwen3-4b/adapter
```

### Cuidados que o script já toma

- **A base é a oficial, na revisão registrada.** O Unsloth, por conta própria, troca alguns repositórios por cópias dele (ao pedir `Qwen/Qwen3-4B`, carregou `unsloth/Qwen3-4B`). O script pede o nome exato, usa a revisão de `configs/bases.yaml` e para se a base carregada não for a pedida.
- **Treino e avaliação usam a mesma pergunta.** O texto que o modelo recebe é montado pela mesma função nos dois lados (`causalista.harness.hf.chat_prompt`), com o raciocínio desligado.
- **A perda cai só sobre a resposta.** Antes de treinar, o script confere, no primeiro exemplo já pronto para o treino, que a parte cobrada é a resposta e mais nada.
- **Exemplo longo demais fica de fora, não é cortado.** Cortar tiraria o fim da resposta. A contagem dos que ficaram de fora vai para o `run.json`.
- **O adaptador é conferido ao carregar.** O `HFModel` recusa um adaptador treinado em outra base, ou cujos pesos não encaixam no modelo. Sem isso a biblioteca só avisa, e o modelo responde como a base pura.

## O que foi conferido nas bibliotecas

Tudo abaixo foi lido no código instalado em `.venv`, nas versões da tabela, e não de memória.

**Unsloth: carregar a base e pôr o LoRA.** O caminho continua sendo `FastLanguageModel.from_pretrained(...)` seguido de `FastLanguageModel.get_peft_model(...)`. Para o Qwen3-4B ele usa um caminho próprio; para o Granite e o Qwen3.5 ele repassa para `FastModel`. Três argumentos importam aqui: `load_in_4bit=False` (o padrão é 4 bits; com `False` ele treina em 16 bits), `use_exact_model_name=True` (sem isso ele troca o repositório) e `text_only=True` (carrega o Qwen3.5 sem a parte de imagem; nas outras duas bases não muda nada). O Unsloth grava código gerado numa pasta `unsloth_compiled_cache` no diretório atual; o script manda isso para `outputs/train/.unsloth_compiled_cache`.

**TRL: `SFTTrainer` e `SFTConfig`.** Na 0.24.0 o tokenizador entra como `processing_class` (não mais `tokenizer`), e o tamanho máximo é `max_length` em `SFTConfig` (não mais `max_seq_length`). O aquecimento é `warmup_steps`, que aceita fração; `warmup_ratio` está marcado para sair. O `SFTTrainer` aceita dados já transformados em tokens (coluna `input_ids`); nesse caso não refaz a montagem do texto, só corta o que passar de `max_length`.

**Treinar só na resposta.** Há quatro caminhos, e o script usa o último:

1. `assistant_only_loss=True` no `SFTConfig`. **Não funciona com estas bases**: depende de uma marca (`{% generation %}`) que nenhum dos três modelos de conversa tem. Conferido: zero tokens marcados nas três.
2. Dados em duas colunas, `prompt` e `completion`. O TRL cobra só a segunda, e aceita uma coluna `chat_template_kwargs` para desligar o raciocínio. Conferido, sem treinar, que nas três bases a pergunta montada assim é o começo exato da conversa completa.
3. `train_on_responses_only` do Unsloth, que procura no texto os marcadores de quem fala. Lido, não rodado.
4. Entregar ao TRL os tokens prontos, com uma coluna `completion_mask` que vale 1 na resposta, e `completion_only_loss=True`. É o que o `train_sft.py` faz, porque assim a pergunta do treino é, token por token, a mesma da avaliação.

**Raciocínio ligado e desligado.** As três bases aceitam `enable_thinking` no modelo de conversa. O que muda é o começo da resposta:

| Base | Desligado: a pergunta termina com | Ligado: a pergunta termina com |
|---|---|---|
| Qwen3.5-4B | `<think>\n\n</think>\n\n` | `<think>\n` |
| Granite 4.2 | `<think></think>` | `<think>\n` |
| Qwen3-4B | `<think>\n\n</think>\n\n` | nada (o modelo abre o raciocínio sozinho) |

O `HFModel` tem a opção `thinking` (desligado por padrão) e o rótulo diz o modo usado, como no `OllamaModel`: "(sem raciocínio)" ou "(com raciocínio)". Uma base sem essa chave fica sem sufixo.

Um detalhe do Qwen3.5: o repositório não traz configuração de geração, e o fim de texto que a geração usa por padrão é `<|endoftext|>`, e não o `<|im_end|>` que encerra a resposta (conferido na configuração do modelo). Por isso o `HFModel` sempre passa à geração o marcador de fim do tokenizador, além do que o modelo declara.

**GRPO, para a fase 5 (notas de 4 de outubro; o script `train_grpo.py` foi escrito e rodado depois, ver `docs/status.md`).**

- As classes são `trl.GRPOTrainer` e `trl.GRPOConfig`. Existe também `trl.RLOOTrainer`, e variantes em `trl.experimental`.
- A recompensa entra em `reward_funcs`: uma função, ou uma lista delas (com pesos em `reward_weights`). A função recebe `prompts`, `completions`, `completion_ids`, `trainer_state` e, como argumentos extras, as outras colunas dos dados. Devolve uma lista de números. Isso serve ao projeto: uma coluna com o nome do mundo permite à função achar o gabarito e dar a nota da seção 5.
- Os dados precisam de uma coluna `prompt`.
- Padrões que não servem aqui e terão de ser mudados: `max_prompt_length=512` (as perguntas do telecom têm cerca de mil tokens, e o que passa do limite é cortado) e `max_completion_length=256`.
- Normalização da recompensa: `scale_rewards="group"` é o padrão (divide pelo desvio dentro do grupo de respostas da mesma pergunta). Há também `"batch"` e `"none"`. É este o ponto do risco descrito na seção 6 da especificação.
- Raciocínio: o `GRPOTrainer` monta a pergunta sem repassar `enable_thinking`, então as três bases gerariam com o raciocínio ligado. O remendo do Unsloth só repassa colunas de texto, e `enable_thinking` é verdadeiro ou falso. Para treinar sem raciocínio será preciso entregar a pergunta já montada como texto, ou outra saída a decidir na fase 5.
- O Unsloth altera o `GRPOTrainer` ao ser importado. O que está descrito acima é o código do TRL; o comportamento com o Unsloth por cima precisa ser conferido de novo quando a fase 5 começar.

## O que não foi verificado

- **O teste de fumaça do Qwen3.5-4B** (treino e geração) **e a geração do Granite 4.2**: não rodaram, pela placa ocupada. Os comandos estão acima.
- **Todos os tempos**: segundos por passo e tokens por segundo foram tomados com a placa cheia e precisam ser medidos de novo.
- **O `HFModel` com o Qwen3.5-4B e com o Granite 4.2 na placa.** Conferido só sem carregar pesos: a classe que o transformers monta para cada base e os nomes das camadas, que são os mesmos do adaptador treinado pelo Unsloth. Com o Qwen3-4B o `HFModel` rodou de ponta a ponta.
- **O `HFModel` com o raciocínio ligado**: a montagem da pergunta e o rótulo foram conferidos; a geração nesse modo não rodou em nenhuma base.
- Naquele dia, nenhum treino completo: os 10 passos do teste de fumaça mostravam que o treino roda e que a perda cai em dados de brinquedo. Os treinos completos vieram depois (5, 7 e 18 de outubro) e estão em `docs/status.md`.
- Os valores padrão do `train_sft.py` (posto do LoRA, taxa de aprendizado, tamanho do lote) não foram comparados com alternativas.
- O caminho de 4 bits (`--load-in-4bit`), `--resume` e `--target-modules` com as camadas de atenção linear do Qwen3.5 não foram rodados.

## Problemas conhecidos do ambiente

- Com a placa escondida (`CUDA_VISIBLE_DEVICES` vazio), importar `peft`, `bitsandbytes` ou `torchao` derruba o Python neste ambiente ("double free"). Não afeta os testes do projeto nem o runner, que não usam essas bibliotecas.
- Ao carregar, o `torchao` avisa que não conseguiu abrir duas bibliotecas suas ("Failed to load ..."). O treino roda mesmo assim.
- Ao carregar o Qwen3.5, o transformers avisa que "o caminho rápido não está disponível". Lido no código: o aviso aparece quando falta qualquer uma de duas bibliotecas, e aqui falta a `causal-conv1d`. A outra (`flash-linear-attention`) o Unsloth traz embutida, e com ele importado o transformers a dá como disponível. O `HFModel` não importa o Unsloth, então na avaliação o Qwen3.5 deve usar o caminho lento nas camadas de atenção linear. Nada disso foi medido: a velocidade do Qwen3.5, no treino e na geração, está por medir.
