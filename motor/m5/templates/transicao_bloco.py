"""Template transicao_bloco: troca de capítulo.

1. lavagem: o gradiente da assinatura cobre a tela e se dissolve (lavagem.duracao_s, padrão 0.4;
   campo lavagem=longa usa lavagem.duracao_longa_s, padrão 1.2)
2. card de vidro aparece no canto inferior esquerdo (posicao_permanente, x 215–785 · y 790–938),
   com o número do capítulo anterior no quadrado
3. rótulo "CAPÍTULO N/X" e título entram em fade (~0.25 s)
4. o número gira do anterior para o novo
O card fica até o fim da duração (o gameplay do capítulo) e sai em fade (saída do kit).
Se o título não couber, o card cresce para a direita (nunca encolhe o título abaixo de 80%).

Opcionais no kit (layout_1080p): card.{x, y, cantos_px, opacidade, contorno_opacidade},
titulo.altura_maiuscula_px (30), rotulo.altura_maiuscula_px (18), numero.altura_maiuscula_px (60).
"""
import re

from PIL import Image, ImageDraw

from ..canal import ErroM5

from . import template
from .desenho import SUPER, Tela, ease_out, escrever, fonte_por_maiuscula, largura


def _tempo(kit, chave, padrao):
    v = kit.animacao.get(chave, padrao)
    return max(v) if isinstance(v, list) else float(v)


def _alfa(img, a):
    if a >= 1:
        return img
    r, g, b, al = img.split()
    return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))


