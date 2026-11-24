"""Template logo_flutuante: logo do canal na tela (abertura, fecho) ou ícone como marca d'água.

- abertura: logo no centro, largura_pct da tela (padrão 0.45)
- fecho: igual, um pouco acima do centro (deixa espaço para o cta_botao)
- marca_dagua: ícone no canto superior direito (marca_px, padrão 90), opacidade 0.6
Abertura e fecho entram em fade com leve escala (entrada do kit) e flutuam devagar (sobe e desce
flutuacao_px, padrão 6, a cada flutuacao_s, padrão 3). Saída: fade (saída do kit).

Arquivos e números opcionais vêm do kit (arquivos, layout_1080p).
"""
import math

from PIL import Image

from ..canal import ErroM5

from . import template
from .desenho import ease_out


def _tempo(kit, chave, padrao):
    v = kit.animacao.get(chave, padrao)
    return max(v) if isinstance(v, list) else float(v)


def _abrir(kit, rel):
    arq = (kit.pasta / "regras" / rel).resolve()
    if not arq.is_file():
        raise ErroM5(f"logo_flutuante: arquivo não encontrado: {arq} (F07)")
    return Image.open(arq).convert("RGBA")


@template("logo_flutuante")
def logo_flutuante(kit, spec, campos, n_quadros, W, H, fps):
    A = spec.get("arquivos") or {}
    L = spec.get("layout_1080p") or {}
    s = H / 1080
    modo = campos["modo"]

    n_ent = max(1, int(round(_tempo(kit, "entrada_s", 0.25) * fps)))
    n_sai = max(1, int(round(_tempo(kit, "saida_s", 0.15) * fps)))

    if modo == "marca_dagua":
        ic = _abrir(kit, A.get("icone", ""))
        lado = int(round(L.get("marca_px", 90) * s))
        ic = ic.resize((lado, int(round(ic.height * lado / ic.width))), Image.LANCZOS)
        opac = float(L.get("marca_opacidade", 0.6))
        margem = int(round(L.get("marca_margem_px", 48) * s))
        pos = (W - margem - ic.width, margem)
        for q in range(n_quadros):
            a = opac * min(1.0, (q + 1) / n_ent) * min(1.0, (n_quadros - q) / n_sai)
            quadro = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            r, g, b, al = ic.split()
            quadro.alpha_composite(Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a)))), pos)
            yield quadro
        return

    logo = _abrir(kit, A.get("logo", ""))
    larg = int(round(W * float(L.get("largura_pct", 0.45))))
    if larg > logo.width * 1.1:
        raise ErroM5(f"logo_flutuante: a logo tem {logo.width} px; ampliar para {larg} px perde nitidez")
    logo = logo.resize((larg, int(round(logo.height * larg / logo.width))), Image.LANCZOS)
    cy = H / 2 if modo == "abertura" else H * float(L.get("fecho_centro_y_pct", 0.40))
    amp = L.get("flutuacao_px", 6) * s
    periodo = float(L.get("flutuacao_s", 3.0))

    for q in range(n_quadros):
        u = min(1.0, (q + 1) / n_ent)
        a = u * min(1.0, (n_quadros - q) / n_sai)
        esc = 0.94 + 0.06 * ease_out(u)
        img = logo if esc >= 1 else logo.resize((int(logo.width * esc), int(logo.height * esc)), Image.BILINEAR)
        if a < 1:
            r, g, b, al = img.split()
            img = Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))
        dy = amp * math.sin(2 * math.pi * q / fps / periodo)
        quadro = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        quadro.alpha_composite(img, (int(round(W / 2 - img.width / 2)), int(round(cy - img.height / 2 + dy))))
        yield quadro
