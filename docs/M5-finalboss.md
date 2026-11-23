# MODELO M5 — DEFINITIVO (v3.1) — M5-finalboss

## 0. META E COMO LER
- id: M5-DEF v3.1
- arquivo: docs/M5-finalboss.md
- nome: Híbrido com Portões + Fase 0 mínima + motor multicanal completo
- projeto: Ecosystem GTA — começa pelo canal principal (vídeos longos sobre GTA VI)
- status: MODELO DEFINITIVO e modelo padrão para a construção no computador novo
- base: M5-DEF v3.0 + mudanças do Apêndice A.5. A v1.0, a v2.0 e a v3.0 ficam guardadas, intactas
- data: 2026-11-23
- autor: Claude (Anthropic), a pedido de Pedro (administrador)
- governança do documento:
  - SOMENTE LEITURA. Serve de consulta quando o projeto se perder no caminho
  - nenhuma IA altera este documento
  - mudança só com ordem explícita de Pedro → cria-se nova versão; esta fica intacta e guardada
- como ler:
  - o Claude Code lê as seções 0 a 5 antes de qualquer ação; as demais, quando a tarefa pedir
  - cada regra está escrita em um lugar só; os outros lugares citam o código dela (ex.: F06)
  - ordem de autoridade: este documento > CLAUDE.md da raiz > CLAUDE.md da pasta (→ 6.2). A ficha do canal (→ 3) guarda valores operacionais, não regras

## 1. PROPÓSITO E ESCOPO
- objetivo: produzir vídeos editados por IA, com qualidade que agrade Pedro. Pedro posta
- em suma: o motor recebe um roteiro travado (→ 3) e entrega um vídeo
- escopo: um motor único, vários canais. Começa pelo canal principal. Novos canais, formatos (→ 3) e fornecedores entram por decisão de Pedro
- prioridade de cada canal nos primeiros meses: identidade visual forte
- premissas definidas por Pedro:
  - direitos autorais desconsiderados nesta análise (decisão do administrador)
  - edição com cortes frequentes; uso de material de terceiros e de fotos, áudios e fontes simples da web
  - uso máximo de ferramentas gratuitas Python/JS para captar e gerar material
  - postagem exclusivamente manual por Pedro; a IA termina na entrega do vídeo
  - roteiro criado por Pedro + Claude
- fora do escopo: Hermes Agent (adiado até Pedro dominar os freios do modelo, → 5), postagem automática, julgamento de qualidade pelo motor, decisões de crescimento

## 2. PRINCÍPIOS
- R1 — economia: não gastar energia (tokens, créditos, tempo de Pedro, tempo de máquina) sem necessidade
- R2 — fidelidade ao documento: o motor é construído como este documento descreve e mantido funcionando bem. Depois de pronto, as mudanças são mínimas e partem de Pedro; o Claude não propõe melhorias por conta própria. Fica de fora só o problema grave: aí avisar Pedro é obrigatório
  - problema grave: algo que quebra o funcionamento, perde dados, gasta créditos ou limite sem controle, ou expõe chaves
- R3 — só o necessário: entregar só o que foi pedido
- princípio de julgamento: o M5 não avalia se um vídeo é bom. Quem julga é Pedro, pela curadoria do canal. A evidência para crescer vem da análise de Pedro, das consultorias dele com IAs e dos dados do canal; o motor não se ocupa disso. O M5 edita bem, entrega o que foi pedido e acumula repertório (→ 3) a partir do que Pedro pede e aprova

