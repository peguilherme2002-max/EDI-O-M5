"""Registro de capacidades: motor/geradores.yaml (doc 7.2)."""
from dataclasses import dataclass
from pathlib import Path

from .canal import FORMATOS, ErroM5, ler_yaml

CAMPOS = ("tipo", "gerador", "formatos", "teto", "status")
STATUS = {"em_teste", "aprovado"}


@dataclass
class Gerador:
    tipo: str
    gerador: str
    formatos: list[str]
    teto: str
    status: str


def ler_registro(caminho: Path) -> list[Gerador]:
    dados = ler_yaml(caminho)
    if not isinstance(dados, dict) or not isinstance(dados.get("geradores"), list):
        raise ErroM5(f"{caminho}: esperado um mapa com a lista 'geradores'")
    erros, saida = [], []
    for i, e in enumerate(dados["geradores"], 1):
        onde = f"geradores.yaml, entrada {i}"
        if not isinstance(e, dict) or sorted(e) != sorted(CAMPOS):
            erros.append(f"{onde}: precisa ter exatamente os campos {', '.join(CAMPOS)}")
            continue
        if e["status"] not in STATUS:
            erros.append(f"{onde}: status '{e['status']}' fora de {sorted(STATUS)}")
        formatos = e["formatos"] if isinstance(e["formatos"], list) else []
        desconhecidos = [f for f in formatos if f not in FORMATOS]
        if not formatos or desconhecidos:
            erros.append(f"{onde}: formatos inválidos {e['formatos']}")
        saida.append(Gerador(str(e["tipo"]), str(e["gerador"]), formatos, str(e["teto"] or ""), str(e["status"])))
    if erros:
        raise ErroM5("registro de capacidades com erros:\n  - " + "\n  - ".join(erros))
    return saida


def buscar(registro: list[Gerador], tipo: str, formato: str) -> tuple[Gerador | None, bool]:
    """Devolve (gerador aprovado para tipo+formato, existe_em_teste)."""
    candidatos = [g for g in registro if g.tipo == tipo and formato in g.formatos]
    aprovado = next((g for g in candidatos if g.status == "aprovado"), None)
    em_teste = any(g.status == "em_teste" for g in candidatos)
    return aprovado, em_teste
