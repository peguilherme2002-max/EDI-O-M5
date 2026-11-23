"""Template barra_progresso_lista: um segmento por item, enchendo da esquerda para a direita; ★ no fim.

Contagem regressiva (item N → 1): com o item_atual na tela, estão cheios (total − item_atual + 1)
segmentos. O segmento do item atual acende com a entrada do template (ease-out, tempo do kit).
No item 1 a ★ acende também.

Medidas do kit (layout_1080p): y, x [início, fim], segmento.espaco_px, cor_cheio, cor_vazio,
estrela_final.cor_apagada/cor_acesa. Opcionais no kit: altura_px (padrão 8), estrela_px (padrão 26),
contorno {cor, px} (contorno escuro para ler em cena clara), opacidade_vazio (padrão 1).
cor_cheio pode ser um papel de gradiente (ex.: assinatura_gradiente): a cor anda ao longo da barra.
"""
from . import template
from .desenho import Tela, ease_out, estrela


@template("barra_progresso_lista")
def barra_progresso_lista(kit, spec, campos, n_quadros, W, H, fps):
    L = spec.get("layout_1080p") or {}
    s = H / 1080                                  # escala a partir de 1080p
    total, atual = int(campos["total_itens"]), int(campos["item_atual"])
    cheios = max(0, min(total, total - atual + 1))

    x_ini, x_fim = (v * s for v in L.get("x", [60, 1825]))
    y = L.get("y", 1053) * s
    alt = L.get("altura_px", 8) * s
    espaco = (L.get("segmento") or {}).get("espaco_px", 6) * s
    est = L.get("estrela_final") or {}
    est_px = L.get("estrela_px", 26) * s
    papel_cheio = L.get("cor_cheio", "texto")
    if papel_cheio in kit.papeis:                 # gradiente ao longo da progressão
        grad = kit.gradiente(papel_cheio)

        def cor_cheio_de(i):
            pos = i / max(1, total - 1) * (len(grad) - 1)
            k = min(int(pos), len(grad) - 2) if len(grad) > 1 else 0
            f = pos - k if len(grad) > 1 else 0
            a, b = grad[k], grad[min(k + 1, len(grad) - 1)]
            return tuple(int(round(a[c] + (b[c] - a[c]) * f)) for c in range(4))
    else:
        _c = kit.cor(papel_cheio)

        def cor_cheio_de(i):
            return _c
    cor_vazio = kit.cor(L.get("cor_vazio", "apoio"), L.get("opacidade_vazio", 1.0))
    cont = L.get("contorno") or {}
    cor_cont = kit.cor(cont["cor"]) if cont.get("cor") else None
    cont_px = cont.get("px", 2) * s
    cor_est_off = kit.cor(est.get("cor_apagada", "apoio"))
    cor_est_on = kit.cor(est.get("cor_acesa", "destaque"))

    entrada = kit.animacao.get("entrada_s", [0.25])
    entrada = max(entrada) if isinstance(entrada, list) else float(entrada)
    larg_seg = (x_fim - x_ini - espaco * (total - 1)) / total

    # só a faixa da barra é desenhada (mais rápido); o resto do quadro fica transparente
    faixa_y0 = int(max(0, y - est_px))
    faixa_h = int(min(H, y + est_px) - faixa_y0)

    def desenhar(prog: float):
        t = Tela(W, H, 0, faixa_y0, W, faixa_h)
        yy = y - faixa_y0
        raio = t.p(alt / 2)
        for i in range(total):
            a = x_ini + i * (larg_seg + espaco)
            caixa = [t.p(a), t.p(yy - alt / 2), t.p(a + larg_seg), t.p(yy + alt / 2)]
            if cor_cont:
                c = t.p(cont_px)
                t.d.rounded_rectangle([caixa[0] - c, caixa[1] - c, caixa[2] + c, caixa[3] + c],
                                      radius=raio + c, fill=cor_cont)
            t.d.rounded_rectangle(caixa, radius=raio, fill=cor_vazio)
            if i < cheios - 1 or (i == cheios - 1 and prog >= 1):
                t.d.rounded_rectangle(caixa, radius=raio, fill=cor_cheio_de(i))
            elif i == cheios - 1 and prog > 0:           # segmento do item atual enchendo
                fim = a + max(alt, larg_seg * prog)
                t.d.rounded_rectangle([caixa[0], caixa[1], t.p(fim), caixa[3]], radius=raio, fill=cor_cheio_de(i))
        acesa = cheios >= total and prog >= 1
        if cor_cont:
            estrela(t.d, t.p(x_fim + espaco + est_px / 2 + 4 * s), t.p(yy), t.p(est_px / 2 + cont_px * 1.6), cor_cont)
        estrela(t.d, t.p(x_fim + espaco + est_px / 2 + 4 * s), t.p(yy), t.p(est_px / 2),
                cor_est_on if acesa else cor_est_off)
        return t.final()

    n_anim = max(1, int(round(entrada * fps)))
    fixo = None
    for i in range(n_quadros):
        if i < n_anim:
            yield desenhar(ease_out((i + 1) / n_anim))
        else:
            fixo = fixo or desenhar(1.0)
            yield fixo