## 3. CONCEITOS-CHAVE
- canal: uma linha editorial com pasta própria em canais/<canal>/; tudo o que é dele fica ali
- ficha do canal (ficha.yaml): os dados operacionais do canal (nicho, vozes, cadência…); Pedro altera quando quiser, sem tocar neste documento. Campos: 6.4
- formato: o perfil de saída de um vídeo — longo, short de roteiro novo ou short de recorte. Detalhes: 7.6
- Fase 0: a definição da identidade visual de um canal, feita uma vez, antes do 1º vídeo. Fluxo: 9.2
- template: peça visual reutilizável (legenda, contador, mapa, citação, transição…)
- kit visual (kit_visual.yaml): o resultado da Fase 0 — 2 fontes, 1 paleta, 4–5 templates
- receita: um padrão de edição aprovado por Pedro, guardado em receitas.yaml
- candidata: um padrão em observação, ainda não aprovado, guardado em receitas_candidatas.md
- repertório: kit visual + receitas + templates aprovados de um canal. Regras: seção 8
- asset: qualquer peça usada na montagem — clipe, imagem, áudio, fonte, animação
- catálogo: os clipes brutos indexados de um canal
- segmento: a unidade do roteiro; cada um tem uma intenção ∈ {gancho, contexto, desenvolvimento, revelacao, humor, transicao, cta}
- roteiro_mestre.yaml: o roteiro de um vídeo, como lista ordenada de segmentos. Campos: 6.5
- EDL (edl.json): a linha do tempo gerada pelo motor — segmento → assets com tempos
- gerador: módulo do motor que produz um tipo de asset ou de formato
- registro de capacidades (motor/geradores.yaml): a lista de tudo o que o motor sabe fazer. Detalhes: 7.2
- portões: pontos em que a produção para até Pedro aprovar

| portão | o que Pedro aprova | regra ligada |
|---|---|---|
| P1 | esqueleto (blocos, intenções, ganchos) | o roteiro completo só é escrito depois dele |
| P2 | roteiro travado | F01, F06 |
| P3 | prévia (versão 480p) | F02 |
| P4 | entrega | F04 |

- roteiro travado: o roteiro aprovado no P2; depois disso só muda por ordem de Pedro, como nova versão
- validação: a checagem do roteiro contra o registro de capacidades, sem IA, antes do P2. Detalhes: 7.3
- backup externo: cópia fora da máquina — repositório Git privado na nuvem (texto) e HD externo ou nuvem (mídia). Detalhes: 6.6
- arquivar: mover para o backup externo, nunca apagar
- checagem de saúde (`m5 checar`): verificação sem IA do estado da máquina e do motor. Detalhes: 7.8
- exceção: quando o motor não consegue resolver algo sozinho. Dois tipos:
  - operacional: falha de execução (link fora do ar, download quebrado, erro de arquivo) → o Claude Code resolve
  - capacidade nova: o roteiro pede algo que o registro não tem → decisão de Pedro (9.5)

## 4. ATORES E RECURSOS
### 4.1 atores
| ator | função |
|---|---|
| Pedro | administrador. Decide canais, formatos, fornecedores e crescimento; define as fichas; escolhe referências e aprova o kit; aprova os portões; coescreve o roteiro; faz a curadoria; posta; exporta métricas; aprova receitas, templates e geradores |
| Claude (chat) | decompõe as referências na Fase 0; propõe pauta e ganchos; coescreve esqueleto e roteiro com Pedro; prepara o material da análise mensal |
| Claude Code | constrói o motor completo, os templates e os geradores novos; executa os comandos; resolve exceções operacionais e registra cada falha; registra candidatas. Nunca decide corte a corte; nunca julga qualidade |
| motor | scripts Python/JS gratuitos e determinísticos: resolve assets por regra e kit; gera EDL, prévia, render final e recortes |
| script de análise (sem IA) | retenção por segmento, mensal |
| fornecedores de voz | narração, conforme a ficha do canal |

- por que o Claude Code não decide cortes: um longo de 15–20 min com cortes de 3–5 s tem ~200–400 decisões; por script custam ~0 tokens; por LLM estourariam o limite do Claude Pro

### 4.2 recursos
- Claude Pro: chat + Claude Code; limite de uso COMPARTILHADO entre os dois
- ElevenLabs: 130.000 créditos/mês; voz clonada de Pedro; tags de pausa/voz já validadas; Pedro acompanha o consumo no painel
- Dark Planner: vozes de biblioteca, alto volume de áudio
- qual fornecedor serve a qual canal e formato: definido na ficha do canal
- ferramentas gratuitas: 7.1

