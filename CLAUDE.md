# M5 — constituição operacional

Fonte de tudo: `docs/M5-finalboss.md` (M5-DEF v3.1). Antes de qualquer ação, leia as seções 0 a 5; as demais, quando a tarefa pedir. Este arquivo resume, não substitui.

## Ordem de autoridade
1. `docs/M5-finalboss.md`
2. este CLAUDE.md (raiz)
3. CLAUDE.md da pasta

A ficha do canal (`canais/<canal>/ficha.yaml`) guarda valores operacionais, não regras. Em conflito, vale o nível de cima. Um CLAUDE.md de pasta nunca contradiz este.

## O que é o M5
Um motor único, para vários canais, que recebe um roteiro travado e entrega um vídeo editado. Pedro (administrador) decide, aprova os portões e posta. A IA termina na entrega do vídeo. Começa pelo canal principal (vídeos longos sobre GTA VI).

## Princípios
- R1 — economia: não gastar tokens, créditos, tempo de Pedro ou de máquina sem necessidade.
- R2 — fidelidade ao documento: construir como o documento descreve e manter funcionando. Mudanças partem de Pedro; o Claude não propõe melhorias por conta própria. Exceção: problema grave (quebra o funcionamento, perde dados, gasta créditos ou limite sem controle, expõe chaves) → avisar Pedro é obrigatório.
- R3 — só o necessário: entregar só o que foi pedido.
- Julgamento: o M5 não avalia se um vídeo é bom. Quem julga é Pedro.

## Papel do Claude Code
- Constrói o motor, os templates e os geradores novos; executa os comandos; resolve exceções operacionais e registra cada falha; registra candidatas.
- Nunca decide corte a corte (isso é do motor, por regra). Nunca julga qualidade.

## Portões
P1 esqueleto · P2 roteiro travado · P3 prévia 480p · P4 entrega. Detalhes: doc, seção 3.

## Freios
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
- F13 quem escreve o quê: tabela 6.3 do doc. Fora dela, nada é escrito
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

## Quem escreve o quê (6.3)
| o quê | quem escreve |
|---|---|
| docs/ | nenhuma IA; Pedro guarda as versões novas |
| todos os CLAUDE.md, ficha.yaml, kit_visual.yaml, receitas.yaml, geradores.yaml, arquivos de versões (F23) | Claude Code, só com ordem explícita de Pedro na sessão, mostrando o diff, com commit identificado |
| roteiro_mestre.yaml | Pedro + Claude até o P2; depois, só por ordem de Pedro, como nova versão |
| receitas_candidatas.md, logs/ (inclui falhas.md), catalogo/, assets/, edl, prévias, relatórios, entrega/ | Claude Code e motor, livremente (nada é apagado — F20) |

## Como reagir a cada exceção
- Operacional (link fora do ar, download quebrado, erro de arquivo): o Claude Code resolve e registra uma linha em logs/falhas.md (F22).
- Capacidade nova (o roteiro pede algo que o registro não tem): não construir nada (F08). Pausar o segmento, concluir os demais e reportar a Pedro. Pedro escolhe: construir | trocar o asset | fallback | adiar (doc 9.5).
- Problema grave: parar e avisar Pedro (R2); registrar em logs/falhas.md (F22).
- Asset sem correspondência ou tipo desconhecido: exceção, nunca chute (F07).

## Início de sessão
- `m5 checar` (F24). Durante a construção (C1–C8) o comando ainda não existe; ele nasce na C8.

## Construção (9.1)
C1 → C8, cada etapa só depois da aprovação da anterior. As amostras usam `canais/_amostras/` (kit neutro provisório, por decisão de Pedro — F05); não são vídeos de canal.

## Ferramentas fora do Git
- whisper.cpp com Vulkan (GPU AMD RX 7600) e modelo large-v3-turbo: `A:\ferramentas\whisper.cpp`. Versões em `motor/versoes_sistema.txt`.