@template("transicao_bloco")
def transicao_bloco(kit, spec, campos, n_quadros, W, H, fps):
    L = spec.get("layout_1080p") or {}
    s = H / 1080
    k = s * SUPER
    Lv, Ro, Ti, Nu, C = (L.get(c) or {} for c in ("lavagem", "rotulo", "titulo", "numero", "card"))

    numero, total = int(campos["numero"]), int(campos["total"])
    if not 1 <= numero <= total:
        raise ErroM5(f"transicao_bloco: capítulo {numero} fora de 1–{total}")
    titulo = str(campos["titulo"])
    rot_txt = re.sub(r"\bN\b", str(numero), str(Ro.get("texto", "CAPÍTULO N/X")))
    rot_txt = re.sub(r"\bX\b", str(total), rot_txt)
    if Ro.get("caixa_alta", True):
        rot_txt = rot_txt.upper()

    # posição permanente do card: "x 215–785 · y 790–938"
    m = re.findall(r"(\d+)\s*[–-]\s*(\d+)", str(L.get("posicao_permanente", "")))
    (cx0, cx1), (cy0, cy1) = ([(int(a), int(b)) for a, b in m] + [(215, 785), (790, 938)])[:2] if len(m) >= 2 \
        else ((215, 785), (790, 938))
    cantos = C.get("cantos_px", 24)
    ch = cy1 - cy0
    pad = 18
    q = ch - 2 * pad                                       # quadrado do número
    qx0, qy0 = cx0 + pad, cy0 + pad
    tx = qx0 + q + 26

    alt_tit = alt_tit_kit = Ti.get("altura_maiuscula_px", 30)
    arq_tit = kit.fonte(Ti.get("fonte", "impacto"))
    f_tit = fonte_por_maiuscula(arq_tit, alt_tit * k)
    alt_rot = Ro.get("altura_maiuscula_px", 18)
    esp_rot = Ro.get("espacamento", 0.2)
    f_rot = fonte_por_maiuscula(kit.fonte(Ro.get("fonte", "apoio")), alt_rot * k)
    limite = W / s - 60
    while tx + largura(titulo, f_tit) / k + 30 > limite and alt_tit > alt_tit_kit * 0.8:
        alt_tit -= 0.5
        f_tit = fonte_por_maiuscula(arq_tit, alt_tit * k)
    precisa = tx + max(largura(titulo, f_tit), largura(rot_txt, f_rot, esp_rot)) / k + 30
    if precisa > limite:
        raise ErroM5(f"transicao_bloco: título largo demais ({titulo!r})")
    cx1 = max(cx1, precisa)

    def P(x, y):
        return x * k, y * k

    # card vazio (vidro escuro + contorno claro fino + quadrado do número)
    tc = Tela(W, H)
    tc.d.rounded_rectangle([*P(cx0, cy0), *P(cx1, cy1)], radius=cantos * k,
                           fill=kit.cor(C.get("fundo", "fundo"), C.get("opacidade", 0.72)),
                           outline=kit.cor("texto", C.get("contorno_opacidade", 0.3)), width=int(2 * k))
    tc.d.rounded_rectangle([*P(qx0, qy0), *P(qx0 + q, qy0 + q)], radius=cantos * 0.5 * k, fill=kit.cor("fundo"))
    card = tc.final()

    # rótulo + título (bloco centrado na vertical do card)
    vao = 16
    bloco = alt_rot + vao + alt_tit_kit
    by = cy0 + (ch - bloco) / 2
    tt = Tela(W, H)
    escrever(tt.d, *P(tx, by), rot_txt, f_rot, kit.cor(Ro.get("cor", "principal")), esp_rot)
    escrever(tt.d, *P(tx, by + alt_rot + vao + (alt_tit_kit - alt_tit)), titulo, f_tit, kit.cor(Ti.get("cor", "texto")))
    textos = tt.final()

    # números (anterior e novo) dentro do quadrado, para o giro
    alt_num = Nu.get("altura_maiuscula_px", 60)
    f_num = fonte_por_maiuscula(kit.fonte(Nu.get("fonte", "impacto")), alt_num * k)
    qw = int(round(q * s))

    def img_num(n):
        t = Tela(qw, qw)
        txt = str(n) if n > 0 else ""
        if txt:
            escrever(t.d, (q / 2 - largura(txt, f_num) / k / 2) * k, (q / 2 - alt_num / 2) * k, txt, f_num,
                     kit.cor(Nu.get("cor", "destaque")))
        return t.final()
    n_ant, n_novo = img_num(numero - 1), img_num(numero)
    mascara = Image.new("L", (qw * SUPER, qw * SUPER), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, qw * SUPER - 1, qw * SUPER - 1], radius=cantos * 0.5 * k, fill=255)
    mascara = mascara.resize((qw, qw), Image.LANCZOS)

    def num_rolando(u):
        camada = Image.new("RGBA", (qw, qw), (0, 0, 0, 0))
        dy = int(round(ease_out(u) * qw))
        camada.alpha_composite(n_ant, (0, -dy))
        camada.alpha_composite(n_novo, (0, qw - dy))
        r, g, b, a = camada.split()
        return Image.merge("RGBA", (r, g, b, Image.composite(a, Image.new("L", a.size, 0), mascara)))

    # lavagem: gradiente diagonal da assinatura
    cores = kit.gradiente(Lv.get("cores", "assinatura_gradiente"))
    pw, ph = 192, 108
    lav = Image.new("RGBA", (pw, ph))
    px = lav.load()
    for yy in range(ph):
        for xx in range(pw):
            tt_ = (xx / pw * 0.7 + yy / ph * 0.3) * (len(cores) - 1)
            i = min(int(tt_), len(cores) - 2)
            fr = tt_ - i
            px[xx, yy] = tuple(int(cores[i][c] + (cores[i + 1][c] - cores[i][c]) * fr) for c in range(3)) + (255,)
    lav = lav.resize((W, H), Image.BILINEAR)

    # ---------- linha do tempo ----------
    dur_lav = float(Lv.get("duracao_longa_s", 1.2) if campos.get("lavagem") == "longa" else Lv.get("duracao_s", 0.4))
    n_lav = max(2, int(round(dur_lav * fps)))
    q_card = int(round(0.75 * dur_lav * fps))            # o card nasce enquanto a lavagem se dissolve
    n_fade_card = max(1, int(round(_tempo(kit, "entrada_s", 0.2) * fps)))
    q_txt = q_card + n_fade_card
    n_txt = max(1, int(round(0.25 * fps)))
    q_giro = q_txt + n_txt + int(round(0.1 * fps))
    n_giro = max(1, int(round(0.25 * fps)))
    n_sai = max(1, int(round(_tempo(kit, "saida_s", 0.15) * fps)))
    pos_num = (int(round(qx0 * s)), int(round(qy0 * s)))

    for f in range(n_quadros):
        quadro = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fim = min(1.0, (n_quadros - f) / n_sai)
        if f >= q_card:
            a = min(1.0, (f - q_card + 1) / n_fade_card) * fim
            c = card.copy()
            if f < q_giro:
                c.alpha_composite(n_ant, pos_num)
            elif f < q_giro + n_giro:
                c.alpha_composite(num_rolando((f - q_giro + 1) / n_giro), pos_num)
            else:
                c.alpha_composite(n_novo, pos_num)
            if f >= q_txt:
                c.alpha_composite(_alfa(textos, min(1.0, (f - q_txt + 1) / n_txt)))
            quadro.alpha_composite(_alfa(c, a))
        if f < n_lav:                                      # lavagem por cima: sobe e se dissolve
            u = (f + 1) / n_lav
            a = (u / 0.45) if u < 0.45 else max(0.0, (1 - u) / 0.55)
            quadro.alpha_composite(_alfa(lav, 0.92 * min(1.0, a)))
        yield quadro