## 5. FREIOS
### gasto
- F01 nenhum crédito de voz gasto antes do P2
- F02 nenhum render final antes do P3
### aprovação
- F03 portão não pode ser pulado; se Pedro não puder revisar, a produção espera
- F04 nenhum vídeo sai sem o P4, em qualquer formato
- F05 canal, formato ou fornecedor novo só por decisão de Pedro
- F06 o P2 só fecha com a validação sem pendências
### motor
- F07 o motor nunca chuta: asset sem correspondência ou tipo desconhecido vira exceção
- F08 o Claude Code nunca constrói gerador no meio de uma rodada: diante de capacidade nova, pausa aquele segmento, conclui os demais e reporta a Pedro
- F09 todo gerador entra no registro de capacidades só depois de uma amostra aprovada por Pedro
- F10 gerador novo, depois da construção: o Claude Code dá a estimativa de custo (pequeno, médio ou grande) antes; constrói só com ordem de Pedro, em sessão separada
- F11 todo gerador é módulo reutilizável, nunca solução de um vídeo só
- F12 correções só tocam os segmentos citados
### escrita e proteção
- F13 quem escreve o quê: tabela 6.3. Fora dela, nada é escrito
- F14 nenhuma IA edita docs/; trava técnica em .claude/settings.json
### repertório
- F15 candidata só vira receita ou template após aparecer em ≥2 vídeos aprovados no P4 + aprovação de Pedro
- F16 receita sem uso por 2 meses → arquivada, não apagada
- F17 catálogo não é compartilhado entre canais sem decisão de Pedro
- F18 short só existe em canal com base documentada: kit visual aprovado + ≥1 longo aprovado no P4
### segurança e histórico
- F19 chaves de API só no .env; nunca no Git, nunca no chat
- F20 Git em todo o projeto; nada é apagado, só arquivado
### manutenção
- F21 a cada etapa ou entrega aprovada: commit + push para o repositório privado; entregas e narrações copiadas para o backup externo (6.6)
- F22 toda exceção operacional resolvida e todo problema grave viram uma linha em logs/falhas.md: data | etapa | sintoma | causa | correção | commit
- F23 versões das ferramentas travadas (motor/requirements.txt e motor/package-lock.json); atualizar só por ordem de Pedro, com amostra aprovada
- F24 toda sessão começa com `m5 checar`; se falhar, nada roda antes de resolver

## 6. ESTRUTURA DO PROJETO
### 6.1 árvore
```
/                          ← raiz do M5
  CLAUDE.md                ← constituição operacional
  .claude/settings.json    ← trava técnica: bloqueia edição de docs/
  .env                     ← chaves de API (fora do Git)
  .gitignore               ← exclui .env, catalogo/, assets/ de mídia e entrega/
  docs/                    ← este documento e as versões anteriores
  motor/                   ← código do M5, único para todos os canais
    geradores.yaml         ← registro de capacidades
    requirements.txt       ← versões travadas (Python)
    package-lock.json      ← versões travadas (JS)
  logs/                    ← custos.csv, falhas.md e registros de uso
  canais/
    <canal>/
      ficha.yaml
      padroes_referencia.md  ← saída da Fase 0 (F0.2)
      regras/              ← kit_visual.yaml, receitas.yaml, receitas_candidatas.md
      templates/
      catalogo/
      assets/              ← + manifest {origem, data}
      roteiros/            ← por vídeo: esqueleto, roteiro_mestre, relatório de validação, correções
      relatorios/          ← relatórios mensais
      entrega/             ← mp4 finais
```

### 6.2 mapa dos CLAUDE.md
- como funciona: o Claude Code sempre lê o CLAUDE.md da raiz; o de uma subpasta, quando mexe em arquivos dela. Por isso todos os freios ficam na raiz; os demais trazem só regras locais e nunca contradizem a raiz

