"""Narração — módulo trocável (doc 7.4).

Entrada: texto do segmento. Saída: áudio + timestamps por palavra.
O resto do motor não sabe qual fornecedor gerou.

- modo API (elevenlabs): por segmento, com timestamps; cache por hash → mudar 1 frase regenera só aquele segmento.
- modo arquivo (dark_planner): Pedro gera e baixa o áudio; o Whisper cria os timestamps localmente
  (whisper.cpp com Vulkan na GPU, por decisão de Pedro). Detalhes no primeiro uso real (doc 12).
"""
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import requests
from dotenv import dotenv_values

from .canal import RAIZ, ErroM5, conferir_formato, fornecedor_voz, ler_ficha, pasta_canal
from .roteiro import Roteiro

MODO_POR_FORNECEDOR = {"elevenlabs": "api", "dark_planner": "arquivo"}
MODELO_ELEVENLABS_PADRAO = "eleven_multilingual_v2"
FORMATO_AUDIO_API = "mp3_44100_128"
EXTENSOES_AUDIO = (".mp3", ".wav", ".m4a", ".flac", ".ogg")
WHISPER_DIR = Path(os.environ.get("M5_WHISPER_CPP", r"A:\ferramentas\whisper.cpp"))
WHISPER_CLI = WHISPER_DIR / "build" / "bin" / "Release" / "whisper-cli.exe"
WHISPER_MODELO = WHISPER_DIR / "models" / "ggml-large-v3-turbo.bin"


@dataclass
class Palavra:
    palavra: str
    inicio_s: float
    fim_s: float


@dataclass
class Narracao:
    segmento: str
    texto: str
    fornecedor: str
    modo: str
    chave: str
    audio: str                      # caminho relativo à raiz do projeto
    duracao_s: float
    caracteres: int
    palavras: list[Palavra] = field(default_factory=list)
    reaproveitada: bool = False     # True = veio do cache, nenhum crédito gasto


# ---------- utilidades ----------

def _rel(p: Path) -> str:
    return p.resolve().relative_to(RAIZ).as_posix()


def _duracao(audio: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(audio)], capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 3)
    except ValueError:
        raise ErroM5(f"não consegui ler a duração de {audio} (ffprobe)")


def _registrar_manifest(pasta_assets: Path, arquivo: Path, origem: str) -> None:
    linha = {"arquivo": _rel(arquivo), "origem": origem, "data": datetime.now().strftime("%Y-%m-%d %H:%M")}
    with open(pasta_assets / "manifest.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")


def _palavras_de_caracteres(chars, inicios, fins) -> list[Palavra]:
    """Junta o alinhamento por caractere em palavras; ignora tags de voz (<break .../>)."""
    palavras, atual, ini, fim, em_tag = [], "", None, None, False
    for c, a, b in zip(chars, inicios, fins):
        if c == "<":
            em_tag = True
        if em_tag:
            if c == ">":
                em_tag = False
            continue
        if c.isspace():
            if atual:
                palavras.append(Palavra(atual, round(ini, 3), round(fim, 3)))
            atual, ini = "", None
            continue
        atual += c
        ini = a if ini is None else ini
        fim = b
    if atual:
        palavras.append(Palavra(atual, round(ini, 3), round(fim, 3)))
    return palavras


# ---------- fornecedores ----------

def _elevenlabs(texto: str, voz: str, modelo: str, chave_api: str) -> tuple[bytes, list[Palavra]]:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voz}/with-timestamps"
    try:
        r = requests.post(url, params={"output_format": FORMATO_AUDIO_API},
                          headers={"xi-api-key": chave_api, "Content-Type": "application/json"},
                          json={"text": texto, "model_id": modelo}, timeout=120)
    except requests.RequestException as e:
        raise ErroM5(f"ElevenLabs fora do ar ou sem rede: {type(e).__name__}")
    if r.status_code != 200:
        try:
            detalhe = r.json().get("detail")
            detalhe = detalhe.get("message", detalhe) if isinstance(detalhe, dict) else detalhe
        except ValueError:
            detalhe = r.text[:200]
        motivo = {401: "chave inválida ou sem permissão", 402: "créditos insuficientes",
                  404: "voz não encontrada (confira ELEVENLABS_VOICE_ID)", 429: "limite de uso atingido"}
        raise ErroM5(f"ElevenLabs respondeu {r.status_code} ({motivo.get(r.status_code, 'erro')}): {detalhe}")
    dados = r.json()
    al = dados.get("alignment") or {}
    palavras = _palavras_de_caracteres(al.get("characters", []),
                                       al.get("character_start_times_seconds", []),
                                       al.get("character_end_times_seconds", []))
    return base64.b64decode(dados["audio_base64"]), palavras


def transcrever_palavras(audio: Path, idioma: str = "pt") -> list[Palavra]:
    """Timestamps por palavra com whisper.cpp (Vulkan/GPU)."""
    if not WHISPER_CLI.is_file() or not WHISPER_MODELO.is_file():
        raise ErroM5(f"whisper.cpp ou modelo não encontrado em {WHISPER_DIR}")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio16k.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(audio),
                        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)], check=True)
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
        if txt:
            o = t["offsets"]
            palavras.append(Palavra(txt, o["from"] / 1000, o["to"] / 1000))
    return palavras


# ---------- comando ----------

