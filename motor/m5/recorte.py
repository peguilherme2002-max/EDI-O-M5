"""Short de recorte (doc 7.6, 9.4): segmentos de um longo aprovado, sem nova narração.

Pedro escolhe os segmentos; o motor reaproveita o EDL do longo (cortes, narração, texto na tela),
recoloca os segmentos em sequência a partir do zero e monta em 9:16.
Saída: roteiros/<video>_recorte_<ids>/ com recorte.yaml, edl.json e a prévia.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path

import yaml

from .canal import FORMATOS, ErroM5, conferir_formato, ler_ficha
from .validacao import _rel

DURACAO_SHORT_S = (30, 60)


def criar_recorte(canal: str, formato: str, roteiro_longo: Path, ids: list[str]) -> tuple[Path, dict, list[str]]:
    if formato != "short_recorte":
        raise ErroM5("m5 recorte só funciona com --formato short_recorte")
    conferir_formato(ler_ficha(canal), canal, formato)          # inclui F18
    arq = roteiro_longo.with_name("edl.json")
    if not arq.is_file():
        raise ErroM5(f"o longo de origem não tem edl.json: {arq} (rode m5 previa nele)")
    longo = json.loads(arq.read_text(encoding="utf-8"))
    if longo.get("formato") != "longo" or longo.get("versao_edl") != 2:
        raise ErroM5("o recorte precisa de um EDL de formato longo (versão 2)")
    por_id = {s["id"]: s for s in longo["segmentos"]}
    faltam = [i for i in ids if i not in por_id]
    if not ids or faltam:
        raise ErroM5(f"segmentos inexistentes no longo: {', '.join(faltam) or '(nenhum informado)'}")
    if len(set(ids)) != len(ids):
        raise ErroM5("segmento repetido na lista do recorte")

    t_q, segmentos = 0, []
    for i in ids:
        s = json.loads(json.dumps(por_id[i]))               # cópia
        delta = t_q - s["inicio_q"]
        s["inicio_q"] += delta
        s["fim_q"] += delta
        for c in s["cortes"]:
            c["entrada_q"] += delta
            c["saida_q"] += delta
        if s["narracao"]:
            s["narracao"]["entrada_q"] += delta
        if s["texto_tela"]:
            s["texto_tela"]["entrada_q"] += delta
            s["texto_tela"]["saida_q"] += delta
        segmentos.append(s)
        t_q = s["fim_q"]

    pasta = roteiro_longo.parent.parent / f"{roteiro_longo.parent.name}_recorte_{'-'.join(ids)}"
    pasta.mkdir(exist_ok=True)
    origem = {"roteiro_longo": _rel(roteiro_longo),
              "edl_longo_sha1": hashlib.sha1(arq.read_bytes()).hexdigest(), "segmentos": ids}
    (pasta / "recorte.yaml").write_text(
        "# short de recorte (7.6): segmentos escolhidos por Pedro de um longo aprovado; sem nova narração\n"
        + yaml.safe_dump(origem, allow_unicode=True, sort_keys=False), encoding="utf-8")

    fps = longo["fps"]
    edl = {
        "versao_edl": 2, "canal": canal, "formato": formato, "resolucao": FORMATOS[formato]["resolucao"],
        "fps": fps, "roteiro": _rel(pasta / "recorte.yaml"), "origem": origem,
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "duracao_total_s": round(t_q / fps, 3), "quadros": t_q, "segmentos": segmentos,
    }
    avisos = []
    lo, hi = DURACAO_SHORT_S
    if not lo <= edl["duracao_total_s"] <= hi:
        avisos.append(f"duração {edl['duracao_total_s']:.1f} s fora da faixa do short ({lo}–{hi} s, 7.6)")
    return pasta, edl, avisos
