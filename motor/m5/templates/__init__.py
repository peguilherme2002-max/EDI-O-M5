"""Motor de templates (F0.4): cada template do kit vira uma camada animada com transparência.

- cada template é um módulo reutilizável (F11) registrado por nome com @template("nome")
- recebe o kit do canal (cores/fontes por papel), a especificação do template no kit e os campos
  vindos do roteiro (texto_tela); devolve os quadros RGBA (Pillow)
- os quadros viram um vídeo com alfa (.mov qtrle) que a montagem sobrepõe ao vídeo
- medidas do kit estão em 1080p; o motor escala para a resolução de saída
"""
import subprocess
from pathlib import Path
from typing import Callable, Iterator

from PIL import Image

from ..canal import ErroM5
from ..kit import Kit

RENDERERS: dict[str, Callable] = {}
FALA: dict[str, str] = {}   # template → campo de texto que segue a fala (recebe _palavras: [[inicio_s, fim_s], ...])


def template(nome: str, fala: str | None = None):
    def registrar(fn):
        RENDERERS[nome] = fn
        if fala:
            FALA[nome] = fala
        return fn
    return registrar


def conferir_campos(spec: dict, campos: dict) -> list[str]:
    """Erros de campo (obrigatório faltando, tipo, tamanho, valores). Usado pelo m5 validar."""
    erros = []
    definicao = spec.get("campos") or {}
    for nome, regra in definicao.items():
        regra = regra or {}
        valor = campos.get(nome)
        if valor is None:
            if regra.get("obrigatorio"):
                erros.append(f"campo obrigatório '{nome}' faltando")
            continue
        tipo = regra.get("tipo")
        if tipo == "int" and not (isinstance(valor, int) and not isinstance(valor, bool)):
            erros.append(f"campo '{nome}' deve ser número inteiro")
        if tipo == "bool" and not isinstance(valor, bool):
            erros.append(f"campo '{nome}' deve ser verdadeiro/falso")
        if tipo == "lista_texto" and not (isinstance(valor, list) and all(isinstance(v, str) for v in valor)):
            erros.append(f"campo '{nome}' deve ser lista de textos")
        if "valores" in regra and valor not in regra["valores"]:
            erros.append(f"campo '{nome}' = {valor!r} fora de {regra['valores']}")
        maximo = regra.get("maximo_caracteres")
        if maximo and isinstance(valor, str) and len(valor) > maximo:
            erros.append(f"campo '{nome}' com {len(valor)} caracteres (máximo {maximo})")
    desconhecidos = [c for c in campos if c not in definicao and c not in ("template", "inicio_s", "duracao_s")
                    and not c.startswith("_")]   # _palavras etc.: postos pelo motor, não pelo roteiro
    if desconhecidos:
        erros.append(f"campos desconhecidos: {', '.join(desconhecidos)}")
    return erros


def quadros(kit: Kit, nome: str, campos: dict, dur_s: float, W: int, H: int, fps: int) -> Iterator[Image.Image]:
    if nome not in RENDERERS:
        raise ErroM5(f"o motor ainda não sabe desenhar o template '{nome}' (capacidade nova: 9.5)")
    spec = kit.template(nome)
    erros = conferir_campos(spec, campos)
    if erros:
        raise ErroM5(f"template '{nome}': " + "; ".join(erros))
    return RENDERERS[nome](kit, spec, campos, int(round(dur_s * fps)), W, H, fps)


def renderizar(kit: Kit, nome: str, campos: dict, dur_s: float, W: int, H: int, fps: int, destino: Path) -> Path:
    """Gera a camada do template como vídeo com transparência (.mov, qtrle)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
                             "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "qtrle", str(destino)],
                            stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for q in quadros(kit, nome, campos, dur_s, W, H, fps):
            proc.stdin.write(q.tobytes())
    finally:
        proc.stdin.close()
        erro = proc.stderr.read().decode("utf-8", "replace")
        proc.wait()
    if proc.returncode != 0:
        raise ErroM5(f"ffmpeg falhou ao gerar o template '{nome}': {erro[-300:]}")
    return destino


# registra os templates construídos
from . import barra_progresso_lista, citacao, cta_botao, contador_flip, legenda_karaoke, lista_item, logo_flutuante, numero_gigante, transicao_bloco  # noqa: E402,F401