def _guardar(pasta: Path, chave: str, n: Narracao) -> None:
    (pasta / f"{chave}.json").write_text(json.dumps(asdict(n), ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")


def _do_cache(pasta: Path, chave: str) -> Narracao | None:
    meta = pasta / f"{chave}.json"
    if not meta.is_file():
        return None
    d = json.loads(meta.read_text(encoding="utf-8"))
    if not (RAIZ / d["audio"]).is_file():
        return None
    d["palavras"] = [Palavra(**p) for p in d["palavras"]]
    d["reaproveitada"] = True
    return Narracao(**d)


def narrar(canal: str, formato: str, roteiro: Roteiro, ids: list[str] | None = None,
           arquivos: Path | None = None, fornecedor: str | None = None,
           voz: str | None = None) -> list[Narracao]:
    # F01: nenhum crédito de voz antes do P2. O registro do P2 no motor ainda não existe;
    # até existir, só as amostras da construção podem narrar.
    if canal != "_amostras":
        raise ErroM5("narração fora de canais/_amostras ainda não liberada: falta o registro do P2 no "
                     "motor (F01). Decisão de Pedro antes do primeiro canal.")
    ficha = ler_ficha(canal)
    conferir_formato(ficha, canal, formato)
    fornecedor = fornecedor or fornecedor_voz(ficha, formato)
    modo = MODO_POR_FORNECEDOR.get(fornecedor or "")
    if not modo:
        raise ErroM5(f"fornecedor de voz desconhecido na ficha para {formato}: '{fornecedor}' (F05)")

    segs = [s for s in roteiro.segmentos if s.narracao]
    if ids:
        faltam = [i for i in ids if i not in {s.id for s in roteiro.segmentos}]
        if faltam:
            raise ErroM5(f"segmentos inexistentes no roteiro: {', '.join(faltam)}")
        sem_texto = [i for i in ids if i not in {s.id for s in segs}]
        if sem_texto:
            raise ErroM5(f"segmentos sem narração: {', '.join(sem_texto)}")
        segs = [s for s in segs if s.id in ids]

    pasta_assets = pasta_canal(canal) / "assets"
    pasta = pasta_assets / "narracao"
    pasta.mkdir(parents=True, exist_ok=True)
    saida: list[Narracao] = []

    if modo == "api":
        env = dotenv_values(RAIZ / ".env")
        chave_api, voz = env.get("ELEVENLABS_API_KEY"), voz or env.get("ELEVENLABS_VOICE_ID")
        if not chave_api or not voz:
            raise ErroM5("preencha ELEVENLABS_API_KEY e ELEVENLABS_VOICE_ID no .env (F19)")
        modelo = ((ficha.get("fornecedor_voz") or {}).get(formato) or {}).get("modelo") or MODELO_ELEVENLABS_PADRAO
        for s in segs:
            chave = hashlib.sha1(f"{fornecedor}|{voz}|{modelo}|{s.narracao}".encode()).hexdigest()[:16]
            n = _do_cache(pasta, chave)
            if n is None:
                audio_bytes, palavras = _elevenlabs(s.narracao, voz, modelo, chave_api)
                audio = pasta / f"{chave}.mp3"
                audio.write_bytes(audio_bytes)
                n = Narracao(s.id, s.narracao, fornecedor, modo, chave, _rel(audio), _duracao(audio),
                             len(s.narracao), palavras)
                _guardar(pasta, chave, n)
                _registrar_manifest(pasta_assets, audio, f"elevenlabs api, modelo {modelo}")
            n.segmento = s.id
            saida.append(n)
    else:
        if arquivos is None or not arquivos.is_dir():
            raise ErroM5("modo arquivo: informe --arquivos com a pasta dos áudios (<id do segmento>.mp3/.wav…)")
        for s in segs:
            achados = [arquivos / f"{s.id}{e}" for e in EXTENSOES_AUDIO if (arquivos / f"{s.id}{e}").is_file()]
            if len(achados) != 1:
                raise ErroM5(f"modo arquivo: esperado exatamente 1 áudio para '{s.id}' em {arquivos} "
                             f"(achados: {len(achados)})")
            origem = achados[0]
            chave = hashlib.sha1(f"{fornecedor}|".encode() + origem.read_bytes()).hexdigest()[:16]
            n = _do_cache(pasta, chave)
            if n is None:
                audio = pasta / f"{chave}{origem.suffix.lower()}"
                shutil.copyfile(origem, audio)
                n = Narracao(s.id, s.narracao, fornecedor, modo, chave, _rel(audio), _duracao(audio),
                             len(s.narracao), transcrever_palavras(audio))
                _guardar(pasta, chave, n)
                _registrar_manifest(pasta_assets, audio, f"{fornecedor}, arquivo importado {origem.name}")
            n.segmento = s.id
            saida.append(n)

    # narracao.json do vídeo: acumula os segmentos já narrados (narrar só alguns não apaga os outros)
    destino = roteiro.caminho.with_name("narracao.json")
    anteriores = {}
    if destino.is_file():
        anteriores = {d["id"]: d for d in json.loads(destino.read_text(encoding="utf-8"))["segmentos"]}
    for n in saida:
        anteriores[n.segmento] = {"id": n.segmento, "chave": n.chave, "audio": n.audio,
                                  "duracao_s": n.duracao_s, "palavras": len(n.palavras)}
    ordem = [s.id for s in roteiro.segmentos]
    destino.write_text(json.dumps({
        "canal": canal, "formato": formato, "roteiro_sha1": roteiro.sha1,
        "segmentos": sorted(anteriores.values(), key=lambda d: ordem.index(d["id"]) if d["id"] in ordem else 999),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return saida
