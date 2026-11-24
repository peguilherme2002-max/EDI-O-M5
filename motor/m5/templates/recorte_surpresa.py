"""Template recorte_surpresa: assunto recortado (PNG transparente) entra de surpresa sobre o vídeo.

O PNG vem do manifest de assets do canal (grupo qualquer; feito pelo m5 recortar), pela regra da mídia
web: a primeira entrada com TODAS as etiquetas do campo "etiquetas" (F07: sem entrada → ErroM5).

Entrada (quadro 0, colada no corte): clarão na cor do kit que some rápido; o fundo escurece; o assunto
sobe de baixo e encolhe de um zoom (escala_inicial → 1) no tempo de entrada do kit (animacao.entrada_s,
o maior valor), curva ease-out, sem bounce; um contorno na cor do kit cola no recorte (efeito adesivo)
e, se o roteiro pedir (raios: true), raios atrás giram devagar. Saída: some em animacao.saida_s (ease-in), no fim da duração.

Campos (roteiro): etiquetas (lista_texto, obrigatório), lado (esquerda | centro | direita),
raios (bool, padrão false).
Medidas no layout_1080p do kit (todas opcionais): altura_px, margem_px, contorno {cor, px},
clarao {cor, opacidade, duracao_s}, escurecimento_fundo {opacidade, duracao_s},
raios {cor, opacidade, quantidade, giro_graus_s}, escala_inicial.
"""
import math

from PIL import Image, ImageDraw, ImageFilter

from ..canal import ErroM5
from ..midia_web import midias_com_etiquetas
from . import CONFERIR, template
from .desenho import ease_in, ease_out


def png_do_recorte(canal: str, etiquetas: list[str]):
    achadas = [(e, p) for e, p in midias_com_etiquetas(canal, etiquetas) if p.suffix.lower() == ".png"]
    if not achadas:
        raise ErroM5(f"recorte_surpresa: nenhum PNG no manifest do canal com as etiquetas {etiquetas} "
                     "(rode m5 recortar) (F07)")
    arq = achadas[0][1]
    if not arq.is_file():
        raise ErroM5(f"recorte_surpresa: PNG registrado, mas o arquivo não existe: {arq} (F07)")
    return arq


def problemas(kit, campos) -> list[str]:
    """Para a validação: o PNG pedido existe no canal?"""
    try:
        png_do_recorte(kit.canal, campos.get("etiquetas") or [])
        return []
    except ErroM5 as e:
        return [str(e)]


CONFERIR["recorte_surpresa"] = problemas


