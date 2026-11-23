"""Caminhos do projeto, ficha do canal e formatos (doc 3, 6.1, 6.4, 7.6)."""
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
REGISTRO_PADRAO = RAIZ / "motor" / "geradores.yaml"

# formatos conhecidos pelo motor (7.6); formato novo só por decisão de Pedro (F05)
FORMATOS = {
    "longo": {"resolucao": [1920, 1080]},
    "short_roteiro_novo": {"resolucao": [1080, 1920]},
    "short_recorte": {"resolucao": [1080, 1920]},
}


class ErroM5(Exception):
    """Erro que interrompe o comando. O motor nunca chuta (F07)."""


def ler_yaml(caminho: Path):
    try:
        return yaml.safe_load(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ErroM5(f"arquivo não encontrado: {caminho}")
    except yaml.YAMLError as e:
        raise ErroM5(f"YAML inválido em {caminho}: {e}")


def pasta_canal(canal: str) -> Path:
    pasta = RAIZ / "canais" / canal
    if not (pasta / "ficha.yaml").is_file():
        raise ErroM5(f"canal desconhecido: '{canal}' (não existe canais/{canal}/ficha.yaml)")
    return pasta


def ler_ficha(canal: str) -> dict:
    ficha = ler_yaml(pasta_canal(canal) / "ficha.yaml")
    if not isinstance(ficha, dict):
        raise ErroM5(f"ficha do canal '{canal}' vazia ou mal formada")
    return ficha


def conferir_formato(ficha: dict, canal: str, formato: str) -> None:
    if formato not in FORMATOS:
        raise ErroM5(f"formato desconhecido: '{formato}'. Conhecidos: {', '.join(FORMATOS)}")
    if formato not in (ficha.get("formatos_ativos") or []):
        raise ErroM5(f"formato '{formato}' não está ativo na ficha do canal '{canal}' (F05)")
    conferir_f18(canal, formato)


def conferir_f18(canal: str, formato: str) -> None:
    """F18: short só existe em canal com kit visual aprovado + ≥1 longo aprovado no P4.
    _amostras não é canal (9.1): a regra não se aplica. Nos canais, o motor ainda não tem
    registro do P4; até ter, recusa e avisa (decisão de Pedro antes do primeiro short)."""
    if not formato.startswith("short") or canal == "_amostras":
        return
    raise ErroM5(f"short recusado no canal '{canal}' (F18): o motor ainda não tem registro de kit "
                 "aprovado e de longo aprovado no P4 para conferir a pré-condição")


def fornecedor_voz(ficha: dict, formato: str) -> str | None:
    entrada = (ficha.get("fornecedor_voz") or {}).get(formato) or {}
    return entrada.get("fornecedor")


def resolver_roteiro(canal: str, roteiro: str) -> Path:
    """O roteiro precisa estar em canais/<canal>/roteiros/ (isolamento entre canais)."""
    caminho = Path(roteiro)
    if not caminho.is_absolute():
        caminho = (Path.cwd() / caminho).resolve()
    pasta_roteiros = (pasta_canal(canal) / "roteiros").resolve()
    if pasta_roteiros not in caminho.parents:
        raise ErroM5(f"o roteiro não pertence ao canal '{canal}': esperado dentro de {pasta_roteiros}")
    if not caminho.is_file():
        raise ErroM5(f"roteiro não encontrado: {caminho}")
    return caminho
