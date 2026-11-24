"""Registro do P2 (roteiro travado): p2.yaml ao lado do roteiro, com o sha1 do roteiro aprovado.

Decisão de Pedro (24/11/2026): narração e prévia de canal só rodam se o sha1 do roteiro bater com o do P2.
Qualquer edição depois do P2 trava de novo (roteiro travado não se edita; nova versão → novo P2).
canais/_amostras não passa por portões (9.1).
"""
from datetime import datetime

import yaml

from .canal import ErroM5
from .roteiro import Roteiro


def arquivo_p2(roteiro: Roteiro):
    return roteiro.caminho.with_name("p2.yaml")


def travar(roteiro: Roteiro, pendencias: int):
    if pendencias:
        raise ErroM5(f"o P2 só fecha com a validação sem pendências: {pendencias} pendência(s) (F06)")
    arq = arquivo_p2(roteiro)
    arq.write_text(yaml.safe_dump({
        "portao": "P2",
        "aprovado_por": "Pedro",
        "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "roteiro": roteiro.caminho.name,
        "versao": roteiro.versao,
        "roteiro_sha1": roteiro.sha1,
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return arq


def exigir_p2(canal: str, roteiro: Roteiro, para_que: str) -> None:
    if canal == "_amostras":
        return
    arq = arquivo_p2(roteiro)
    if not arq.is_file():
        raise ErroM5(f"{para_que} só depois do P2: rode m5 travar quando Pedro aprovar o roteiro (F01/F03)")
    p2 = yaml.safe_load(arq.read_text(encoding="utf-8")) or {}
    if p2.get("roteiro_sha1") != roteiro.sha1:
        raise ErroM5(f"o roteiro mudou depois do P2: nova versão precisa de novo P2 antes de {para_que} (F03)")
