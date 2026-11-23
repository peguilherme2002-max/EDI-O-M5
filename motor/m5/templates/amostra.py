"""Amostra de template para a F0.5: o template sobre um trecho de vídeo (ou sobre a cor de fundo do kit)."""
import subprocess
import tempfile
from pathlib import Path

from ..canal import FORMATOS, ErroM5
from ..kit import Kit
from . import renderizar

FPS = 30


def converter_campos(spec: dict, pares: list[str]) -> dict:
    """['total_itens=15', 'item_atual=3'] → {'total_itens': 15, 'item_atual': 3}, com o tipo do kit."""
    definicao = spec.get("campos") or {}
    campos = {}
    for par in pares:
        if "=" not in par:
            raise ErroM5(f"campo mal escrito: '{par}' (use nome=valor)")
        nome, valor = par.split("=", 1)
        nome = nome.strip()
        tipo = (definicao.get(nome) or {}).get("tipo")
        if tipo == "int":
            try:
                campos[nome] = int(valor)
            except ValueError:
                raise ErroM5(f"campo '{nome}' deve ser número inteiro")
        elif tipo == "bool":
            campos[nome] = valor.strip().lower() in ("1", "true", "sim", "s", "yes")
        else:
            campos[nome] = valor
    return campos


def gerar_amostra(canal: str, formato: str, nome: str, pares: list[str], destino: Path,
                  fundo: Path | None = None, inicio_s: float = 0.0, dur_s: float = 5.0,
                  previa: bool = False) -> Path:
    if formato not in FORMATOS:
        raise ErroM5(f"formato desconhecido: '{formato}'")
    kit = Kit(canal)
    campos = converter_campos(kit.template(nome), pares)
    W, H = FORMATOS[formato]["resolucao"]
    if previa:
        W, H = (854, 480) if W >= H else (480, 854)
    if fundo is not None and not fundo.is_file():
        raise ErroM5(f"vídeo de fundo não encontrado: {fundo}")
    with tempfile.TemporaryDirectory(prefix="m5_tpl_") as tmp:
        camada = renderizar(kit, nome, campos, dur_s, W, H, FPS, Path(tmp) / "camada.mov")
        if fundo is not None:
            base = ["-ss", f"{inicio_s:.3f}", "-t", f"{dur_s:.3f}", "-i", str(fundo)]
            ajuste = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                      f"fps={FPS},setsar=1[b]")
        else:
            r, g, b, _ = kit.cor("fundo")
            base = ["-f", "lavfi", "-t", f"{dur_s:.3f}", "-i", f"color=c=0x{r:02x}{g:02x}{b:02x}:s={W}x{H}:r={FPS}"]
            ajuste = "[0:v]null[b]"
        destino.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *base, "-i", str(camada),
                            "-filter_complex", f"{ajuste};[b][1:v]overlay=0:0:format=auto[v]",
                            "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(destino)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise ErroM5(f"ffmpeg falhou na amostra: {r.stderr[-300:]}")
    return destino
