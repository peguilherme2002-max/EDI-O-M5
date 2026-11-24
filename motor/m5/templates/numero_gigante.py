"""Template numero_gigante: dado-chave no centro (estrelas, rótulo de cima, valor, — rótulo de baixo —).

Entrada no corte (quadro 0): o fundo escurece aos poucos (escurecimento_fundo do kit); o valor e os
rótulos vão de translúcido e borrado a sólido em poucos quadros (quadros_foco, padrão 3); as estrelas
aparecem depois (atraso_estrelas_s, padrão 0.2). Saída: some no corte seguinte (fim da duração, sem fade).

Tudo do layout_1080p do kit: valor, rotulos, estrelas, escurecimento_fundo.
Opcionais no kit: altura de maiúscula dos rótulos, vãos, tamanho das estrelas, traços do rótulo de baixo.
"""
from PIL import Image, ImageFilter

from ..canal import ErroM5

from . import template
from .desenho import SUPER, Tela, ease_out, escrever, estrela, fonte_por_maiuscula, largura


@template("numero_gigante")
def numero_gigante(kit, spec, campos, n_quadros, W, H, fps):
    L = spec.get("layout_1080p") or {}
    s = H / 1080
    k = s * SUPER
    V, R = L.get("valor") or {}, L.get("rotulos") or {}
    E, F = L.get("estrelas") or {}, L.get("escurecimento_fundo") or {}

    valor = str(campos["valor"])
    cima = campos.get("rotulo_cima")
    baixo = campos.get("rotulo_baixo")
    com_estrelas = campos.get("estrelas", True)
    if R.get("caixa_alta", True):
        cima = cima.upper() if cima else cima
        baixo = baixo.upper() if baixo else baixo

    larg_tela = W / s                                   # largura em px de 1080p
    margem = larg_tela * 0.06
    # valor: altura de maiúscula do kit; diminui só se não couber
    arq_val = kit.fonte(V.get("fonte", "impacto"))
    alt_val = V.get("altura_px", 200)
    f_val = fonte_por_maiuscula(arq_val, alt_val * k)
    while largura(valor, f_val) / k > larg_tela - 2 * margem and alt_val > 60:
        alt_val -= 2
        f_val = fonte_por_maiuscula(arq_val, alt_val * k)
    if largura(valor, f_val) / k > larg_tela - 2 * margem:
        raise ErroM5(f"numero_gigante: valor '{valor}' largo demais para a tela")

    arq_rot = kit.fonte(R.get("fonte", "apoio"))
    alt_rot = R.get("altura_maiuscula_px", 34)
    esp_rot = R.get("espacamento", 0.25)
    f_rot = fonte_por_maiuscula(arq_rot, alt_rot * k)
    vao = R.get("vao_px", 34)                           # entre rótulo e valor
    est_r = E.get("raio_px", 15)
    est_passo = est_r * 2.6
    vao_est = E.get("vao_px", 22)                       # entre estrelas e o rótulo de cima
    traco = R.get("traco_px", [70, 4])                  # comprimento, espessura dos traços do rótulo de baixo
    vao_traco = R.get("vao_traco_px", 26)

    # pilha vertical centrada na tela
    pecas = []                                          # (tipo, altura)
    if com_estrelas:
        pecas.append(("estrelas", est_r * 2))
        pecas.append(("vao", vao_est if cima else vao))
    if cima:
        pecas += [("cima", alt_rot), ("vao", vao)]
    pecas.append(("valor", alt_val))
    if baixo:
        pecas += [("vao", vao), ("baixo", alt_rot)]
    total = sum(a for _, a in pecas)
    cx = larg_tela / 2
    y = 1080 / 2 - total / 2

    texto = Tela(W, H)
    ceu = Tela(W, H)
    cor_txt = kit.cor(V.get("cor", "texto"))
    cor_rot = kit.cor(R.get("cor", "texto"))

    def P(x, yy):
        return x * k, yy * k

    for tipo, alt in pecas:
        if tipo == "estrelas":
            n = int(E.get("quantidade", 6))
            x0 = cx - (n - 1) * est_passo / 2
            for i in range(n):
                estrela(ceu.d, *P(x0 + i * est_passo, y + est_r), est_r * k, kit.cor(E.get("cor", "destaque")))
        elif tipo == "cima":
            w = largura(cima, f_rot, esp_rot) / k
            escrever(texto.d, *P(cx - w / 2, y), cima, f_rot, cor_rot, esp_rot)
        elif tipo == "valor":
            w = largura(valor, f_val) / k
            escrever(texto.d, *P(cx - w / 2, y), valor, f_val, cor_txt)
        elif tipo == "baixo":
            w = largura(baixo, f_rot, esp_rot) / k
            escrever(texto.d, *P(cx - w / 2, y), baixo, f_rot, cor_rot, esp_rot)
            meio = y + alt_rot / 2
            for lado in (-1, 1):
                xa = cx + lado * (w / 2 + vao_traco)
                xb = xa + lado * traco[0]
                texto.d.rectangle([*P(min(xa, xb), meio - traco[1] / 2), *P(max(xa, xb), meio + traco[1] / 2)],
                                  fill=cor_rot)
        y += alt

    camada_texto = texto.final()
    camada_est = ceu.final() if com_estrelas else None

    # ---------- animação ----------
    opac = float(F.get("opacidade", 0.45))
    n_esc = max(1, int(round(float(F.get("duracao_s", 0.3)) * fps)))
    n_foco = max(1, int(L.get("quadros_foco", 3)))
    atraso_est = int(round(L.get("atraso_estrelas_s", 0.2) * fps))
    borrao_max = 14 * s

    def com_alfa(img, a):
        if a >= 1:
            return img
        r, g, b, al = img.split()
        return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))

    # quadros de foco pré-calculados (translúcido e borrado → sólido)
    foco = []
    for i in range(n_foco):
        t = (i + 1) / (n_foco + 1)
        img = camada_texto.filter(ImageFilter.GaussianBlur(borrao_max * (1 - t)))
        foco.append(com_alfa(img, 0.25 + 0.75 * t))

    for i in range(n_quadros):
        a_fundo = opac * ease_out((i + 1) / n_esc)
        q = Image.new("RGBA", (W, H), (0, 0, 0, int(round(255 * a_fundo))))
        q.alpha_composite(foco[i] if i < n_foco else camada_texto)
        if camada_est is not None and i >= atraso_est:
            q.alpha_composite(camada_est)
        yield q
