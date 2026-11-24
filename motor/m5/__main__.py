"""Linha de comando do M5. Todo comando recebe --canal e --formato (motor/CLAUDE.md).

  m5 validar --canal <c> --formato <f> --roteiro <arquivo>
  m5 edl     --canal <c> --formato <f> --roteiro <arquivo>
  m5 narrar  --canal <c> --formato <f> --roteiro <arquivo> [--segmentos s01,s02] [--arquivos <pasta>]
  m5 captar  --canal <c> --formato <f> --url <link> [--inicio 0:30 --fim 1:00] [--etiquetas a,b] [--idioma pt]
  m5 travar  --canal <c> --formato <f> --roteiro <arquivo>          → p2.yaml (P2), libera narração e prévia
  m5 previa  --canal <c> --formato <f> --roteiro <arquivo>          → EDL + previa.mp4 (480p) para o P3
  m5 render  --canal <c> --formato <f> --roteiro <arquivo> --p3     → final.mp4, só depois do P3 (F02)
  m5 recorte --canal <c> --formato short_recorte --roteiro <roteiro do longo> --segmentos s01,s03
  m5 template --canal <c> --formato <f> --template <nome> --campo k=v [--campo k=v] [--fundo <video> --inicio s] [--duracao s]
                                                                     → amostra de template do kit (F0.4/F0.5)
  m5 checar                                                          → checagem de saúde (7.8, F24)
  m5 backup  --canal <c> --formato <f|-> [--teste]                   → copia entregas e narrações (6.6, F21)
  m5 custo   --canal <c|-> --formato <f|-> --item tempo_pedro --quantidade 30 --unidade minutos [--video v] [--obs ...]
                                                                     → acrescenta uma linha em logs/custos.csv (10.2)
                                                                     → recorte 9:16 + prévia para o P3

Saída: 0 = ok · 1 = pendências na validação · 2 = erro (nada foi gerado)
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from .canal import FORMATOS, REGISTRO_PADRAO, ErroM5, pasta_canal, resolver_roteiro
from .backup import fazer_backup
from .catalogo import captar, importar_ficha
from .templates.amostra import gerar_amostra
from .saude import checar
from .custos import etapa_do_canal, registrar
from .edl import escrever_edl, gerar_edl
from .montagem import montar
from .recorte import criar_recorte
from .narracao import narrar
from .p2 import exigir_p2, travar
from .roteiro import ler_roteiro
from .validacao import ROTULO, escrever_relatorio, validar


def _args(sub, nome, ajuda, roteiro=True):
    p = sub.add_parser(nome, help=ajuda)
    p.add_argument("--canal", required=True)
    p.add_argument("--formato", required=True)
    if roteiro:
        p.add_argument("--roteiro", required=True, help="caminho do roteiro_mestre.yaml")
    return p


def _sha1(arq: Path) -> str:
    return hashlib.sha1(arq.read_bytes()).hexdigest()


def _gravar_json(arq: Path, dados) -> None:
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _render(a, caminho: Path) -> int:
    # F02: nenhum render final antes do P3. --p3 confirma a aprovação de Pedro; fora de _amostras
    # fica registrada em p3.yaml com o sha1 do edl.json aprovado (mesmo modelo do p2.yaml).
    if not a.p3:
        raise ErroM5("render final só depois do P3: passe --p3 quando Pedro aprovar a prévia (F02)")
    arq_edl, marca = caminho.with_name("edl.json"), caminho.with_name("previa.json")
    if not arq_edl.is_file() or not marca.is_file() or not caminho.with_name("previa.mp4").is_file():
        raise ErroM5("não há prévia para este roteiro: rode m5 previa antes (F02)")
    if json.loads(marca.read_text(encoding="utf-8"))["edl_sha1"] != _sha1(arq_edl):
        raise ErroM5("o edl.json mudou depois da prévia: gere e aprove uma nova prévia (F02)")
    edl = json.loads(arq_edl.read_text(encoding="utf-8"))
    if a.canal != "_amostras":
        from datetime import datetime
        import yaml
        caminho.with_name("p3.yaml").write_text(yaml.safe_dump(
            {"portao": "P3", "aprovado_por": "Pedro", "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
             "edl_sha1": _sha1(arq_edl)}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    final = montar(edl, "final", caminho.with_name("final.mp4"))
    print(f"final: {final}  ({edl['duracao_total_s']:.1f} s)")
    return 0


def main(argv=None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        fluxo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="m5")
    sub = ap.add_subparsers(dest="comando", required=True)
    _args(sub, "validar", "valida o roteiro contra o registro de capacidades (7.3)")
    _args(sub, "edl", "gera o edl.json do roteiro (exige validação sem pendências)")
    p = _args(sub, "narrar", "narra os segmentos (7.4): modo API ou modo arquivo, conforme a ficha")
    p.add_argument("--segmentos", help="ids separados por vírgula (padrão: todos com narração)")
    p.add_argument("--arquivos", help="modo arquivo: pasta com <id>.mp3/.wav…")
    p = _args(sub, "captar", "baixa um vídeo (ou trecho) para o catálogo do canal e indexa (7.5)", roteiro=False)
    p.add_argument("--url", required=True)
    p.add_argument("--inicio", help="início do trecho (s, mm:ss ou hh:mm:ss)")
    p.add_argument("--fim", help="fim do trecho")
    p.add_argument("--etiquetas", help="etiquetas separadas por vírgula, usadas para casar com o roteiro")
    p.add_argument("--idioma", default="auto", help="idioma da fala para a transcrição (padrão: auto)")
    p = _args(sub, "importar", "importa gameplay local para o catálogo: 1 clipe por linha da ficha .md", roteiro=False)
    p.add_argument("--ficha", required=True, action="append", help="ficha .md (repita para várias)")
    _args(sub, "travar", "registra o P2: grava p2.yaml com o sha1 do roteiro (exige validação sem pendências)")
    _args(sub, "previa", "gera o EDL e a prévia 480p para o P3")
    p = _args(sub, "recorte", "short de recorte: segmentos de um longo aprovado, em 9:16 (7.6)")
    p.add_argument("--segmentos", required=True, help="ids do longo, na ordem do short, separados por vírgula")
    p = _args(sub, "render", "render final a partir do EDL da prévia aprovada no P3 (F02)")
    p.add_argument("--p3", action="store_true", help="confirma que Pedro aprovou a prévia (P3)")
    p = _args(sub, "custo", "registra um custo à mão em logs/custos.csv (tempo de Pedro, uso do Claude…)", roteiro=False)
    p.add_argument("--item", required=True, choices=["narracao", "claude", "tempo_pedro", "outro"])
    p.add_argument("--quantidade", required=True, type=float)
    p.add_argument("--unidade", required=True, help="ex.: minutos, creditos, audios, %% do limite")
    p.add_argument("--fornecedor", help="padrão: pedro (tempo_pedro), claude_pro (claude)")
    p.add_argument("--video", default="-")
    p.add_argument("--etapa", choices=["producao", "construcao"])
    p.add_argument("--refacao", action="store_true")
    p.add_argument("--obs", default="")
    p = sub.add_parser("checar", help="checagem de saúde da máquina e do motor (7.8, F24)")
    p.add_argument("--detalhes", action="store_true", help="mostra também o que passou")
    p = _args(sub, "backup", "copia entregas e narrações do canal para o backup externo (6.6, F21)", roteiro=False)
    p.add_argument("--teste", action="store_true", help="inclui um arquivo de teste")
    p = _args(sub, "recortar", "busca a foto de maior resolução na web, tira o fundo e registra no manifest", roteiro=False)
    p.add_argument("--busca", required=True, help='ex.: "Trevor Philips GTA 5"')
    p.add_argument("--nome", required=True, help="nome do arquivo (ex.: trevor)")
    p.add_argument("--etiquetas", required=True, help="etiquetas separadas por vírgula, usadas pelo roteiro")
    p.add_argument("--url", help="usa esta imagem em vez da busca")
    p = _args(sub, "template", "amostra de um template do kit do canal (F0.4/F0.5)", roteiro=False)
    p.add_argument("--template", required=True)
    p.add_argument("--campo", action="append", default=[], help="nome=valor (repita para cada campo)")
    p.add_argument("--fundo", help="vídeo de fundo (padrão: cor de fundo do kit)")
    p.add_argument("--inicio", type=float, default=0.0, help="segundo do vídeo de fundo onde começa")
    p.add_argument("--duracao", type=float, default=5.0)
    p.add_argument("--saida", help="arquivo de saída (padrão: canais/<c>/templates/amostras/<template>.mp4)")
    a = ap.parse_args(argv)
    try:
        if a.comando == "recortar":
            from .recorte_imagem import recortar
            arq = recortar(a.canal, a.busca, a.nome, [e.strip() for e in a.etiquetas.split(",") if e.strip()], a.url)
            print(f"recorte: {arq}")
            return 0
        if a.comando == "template":
            destino = Path(a.saida) if a.saida else pasta_canal(a.canal) / "templates" / "amostras" / f"{a.template}.mp4"
            arq = gerar_amostra(a.canal, a.formato, a.template, a.campo, destino,
                                Path(a.fundo) if a.fundo else None, a.inicio, a.duracao)
            print(f"amostra: {arq}")
            return 0
        if a.comando == "checar":
            itens = checar()
            falhas = [i for i in itens if not i.ok]
            for i in (itens if a.detalhes else falhas):
                print(f"  {'ok   ' if i.ok else 'FALHA'} [{i.grupo}] {i.nome}" + (f" — {i.detalhe}" if i.detalhe else ""))
            print("ok" if not falhas else f"{len(falhas)} falha(s): resolva antes de rodar qualquer coisa (F24)")
            return 0 if not falhas else 1
        if a.comando == "backup":
            if a.formato != "-" and a.formato not in FORMATOS:
                raise ErroM5(f"formato desconhecido: '{a.formato}' (use - para todos)")
            r = fazer_backup(a.canal, a.teste)
            print(f"backup: {r['destino']}")
            print(f"  copiados: {r['copiados']} ({r['mb_copiados']} MB) · já iguais: {r['ja_iguais']} · versões antigas guardadas: {r['versoes_guardadas']}")
            return 0
        if a.comando == "custo":
            if a.canal != "-":
                pasta_canal(a.canal)
            if a.formato != "-" and a.formato not in FORMATOS:
                raise ErroM5(f"formato desconhecido: '{a.formato}'")
            forn = a.fornecedor or {"tempo_pedro": "pedro", "claude": "claude_pro"}.get(a.item, "-")
            etapa = a.etapa or (etapa_do_canal(a.canal) if a.canal != "-" else "construcao")
            linha = registrar(a.canal, a.video, a.formato, etapa, a.item, forn, a.quantidade, a.unidade,
                              a.refacao, a.obs)
            print("custo registrado: " + " | ".join(f"{k}={v}" for k, v in linha.items()))
            return 0
        if a.comando == "captar":
            etq = [e for e in (a.etiquetas or "").split(",") if e.strip()]
            c = captar(a.canal, a.formato, a.url, a.inicio, a.fim, etq, a.idioma)
            print(f"clipe: {c.id}{'  (já estava no catálogo; nada baixado)' if c.reaproveitado else ''}")
            print(f"  {c.origem['titulo']} — {c.origem['canal_origem']}")
            print(f"  {c.duracao_s:.1f} s · {c.resolucao[0]}x{c.resolucao[1]} · {len(c.cenas)} cenas · etiquetas: {', '.join(c.etiquetas) or '-'}")
            return 0
        if a.comando == "importar":
            for f in a.ficha:
                novos, ja = importar_ficha(a.canal, Path(f))
                print(f"{Path(f).name}: {novos} clipes novos · {ja} já no catálogo", flush=True)
            return 0
        caminho = resolver_roteiro(a.canal, a.roteiro)
        if a.comando == "narrar":
            ids = [i.strip() for i in a.segmentos.split(",")] if a.segmentos else None
            for n in narrar(a.canal, a.formato, ler_roteiro(caminho), ids,
                            Path(a.arquivos) if a.arquivos else None):
                estado = "cache, 0 créditos" if n.reaproveitada else f"{n.modo}, {n.caracteres} caracteres"
                print(f"  {n.segmento:<6} {n.duracao_s:6.2f} s  {len(n.palavras):3d} palavras  ({estado})  {n.audio}")
            return 0
        if a.comando == "render":
            return _render(a, caminho)
        if a.comando == "recorte":
            ids = [i.strip() for i in a.segmentos.split(",") if i.strip()]
            pasta, edl, avisos = criar_recorte(a.canal, a.formato, caminho, ids)
            arq_edl = escrever_edl(edl, pasta / "edl.json")
            previa = montar(edl, "previa", pasta / "previa.mp4")
            _gravar_json(pasta / "previa.json", {"edl_sha1": _sha1(arq_edl)})
            print(f"recorte: {pasta}")
            print(f"prévia: {previa}  ({edl['duracao_total_s']:.1f} s)")
            for av in avisos:
                print(f"aviso: {av}")
            return 0
        resultado = validar(a.canal, a.formato, ler_roteiro(caminho), REGISTRO_PADRAO)
        if a.comando == "travar":
            print(f"P2 registrado: {travar(resultado.roteiro, resultado.pendencias)}")
            return 0
        if a.comando == "previa":
            exigir_p2(a.canal, resultado.roteiro, "a prévia")
            edl = gerar_edl(resultado)
            arq_edl = escrever_edl(edl, caminho.with_name("edl.json"))
            previa = montar(edl, "previa", caminho.with_name("previa.mp4"))
            _gravar_json(caminho.with_name("previa.json"), {"edl_sha1": _sha1(arq_edl)})
            print(f"edl: {arq_edl}")
            print(f"prévia: {previa}  ({edl['duracao_total_s']:.1f} s)")
            return 0
        if a.comando == "validar":
            destino = escrever_relatorio(resultado)
            for s in resultado.segmentos:
                print(f"  {s.segmento.id:<12} {ROTULO[s.marca]}")
            print(f"relatório: {destino}")
            return 1 if resultado.pendencias else 0
        destino = escrever_edl(gerar_edl(resultado), caminho.with_name("edl.json"))
        print(f"edl: {destino}")
        return 0
    except ErroM5 as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