| arquivo | conteúdo |
|---|---|
| /CLAUDE.md | constituição: o que é o M5, princípios, papel do Claude Code, freios F01–F24, ordem de autoridade, como reagir a cada tipo de exceção |
| motor/CLAUDE.md | padrões de código: todo gerador é módulo + entrada no registro + amostra; nada específico de canal dentro do motor; todo comando recebe --canal e --formato |
| canais/CLAUDE.md | como um canal é estruturado; fluxo de abertura (9.2); isolamento entre canais |
| canais/<canal>/CLAUDE.md | identidade do canal: tom, estética, público. Escrito com Pedro na abertura |
| canais/<canal>/regras/CLAUDE.md | área protegida: só receitas_candidatas.md é escrita livremente; o resto, conforme 6.3 |
| canais/<canal>/roteiros/CLAUDE.md | formato do roteiro_mestre; validação antes do P2; roteiro travado não se edita |
| docs/CLAUDE.md | somente leitura, sem exceção |
| logs/, templates/, catalogo/, assets/, relatorios/, entrega/ | CLAUDE.md curto (1–3 linhas): o que entra ali; nada é apagado |

### 6.3 quem escreve o quê
| o quê | quem escreve |
|---|---|
| docs/ | nenhuma IA; Pedro guarda as versões novas |
| CLAUDE.md (todos), ficha.yaml, kit_visual.yaml, receitas.yaml, geradores.yaml, arquivos de versões (F23) | Claude Code, só com ordem explícita de Pedro na sessão, mostrando o diff, com commit identificado |
| roteiro_mestre.yaml | Pedro + Claude até o P2; depois, só por ordem de Pedro, como nova versão |
| receitas_candidatas.md, logs/ (inclui falhas.md), catalogo/, assets/, edl, prévias, relatórios, entrega/ | Claude Code e motor, livremente (nada é apagado — F20) |

### 6.4 ficha do canal (só a estrutura; os valores ficam fora deste documento)
- campos: nicho | status (ativo/aguardando) | fornecedor e voz por formato | formatos ativos | cadência por formato | estratégia de shorts (recorte, roteiro novo, ambos) | compartilhamento de catálogo | pendências operacionais

### 6.5 artefatos
- roteiro_mestre.yaml — campos por segmento: id | intencao | narracao (texto + tags de voz) | visual {fonte ∈ {catalogo, web, gerado}, busca, etiquetas[]} | texto_tela | sfx | duracao_alvo_s
- edl.json — segmento → assets com tempos de entrada e saída
- todo comando do motor recebe canal e formato (ex.: `m5 previa --canal principal --formato longo`)

### 6.6 backup
| o quê | importância | destino |
|---|---|---|
| docs, regras, kit, receitas, fichas, CLAUDE.md, roteiros, código, logs | insubstituível (texto, pequeno) | repositório Git privado na nuvem, push a cada aprovação (F21) |
| entregas (mp4 finais) | alta | HD externo ou pasta sincronizada na nuvem |
| narrações geradas | média (custaram créditos) | junto com as entregas |
| catálogo | baixa (baixa de novo) | fora do Git; sem backup obrigatório |
| chaves do .env | alta | gerenciador de senhas de Pedro; nunca no Git (F19) |
- disco cheio: o que for arquivado vai para o backup externo (é assim que F20 convive com o espaço em disco)

## 7. O MOTOR
### 7.1 ferramentas gratuitas
- captação: yt-dlp
- indexação: faster-whisper (transcrição local), PySceneDetect (cortes de cena), ffmpeg (miniaturas)
- montagem: ffmpeg, MoviePy
- animação: Remotion (JS), Manim (Python), Pillow
- áudio: librosa (batidas/picos), auto-editor (silêncios)
- imagem: rembg (remoção de fundo)
- fontes web: APIs Pexels, Pixabay, Openverse, Freesound, Giphy; Google Fonts
- ferramenta nova entra como gerador (9.5)

