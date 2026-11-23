"""Geração do EDL (edl.json): segmento → assets com tempos de entrada e saída (doc 3, 6.5).

Na C2 os tempos vêm de duracao_alvo_s e os assets ficam "a_resolver":
a resolução de assets (C4/C5) e os timestamps da narração (C3) preenchem depois.
"""
import json
from datetime import datetime
from pathlib import Path

from .canal import FORMATOS, ErroM5, fornecedor_voz, ler_ficha
from .roteiro import Roteiro
from .validacao import PENDENCIA, Resultado, _rel


def gerar_edl(r: Resultado) -> dict:
    # pendência aberta = algo sem gerador; o motor não monta linha do tempo chutando (F06, F07)
    if r.pendencias:
        ids = [s.segmento.id for s in r.segmentos if s.marca == PENDENCIA]
        raise ErroM5(f"EDL recusado: {r.pendencias} segmento(s) com pendência ({', '.join(ids)}). "
                     "Resolva pela 9.5 e valide de novo.")
    rot: Roteiro = r.roteiro
    fornecedor = fornecedor_voz(ler_ficha(r.canal), r.formato)
    t = 0.0
    segmentos = []
    for seg in rot.segmentos:
        ini, fim = round(t, 3), round(t + seg.duracao_alvo_s, 3)
        assets = [{
            "faixa": "visual", "fonte": seg.visual.fonte, "busca": seg.visual.busca,
            "etiquetas": seg.visual.etiquetas,
            "entrada_s": ini, "saida_s": fim, "arquivo": None, "status": "a_resolver",
        }]
        if seg.narracao:
            assets.append({"faixa": "narracao", "texto": seg.narracao, "fornecedor": fornecedor,
                           "entrada_s": ini, "saida_s": fim, "arquivo": None, "status": "a_gerar"})
        if seg.texto_tela:
            assets.append({"faixa": "texto_tela", "texto": seg.texto_tela,
                           "entrada_s": ini, "saida_s": fim, "status": "a_resolver"})
        for sfx in seg.sfx:
            assets.append({"faixa": "sfx", "busca": sfx, "entrada_s": ini, "saida_s": None,
                           "arquivo": None, "status": "a_resolver"})
        segmentos.append({"id": seg.id, "intencao": seg.intencao,
                          "inicio_s": ini, "fim_s": fim, "assets": assets})
        t += seg.duracao_alvo_s
    return {
        "versao_edl": 1,
        "canal": r.canal,
        "formato": r.formato,
        "resolucao": FORMATOS[r.formato]["resolucao"],
        "roteiro": _rel(rot.caminho),
        "roteiro_sha1": rot.sha1,
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "duracao_total_s": round(t, 3),
        "segmentos": segmentos,
    }


def escrever_edl(edl: dict, destino: Path) -> Path:
    destino.write_text(json.dumps(edl, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino
