"""Template lista_item: lower third do item da lista (escudo numerado, aba do selo, caixa de título).

Fica na tela o item inteiro. Entrada: o bloco desliza da esquerda (ease-out, tempo de entrada do kit),
começando um pouco depois do corte (atraso_s); como o texto está mais à direita, aparece antes do
escudo. Saída: desliza para a esquerda (ease-in, tempo de saída do kit) no fim da duração.

Tudo do layout_1080p do kit: escudo, aba_selo, caixa, titulo, subtitulo, linha_base.
Opcionais no kit: atraso_s (padrão 0.3), altura do título/subtítulo/número em px de maiúscula.
"""
from PIL import Image

from ..canal import ErroM5

from . import template
from .desenho import SUPER, Tela, ease_in, ease_out, escrever, estrela, fonte_por_maiuscula, largura


def _escudo(x0, y0, x1, y1, n=24):
    """Contorno de escudo: topo reto, laterais retas e base em ponta curva."""
    cx, joelho = (x0 + x1) / 2, y0 + (y1 - y0) * 0.58
    pts = [(x0, y0), (x1, y0), (x1, joelho)]
    for i in range(1, n + 1):                      # curva lado direito → ponta
        t = i / n
        ctrl = (x1, y0 + (y1 - y0) * 0.86)
        px = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * ctrl[0] + t ** 2 * cx
        py = (1 - t) ** 2 * joelho + 2 * (1 - t) * t * ctrl[1] + t ** 2 * y1
        pts.append((px, py))
    for i in range(1, n + 1):                      # ponta → lado esquerdo
        t = i / n
        ctrl = (x0, y0 + (y1 - y0) * 0.86)
        px = (1 - t) ** 2 * cx + 2 * (1 - t) * t * ctrl[0] + t ** 2 * x0
        py = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * ctrl[1] + t ** 2 * joelho
        pts.append((px, py))
    return pts


def _tempo(kit, chave, padrao):
    v = kit.animacao.get(chave, padrao)
    return max(v) if isinstance(v, list) else float(v)