### 7.2 registro de capacidades
- campos por entrada: tipo | gerador | formatos suportados | teto conhecido | status (em teste / aprovado)
- nasce preenchido ao fim da construção (9.1) e cresce com os geradores novos
- teto conhecido geral: código anima bem, mas não cria arte de personagem sozinho; a amostra mostra o teto de cada tipo

### 7.3 validação
- comando: `m5 validar --canal <c> --formato <f> --roteiro <arquivo>` — script sem IA, ~0 tokens
- saída: relatorio_validacao.md em roteiros/, com cada segmento marcado como:
  - ok
  - baixar material (normal; segue)
  - sem gerador → pendência (Pedro decide: 9.5)
  - teto conhecido → aviso antes do P2

### 7.4 narração (módulo trocável)
- entrada: texto do segmento; saída: áudio + timestamps. O resto do motor não sabe qual fornecedor gerou
- modo API (ex.: ElevenLabs): por segmento, com timestamps, cache por hash do texto → alteração em 1 frase regenera só aquele segmento
- modo arquivo importado (ex.: Dark Planner sem API): Pedro gera e baixa o áudio; o faster-whisper cria os timestamps localmente. A interface fica pronta na construção; os detalhes são definidos no primeiro uso real (12)
- o custo de cada geração vai para logs/custos.csv

### 7.5 material bruto e catálogo
- cada canal tem o seu catálogo (F17)
- sob demanda: baixa só o que o roteiro pede; sem pré-carga de biblioteca
- fontes, por prioridade: (1) material oficial/trailers; (2) gameplay e lives de terceiros via yt-dlp; (3) gravação própria só para lacunas
- indexação automática na entrada; o catálogo cresce vídeo a vídeo e é reaproveitado

### 7.6 formatos
| formato | proporção | duração | etapas de controle |
|---|---|---|---|
| longo | 16:9, 1080p | 15–20 min | P1 → validação → P2 → P3 → P4 |
| short — roteiro novo | 9:16, 1080×1920 | 30–60 s | validação → P2 → P3 → P4 |
| short — recorte de longo | 9:16, 1080×1920 | 30–60 s | P3 → P4 (o P2 vem do longo de origem) |

- todo short pertence a um canal e lê o repertório desse canal; o 9:16 é uma camada de adaptação de layout dentro do kit do canal, não uma identidade separada
- pré-condição do short: F18
- recorte: segmentos de um longo aprovado no P4, escolhidos por intenção e tempo do roteiro_mestre; sem nova narração
- formato novo (ex.: vídeo 100% animado): por decisão de Pedro (F05), construído como gerador (9.5)

### 7.7 motor extensível
- qualquer asset ou formato pode ser pedido no roteiro
- o que o registro não tem aparece na validação, antes do P2 — nunca no meio da rodada
- todo gerador construído serve a todos os canais

### 7.8 checagem de saúde
- comando: `m5 checar` — script sem IA, ~0 tokens, no início de toda sessão (F24)
- confere: ferramentas instaladas nas versões travadas (F23) | chaves presentes no .env | espaço em disco | registro de capacidades consistente com os geradores existentes | Git sem pendências e último push feito
- saída: ok, ou a lista do que falhou

## 8. REPERTÓRIO
- composição: kit visual + receitas + templates aprovados, por canal
- nasce na Fase 0 (kit) e cresce com o uso: o Claude Code registra candidatas; Pedro aprova pela regra F15
- o roteiro é sempre escrito com o repertório vigente do canal
- cada receita é marcada com o formato em que nasceu (longo ou short); o short lê todo o repertório do canal e usa as receitas marcadas como short quando existirem
- o kit só muda com aprovação de Pedro (6.3)
- arquivamento: F16

