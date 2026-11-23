"""Checagem de saúde: m5 checar (doc 7.8, F24). Sem IA, ~0 tokens.

Confere:
  1. ferramentas nas versões travadas (F23): requirements.txt, package-lock.json, versoes_sistema.txt
  2. chaves presentes no .env (sem mostrar valores — F19) e destino do backup acessível
  3. espaço em disco (pasta do projeto e pasta temporária da montagem)
  4. registro de capacidades consistente com os geradores existentes
  5. Git sem pendências e último push feito
Saída: ok, ou a lista do que falhou. Se falhar, nada roda antes de resolver (F24).
"""
import hashlib
import importlib.metadata as md
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import dotenv_values

from .canal import RAIZ, REGISTRO_PADRAO, ErroM5
from .registro import ler_registro

DISCO_MIN_GB = 20
NODE_PADRAO = Path(r"C:\Program Files\nodejs")


@dataclass
class Item:
    grupo: str
    nome: str
    ok: bool
    detalhe: str = ""


def _rodar(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).rstrip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, f"{type(e).__name__}: {e}"


def _exe(nome: str) -> str | None:
    for alvo in (f"{nome}.cmd", f"{nome}.exe", nome):      # no Windows o npm é npm.cmd
        achado = shutil.which(alvo)
        if achado:
            return achado
    for ext in (".cmd", ".exe", ""):
        p = NODE_PADRAO / f"{nome}{ext}"
        if p.is_file():
            return str(p)
    return None


# ---------- 1. versões travadas ----------

def _norm_pacote(nome: str) -> str:
    return re.sub(r"[-_.]+", "-", nome).lower()


def _versoes_pip() -> list[Item]:
    itens = []
    instalados = {_norm_pacote(d.metadata["Name"]): d.version for d in md.distributions()}
    for linha in (RAIZ / "motor" / "requirements.txt").read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "==" not in linha:
            continue
        nome, ver = linha.split("==", 1)
        atual = instalados.get(_norm_pacote(nome))
        if atual != ver:
            itens.append(Item("versões", f"pip {nome}", False, f"travado {ver}, instalado {atual or 'ausente'}"))
    if not itens:
        itens.append(Item("versões", "pacotes Python (requirements.txt)", True))
    return itens


def _versoes_npm() -> list[Item]:
    lock = json.loads((RAIZ / "motor" / "package-lock.json").read_text(encoding="utf-8"))
    itens = []
    for caminho, info in (lock.get("packages") or {}).items():
        if not caminho:
            continue
        pj = RAIZ / "motor" / caminho / "package.json"
        atual = json.loads(pj.read_text(encoding="utf-8")).get("version") if pj.is_file() else None
        if atual != info.get("version"):
            itens.append(Item("versões", f"npm {caminho}", False,
                              f"travado {info.get('version')}, instalado {atual or 'ausente'}"))
    return itens or [Item("versões", "pacotes JS (package-lock.json)", True)]


def _travado(texto: str, chave: str) -> str | None:
    m = re.search(rf"^{re.escape(chave)}\s+(\S+)", texto, re.M)
    return m.group(1) if m else None


def _versoes_sistema() -> list[Item]:
    txt = (RAIZ / "motor" / "versoes_sistema.txt").read_text(encoding="utf-8")
    itens = []

    def comparar(nome, esperado, obtido, contem=False):
        ok = esperado is not None and obtido is not None and (esperado in obtido if contem else esperado == obtido)
        itens.append(Item("versões", nome, ok, "" if ok else f"travado {esperado}, encontrado {obtido or 'ausente'}"))

    comparar("python", _travado(txt, "python"), sys.version.split()[0])
    node = _exe("node")
    comparar("node", _travado(txt, "node"), _rodar([node, "--version"])[1].strip().lstrip("v") if node else None)
    npm = _exe("npm")
    comparar("npm", _travado(txt, "npm"), _rodar([npm, "--version"])[1].strip() if npm else None)
    comparar("git", _travado(txt, "git"), _rodar(["git", "--version"])[1].strip().replace("git version ", ""))
    cod, saida = _rodar(["ffmpeg", "-version"])
    comparar("ffmpeg", _travado(txt, "ffmpeg"), saida.splitlines()[0] if cod == 0 and saida else None, contem=True)

    m = re.search(r"driver gpu\s+.*?driver (\S+?),", txt)
    cod, saida = _rodar(["powershell", "-NoProfile", "-Command",
                         "(Get-CimInstance Win32_VideoController).DriverVersion"])
    comparar("driver da GPU", m.group(1) if m else None, saida if cod == 0 else None, contem=True)

    wdir = Path(r"A:\ferramentas\whisper.cpp")
    m = re.search(r"whisper\.cpp\s+.*?commit (\w+)", txt)
    cod, saida = _rodar(["git", "-C", str(wdir), "rev-parse", "--short", "HEAD"])
    comparar("whisper.cpp (commit)", m.group(1) if m else None, saida.strip() if cod == 0 else None)
    cli = wdir / "build" / "bin" / "Release" / "whisper-cli.exe"
    itens.append(Item("versões", "whisper.cpp (binário Vulkan)", cli.is_file(), "" if cli.is_file() else f"ausente: {cli}"))

    m = re.search(r"sha1 ([0-9a-f]{40})\s+(\S+\.bin)", txt)
    modelo = Path(m.group(2)) if m else None
    if modelo and modelo.is_file():
        h = hashlib.sha1()
        with open(modelo, "rb") as f:
            for bloco in iter(lambda: f.read(8 << 20), b""):
                h.update(bloco)
        comparar("modelo whisper (sha1)", m.group(1), h.hexdigest())
    else:
        itens.append(Item("versões", "modelo whisper", False, f"ausente: {modelo}"))
    return itens


