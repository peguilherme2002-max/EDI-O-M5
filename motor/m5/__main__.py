"""Linha de comando do M5. Todo comando recebe --canal e --formato (motor/CLAUDE.md).

  m5 validar --canal <c> --formato <f> --roteiro <arquivo>
  m5 edl     --canal <c> --formato <f> --roteiro <arquivo>
  m5 narrar  --canal <c> --formato <f> --roteiro <arquivo> [--segmentos s01,s02] [--arquivos <pasta>]
  m5 captar  --canal <c> --formato <f> --url <link> [--inicio 0:30 --fim 1:00] [--etiquetas a,b] [--idioma pt]

Saída: 0 = ok · 1 = pendências na validação · 2 = erro (nada foi gerado)
"""
import argparse
import sys
from pathlib import Path

from .canal import REGISTRO_PADRAO, ErroM5, resolver_roteiro
from .catalogo import captar
from .edl import escrever_edl, gerar_edl
from .narracao import narrar
from .roteiro import ler_roteiro
from .validacao import ROTULO, escrever_relatorio, validar


def _args(sub, nome, ajuda, roteiro=True):
    p = sub.add_parser(nome, help=ajuda)
    p.add_argument("--canal", required=True)
    p.add_argument("--formato", required=True)
    if roteiro:
        p.add_argument("--roteiro", required=True, help="caminho do roteiro_mestre.yaml")
    return p


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
    a = ap.parse_args(argv)
    try:
        if a.comando == "captar":
            etq = [e for e in (a.etiquetas or "").split(",") if e.strip()]
            c = captar(a.canal, a.formato, a.url, a.inicio, a.fim, etq, a.idioma)
            print(f"clipe: {c.id}{'  (já estava no catálogo; nada baixado)' if c.reaproveitado else ''}")
            print(f"  {c.origem['titulo']} — {c.origem['canal_origem']}")
            print(f"  {c.duracao_s:.1f} s · {c.resolucao[0]}x{c.resolucao[1]} · {len(c.cenas)} cenas · etiquetas: {', '.join(c.etiquetas) or '-'}")
            return 0
        caminho = resolver_roteiro(a.canal, a.roteiro)
        if a.comando == "narrar":
            ids = [i.strip() for i in a.segmentos.split(",")] if a.segmentos else None
            for n in narrar(a.canal, a.formato, ler_roteiro(caminho), ids,
                            Path(a.arquivos) if a.arquivos else None):
                estado = "cache, 0 créditos" if n.reaproveitada else f"{n.modo}, {n.caracteres} caracteres"
                print(f"  {n.segmento:<6} {n.duracao_s:6.2f} s  {len(n.palavras):3d} palavras  ({estado})  {n.audio}")
            return 0
        resultado = validar(a.canal, a.formato, ler_roteiro(caminho), REGISTRO_PADRAO)
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
