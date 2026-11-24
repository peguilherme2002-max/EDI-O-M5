"""Template cta_botao: botão flutuante de inscreva-se, curtir ou comente, clicado por um cursor.

Linha do tempo: o botão entra (fade + escala, entrada do kit) → o cursor chega (clique_s, padrão 1.1) →
o botão afunda e brilha na cor de clique; inscreva_se vira INSCRITO → o cursor sai. Saída: fade.
Botão em pílula na cor do kit com brilho; ícone e texto em caixa alta. Terço inferior, centralizado.

Opcionais no kit (layout_1080p): altura_px (96), centro_y (790), texto_altura_maiuscula_px (38), clique_s.
"""
from PIL import Image, ImageDraw, ImageFilter

from . import template
from .desenho import SUPER, Tela, ease_in, ease_out, escrever, fonte_por_maiuscula, largura

PADRAO = {"inscreva_se": "INSCREVA-SE", "curtir": "CURTIR", "comente": "COMENTE"}


def _tempo(kit, chave, padrao):
    v = kit.animacao.get(chave, padrao)
    return max(v) if isinstance(v, list) else float(v)


def _icone(d, tipo, x, y, t, cor):
    """Ícone no quadrado (x, y, lado t)."""
    if tipo == "inscreva_se":                       # sino
        d.pieslice([x + t * 0.18, y + t * 0.08, x + t * 0.82, y + t * 0.78], 180, 360, fill=cor)
        d.rectangle([x + t * 0.18, y + t * 0.42, x + t * 0.82, y + t * 0.72], fill=cor)
        d.polygon([(x + t * 0.08, y + t * 0.80), (x + t * 0.92, y + t * 0.80),
                   (x + t * 0.80, y + t * 0.66), (x + t * 0.20, y + t * 0.66)], fill=cor)
        d.ellipse([x + t * 0.40, y + t * 0.80, x + t * 0.60, y + t * 0.98], fill=cor)
    elif tipo == "curtir":                          # polegar para cima
        d.rounded_rectangle([x + t * 0.04, y + t * 0.42, x + t * 0.24, y + t * 0.96], radius=t * 0.04, fill=cor)
        d.rounded_rectangle([x + t * 0.30, y + t * 0.40, x + t * 0.94, y + t * 0.96], radius=t * 0.12, fill=cor)
        d.polygon([(x + t * 0.30, y + t * 0.46), (x + t * 0.48, y + t * 0.06), (x + t * 0.62, y + t * 0.10),
                   (x + t * 0.58, y + t * 0.44)], fill=cor)
    else:                                           # balão de comentário
        d.rounded_rectangle([x + t * 0.04, y + t * 0.08, x + t * 0.96, y + t * 0.74], radius=t * 0.16, fill=cor)
        d.polygon([(x + t * 0.22, y + t * 0.70), (x + t * 0.46, y + t * 0.70), (x + t * 0.18, y + t * 0.96)], fill=cor)


