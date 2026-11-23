"""Linha de comando do M5. Todo comando recebe --canal e --formato (motor/CLAUDE.md).

  m5 validar --canal <c> --formato <f> --roteiro <arquivo>
  m5 edl     --canal <c> --formato <f> --roteiro <arquivo>

Saída: 0 = ok · 1 = pendências na validação · 2 = erro (nada foi gerado)
"""
import argparse
import sys

from .canal import REGISTRO_PADRAO, ErroM5, resolver_roteiro
from .edl import escrever_edl, gerar_edl
from .roteiro import ler_roteiro
from .validacao import ROTULO, escrever_relatorio, validar


def _args(sub, nome, ajuda):
    p = sub.add_parser(nome, help=ajuda)
    p.add_argument("--canal", required=True)
    p.add_argument("--formato", required=True)
    p.add_argument("--roteiro", required=True, help="caminho do roteiro_mestre.yaml")
    return p


def main(argv=None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        fluxo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="m5")
    sub = ap.add_subparsers(dest="comando", required=True)
    _args(sub, "validar", "valida o roteiro contra o registro de capacidades (7.3)")
    _args(sub, "edl", "gera o edl.json do roteiro (exige validação sem pendências)")
    a = ap.parse_args(argv)
    try:
        caminho = resolver_roteiro(a.canal, a.roteiro)
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