## 9. FLUXOS (em ordem cronológica)
### 9.1 construção do motor (uma vez; Claude Code, várias sessões)
| etapa | o que se constrói | amostra para Pedro aprovar (F09) |
|---|---|---|
| C1 | estrutura de pastas, todos os CLAUDE.md, .claude/settings.json, .env de modelo, .gitignore, Git com repositório privado na nuvem, versões travadas das ferramentas, logs/falhas.md | a árvore criada e o primeiro push |
| C2 | núcleo: leitura do roteiro_mestre, registro de capacidades, validação, EDL | um roteiro de amostra validado |
| C3 | narração: modo API (ElevenLabs) + interface do modo arquivo | 3 segmentos narrados com timestamps |
| C4 | captação e indexação do catálogo | 1 vídeo baixado e indexado |
| C5 | montagem, prévia 480p, render final | uma amostra de 1 min em 16:9 |
| C6 | formatos de short (roteiro novo e recorte) | uma amostra 9:16 |
| C7 | registro de custos em logs/ | as entradas geradas pelas amostras |
| C8 | `m5 checar` e rotina de backup externo | checagem passando; um arquivo de teste copiado para o backup externo |
- cada etapa só começa depois da aprovação da anterior
- as amostras da construção usam um kit neutro provisório; não são vídeos de canal, por isso F18 não se aplica a elas
- ao fim da C8, o registro de capacidades está preenchido e o motor está pronto para abrir o canal principal
- os templates de cada canal são construídos na Fase 0 dele (F0.4)

### 9.2 abertura de canal (por decisão de Pedro)
| passo | ator | ação | saída |
|---|---|---|---|
| A1 | Pedro | decide abrir o canal | — |
| A2 | Claude Code, por ordem de Pedro | cria a pasta, a ficha e o CLAUDE.md do canal | canais/<canal>/ |
| A3 | Pedro + Claude + Claude Code | Fase 0 (abaixo) | kit aprovado |
| A4 | Pedro + motor | piloto curto em formato longo (16:9, ~1–2 min), pelos portões do longo, para testar o kit. O piloto não conta como longo aprovado para F18 | piloto aprovado |

Fase 0 (uma vez por canal):
| passo | ator | ação | saída |
|---|---|---|---|
| F0.1 | Pedro | escolhe 3–5 vídeos de referência | lista de referências |
| F0.2 | Claude | decompõe ritmo de corte, fontes, paleta, animações, frequência de sfx | padroes_referencia.md |
| F0.3 | Pedro + Claude | define o kit: 2 fontes, 1 paleta, 4–5 templates | regras/kit_visual.yaml |
| F0.4 | Claude Code | constrói os templates do kit | templates/ |
| F0.5 | Pedro | aprova o kit em amostras curtas | kit aprovado |
- os vídeos de referência não vão para o computador novo; vai só o kit (e os arquivos de fontes/sfx escolhidos)

### 9.3 vídeo longo
| passo | ator | ação | saída | controle |
|---|---|---|---|---|
| 1 | Claude | pauta + 3 ganchos, a partir de tendências e do repertório | proposta | — |
| 2 | Pedro + Claude | esqueleto: blocos, intenções, ganchos, momentos especiais | esqueleto.md | P1 |
| 3 | Pedro + Claude | roteiro completo com o repertório vigente | roteiro_mestre.yaml | — |
| 4 | motor | validação (7.3); pendências → 9.5 | relatorio_validacao.md | — |
| 5 | Pedro | revisão final | roteiro travado | P2 (F06) |
| 6 | Claude Code + motor | narração, assets, EDL, prévia 480p. Exceção operacional → Claude Code resolve e registra (F22); capacidade nova → F08 | previa.mp4 | — |
| 7 | Pedro | revisa a prévia; lista de correções (segmento \| o que mudar \| usando quê) | correções | P3 |
| 8 | Claude Code | aplica só nos segmentos citados (F12); render final; registra candidatas | final.mp4 + candidatas | — |
| 9 | Pedro | aprova o vídeo e as candidatas que cumprem F15; o Claude Code grava receitas.yaml por ordem dele (6.3) e faz o backup (F21) | entrega; receitas.yaml v+1 | P4 |
| 10 | Pedro | posta; exporta CSV + retenção após 7 dias | dados | — |

