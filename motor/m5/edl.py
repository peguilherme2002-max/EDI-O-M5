"""Geração do EDL (edl.json): segmento → assets com tempos de entrada e saída (doc 3, 6.5).

Regras de resolução (determinísticas, sem IA — o motor nunca chuta, F07):
- duração do segmento: narração + respiro; sem narração, duracao_alvo_s
- tudo em quadros (30 fps): os tempos não acumulam erro, mesmo com centenas de cortes
- visual de catálogo: primeiro clipe do índice com todas as etiquetas; usa as cenas do clipe
  em ordem, continuando de onde o segmento anterior parou (volta ao início só quando acabam)
- texto na tela: template texto_tela do kit. Entra quando a narração fala as palavras do texto
  (o maior começo do texto, mínimo 2 palavras, achado na fala); se a fala não tem essas palavras,
  entra no início do segmento. Fica TEXTO_TELA_MAX_S, sem passar do fim do segmento
"""
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from .canal import FORMATOS, RAIZ, ErroM5, pasta_canal
from .catalogo import clipes_com_etiquetas
from .roteiro import Roteiro, Segmento
from .validacao import PENDENCIA, Resultado, _rel

FPS = 30
RESPIRO_S = 0.35          # silêncio depois da narração, antes do próximo segmento
CORTE_MIN_S = 0.6         # sobra menor que isto vira parte do corte anterior
CORTE_MAX_S = 5.0
TEXTO_TELA_MAX_S = 3.5
TEXTO_ANTECIPA_S = 0.1    # o texto aparece um pouco antes da palavra ser dita


def _q(segundos: float) -> int:
    return int(round(segundos * FPS))


def _narracoes(rot: Roteiro) -> dict:
    arq = rot.caminho.with_name("narracao.json")
    if not arq.is_file():
        return {}
    return {d["id"]: d for d in json.loads(arq.read_text(encoding="utf-8"))["segmentos"]}


def _narracao_do_segmento(seg: Segmento, narr: dict) -> dict:
    d = narr.get(seg.id)
    if not d:
        raise ErroM5(f"segmento {seg.id}: sem narração gerada (rode m5 narrar antes)")
    meta = RAIZ / Path(d["audio"]).parent / f"{d['chave']}.json"
    texto = json.loads(meta.read_text(encoding="utf-8"))["texto"] if meta.is_file() else None
    if texto != seg.narracao:
        raise ErroM5(f"segmento {seg.id}: a narração gerada não corresponde ao texto atual do roteiro "
                     "(rode m5 narrar de novo para este segmento)")
    return d


