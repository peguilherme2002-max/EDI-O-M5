# Relatório de validação

- canal: cofre-de-leonida
- formato: longo
- roteiro: canais/cofre-de-leonida/templates/amostras/montagem/roteiro_mestre.yaml (versão 1)
- sha1 do roteiro: 147631ab82b70ae4acd411966478abe39c1e4541
- registro: motor/geradores.yaml
- gerado em: 2026-11-24 09:45
- segmentos: 4 · duração-alvo total: 35 s

## Resumo

| marcação | segmentos |
|---|---|
| ok | 3 |
| baixar material | 0 |
| teto conhecido → aviso | 1 |
| sem gerador → pendência | 0 |

**O P2 pode fechar?** sim

## Segmentos

| segmento | intenção | duração (s) | marcação |
|---|---|---|---|
| s00 | gancho | 3 | ok |
| s01 | gancho | 12 | ok |
| s02 | contexto | 10 | teto conhecido → aviso |
| s03 | revelacao | 10 | ok |

## Detalhes

### s00 — ok

- [ok] visual gerado: logo_flutuante — m5.templates.logo_flutuante

### s01 — ok

- [ok] narração, 204 caracteres, fornecedor elevenlabs — m5.narracao
- [ok] visual catalogo: "trailer 1 GTA VI Vice City" — m5.catalogo
- [ok] texto na tela: template legenda_karaoke — m5.templates.legenda_karaoke

### s02 — teto conhecido → aviso

- [ok] narração, 171 caracteres, fornecedor elevenlabs — m5.narracao
- [teto conhecido → aviso] visual web: "mapa oficial de Leonida" — m5.midia_web: imagem fora de 16:9 fica com faixas pretas (sem zoom nem recorte)
- [ok] texto na tela: template lista_item — m5.templates.lista_item

### s03 — ok

- [ok] narração, 184 caracteres, fornecedor elevenlabs — m5.narracao
- [ok] visual catalogo: "trailer 1 montagem rápida" — m5.catalogo
- [ok] texto na tela: template citacao — m5.templates.citacao
