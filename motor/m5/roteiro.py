"""Leitura do roteiro_mestre.yaml (campos da 6.5)."""
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from .canal import ErroM5, ler_yaml

INTENCOES = {"gancho", "contexto", "desenvolvimento", "revelacao", "humor", "transicao", "cta"}
FONTES = {"catalogo", "web", "gerado"}
CAMPOS = ("id", "intencao", "narracao", "visual", "texto_tela", "sfx", "duracao_alvo_s")
CAMPOS_VISUAL = ("fonte", "busca", "etiquetas")


@dataclass
class Visual:
    fonte: str
    busca: str          # fonte=gerado: nome do tipo de asset a gerar (ex.: contador)
    etiquetas: list[str] = field(default_factory=list)
    dur_s: float | None = None   # só na lista de cortes; mapa único = o segmento inteiro


@dataclass
class Segmento:
    id: str
    intencao: str
    narracao: str        # texto + tags de voz; vazio = segmento sem narração
    visual: list[Visual]   # um item por corte; o mapa único vira lista de um item sem dur_s
    texto_tela: str | dict | None   # texto simples (template texto_tela do kit) ou {template: <nome>, campos...}
    sfx: list[str]
    duracao_alvo_s: float


@dataclass
class Roteiro:
    caminho: Path
    sha1: str
    titulo: str | None
    versao: str | None
    segmentos: list[Segmento]

    @property
    def duracao_total_s(self) -> float:
        return sum(s.duracao_alvo_s for s in self.segmentos)


def _texto(valor, nome, erros, onde, obrigatorio=True):
    if valor is None:
        if obrigatorio:
            erros.append(f"{onde}: campo '{nome}' vazio")
        return None
    if not isinstance(valor, str):
        erros.append(f"{onde}: campo '{nome}' deve ser texto")
        return None
    valor = valor.strip()
    if obrigatorio and not valor:
        erros.append(f"{onde}: campo '{nome}' vazio")
    return valor


def _lista_textos(valor, nome, erros, onde):
    if valor is None:
        return []
    if isinstance(valor, str):
        valor = [valor]
    if not isinstance(valor, list) or not all(isinstance(v, str) and v.strip() for v in valor):
        erros.append(f"{onde}: campo '{nome}' deve ser uma lista de textos")
        return []
    return [v.strip() for v in valor]


def _visual(vis, nome, erros, onde, com_dur) -> Visual | None:
    campos = CAMPOS_VISUAL + (("dur_s",) if com_dur else ())
    if not isinstance(vis, dict):
        erros.append(f"{onde}: {nome} deve ser um mapa com {', '.join(campos)}")
        return None
    faltam_v = [c for c in campos if c not in vis]
    sobram_v = [c for c in vis if c not in campos]
    if faltam_v:
        erros.append(f"{onde}: {nome} sem campos: {', '.join(faltam_v)}")
    if sobram_v:
        erros.append(f"{onde}: {nome} com campos desconhecidos: {', '.join(sobram_v)}")
    if faltam_v or sobram_v:
        return None
    fonte = _texto(vis["fonte"], f"{nome}.fonte", erros, onde)
    if fonte and fonte not in FONTES:
        erros.append(f"{onde}: {nome}.fonte '{fonte}' fora de {sorted(FONTES)}")
    busca = _texto(vis["busca"], f"{nome}.busca", erros, onde)
    etiquetas = _lista_textos(vis["etiquetas"], f"{nome}.etiquetas", erros, onde)
    dur = None
    if com_dur:
        dur = vis["dur_s"]
        if isinstance(dur, bool) or not isinstance(dur, (int, float)) or dur <= 0:
            erros.append(f"{onde}: {nome}.dur_s deve ser um número maior que zero")
            return None
        dur = float(dur)
    return Visual(fonte or "", busca or "", etiquetas, dur)


def _segmento(bruto, pos, erros) -> Segmento | None:
    onde = f"segmento {pos}"
    if not isinstance(bruto, dict):
        erros.append(f"{onde}: deve ser um mapa com os campos {', '.join(CAMPOS)}")
        return None
    if isinstance(bruto.get("id"), (str, int)):
        onde = f"segmento '{bruto['id']}'"
    faltam = [c for c in CAMPOS if c not in bruto]
    sobram = [c for c in bruto if c not in CAMPOS]
    if faltam:
        erros.append(f"{onde}: faltam campos: {', '.join(faltam)}")
    if sobram:
        erros.append(f"{onde}: campos desconhecidos: {', '.join(sobram)}")
    if faltam:
        return None

    sid = str(bruto["id"]).strip()
    intencao = _texto(bruto["intencao"], "intencao", erros, onde)
    if intencao and intencao not in INTENCOES:
        erros.append(f"{onde}: intencao '{intencao}' fora de {sorted(INTENCOES)}")
    narracao = _texto(bruto["narracao"], "narracao", erros, onde, obrigatorio=False) or ""
    if isinstance(bruto["texto_tela"], dict):
        texto_tela = dict(bruto["texto_tela"])
        nome = texto_tela.get("template")
        if not isinstance(nome, str) or not nome.strip():
            erros.append(f"{onde}: texto_tela como mapa precisa do campo 'template' (nome de um template do kit)")
        else:
            texto_tela["template"] = nome.strip()
    else:
        texto_tela = _texto(bruto["texto_tela"], "texto_tela", erros, onde, obrigatorio=False) or None
    sfx = _lista_textos(bruto["sfx"], "sfx", erros, onde)

    dur = bruto["duracao_alvo_s"]
    if isinstance(dur, bool) or not isinstance(dur, (int, float)) or dur <= 0:
        erros.append(f"{onde}: duracao_alvo_s deve ser um número maior que zero")
        dur = 0

    vis = bruto["visual"]
    visual = None
    if isinstance(vis, dict):
        v = _visual(vis, "visual", erros, onde, com_dur=False)
        visual = [v] if v else None
    elif isinstance(vis, list) and vis:
        itens = [_visual(item, f"visual[{i}]", erros, onde, com_dur=True) for i, item in enumerate(vis, 1)]
        visual = itens if all(itens) else None
    else:
        erros.append(f"{onde}: visual deve ser um mapa com {', '.join(CAMPOS_VISUAL)} "
                     f"ou uma lista não vazia de cortes com {', '.join(CAMPOS_VISUAL)}, dur_s")

    if visual is None:
        return None
    return Segmento(sid, intencao or "", narracao, visual, texto_tela, sfx, float(dur))


def ler_roteiro(caminho: Path) -> Roteiro:
    """Lê e confere a estrutura. Qualquer erro interrompe: o motor não chuta (F07)."""
    dados = ler_yaml(caminho)
    titulo = versao = None
    if isinstance(dados, dict):
        titulo = dados.get("titulo")
        versao = dados.get("versao")
        dados = dados.get("segmentos")
    if not isinstance(dados, list) or not dados:
        raise ErroM5(f"{caminho}: o roteiro precisa ter uma lista 'segmentos' não vazia")

    erros: list[str] = []
    segmentos = [s for i, b in enumerate(dados, 1) if (s := _segmento(b, i, erros))]
    ids = [s.id for s in segmentos]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    if repetidos:
        erros.append(f"ids repetidos: {', '.join(repetidos)}")
    if erros:
        raise ErroM5("roteiro com erros de estrutura:\n  - " + "\n  - ".join(erros))

    sha1 = hashlib.sha1(caminho.read_bytes()).hexdigest()
    return Roteiro(caminho, sha1, titulo, None if versao is None else str(versao), segmentos)