### 9.4 short
- antes de tudo: o motor confere a pré-condição F18; se faltar, recusa e avisa
- roteiro novo: Pedro + Claude escrevem com o repertório do canal → validação → P2 → narração + prévia → P3 → render 9:16 → P4
- recorte: Pedro escolhe os segmentos de um longo aprovado → prévia → P3 → render 9:16 → P4
- depois do P4: candidatas como no longo, marcadas como short

### 9.5 gerador novo (capacidade nova)
- origem: pendência na validação ou, raramente, exceção de capacidade nova no passo 6
- Pedro escolhe, por pendência: construir | trocar o asset no roteiro | fallback (ex.: imagem da web + texto na tela) | adiar o segmento
- construir: Claude Code dá a estimativa → Pedro dá a ordem → construção em sessão separada → amostra → Pedro aprova → entra no registro → o roteiro é validado de novo (F09, F10, F11)
- o custo vai para logs/custos.csv como "construção"

### 9.6 ciclo mensal
- script de análise → Claude prepara o material → Pedro decide
- entrada: dados do mês (retenção por segmento e intenção) + registros de 10
- saída: relatorios/relatorio_mensal.md, como material para a curadoria de Pedro

## 10. CUSTOS E REGISTRO
### 10.1 estimativas
- voz, longo: 140–150 palavras/min → ~12.600–18.000 caracteres; com ~10% de refação → ~14.000–20.000 créditos ElevenLabs (premissa ~1 crédito/caractere; confirmar no painel)
- voz, short de roteiro novo: ~1.000 caracteres; short de recorte: 0 (reaproveita a narração do longo)
- Dark Planner: limite real a confirmar no plano contratado
- tempo de Pedro: Fase 0, poucas horas por canal; longo, ~3 h (cai com a maturidade do repertório); recorte, minutos; análise mensal, ~1 h
- Claude Pro: construção do motor, ALTO e concentrado nas sessões de construção; Fase 0, BAIXO/MÉDIO; longo, MÉDIO no chat + BAIXO no Code; gerador novo, custo único de construção e depois ~0 por uso
- máquina: 1 prévia 480p + 1 render final por vídeo
- backup: repositório privado sem custo; HD externo ou nuvem por conta de Pedro
### 10.2 registro contínuo
- logs/custos.csv, por vídeo e por construção: créditos/áudios gastos, % de refação, uso do Claude quando disponível, tempo de Pedro quando ele informar
- é material para a curadoria de Pedro; não trava nenhuma decisão

## 11. RISCOS E CONTINGÊNCIAS
| risco | contingência |
|---|---|
| gargalo humano: a produção depende de Pedro nos portões, em vários canais e formatos | reduzir canais/formatos ativos na ficha; em último caso, M1 é o fallback mais simples |
| módulo construído antes do uso real pode precisar de ajuste no 1º vídeo | amostra aprovada em cada etapa (9.1); o ajuste é tratado como exceção operacional |
| teto de qualidade de animações feitas só por código | o registro guarda o teto; a validação avisa antes do P2 |
| modo arquivo importado: corrigir pode exigir regerar o áudio no fornecedor | detalhes no primeiro uso real (12) |
| fornecedor de voz falha | trocar na ficha do canal; o motor não muda |
| limite do Claude Pro aperta | decisão de Pedro, fora do modelo |
| estimativas de custo não verificadas | o registro contínuo (10.2) mostra os números reais |
| perda ou defeito da máquina | backup externo (F21, 6.6) |
| disco cheio de vídeo (nada é apagado) | arquivar no backup externo (6.6) |
| atualização de ferramenta quebra o motor | versões travadas (F23); `m5 checar` acusa antes de rodar (F24) |
| o mesmo bug investigado do zero a cada sessão | logs/falhas.md (F22) |
| material de terceiros | risco de reivindicação desconsiderado por decisão de Pedro; registrar se ocorrer |

