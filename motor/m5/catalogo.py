"""Captação e indexação do catálogo (doc 7.5).

- captação: yt-dlp, sob demanda (só o que o roteiro pede), um trecho ou o vídeo inteiro
- indexação automática na entrada: cortes de cena (PySceneDetect), miniaturas (ffmpeg),
  transcrição com timestamps (whisper.cpp na GPU)
- cada canal tem o seu catálogo (F17): canais/<canal>/catalogo/
    indice.json              lista dos clipes do canal
    <clipe>/video.mp4        o trecho baixado
    <clipe>/clipe.json       origem, etiquetas, cenas (com miniatura e texto falado)
    <clipe>/palavras.json    transcrição palavra a palavra
    <clipe>/miniaturas/      1 jpg por cena
"""
import json
import re
import shutil
import subprocess
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from .canal import ErroM5, conferir_formato, ler_ficha, pasta_canal
from .transcricao import transcrever_palavras

FORMATO_YTDLP = "bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/b"
NODE_PADRAO = Path(r"C:\Program Files\nodejs\node.exe")


@dataclass
class Cena:
    n: int
    inicio_s: float
    fim_s: float
    miniatura: str
    texto: str


@dataclass
class Clipe:
    id: str
    origem: dict
    etiquetas: list[str]
    duracao_s: float
    resolucao: list[int]
    cenas: list[Cena] = field(default_factory=list)
    reaproveitado: bool = False


# ---------- utilidades ----------

def segundos(valor: str | float | int | None) -> float | None:
    """'90', '1:30' ou '00:01:30' → 90.0"""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    partes = str(valor).strip().split(":")
    try:
        total = 0.0
        for p in partes:
            total = total * 60 + float(p)
        return total
    except ValueError:
        raise ErroM5(f"tempo inválido: '{valor}' (use segundos, mm:ss ou hh:mm:ss)")


def _hms(s: float) -> str:
    s = int(round(s))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def _ytdlp_base() -> list[str]:
    node = shutil.which("node") or (str(NODE_PADRAO) if NODE_PADRAO.is_file() else None)
    if not node:
        raise ErroM5("Node.js não encontrado: o yt-dlp precisa dele para o YouTube (--js-runtimes)")
    return ["yt-dlp", "--js-runtimes", f"node:{node}", "--no-playlist", "--no-warnings"]


def _ffprobe(video: Path) -> tuple[float, list[int]]:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height:format=duration", "-of", "json", str(video)],
                       capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        return round(float(d["format"]["duration"]), 3), [d["streams"][0]["width"], d["streams"][0]["height"]]
    except (ValueError, KeyError, IndexError):
        raise ErroM5(f"não consegui ler o vídeo baixado: {video}")


def _ler_indice(pasta: Path) -> dict:
    arq = pasta / "indice.json"
    return json.loads(arq.read_text(encoding="utf-8")) if arq.is_file() else {"clipes": []}


def _gravar_json(arq: Path, dados) -> None:
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------- indexação ----------

def indexar(video: Path, pasta_clipe: Path, idioma: str = "auto", transcrever: bool = True) -> tuple[list[Cena], list]:
    from scenedetect import ContentDetector, detect

    duracao, _ = _ffprobe(video)
    cortes = detect(str(video), ContentDetector())
    faixas = [(a.get_seconds(), b.get_seconds()) for a, b in cortes] or [(0.0, duracao)]

    palavras = transcrever_palavras(video, idioma) if transcrever else []
    mini = pasta_clipe / "miniaturas"
    mini.mkdir(exist_ok=True)
    cenas = []
    for n, (ini, fim) in enumerate(faixas, 1):
        jpg = mini / f"cena_{n:03d}.jpg"
        meio = ini + (fim - ini) / 2
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{meio:.3f}", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=320:-2", "-q:v", "4", str(jpg)], check=True)
        texto = " ".join(p.palavra for p in palavras if p.inicio_s < fim and p.fim_s > ini)
        cenas.append(Cena(n, round(ini, 3), round(fim, 3), jpg.relative_to(pasta_clipe).as_posix(), texto))
    return cenas, palavras


# ---------- comando ----------