@template("lista_item")
def lista_item(kit, spec, campos, n_quadros, W, H, fps):
    L = spec.get("layout_1080p") or {}
    s = H / 1080
    E, A, C = L.get("escudo") or {}, L.get("aba_selo") or {}, L.get("caixa") or {}
    T, Sb, LB = L.get("titulo") or {}, L.get("subtitulo") or {}, L.get("linha_base") or {}

    numero = f"{int(campos['numero']):02d}"
    selo = str(campos["selo"])
    titulo = str(campos["titulo"])
    subtitulo = str(campos["subtitulo"])
    if A.get("caixa_alta", True):
        selo = selo.upper()
    if T.get("caixa_alta", True):
        titulo = titulo.upper()
    if Sb.get("caixa_alta", True):
        subtitulo = subtitulo.upper()

    ex0, ex1 = E.get("x", [62, 250])
    ey0, ey1 = E.get("y", [772, 985])
    ay0, ay1 = A.get("y", [783, 818])
    cy0, cy1 = C.get("y", [818, 955])
    cx0 = C.get("x_inicio", 250)
    folga = C.get("folga_direita_px", 60)
    pad = C.get("margem_texto_px", 30)
    lb_y, lb_esp = LB.get("y", 953), LB.get("espessura_px", 4)

    # fontes (em px de 1080p × SUPER, para desenhar na tela superamostrada)
    k = s * SUPER
    arq_tit = kit.fonte(T.get("fonte", "impacto"))
    alt_tit = alt_tit_kit = T.get("altura_maiuscula_px", 55)
    f_tit = fonte_por_maiuscula(arq_tit, alt_tit * k)
    f_sub = fonte_por_maiuscula(kit.fonte(Sb.get("fonte", "apoio")), Sb.get("altura_maiuscula_px", 22) * k)
    f_selo = fonte_por_maiuscula(kit.fonte(A.get("texto_fonte", "apoio"), "pilula"),
                                 A.get("altura_maiuscula_px", 14) * k)
    esp_sub, esp_selo = Sb.get("espacamento", 0.2), A.get("espacamento", 0.2)

    tit_x = cx0 + pad
    limite = 1920 - 20
    larg_sub = largura(subtitulo, f_sub, esp_sub) / k
    # título longo: diminui só o necessário para caber (decisão de Pedro, 23/11/2026), até 80% do kit
    while tit_x + largura(titulo, f_tit) / k + folga > limite and alt_tit > alt_tit_kit * 0.8:
        alt_tit -= 0.5
        f_tit = fonte_por_maiuscula(arq_tit, alt_tit * k)
    larg_tit = largura(titulo, f_tit) / k
    cx1 = tit_x + max(larg_tit, larg_sub) + folga
    if cx1 > limite:
        raise ErroM5(f"lista_item: título/subtítulo largos demais para a tela ({cx1:.0f} px de 1920)")

    # aba do selo: 6 estrelas + rótulo
    est = A.get("estrelas") or {}
    n_est = int(est.get("quantidade", 6))
    est_r = (ay1 - ay0) * 0.24
    ax0 = A.get("x_inicio", 270)
    aba_pad = 16
    est_passo = est_r * 2.5
    selo_x = ax0 + aba_pad + n_est * est_passo + 10
    ax1 = selo_x + largura(selo, f_selo, esp_selo) / k + aba_pad + 8

    # ---------- desenho estático (faixa do lower third) ----------
    fy0 = int(max(0, (ey0 - 12) * s))
    fy1 = int(min(H, (ey1 + 12) * s))
    t = Tela(W, H, 0, fy0, W, fy1 - fy0)

    def P(x, y):
        return x * k, y * k - fy0 * SUPER

    fundo = kit.cor(C.get("fundo", "fundo"))
    # aba e caixa
    t.d.rectangle([*P(ax0, ay0), *P(ax1, ay1)], fill=kit.cor(A.get("fundo", "fundo")))
    t.d.rectangle([*P(cx0, cy0), *P(cx1, cy1)], fill=fundo)
    # estrelas e selo
    cor_est = kit.cor(est.get("cor", "destaque"))
    for i in range(n_est):
        ex, ey = P(ax0 + aba_pad + est_r + i * est_passo, (ay0 + ay1) / 2)
        estrela(t.d, ex, ey, est_r * k, cor_est)
    selo_topo = (ay0 + ay1) / 2 - (A.get("altura_maiuscula_px", 14)) / 2
    escrever(t.d, *P(selo_x, selo_topo), selo, f_selo, kit.cor(A.get("texto_cor", "texto")), esp_selo)
    # título e subtítulo
    # bloco título + subtítulo centralizado entre o topo da caixa e a linha de base
    alt_sub = Sb.get("altura_maiuscula_px", 22)
    vao = (cy1 - cy0) * 0.13
    bloco_topo = cy0 + ((lb_y - lb_esp / 2 - cy0) - (alt_tit_kit + vao + alt_sub)) / 2
    tit_topo = bloco_topo + (alt_tit_kit - alt_tit)          # título encolhido mantém a mesma base
    escrever(t.d, *P(tit_x, tit_topo), titulo, f_tit, kit.cor(T.get("cor", "texto")))
    sub_topo = bloco_topo + alt_tit_kit + vao
    escrever(t.d, *P(tit_x, sub_topo), subtitulo, f_sub, kit.cor(Sb.get("cor", "principal")), esp_sub)
    # linha de base, do meio do escudo ao fim da caixa
    t.d.rectangle([*P((ex0 + ex1) / 2, lb_y - lb_esp / 2), *P(cx1, lb_y + lb_esp / 2)],
                  fill=kit.cor(LB.get("cor", "texto")))
    # escudo por cima: contorno e miolo
    cont = E.get("contorno_px", 8)
    t.d.polygon([P(x, y) for x, y in _escudo(ex0, ey0, ex1, ey1)], fill=kit.cor(E.get("contorno", "texto")))
    t.d.polygon([P(x, y) for x, y in _escudo(ex0 + cont, ey0 + cont, ex1 - cont, ey1 - cont * 1.7)],
                fill=kit.cor(E.get("fundo", "fundo")))
    # número: cabe em 72% da largura do escudo
    alt_num = E.get("altura_maiuscula_px", 95)
    f_num = fonte_por_maiuscula(kit.fonte(E.get("numero_fonte", "impacto")), alt_num * k)
    while largura(numero, f_num) / k > (ex1 - ex0) * 0.72 and alt_num > 30:
        alt_num -= 3
        f_num = fonte_por_maiuscula(kit.fonte(E.get("numero_fonte", "impacto")), alt_num * k)
    num_x = (ex0 + ex1) / 2 - largura(numero, f_num) / k / 2
    num_topo = ey0 + (ey1 - ey0) * 0.44 - alt_num / 2
    escrever(t.d, *P(num_x, num_topo), numero, f_num, kit.cor(E.get("numero_cor", "texto")))

    bloco = t.final()                               # quadro inteiro, transparente fora do bloco
    vazio = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # ---------- animação ----------
    atraso = int(round(L.get("atraso_s", 0.3) * fps))
    n_ent = max(1, int(round(_tempo(kit, "entrada_s", 0.2) * fps)))
    n_sai = max(1, int(round(_tempo(kit, "saida_s", 0.15) * fps)))
    fora = int((cx1 + 40) * s)                      # deslocamento para sair inteiro da tela

    def deslocado(dx):
        q = vazio.copy()
        q.paste(bloco, (int(round(dx)), 0), bloco)
        return q

    for i in range(n_quadros):
        if i < atraso:
            yield vazio
        elif i < atraso + n_ent:
            yield deslocado(-fora * (1 - ease_out((i - atraso + 1) / n_ent)))
        elif i >= n_quadros - n_sai:
            yield deslocado(-fora * ease_in((i - (n_quadros - n_sai) + 1) / n_sai))
        else:
            yield bloco