## 12. PENDÊNCIAS
- hardware do computador novo: afeta o tempo de render; não altera a arquitetura
- modo arquivo importado (Dark Planner): detalhes no primeiro uso real
- limite do plano Dark Planner: a confirmar
- repositório privado na nuvem (ex.: GitHub privado) e destino do backup de mídia (HD externo ou nuvem): escolha de Pedro antes da C1; o login no repositório é feito pelo próprio Pedro
- pendências operacionais de cada canal: na ficha dele

## APÊNDICE — HISTÓRICO E ORIGEM
### A.1 composição
| elemento | origem | situação na v3.0 |
|---|---|---|
| IA de roteiro centralizada no Claude (com Pedro) | M1 | mantida |
| ChatGPT grátis como opinião externa | M2 | removido |
| kit visual antes do 1º vídeo | M3 | Fase 0 mínima, por canal |
| receitas | M3 | repertório por canal (seção 8) |
| retenção por segmento | M4 | ciclo mensal, como material da curadoria de Pedro |
| portões de aprovação | M5 | P1–P4; o short sempre passa pelo P4 |
| prévia 480p antes do render final | M5 | mantida |

### A.2 ajustes da v1.0
1. Fase 0 mínima antes do 1º vídeo de cada canal — mantido
2. receita candidata só entra após ≥2 vídeos aprovados + aprovação de Pedro — mantido (F15)
3. medir o Claude Pro nos 3 primeiros vídeos antes do ChatGPT Plus — removido na v3.0

### A.3 mudanças da v2.0
1. motor único multicanal; canal e formato como parâmetros
2. formato short (roteiro novo e recorte)
3. narração trocável: ElevenLabs e Dark Planner; modo API e modo arquivo importado
4. catálogo próprio por canal
5. abertura de canal por decisão exclusiva de Pedro
6. motor extensível
7. princípio de julgamento: o M5 executa e acumula repertório; não avalia qualidade

### A.4 mudanças da v3.0
1. R2 reescrita: de "crescer só com evidência" para "fidelidade ao documento" (texto de Pedro)
2. princípio de julgamento ampliado: a evidência para crescer é de Pedro, não do motor
3. motor completo desde o começo, com plano de construção em etapas (9.1)
4. registro de capacidades + validação antes do P2; gerador novo com estimativa, ordem de Pedro, sessão separada e amostra aprovada
5. CLAUDE.md na raiz e em cada pasta; trava técnica em docs/; tabela de quem escreve o quê (resolve a contradição da v2 sobre regras/)
6. short: sempre passa pelo P4; herda o repertório do canal (sai "o vertical não herda as receitas do longo"); só existe com base documentada
7. ChatGPT grátis e ChatGPT Plus removidos
8. a medição inicial virou registro contínuo, sem travar decisões
9. documento reordenado: conceitos antes do uso, cada regra em um lugar só (códigos F), fluxos em ordem cronológica, histórico no apêndice
10. removidos também: o freio do ChatGPT Plus, "P2 ainda mais rígido" no modo arquivo e o risco "várias novidades no mesmo vídeo" (assunto da curadoria)

### A.5 mudanças da v3.1 (M5-finalboss)
1. backup externo: repositório Git privado na nuvem para o texto; HD externo ou nuvem para a mídia (F21, 6.6)
2. registro de falhas em logs/falhas.md (F22)
3. versões das ferramentas travadas; atualização só por ordem de Pedro (F23)
4. checagem de saúde `m5 checar` no início de toda sessão (F24, 7.8)
5. construção ganha a etapa C8; C1 passa a incluir repositório remoto, .gitignore, versões e falhas.md
6. conceitos novos: backup externo, arquivar, checagem de saúde

### A.6 diferencial
- um motor, vários canais: uma correção beneficia todos
- motor completo: Pedro pede, o motor executa
- identidade visual desde o 1º vídeo de cada canal
- cada erro é capturado na etapa mais barata possível
- o repertório cresce a partir do que Pedro pede e aprova, sem a máquina tentar julgar
