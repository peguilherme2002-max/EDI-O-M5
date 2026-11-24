"""Template contador_flip: número com um dígito por ladrilho, que giram até parar no valor.

valor "19 MI": a parte numérica ("19", aceita . e ,) vira ladrilhos; o resto ("MI") é a unidade, ao lado.
Ladrilhos alternam cor_1 (sólida) e cor_2 (gradiente vertical). Rótulo embaixo; fonte_dado vira pílula
em cima; cadeado (variação cofre) desenha um cadeado à esquerda.

Animação: o grupo entra em fade com leve escala (tempo de entrada do kit); os dígitos rolam para cima
e param da esquerda para a direita, o último em giro_total_s (padrão 1.5). Saída: fade (saída do kit).
Opcionais no kit (layout_1080p): ladrilho.largura_px/altura_px/vao_px, numero.altura_maiuscula_px,
rotulo.altura_maiuscula_px, pilula.*, giro_total_s.
"""
import re

from PIL import Image, ImageDraw

from ..canal import ErroM5

from . import template
from .desenho import SUPER, Tela, ease_out, escrever, fonte_por_maiuscula, largura


def _gradiente_vertical(w, h, cores):
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    n = len(cores) - 1
    for y in range(h):
        t = y / max(1, h - 1) * n
        i = min(int(t), n - 1)
        f = t - i
        a, b = cores[i], cores[i + 1]
        d.line([(0, y), (w, y)], fill=tuple(int(a[c] + (b[c] - a[c]) * f) for c in range(4)))
    return img


def _cadeado(d, x, y, w, h, cor):
    """Cadeado: arco em cima e corpo retangular embaixo (x, y = canto superior esquerdo)."""
    esp = w * 0.16
    corpo_y = y + h * 0.42
    d.arc([x + w * 0.18, y, x + w * 0.82, y + h * 0.75], 180, 360, fill=cor, width=int(esp))
    d.rectangle([x + w * 0.18, y + h * 0.37 - 1, x + w * 0.18 + esp, corpo_y], fill=cor)
    d.rectangle([x + w * 0.82 - esp, y + h * 0.37 - 1, x + w * 0.82, corpo_y], fill=cor)
    d.rounded_rectangle([x, corpo_y, x + w, y + h], radius=w * 0.12, fill=cor)


