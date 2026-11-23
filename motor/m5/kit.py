"""Leitura do kit visual do canal (regras/kit_visual.yaml).

Cores e fontes sempre pelos PAPÉIS do kit, nunca com valores soltos no código:
trocar a paleta de um canal exige mudar um só arquivo (o kit dele). Nada de canal no motor.
"""
from pathlib import Path

from PIL import ImageColor

from .canal import ErroM5, ler_yaml, pasta_canal


class Kit:
    def __init__(self, canal: str):
        self.canal = canal
        self.pasta = pasta_canal(canal)
        dados = ler_yaml(self.pasta / "regras" / "kit_visual.yaml") or {}
        if not isinstance(dados, dict):
            raise ErroM5(f"kit_visual.yaml do canal '{canal}' mal formado")
        self.dados = dados
        self.paleta: dict = dados.get("paleta") or {}
        self.papeis: dict = dados.get("papeis_de_cor") or {}
        self.fontes: dict = dados.get("fontes") or {}
        self.templates: dict = dados.get("templates") or {}
        self.animacao: dict = dados.get("animacao") or {}

    # ---------- cores ----------
    def cor(self, papel: str, opacidade: float = 1.0) -> tuple[int, int, int, int]:
        """Cor de um papel da paleta (ex.: 'texto', 'fundo', 'destaque')."""
        valor = self.paleta.get(papel)
        if not isinstance(valor, str):
            raise ErroM5(f"kit do canal '{self.canal}': papel de cor desconhecido '{papel}' (F07)")
        r, g, b = ImageColor.getrgb(valor)[:3]
        return r, g, b, int(round(255 * max(0.0, min(1.0, opacidade))))

    def gradiente(self, papel: str) -> list[tuple[int, int, int, int]]:
        """Lista de cores de um papel de gradiente (ex.: 'assinatura_gradiente')."""
        cores = self.papeis.get(papel)
        if not isinstance(cores, list) or not cores:
            raise ErroM5(f"kit do canal '{self.canal}': gradiente desconhecido '{papel}' (F07)")
        return [(*ImageColor.getrgb(c)[:3], 255) for c in cores]

    # ---------- fontes ----------
    def fonte(self, papel: str, peso: str | None = None) -> Path:
        """Arquivo da fonte de um papel (ex.: 'impacto', 'apoio', 'texto'; peso 'bold'/'semibold'/'pilula')."""
        f = self.fontes.get(papel)
        if isinstance(f, str):                      # forma curta: "Inter Bold" → Inter-Bold.ttf
            nome = f"{f.replace(' ', '-')}.ttf"
        elif isinstance(f, dict):
            chave = {"pilula": "variante_pilula"}.get(peso or "", f"arquivo_{peso}" if peso else "arquivo")
            nome = f.get(chave) or f.get("arquivo") or f.get("arquivo_bold")
        else:
            nome = None
        if not nome:
            raise ErroM5(f"kit do canal '{self.canal}': fonte desconhecida '{papel}' {peso or ''} (F07)")
        arq = self.pasta / "assets" / "fontes" / nome
        if not arq.is_file():
            raise ErroM5(f"fonte do kit não encontrada: {arq} (F07)")
        return arq

    def espacamento(self, papel: str) -> float:
        f = self.fontes.get(papel)
        return float(f.get("espacamento", 0)) if isinstance(f, dict) else 0.0

    # ---------- templates ----------
    def template(self, nome: str) -> dict:
        spec = self.templates.get(nome)
        if not isinstance(spec, dict):
            raise ErroM5(f"template '{nome}' não existe no kit do canal '{self.canal}' (F07)")
        return spec