def captar(canal: str, formato: str, url: str, inicio=None, fim=None,
           etiquetas: list[str] | None = None, idioma: str = "auto") -> Clipe:
    ficha = ler_ficha(canal)
    conferir_formato(ficha, canal, formato)
    ini, fim_s = segundos(inicio), segundos(fim)
    if (ini is None) != (fim_s is None) or (ini is not None and fim_s <= ini):
        raise ErroM5("informe --inicio e --fim juntos, com fim maior que início")

    r = subprocess.run(_ytdlp_base() + ["-J", "--skip-download", url],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise ErroM5(f"yt-dlp não conseguiu ler o link (fora do ar, privado ou removido?): {r.stderr.strip()[-300:]}")
    info = json.loads(r.stdout)
    vid = re.sub(r"[^A-Za-z0-9_-]", "_", str(info.get("id") or "video"))
    clipe_id = vid if ini is None else f"{vid}_{int(ini):05d}-{int(fim_s):05d}"

    pasta = pasta_canal(canal) / "catalogo"
    indice = _ler_indice(pasta)
    pasta_clipe = pasta / clipe_id
    if any(c["id"] == clipe_id for c in indice["clipes"]) and (pasta_clipe / "clipe.json").is_file():
        d = json.loads((pasta_clipe / "clipe.json").read_text(encoding="utf-8"))
        d["cenas"] = [Cena(**c) for c in d["cenas"]]
        return Clipe(**d, reaproveitado=True)          # catálogo reaproveitado, nada baixado

    pasta_clipe.mkdir(parents=True, exist_ok=True)
    video = pasta_clipe / "video.mp4"
    cmd = _ytdlp_base() + ["-f", FORMATO_YTDLP, "--merge-output-format", "mp4", "-o", str(video)]
    if ini is not None:
        cmd += ["--download-sections", f"*{_hms(ini)}-{_hms(fim_s)}", "--force-keyframes-at-cuts"]
    r = subprocess.run(cmd + [url], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not video.is_file():
        raise ErroM5(f"download falhou: {r.stderr.strip()[-300:]}")

    duracao, resolucao = _ffprobe(video)
    cenas, palavras = indexar(video, pasta_clipe, idioma)
    _gravar_json(pasta_clipe / "palavras.json", [asdict(p) for p in palavras])
    origem = {
        "url": info.get("webpage_url") or url,
        "titulo": info.get("title"),
        "canal_origem": info.get("channel") or info.get("uploader"),
        "trecho": None if ini is None else [ini, fim_s],
        "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    clipe = Clipe(clipe_id, origem, [e.strip().lower() for e in (etiquetas or []) if e.strip()],
                  duracao, resolucao, cenas)
    dados = asdict(clipe)
    dados.pop("reaproveitado")
    _gravar_json(pasta_clipe / "clipe.json", dados)

    indice["clipes"] = [c for c in indice["clipes"] if c["id"] != clipe_id] + [{
        "id": clipe_id, "titulo": origem["titulo"], "etiquetas": clipe.etiquetas,
        "duracao_s": duracao, "cenas": len(cenas), "arquivo": f"{clipe_id}/video.mp4",
    }]
    _gravar_json(pasta / "indice.json", indice)
    return clipe


def clipes_com_etiquetas(canal: str, etiquetas: list[str]) -> list[dict]:
    """Clipes do catálogo do canal que têm todas as etiquetas pedidas (regra, sem IA)."""
    pedidas = {e.strip().lower() for e in etiquetas if e.strip()}
    if not pedidas:
        return []
    indice = _ler_indice(pasta_canal(canal) / "catalogo")
    return [c for c in indice["clipes"] if pedidas <= set(c.get("etiquetas", []))]


# ---------- importação de gameplay local (ficha .md do acervo) ----------

LINHA_MD = re.compile(r"^\|\s*([\d.]+)\s*(?:[–-]\s*([\d.]+))?\s*\|(.+?)\|\s*[\d.]+\s*\|(.+?)\|\s*$")


def _sem_acento(e: str) -> str:
    """Etiquetas do catálogo sem acento (convenção do índice: 'perseguicao')."""
    return unicodedata.normalize("NFKD", e.strip().lower()).encode("ascii", "ignore").decode()


def ler_ficha_md(md: Path) -> tuple[Path, list[str], list[dict]]:
    """Ficha de gameplay (- Arquivo:, - Palavras-chave gerais:, tabelas 'inicio | Cena | foco_x | palavras-chave')."""
    texto = md.read_text(encoding="utf-8")
    arq = re.search(r"^- Arquivo:\s*(.+?)\s*$", texto, re.M)
    if not arq:
        raise ErroM5(f"ficha sem '- Arquivo:': {md} (F07)")
    video = (md.parent / arq.group(1)).resolve()
    if not video.is_file():
        raise ErroM5(f"vídeo da ficha não encontrado: {video} (F07)")
    pers = re.search(r"^- Personagem:\s*(.+)$", texto, re.M)
    base = ["gta vi", video.stem] + (["jason"] if pers and pers.group(1).lower().startswith("jason") else [])
    trechos = []
    for linha in texto.splitlines():
        m = LINHA_MD.match(linha)
        if not m:
            continue
        ini = float(m.group(1))
        fim = float(m.group(2)) if m.group(2) else ini + 2      # shortcut: linha com um só tempo vira 2 s; pedir o fim na ficha se ficar curto
        if fim <= ini:
            continue
        etq = [_sem_acento(e) for e in m.group(4).split(",") if e.strip()]
        trechos.append({"inicio": ini, "fim": fim, "titulo": m.group(3).replace("**", "").strip(), "etiquetas": etq})
    if not trechos:
        raise ErroM5(f"ficha sem linhas de cena: {md} (F07)")
    return video, base, trechos


def importar_ficha(canal: str, md: Path) -> tuple[int, int]:
    """Cada linha da ficha vira um clipe do catálogo: trecho recodificado, cortes de cena e miniaturas.
    Sem transcrição (o áudio dos clipes não entra na montagem: kit volume_clipe 0). Retoma de onde parou."""
    video, base, trechos = ler_ficha_md(md)
    pasta = pasta_canal(canal) / "catalogo"
    pasta.mkdir(exist_ok=True)
    novos = ja = 0
    for t in trechos:
        clipe_id = f"{video.stem}_{int(t['inicio']):05d}-{int(t['fim']):05d}"
        indice = _ler_indice(pasta)
        pasta_clipe = pasta / clipe_id
        if any(c["id"] == clipe_id for c in indice["clipes"]) and (pasta_clipe / "clipe.json").is_file():
            ja += 1
            continue
        pasta_clipe.mkdir(exist_ok=True)
        saida = pasta_clipe / "video.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t['inicio']:.3f}", "-to", f"{t['fim']:.3f}",
                        "-i", str(video), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", str(saida)], check=True)
        duracao, resolucao = _ffprobe(saida)
        cenas, _ = indexar(saida, pasta_clipe, transcrever=False)
        _gravar_json(pasta_clipe / "palavras.json", [])
        etiquetas = list(dict.fromkeys(base + t["etiquetas"]))
        # vídeo fora do canal (ex.: A:\pacotes_peqgameplay) guarda o caminho completo
        arquivo = video.relative_to(pasta_canal(canal)).as_posix() if video.is_relative_to(pasta_canal(canal)) else video.as_posix()
        origem = {"arquivo": arquivo, "ficha": md.name,
                  "titulo": t["titulo"], "trecho": [t["inicio"], t["fim"]],
                  "data": datetime.now().strftime("%Y-%m-%d %H:%M")}
        dados = asdict(Clipe(clipe_id, origem, etiquetas, duracao, resolucao, cenas))
        dados.pop("reaproveitado")
        _gravar_json(pasta_clipe / "clipe.json", dados)
        indice["clipes"] = [c for c in indice["clipes"] if c["id"] != clipe_id] + [{
            "id": clipe_id, "titulo": t["titulo"][:120], "etiquetas": etiquetas,
            "duracao_s": duracao, "cenas": len(cenas), "arquivo": f"{clipe_id}/video.mp4"}]
        _gravar_json(pasta / "indice.json", indice)
        novos += 1
    return novos, ja