@template("contador_flip")
def contador_flip(kit, spec, campos, n_quadros, W, H, fps):
    L = spec.get("layout_1080p") or {}
    s = H / 1080
    k = s * SUPER
    Ld, N, R, Pl = L.get("ladrilho") or {}, L.get("numero") or {}, L.get("rotulo") or {}, L.get("pilula") or {}

    valor = str(campos["valor"]).strip()
    m = re.match(r"^([\d.,]*\d)\s*(.*)$", valor)
    if not m:
        raise ErroM5(f"contador_flip: valor '{valor}' não começa por número")
    numero, unidade = m.group(1), m.group(2).upper()
    rotulo = str(campos["rotulo"]).upper() if R.get("caixa_alta", True) else str(campos["rotulo"])
    fonte_dado = campos.get("fonte_dado")
    cadeado = campos.get("cadeado", False)

    lw, lh = Ld.get("largura_px", 150), Ld.get("altura_px", 200)
    vao = Ld.get("vao_px", 14)
    cantos = Ld.get("cantos_px", 16)
    alt_num = N.get("altura_maiuscula_px", 120)
    f_num = fonte_por_maiuscula(kit.fonte(N.get("fonte", "impacto")), alt_num * k)
    cor_num = kit.cor(N.get("cor", "principal"))                 # dígito (sobre o ladrilho)
    cor_uni = kit.cor(N.get("cor_unidade", N.get("cor", "principal")))   # unidade e separadores (sobre o fundo)
    alt_rot = R.get("altura_maiuscula_px", 40)
    esp_rot = R.get("espacamento", kit.espacamento(R.get("fonte", "apoio")))
    f_rot = fonte_por_maiuscula(kit.fonte(R.get("fonte", "apoio")), alt_rot * k)

    # ---------- diagrama (px de 1080p) ----------
    pecas = []                                      # ("lad", dígito) ou ("sep", caractere)
    for c in numero:
        pecas.append(("lad", int(c)) if c.isdigit() else ("sep", c))
    larg_sep = alt_num * 0.35
    larg_lads = sum(lw if t == "lad" else larg_sep for t, _ in pecas) + vao * (len(pecas) - 1)
    larg_uni = largura(unidade, f_num) / k if unidade else 0
    vao_uni = 30 if unidade else 0
    cad_w, cad_h = (lh * 0.55, lh * 0.7) if cadeado else (0, 0)
    vao_cad = 36 if cadeado else 0
    total_w = cad_w + vao_cad + larg_lads + vao_uni + larg_uni
    if total_w > W / s - 120:
        raise ErroM5(f"contador_flip: valor '{valor}' largo demais para a tela")

    alt_pil = Pl.get("altura_maiuscula_px", 20)
    vao_pil = Pl.get("vao_px", 28)
    vao_rot = R.get("vao_px", 44)
    total_h = (alt_pil + 24 + vao_pil if fonte_dado else 0) + lh + vao_rot + alt_rot
    x0 = W / s / 2 - total_w / 2
    y = 1080 / 2 - total_h / 2

    est = Tela(W, H)                                # parte parada: pílula, cadeado, unidade, rótulo

    def P(x, yy):
        return x * k, yy * k

    if fonte_dado:
        txt = str(fonte_dado).upper()
        f_pil = fonte_por_maiuscula(kit.fonte("apoio", "pilula"), alt_pil * k)
        esp_pil = Pl.get("espacamento", 0.15)
        pw = largura(txt, f_pil, esp_pil) / k + 44
        ph = alt_pil + 24
        px = W / s / 2 - pw / 2
        est.d.rounded_rectangle([*P(px, y), *P(px + pw, y + ph)], radius=ph / 2 * k,
                                fill=kit.cor(Pl.get("fundo", "texto")))
        escrever(est.d, *P(px + 22, y + 12), txt, f_pil, kit.cor(Pl.get("cor", "fundo")), esp_pil)
        y += ph + vao_pil
    lad_y = y
    x = x0
    if cadeado:
        _cadeado(est.d, *P(x, lad_y + (lh - cad_h) / 2), cad_w * k, cad_h * k, kit.cor("destaque"))
        x += cad_w + vao_cad
    posicoes = []                                   # (x, dígito) de cada ladrilho
    for tipo, v in pecas:
        if tipo == "lad":
            posicoes.append((x, v))
            x += lw + vao
        else:
            escrever(est.d, *P(x + larg_sep / 2 - largura(v, f_num) / k / 2, lad_y + (lh + alt_num) / 2 - alt_num),
                     v, f_num, cor_uni)
            x += larg_sep + vao
    if unidade:
        escrever(est.d, *P(x - vao + vao_uni, lad_y + (lh - alt_num) / 2), unidade, f_num, cor_uni)
    rw = largura(rotulo, f_rot, esp_rot) / k
    escrever(est.d, *P(W / s / 2 - rw / 2, lad_y + lh + vao_rot), rotulo, f_rot,
             kit.cor(R.get("cor", "texto")), esp_rot)
    parado = est.final()

    # ladrilhos (fundo) e dígitos 0–9, na resolução de saída
    tw, th = int(round(lw * s)), int(round(lh * s))
    mascara = Image.new("L", (tw * SUPER, th * SUPER), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, tw * SUPER - 1, th * SUPER - 1], radius=cantos * k, fill=255)
    mascara = mascara.resize((tw, th), Image.LANCZOS)
    c1 = Ld.get("cor_1", "texto")
    c2 = Ld.get("cor_2", "positivo_gradiente")

    def fundo_lad(papel):
        if papel in kit.papeis:
            img = _gradiente_vertical(tw, th, kit.gradiente(papel))
        else:
            img = Image.new("RGBA", (tw, th), kit.cor(papel))
        img.putalpha(mascara)
        return img
    fundos = [fundo_lad(c1), fundo_lad(c2)]
    digitos = []
    for dgt in range(10):
        t = Tela(tw, th)
        dw = largura(str(dgt), f_num) / k
        escrever(t.d, (lw / 2 - dw / 2) * k, (lh / 2 - alt_num / 2) * k, str(dgt), f_num, cor_num)
        digitos.append(t.final())

    def ladrilho(i, pos):
        """pos: posição contínua do rolo (inteiro = dígito parado)."""
        base = fundos[i % 2].copy()
        atual, frac = int(pos) % 10, pos - int(pos)
        camada = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        dy = int(round(frac * th))
        camada.alpha_composite(digitos[atual], (0, -dy) if dy else (0, 0))
        if dy:
            camada.alpha_composite(digitos[(atual + 1) % 10], (0, th - dy))
        r, g, b, a = camada.split()
        a = Image.composite(a, Image.new("L", a.size, 0), mascara)
        camada = Image.merge("RGBA", (r, g, b, a))
        base.alpha_composite(camada)
        return base

    # ---------- animação ----------
    giro = float(L.get("giro_total_s", 1.5))
    ent = kit.animacao.get("entrada_s", 0.25)
    n_ent = max(1, int(round((max(ent) if isinstance(ent, list) else float(ent)) * fps)))
    sai = kit.animacao.get("saida_s", 0.15)
    n_sai = max(1, int(round((max(sai) if isinstance(sai, list) else float(sai)) * fps)))
    n_lad = len(posicoes)
    paradas = [giro * (0.55 + 0.45 * (i + 1) / n_lad) for i in range(n_lad)]   # da esquerda para a direita
    voltas = [12 + 3 * i for i in range(n_lad)]                                # números que cada um rola

    for q in range(n_quadros):
        t = q / fps
        quadro = parado.copy()
        for i, (lx, dgt) in enumerate(posicoes):
            u = min(1.0, t / paradas[i])
            pos = dgt - voltas[i] * (1 - ease_out(u)) + 10 * voltas[i]          # +10·voltas: sempre positivo
            quadro.alpha_composite(ladrilho(i, pos), (int(round(lx * s)), int(round(lad_y * s))))
        a = min(1.0, (q + 1) / n_ent) * min(1.0, (n_quadros - q) / n_sai)
        esc = 0.94 + 0.06 * ease_out((q + 1) / n_ent)
        if esc < 1:
            w2, h2 = int(W * esc), int(H * esc)
            menor = quadro.resize((w2, h2), Image.BILINEAR)
            quadro = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            quadro.alpha_composite(menor, ((W - w2) // 2, (H - h2) // 2))
        if a < 1:
            r, g, b, al = quadro.split()
            quadro = Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))
        yield quadro