def _norm(palavra: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", palavra).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sem_acento.lower())


def _inicio_texto_na_fala(texto: str, narr: dict) -> float | None:
    """Segundos (dentro da narração) em que a fala diz o começo do texto na tela; None se não diz."""
    meta = RAIZ / Path(narr["audio"]).parent / f"{narr['chave']}.json"
    palavras = json.loads(meta.read_text(encoding="utf-8"))["palavras"] if meta.is_file() else []
    fala = [_norm(p["palavra"]) for p in palavras]
    alvo = [w for w in (_norm(x) for x in texto.split()) if w]
    minimo = min(2, len(alvo))
    for tam in range(len(alvo), minimo - 1, -1):          # maior começo do texto primeiro
        trecho = alvo[:tam]
        for i in range(len(fala) - tam + 1):
            if fala[i:i + tam] == trecho:
                return palavras[i]["inicio_s"]
    return None


def _clipe(canal: str, seg: Segmento) -> dict:
    achados = clipes_com_etiquetas(canal, seg.visual.etiquetas)
    if not achados:
        raise ErroM5(f"segmento {seg.id}: nenhum clipe do catálogo com as etiquetas {seg.visual.etiquetas} (F07)")
    pasta = pasta_canal(canal) / "catalogo" / achados[0]["id"]
    dados = json.loads((pasta / "clipe.json").read_text(encoding="utf-8"))
    dados["video"] = pasta / "video.mp4"
    return dados


def _cortes(clipe: dict, cursor: dict, total_q: int, inicio_q: int) -> list[dict]:
    cenas = clipe["cenas"]
    dur_clipe_q = _q(clipe["duracao_s"])
    cortes, feito = [], 0
    while feito < total_q:
        cena = cenas[cursor.get(clipe["id"], 0) % len(cenas)]
        cursor[clipe["id"]] = cursor.get(clipe["id"], 0) + 1
        ini_q = _q(cena["inicio_s"])
        tam = min(_q(cena["fim_s"]) - ini_q, _q(CORTE_MAX_S), total_q - feito)
        if total_q - feito - tam < _q(CORTE_MIN_S):          # sobra curta: estende este corte
            tam = min(total_q - feito, dur_clipe_q - ini_q)
        if tam <= 0:
            continue
        cortes.append({
            "clipe": clipe["id"], "cena": cena["n"], "arquivo": _rel(clipe["video"]),
            "origem_inicio_q": ini_q, "quadros": tam,
            "entrada_q": inicio_q + feito, "saida_q": inicio_q + feito + tam,
        })
        feito += tam
    return cortes


def gerar_edl(r: Resultado) -> dict:
    # pendência aberta = algo sem gerador; o motor não monta linha do tempo chutando (F06, F07)
    if r.pendencias:
        ids = [s.segmento.id for s in r.segmentos if s.marca == PENDENCIA]
        raise ErroM5(f"EDL recusado: {r.pendencias} segmento(s) com pendência ({', '.join(ids)}). "
                     "Resolva pela 9.5 e valide de novo.")
    rot = r.roteiro
    narr = _narracoes(rot)
    cursor: dict = {}
    t_q = 0
    segmentos = []
    for seg in rot.segmentos:
        n = _narracao_do_segmento(seg, narr) if seg.narracao else None
        dur_q = _q(n["duracao_s"] + RESPIRO_S) if n else _q(seg.duracao_alvo_s)
        if seg.visual.fonte != "catalogo":
            raise ErroM5(f"segmento {seg.id}: a montagem ainda não sabe usar visual '{seg.visual.fonte}' "
                         "(capacidade nova: 9.5)")
        if seg.sfx:
            raise ErroM5(f"segmento {seg.id}: a montagem ainda não sabe usar sfx (capacidade nova: 9.5)")
        texto = None
        if seg.texto_tela:
            achado = _inicio_texto_na_fala(seg.texto_tela, n) if n else None
            entrada = t_q + (max(0, int((achado - TEXTO_ANTECIPA_S) * FPS)) if achado is not None else 0)
            texto = {"texto": seg.texto_tela, "entrada_q": entrada,
                     "saida_q": min(t_q + dur_q, entrada + _q(TEXTO_TELA_MAX_S)),
                     "alinhado_a_fala": achado is not None}
        segmentos.append({
            "id": seg.id, "intencao": seg.intencao, "inicio_q": t_q, "fim_q": t_q + dur_q,
            "cortes": _cortes(_clipe(r.canal, seg), cursor, dur_q, t_q),
            "narracao": None if not n else {"arquivo": n["audio"], "entrada_q": t_q, "duracao_s": n["duracao_s"]},
            "texto_tela": texto,
        })
        t_q += dur_q
    return {
        "versao_edl": 2,
        "canal": r.canal,
        "formato": r.formato,
        "resolucao": FORMATOS[r.formato]["resolucao"],
        "fps": FPS,
        "roteiro": _rel(rot.caminho),
        "roteiro_sha1": rot.sha1,
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "duracao_total_s": round(t_q / FPS, 3),
        "quadros": t_q,
        "segmentos": segmentos,
    }


def escrever_edl(edl: dict, destino: Path) -> Path:
    destino.write_text(json.dumps(edl, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino
