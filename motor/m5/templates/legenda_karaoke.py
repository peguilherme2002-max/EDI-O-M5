"""Template legenda_karaoke: legenda palavra por palavra no rodapé, sem caixa, com contorno e sombra.

Cada palavra aparece no instante em que é dita (_palavras: [[inicio_s, fim_s], ...], vindo dos
timestamps da narração, M5 7.4) e fica até o fim da frase. As palavras já nascem no lugar final
(a frase inteira é diagramada antes), então nada pula. Palavra-chave na cor de destaque.
Saída: some com a frase (fade com o tempo de saída do kit).

Do layout_1080p do kit: fonte, peso, caixa, cor, contorno, cor_palavra_chave, sombra.
Opcionais no kit: altura_maiuscula_px (padrão 44), base_y (1000), largura_max_px (1500), quadros_entrada (2).
"""
import re

from PIL import Image, ImageFilter

from ..canal import ErroM5

from . import template
from .desenho import SUPER, Tela, fonte_por_maiuscula


def _limpa(p: str) -> str:
    return re.sub(r"[^\w]", "", p.lower())


@template("legenda_karaoke", fala="texto")
def legenda_karaoke(kit, spec, campos, n_quadros, W, H, fps):
    L = spec.get("layout_1080p") or {}
    s = H / 1080
    k = s * SUPER
    texto = str(campos["texto"])
    if L.get("caixa", "minuscula") == "minuscula":
        texto = texto.lower()
    palavras = texto.split()
    tempos = campos.get("_palavras")
    if not tempos or len(tempos) != len(palavras):
        raise ErroM5(f"legenda_karaoke: {len(palavras)} palavras e {len(tempos or [])} tempos da narração")
    chaves = {_limpa(c) for c in (campos.get("palavra_chave") or [])}

    peso = L.get("peso", "bold")
    fonte = kit.fonte(L.get("fonte", "texto"), peso)
    alt = L.get("altura_maiuscula_px", 44)
    f = fonte_por_maiuscula(fonte, alt * k)
    esp = float((kit.fontes.get(L.get("fonte", "texto")) or {}).get("espacamento_legenda", 0.0)) * f.size
    cont = L.get("contorno") or {}
    cont_px = cont.get("espessura_px", 4) * k
    cor = kit.cor(L.get("cor", "texto"))
    cor_chave = kit.cor(L.get("cor_palavra_chave", "destaque"))
    cor_cont = kit.cor(cont.get("cor", "contorno_texto"))

    def larg(p):
        return (sum(f.getlength(c) for c in p) + esp * (len(p) - 1)) / k

    # quebra em linhas (no máximo 2) dentro da largura máxima
    larg_max = L.get("largura_max_px", 1500)
    espaco = f.getlength(" ") / k
    linhas, atual = [], []
    for i, p in enumerate(palavras):
        teste = atual + [i]
        if atual and sum(larg(palavras[j]) for j in teste) + espaco * (len(teste) - 1) > larg_max:
            linhas.append(atual)
            atual = [i]
        else:
            atual = teste
    linhas.append(atual)
    if len(linhas) > 2:
        raise ErroM5(f"legenda_karaoke: frase longa demais para 2 linhas ({len(texto)} caracteres)")

    base_y = L.get("base_y", 1000)
    entrelinha = alt * 1.75
    _, topo_h, _, base_h = f.getbbox("H")
    pos = {}                                        # palavra → (x, y do topo da maiúscula) em px de 1080p
    for n, linha in enumerate(linhas):
        y_topo = base_y - alt - (len(linhas) - 1 - n) * entrelinha
        total = sum(larg(palavras[j]) for j in linha) + espaco * (len(linha) - 1)
        x = W / s / 2 - total / 2
        for j in linha:
            pos[j] = (x, y_topo)
            x += larg(palavras[j]) + espaco

    # faixa desenhada: do topo da primeira linha à base, com folga para contorno e sombra
    fy0 = int(max(0, (base_y - alt - (len(linhas) - 1) * entrelinha - 40) * s))
    fy1 = int(min(H, (base_y + 40) * s))
    sombra = L.get("sombra", "suave")

    camadas = []
    for i, p in enumerate(palavras):
        t = Tela(W, H, 0, fy0, W, fy1 - fy0)
        x, y = pos[i]
        cx, cy = x * k, y * k - fy0 * SUPER - topo_h
        c_fill = cor_chave if _limpa(p) in chaves else cor
        for passo in ("contorno", "texto"):         # contorno primeiro: letras não cobrem o contorno das vizinhas
            xx = cx
            for c in p:
                if passo == "contorno":
                    t.d.text((xx, cy), c, font=f, fill=cor_cont, stroke_width=int(round(cont_px)), stroke_fill=cor_cont)
                else:
                    t.d.text((xx, cy), c, font=f, fill=c_fill)
                xx += f.getlength(c) + esp
        img = t.img.resize((t.w, t.h), Image.LANCZOS)
        if sombra:
            a = img.split()[3].filter(ImageFilter.GaussianBlur(6 * s)).point(lambda v: int(v * 0.6))
            sb = Image.new("RGBA", img.size, (0, 0, 0, 0))
            sb.putalpha(a)
            base = Image.new("RGBA", img.size, (0, 0, 0, 0))
            base.paste(sb, (0, int(round(4 * s))), sb)
            base.alpha_composite(img)
            img = base
        camadas.append(img)

    # ---------- animação ----------
    n_ent = max(1, int(L.get("quadros_entrada", 2)))
    saida = kit.animacao.get("saida_s", 0.15)
    n_sai = max(1, int(round((max(saida) if isinstance(saida, list) else float(saida)) * fps)))
    inicio = [int(round(t0 * fps)) for t0, _ in tempos]

    def alfa(img, a):
        r, g, b, al = img.split()
        return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))

    for q in range(n_quadros):
        faixa = Image.new("RGBA", (W, fy1 - fy0), (0, 0, 0, 0))
        fim = min(1.0, (n_quadros - q) / n_sai)
        for i, img in enumerate(camadas):
            if q < inicio[i]:
                continue
            a = min(1.0, (q - inicio[i] + 1) / n_ent) * fim
            faixa.alpha_composite(img if a >= 1 else alfa(img, a))
        quadro = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        quadro.paste(faixa, (0, fy0))
        yield quadro