@template("recorte_surpresa")
def recorte_surpresa(kit, spec, campos, n_quadros, W, H, fps):
    L = spec.get("layout_1080p") or {}
    s = H / 1080
    A = kit.animacao
    ent = A.get("entrada_s", 0.25)
    n_ent = max(1, int(round((max(ent) if isinstance(ent, list) else float(ent)) * fps)))
    n_sai = max(1, int(round(float(A.get("saida_s", 0.15)) * fps)))

    img = Image.open(png_do_recorte(kit.canal, campos["etiquetas"])).convert("RGBA")
    alt = L.get("altura_px", 900) * s
    if img.height * (alt / img.height) > H or img.width * (alt / img.height) > W * 0.9:
        alt = min(H, img.height * (W * 0.9) / img.width)
    esc = alt / img.height
    img = img.resize((max(1, round(img.width * esc)), max(1, round(img.height * esc))), Image.LANCZOS)

    # contorno (adesivo): alfa dilatado, pintado na cor do kit, por baixo do recorte
    C = L.get("contorno") or {}
    px = max(0, int(round(C.get("px", 8) * s)))
    pad = px + 2
    base = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    if px:
        alfa = Image.new("L", base.size, 0)
        alfa.paste(img.getchannel("A"), (pad, pad))
        alfa = alfa.filter(ImageFilter.MaxFilter(2 * px + 1)).filter(ImageFilter.GaussianBlur(1))
        cor = Image.new("RGBA", base.size, kit.cor(C.get("cor", "principal")))
        cor.putalpha(alfa)
        base.alpha_composite(cor)
    base.alpha_composite(img, (pad, pad))
    assunto = base

    margem = L.get("margem_px", 80) * s
    lado = campos.get("lado", "direita")
    cx = {"esquerda": margem + assunto.width / 2, "centro": W / 2,
          "direita": W - margem - assunto.width / 2}.get(lado)
    if cx is None:
        raise ErroM5(f"recorte_surpresa: lado '{lado}' desconhecido (F07)")
    pe = H + pad                                         # base do assunto colada na borda de baixo

    # raios atrás do assunto
    R = L.get("raios") or {}
    n_raios = int(R.get("quantidade", 14)) if campos.get("raios", False) else 0
    raio = math.hypot(W, H)
    cy_raios = H - assunto.height * 0.55

    def raios(angulo: float) -> Image.Image:
        q = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(q)
        cor = kit.cor(R.get("cor", "destaque"), float(R.get("opacidade", 0.35)))
        for i in range(n_raios):
            a0 = math.radians(angulo + i * 360 / n_raios)
            a1 = a0 + math.radians(360 / n_raios / 2)
            d.polygon([(cx, cy_raios), (cx + raio * math.cos(a0), cy_raios + raio * math.sin(a0)),
                       (cx + raio * math.cos(a1), cy_raios + raio * math.sin(a1))], fill=cor)
        return q

    E = L.get("escurecimento_fundo") or {}
    op_esc = float(E.get("opacidade", 0.45))
    n_esc = max(1, int(round(float(E.get("duracao_s", 0.2)) * fps)))
    F = L.get("clarao") or {}
    n_clar = max(1, int(round(float(F.get("duracao_s", 0.15)) * fps)))
    op_clar = float(F.get("opacidade", 0.7))
    giro = float(R.get("giro_graus_s", 6))
    esc0 = float(L.get("escala_inicial", 1.3))

    for i in range(n_quadros):
        t_ent = ease_out((i + 1) / n_ent)
        t_sai = ease_in((i - (n_quadros - n_sai) + 1) / n_sai) if i >= n_quadros - n_sai else 0.0
        vis = 1 - t_sai
        q = Image.new("RGBA", (W, H), (0, 0, 0, int(round(255 * op_esc * ease_out((i + 1) / n_esc) * vis))))
        if n_raios and vis > 0:
            r = raios(giro * i / fps)
            r.putalpha(r.getchannel("A").point(lambda v: int(v * t_ent * vis)))
            q.alpha_composite(r)
        k = esc0 + (1 - esc0) * t_ent
        a = assunto if abs(k - 1) < 1e-3 else assunto.resize(
            (max(1, round(assunto.width * k)), max(1, round(assunto.height * k))), Image.BILINEAR)
        sobe = (1 - t_ent) * assunto.height * 0.35 + t_sai * assunto.height * 0.25
        x = round(cx - a.width / 2)
        y = round(pe - a.height + sobe)
        if vis < 1:
            a = a.copy()
            a.putalpha(a.getchannel("A").point(lambda v: int(v * vis)))
        q.alpha_composite(a, (x, y)) if 0 <= x and 0 <= y and x + a.width <= W and y + a.height <= H \
            else _colar(q, a, x, y)
        if i < n_clar:
            f = Image.new("RGBA", (W, H), kit.cor(F.get("cor", "texto"), op_clar * (1 - i / n_clar)))
            q.alpha_composite(f)
        yield q


def _colar(q: Image.Image, a: Image.Image, x: int, y: int) -> None:
    """alpha_composite que aceita a imagem saindo da tela."""
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(a.width, q.width - x), min(a.height, q.height - y)
    if cx1 > cx0 and cy1 > cy0:
        q.alpha_composite(a.crop((cx0, cy0, cx1, cy1)), (x + cx0, y + cy0))
