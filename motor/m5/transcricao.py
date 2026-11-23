"""Transcrição local com timestamps por palavra: whisper.cpp com Vulkan na GPU (decisão de Pedro).
Usada pela narração (modo arquivo, 7.4) e pela indexação do catálogo (7.5)."""
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .canal import ErroM5

WHISPER_DIR = Path(os.environ.get("M5_WHISPER_CPP", r"A:\ferramentas\whisper.cpp"))
WHISPER_CLI = WHISPER_DIR / "build" / "bin" / "Release" / "whisper-cli.exe"
WHISPER_MODELO = WHISPER_DIR / "models" / "ggml-large-v3-turbo.bin"


@dataclass
class Palavra:
    palavra: str
    inicio_s: float
    fim_s: float


def transcrever_palavras(midia: Path, idioma: str = "pt") -> list[Palavra]:
    """Áudio ou vídeo → palavras com início e fim (s). idioma 'auto' detecta sozinho."""
    if not WHISPER_CLI.is_file() or not WHISPER_MODELO.is_file():
        raise ErroM5(f"whisper.cpp ou modelo não encontrado em {WHISPER_DIR}")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio16k.wav"
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(midia), "-vn",
                            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise ErroM5(f"ffmpeg não conseguiu extrair o áudio de {midia}: {r.stderr[-300:]}")
        base = Path(tmp) / "saida"
        r = subprocess.run([str(WHISPER_CLI), "-m", str(WHISPER_MODELO), "-f", str(wav), "-l", idioma,
                            "-ml", "1", "-sow", "-oj", "-np", "-of", str(base)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        saida = base.with_suffix(".json")
        if r.returncode != 0 or not saida.is_file():
            raise ErroM5(f"whisper.cpp falhou (código {r.returncode}): {r.stderr[-300:]}")
        dados = json.loads(saida.read_text(encoding="utf-8", errors="replace"))
    palavras = []
    for t in dados.get("transcription", []):
        txt = t.get("text", "").strip()
        if txt and not (txt.startswith("[") and txt.endswith("]")):   # ignora marcas como [Música]
            o = t["offsets"]
            palavras.append(Palavra(txt, o["from"] / 1000, o["to"] / 1000))
    return palavras
