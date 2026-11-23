"""Utilidades de desenho e animação comuns aos templates."""
from PIL import Image, ImageDraw

SUPER = 3       # superamostragem: desenha 3× maior e reduz → bordas suaves


def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t ** 3


def estrela(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, cor) -> None:
    """Estrela de 5 pontas centrada em (cx, cy) com raio externo r."""
    import math
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    draw.polygon(pts, fill=cor)


class Tela:
    """Camada RGBA superamostrada; .final() devolve na resolução de saída."""

    def __init__(self, W: int, H: int, x0: int = 0, y0: int = 0, w: int | None = None, h: int | None = None):
        self.W, self.H = W, H
        self.x0, self.y0 = x0, y0
        self.w, self.h = w or W, h or H
        self.img = Image.new("RGBA", (self.w * SUPER, self.h * SUPER), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def p(self, v: float) -> float:
        return v * SUPER

    def final(self) -> Image.Image:
        """Quadro inteiro (W×H) com a região desenhada no lugar."""
        reduzida = self.img.resize((self.w, self.h), Image.LANCZOS)
        if (self.x0, self.y0, self.w, self.h) == (0, 0, self.W, self.H):
            return reduzida
        quadro = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        quadro.paste(reduzida, (self.x0, self.y0))
        return quadro
