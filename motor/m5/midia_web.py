"""Mídia web do canal (visual.fonte=web): imagem ou vídeo já baixado e registrado no manifest de assets.

Regra (sem IA, F07): vale a primeira entrada do manifest que tem TODAS as etiquetas do visual.
Só entram entradas com o campo "etiquetas". Caminho do arquivo:
- manifest.yaml (grupos de listas): relativo a canais/<canal>/assets/
- manifest.jsonl (uma entrada por linha): relativo à raiz do projeto (como a narração grava)
Ex. (manifest.yaml): web: [{arquivo: web/trevor.png, origem: "<url>", data: 2026-11-24, etiquetas: [trevor]}]
"""
import json
from pathlib import Path

from .canal import RAIZ, ErroM5, ler_yaml, pasta_canal

IMAGEM = (".png", ".jpg", ".jpeg", ".webp")
VIDEO = (".mp4", ".mov", ".webm", ".mkv")


def _entradas(canal: str) -> list[tuple[dict, Path]]:
    assets = pasta_canal(canal) / "assets"
    saida = []
    arq = assets / "manifest.yaml"
    if arq.is_file():
        dados = ler_yaml(arq) or {}
        grupos = dados.values() if isinstance(dados, dict) else [dados]
        for g in grupos:
            for e in g if isinstance(g, list) else []:
                if isinstance(e, dict) and e.get("etiquetas") and e.get("arquivo"):
                    saida.append((e, assets / e["arquivo"]))
    arq = assets / "manifest.jsonl"
    if arq.is_file():
        for linha in arq.read_text(encoding="utf-8").splitlines():
            if linha.strip():
                e = json.loads(linha)
                if e.get("etiquetas") and e.get("arquivo"):
                    saida.append((e, RAIZ / e["arquivo"]))
    return saida


def midias_com_etiquetas(canal: str, etiquetas: list[str]) -> list[tuple[dict, Path]]:
    pedidas = {e.strip().lower() for e in etiquetas if e.strip()}
    if not pedidas:
        return []
    return [(e, p) for e, p in _entradas(canal)
            if pedidas <= {str(x).strip().lower() for x in e["etiquetas"]}]


def tipo_midia(arquivo: Path) -> str:
    ext = arquivo.suffix.lower()
    if ext in IMAGEM:
        return "imagem"
    if ext in VIDEO:
        return "video"
    raise ErroM5(f"mídia web de tipo desconhecido: {arquivo.name} (F07)")


def midia(canal: str, etiquetas: list[str], onde: str) -> tuple[str, Path]:
    """(tipo, arquivo) da mídia web; ErroM5 se não houver ou o arquivo não existir (F07)."""
    achadas = midias_com_etiquetas(canal, etiquetas)
    if not achadas:
        raise ErroM5(f"{onde}: nenhuma mídia web no manifest do canal com as etiquetas {etiquetas} (F07)")
    _, arq = achadas[0]
    if not arq.is_file():
        raise ErroM5(f"{onde}: mídia web registrada, mas o arquivo não existe: {arq} (F07)")
    return tipo_midia(arq), arq