def _cursor(escala):
    """Seta de mouse creme com contorno escuro (imagem pequena; ponta em (0, 0))."""
    t = int(56 * escala * SUPER)
    img = Image.new("RGBA", (t, t), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(0.06, 0.04), (0.06, 0.80), (0.26, 0.62), (0.40, 0.94), (0.52, 0.88), (0.38, 0.58), (0.64, 0.58)]
    d.polygon([(px * t, py * t) for px, py in pts], fill=(255, 253, 234, 255), outline=(36, 1, 27, 255),
              width=max(1, int(t * 0.05)))
    return img.resize((t // SUPER, t // SUPER), Image.LANCZOS)


@template("cta_botao")
def cta_botao(kit, spec, campos, n_quadros, W, H, fps):
    E = spec.get("estilo") or {}
    L = spec.get("layout_1080p") or {}
    s = H / 1080
    k = s * SUPER
    B, T, I, C = (E.get(c) or {} for c in ("botao", "texto", "icone", "clique"))
    tipo = campos["tipo"]
    texto = str(campos.get("texto") or PADRAO[tipo])
    texto_clicado = "INSCRITO" if tipo == "inscreva_se" and not campos.get("texto") else texto
    if T.get("caixa_alta", True):
        texto, texto_clicado = texto.upper(), texto_clicado.upper()

    bh = L.get("altura_px", 96)
    alt_t = L.get("texto_altura_maiuscula_px", 38)
    f = fonte_por_maiuscula(kit.fonte(T.get("fonte", "apoio")), alt_t * k)
    esp = kit.espacamento(T.get("fonte", "apoio"))
    ic = bh * 0.46
    pad = bh * 0.45
    larg_txt = max(largura(texto, f, esp), largura(texto_clicado, f, esp)) / k
    bw = pad + ic + 22 + larg_txt + pad
    cx, cy = W / s / 2, L.get("centro_y", 790)
    x0, y0 = cx - bw / 2, cy - bh / 2
    margem = 60                                     # espaço para o brilho
    rx0, ry0 = int((x0 - margem) * s), int((y0 - margem) * s)
    rw, rh = int((bw + 2 * margem) * s), int((bh + 2 * margem) * s)

    def botao(cor_fundo, cor_brilho, cor_conteudo, txt):
        t = Tela(rw, rh)

        def P(x, y):
            return (x - x0 + margem) * k, (y - y0 + margem) * k
        t.d.rounded_rectangle([*P(x0, y0), *P(x0 + bw, y0 + bh)], radius=bh / 2 * k, fill=cor_fundo)
        _icone(t.d, tipo, *P(x0 + pad, cy - ic / 2), ic * k, cor_conteudo)
        tw = largura(txt, f, esp) / k
        tx = x0 + pad + ic + 22 + (larg_txt - tw) / 2
        escrever(t.d, *P(tx, cy - alt_t / 2), txt, f, cor_conteudo, esp)
        img = t.final()
        brilho = Image.new("RGBA", img.size, cor_brilho[:3] + (0,))
        brilho.putalpha(img.split()[3].filter(ImageFilter.GaussianBlur(18 * s)).point(lambda v: int(v * 0.7)))
        brilho.alpha_composite(img)
        return brilho

    normal = botao(kit.cor(B.get("cor", "principal")), kit.cor(B.get("brilho", "principal")),
                   kit.cor(I.get("cor", "texto")), texto)
    cor_clq = kit.cor(C.get("cor", "destaque"))
    clicado = botao(cor_clq, cor_clq, kit.cor("fundo"), texto_clicado)   # creme não se lê no amarelo
    cursor = _cursor(s)

    # ---------- linha do tempo ----------
    n_ent = max(1, int(round(_tempo(kit, "entrada_s", 0.25) * fps)))
    n_sai = max(1, int(round(_tempo(kit, "saida_s", 0.15) * fps)))
    q_clique = int(round(float(L.get("clique_s", 1.1)) * fps))
    q_cur_ini = max(n_ent, q_clique - int(round(0.55 * fps)))
    q_cur_sai = q_clique + int(round(0.45 * fps))
    n_cur_sai = int(round(0.4 * fps))
    n_afunda = max(2, int(round(0.15 * fps)))
    alvo = ((cx + bw * 0.18) * s, (cy + bh * 0.12) * s)
    fora = (W * 0.78, H * 1.05)

    for q in range(n_quadros):
        u = min(1.0, (q + 1) / n_ent)
        a = u * min(1.0, (n_quadros - q) / n_sai)
        img = clicado if q >= q_clique else normal
        esc = 0.85 + 0.15 * ease_out(u)
        if q_clique <= q < q_clique + n_afunda:     # afunda e volta
            v = (q - q_clique) / n_afunda
            esc *= 1 - 0.07 * (1 - abs(2 * v - 1))
        if esc != 1:
            img = img.resize((max(1, int(img.width * esc)), max(1, int(img.height * esc))), Image.BILINEAR)
        if a < 1:
            r, g, b, al = img.split()
            img = Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))
        quadro = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        quadro.alpha_composite(img, (int(rx0 + rw / 2 - img.width / 2), int(ry0 + rh / 2 - img.height / 2)))
        # cursor: chega até o botão, clica e sai
        if q_cur_ini <= q < q_cur_sai + n_cur_sai:
            if q < q_clique:
                p = ease_out((q - q_cur_ini + 1) / max(1, q_clique - q_cur_ini))
                px, py = fora[0] + (alvo[0] - fora[0]) * p, fora[1] + (alvo[1] - fora[1]) * p
            elif q < q_cur_sai:
                px, py = alvo
            else:
                p = ease_in((q - q_cur_sai + 1) / n_cur_sai)
                px, py = alvo[0] + (fora[0] - alvo[0]) * p, alvo[1] + (fora[1] - alvo[1]) * p
            quadro.alpha_composite(cursor, (int(px), int(py)))
        yield quadro