# ---------- 2. chaves e destino do backup ----------

def _chaves() -> list[Item]:
    env = dotenv_values(RAIZ / ".env") if (RAIZ / ".env").is_file() else {}
    # a chave da API vale para tudo; a voz de produção só é exigida quando um canal real ativo
    # usa a ElevenLabs (as amostras da construção usam voz de teste)
    precisa = set()
    for ficha in (RAIZ / "canais").glob("*/ficha.yaml"):
        dados = yaml.safe_load(ficha.read_text(encoding="utf-8")) or {}
        if dados.get("status") != "ativo":
            continue
        for formato in dados.get("formatos_ativos") or []:
            forn = ((dados.get("fornecedor_voz") or {}).get(formato) or {}).get("fornecedor")
            if forn == "elevenlabs":
                precisa.add("ELEVENLABS_API_KEY")
                if ficha.parent.name != "_amostras":
                    precisa.add("ELEVENLABS_VOICE_ID")
    itens = [Item("chaves", k, bool(env.get(k)), "" if env.get(k) else "vazia ou ausente no .env")
             for k in sorted(precisa)]
    destino = env.get("M5_BACKUP_DESTINO")
    if not destino:
        itens.append(Item("chaves", "M5_BACKUP_DESTINO", False, "destino do backup de mídia não definido no .env (6.6)"))
    else:
        ok = Path(destino).is_dir()
        itens.append(Item("chaves", "destino do backup", ok, "" if ok else f"inacessível: {destino}"))
    return itens


# ---------- 3. disco ----------

def _disco() -> list[Item]:
    itens = []
    for nome, pasta in (("disco do projeto", RAIZ), ("disco temporário (montagem)", Path(tempfile.gettempdir()))):
        livre = shutil.disk_usage(pasta).free / 1024 ** 3
        ok = livre >= DISCO_MIN_GB
        itens.append(Item("disco", f"{nome} ({pasta.drive or pasta})", ok,
                          f"{livre:.0f} GB livres" + ("" if ok else f" (mínimo {DISCO_MIN_GB} GB; arquivar no backup — 6.6)")))
    return itens


# ---------- 4. registro de capacidades ----------

def _registro() -> list[Item]:
    try:
        registro = ler_registro(REGISTRO_PADRAO)
    except ErroM5 as e:
        return [Item("registro", "geradores.yaml", False, str(e))]
    itens = []
    for g in registro:
        modulo = g.gerador.split()[0]
        arq = RAIZ / "motor" / Path(*modulo.split(".")).with_suffix(".py")
        if not arq.is_file():
            itens.append(Item("registro", f"{g.tipo} → {modulo}", False, f"módulo não existe: {arq.relative_to(RAIZ)}"))
    return itens or [Item("registro", f"geradores.yaml ({len(registro)} entradas)", True)]


# ---------- 5. Git ----------

def _git() -> list[Item]:
    itens = []
    cod, saida = _rodar(["git", "status", "--porcelain"], cwd=RAIZ)
    pend = [l for l in saida.splitlines() if l.strip()] if cod == 0 else ["git status falhou"]
    itens.append(Item("git", "sem pendências", not pend,
                      "" if not pend else f"{len(pend)} arquivo(s) sem commit: " + ", ".join(l[3:] for l in pend[:5])))
    cod, saida = _rodar(["git", "fetch", "--quiet", "origin"], cwd=RAIZ, timeout=60)
    if cod != 0:
        itens.append(Item("git", "último push feito", False, f"não consegui falar com o remoto: {saida[-200:]}"))
        return itens
    cod, saida = _rodar(["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"], cwd=RAIZ)
    try:
        frente, atras = (int(x) for x in saida.split())
    except ValueError:
        itens.append(Item("git", "último push feito", False, f"sem ramo remoto configurado: {saida[-200:]}"))
        return itens
    ok = frente == 0 and atras == 0
    itens.append(Item("git", "último push feito", ok,
                      "" if ok else f"{frente} commit(s) sem push, {atras} commit(s) do remoto não baixados"))
    return itens


def checar() -> list[Item]:
    itens = []
    for grupo in (_versoes_pip, _versoes_npm, _versoes_sistema, _chaves, _disco, _registro, _git):
        try:
            itens += grupo()
        except Exception as e:                      # uma checagem quebrada também é falha
            itens.append(Item(grupo.__name__.strip("_"), "checagem", False, f"{type(e).__name__}: {e}"))
    return itens
