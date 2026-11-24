"""Template citacao: frase de alguém à esquerda, sem caixa, com marca-texto que corre com a fala.

O fundo escurece (escurecimento.opacidade, padrão 0.5) para dar leitura. Barra vertical à esquerda,
frase em várias linhas, autor embaixo. Se houver trecho_marcado, o marca-texto cresce sobre cada
palavra do trecho enquanto ela é dita (_palavras: tempos da narração, M5 7.4) e a palavra marcada
troca de cor. Entrada: fade (entrada do kit). Saída: fade (saída do kit) no fim da duração.

Do layout_1080p do kit: posicao (x 140–1000), barra, frase, autor, marca_texto.
Opcionais: frase.altura_maiuscula_px (38), autor.altura_maiuscula_px (24), entrelinha (1.6), escurecimento.
"""
import re

from PIL import Image

from ..canal import ErroM5

from . import template
from .desenho import SUPER, Tela, escrever, fonte_por_maiuscula, largura


def _limpa(p):
    return re.sub(r"[^\w]", "", p.lower())


def _tempo(kit, chave, padrao):
    v = kit.animacao.get(chave, padrao)
    return max(v) if isinstance(v, list) else float(v)


@template("citacao", fala="frase")
def citacao(kit, spec, campos, n_quadros, W, H, fps):
    L = spec.get("layout_1080p") or {}
    s = H / 1080
    k = s * SUPER
    B, Fr, Au, M = L.get("barra") or {}, L.get("frase") or {}, L.get("autor") or {}, L.get("marca_texto") or {}
    x_ini, x_fim = L.get("x", [140, 1000])

    frase = str(campos["frase"])
    autor = str(campos.get("autor") or "")          # sem autor: frase do próprio narrador
    if Au.get("caixa_alta", True):
        autor = autor.upper()
    palavras = frase.split()
    tempos = campos.get("_palavras")
    if not tempos or len(tempos) != len(palavras):
        raise ErroM5(f"citacao: {len(palavras)} palavras e {len(tempos or [])} tempos da narração")

    # palavras marcadas: a sequência do trecho_marcado dentro da frase
    marcadas = set()
    trecho = campos.get("trecho_marcado")
    if trecho:
        alvo = [_limpa(p) for p in str(trecho).split()]
        limpas = [_limpa(p) for p in palavras]
        for i in range(len(limpas) - len(alvo) + 1):
            if limpas[i:i + len(alvo)] == alvo:
                marcadas = set(range(i, i + len(alvo)))
                break
        if not marcadas:
            raise ErroM5(f"citacao: trecho_marcado '{trecho}' não está na frase (F07)")

    alt = Fr.get("altura_maiuscula_px", 38)
    f = fonte_por_maiuscula(kit.fonte(Fr.get("fonte", "texto"), Fr.get("peso", "semibold")), alt * k)
    alt_au = Au.get("altura_maiuscula_px", 24)
    esp_au = Au.get("espacamento", 0.2)
    f_au = fonte_por_maiuscula(kit.fonte(Au.get("fonte", "apoio")), alt_au * k)
    barra_w = B.get("largura_px", 8)
    tx = x_ini + barra_w + 36
    larg_max = x_fim - tx
    espaco = f.getlength(" ") / k

    # quebra de linhas
    linhas, atual, w_atual = [], [], 0.0
    for i, p in enumerate(palavras):
        wp = f.getlength(p) / k
        if atual and w_atual + espaco + wp > larg_max:
            linhas.append(atual)
            atual, w_atual = [i], wp
        else:
            w_atual = w_atual + (espaco if atual else 0) + wp
            atual.append(i)
    linhas.append(atual)

    entre = alt * Fr.get("entrelinha", 1.6)
    vao_au = Au.get("vao_px", 44)
    altura_bloco = alt + (len(linhas) - 1) * entre + ((vao_au + alt_au) if autor else 0)
    y0 = 1080 / 2 - altura_bloco / 2
    pos = {}
    for n, linha in enumerate(linhas):
        x = tx
        for i in linha:
            pos[i] = (x, y0 + n * entre)
            x += f.getlength(palavras[i]) / k + espaco

    # ---------- camada fixa ----------
    t = Tela(W, H)

    def P(x, y):
        return x * k, y * k

    folga = alt * 0.35
    t.d.rectangle([*P(x_ini, y0 - folga), *P(x_ini + barra_w, y0 + altura_bloco + folga * 0.4)],
                  fill=kit.cor(B.get("cor", "principal")))
    cor_txt = kit.cor(Fr.get("cor", "texto"))
    for i, p in enumerate(palavras):
        escrever(t.d, *P(*pos[i]), p, f, cor_txt)
    if autor:
        escrever(t.d, *P(tx, y0 + (len(linhas) - 1) * entre + alt + vao_au), autor, f_au,
                 kit.cor(Au.get("cor", "destaque")), esp_au)
    fixa = t.final()

    # marca-texto de cada palavra marcada (recorte pronto para crescer da esquerda para a direita)
    cor_marca = kit.cor(M.get("cor", "destaque"))
    cor_marcado = kit.cor(M.get("texto_marcado", "contorno_texto"))
    pad_v, pad_h = alt * 0.32, alt * 0.18
    marcas = {}
    for i in sorted(marcadas):
        x, y = pos[i]
        wp = f.getlength(palavras[i]) / k
        prox_mesma_linha = (i + 1) in marcadas and pos[i + 1][1] == y
        x0, x1 = x - pad_h, x + wp + (espaco + pad_h if prox_mesma_linha else pad_h)
        y0m, y1m = y - pad_v, y + alt + pad_v
        tm = Tela(W, H)
        tm.d.rectangle([*P(x0, y0m), *P(x1, y1m)], fill=cor_marca)
        escrever(tm.d, *P(x, y), palavras[i], f, cor_marcado)
        img = tm.final()
        caixa = (int(x0 * s), int(y0m * s), int(x1 * s) + 1, int(y1m * s) + 1)
        marcas[i] = (img.crop(caixa), caixa)

    # ---------- animação ----------
    opac = float((L.get("escurecimento") or {}).get("opacidade", 0.5))
    n_ent = max(1, int(round(_tempo(kit, "entrada_s", 0.25) * fps)))
    n_sai = max(1, int(round(_tempo(kit, "saida_s", 0.15) * fps)))

    for q in range(n_quadros):
        tq = q / fps
        a = min(1.0, (q + 1) / n_ent) * min(1.0, (n_quadros - q) / n_sai)
        quadro = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * opac * a)))
        camada = fixa.copy()
        for i, (img, (cx0, cy0, cx1, cy1)) in marcas.items():
            ini, fim = tempos[i]
            if tq < ini:
                continue
            u = min(1.0, (tq - ini) / max(1e-3, fim - ini))
            w = max(1, int(round(img.width * u)))
            camada.alpha_composite(img.crop((0, 0, w, img.height)), (cx0, cy0))
        if a < 1:
            r, g, b, al = camada.split()
            camada = Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))
        quadro.alpha_composite(camada)
        yield quadro
