"""Backup externo da mídia (doc 6.6, F21).

- texto (docs, regras, roteiros, código, logs): vai pelo Git, commit + push a cada aprovação
- mídia: entregas (mp4 finais, alta importância) e narrações (média, custaram créditos)
  são copiadas para M5_BACKUP_DESTINO (HD externo ou pasta sincronizada na nuvem), definido no .env
- catálogo: sem backup obrigatório (baixa de novo)

Regras: copia só o que é novo ou mudou (tamanho ou data); nunca apaga nem sobrescreve uma versão
diferente no destino — a versão antiga fica guardada com sufixo de data (F20).
Cada execução vira uma linha em logs/backups.csv.
"""
import csv
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values

from .canal import RAIZ, ErroM5, pasta_canal

PASTAS = {"entrega": "entrega", "narracao": "assets/narracao"}


def destino_backup() -> Path:
    env = dotenv_values(RAIZ / ".env") if (RAIZ / ".env").is_file() else {}
    d = env.get("M5_BACKUP_DESTINO")
    if not d:
        raise ErroM5("defina M5_BACKUP_DESTINO no .env (HD externo ou pasta sincronizada na nuvem — 6.6)")
    p = Path(d)
    if not p.is_dir():
        raise ErroM5(f"destino do backup inacessível: {p} (HD desconectado ou pasta inexistente?)")
    return p


def fazer_backup(canal: str, arquivo_teste: bool = False) -> dict:
    origem_canal = pasta_canal(canal)
    raiz_destino = destino_backup() / "M5" / "canais" / canal
    copiados, iguais, bytes_copiados, guardados = [], 0, 0, 0
    agora = datetime.now()

    arquivos: list[tuple[Path, Path]] = []
    for rel in PASTAS.values():
        base = origem_canal / rel
        if base.is_dir():
            for f in sorted(base.rglob("*")):
                if f.is_file() and f.name != "CLAUDE.md":
                    arquivos.append((f, raiz_destino / rel / f.relative_to(base)))
    if arquivo_teste:
        teste = Path(tempfile.gettempdir()) / "m5_backup_teste.txt"
        teste.write_text(f"M5 — arquivo de teste do backup externo (C8), {agora:%Y-%m-%d %H:%M:%S}\n", encoding="utf-8")
        arquivos.append((teste, destino_backup() / "M5" / "teste" / teste.name))

    for src, dst in arquivos:
        st = src.stat()
        if dst.is_file():
            dt = dst.stat()
            if dt.st_size == st.st_size and int(dt.st_mtime) >= int(st.st_mtime):
                iguais += 1
                continue
            # versão diferente no destino: guarda a antiga, não sobrescreve (F20)
            antiga = dst.with_name(f"{dst.stem}.ate_{agora:%Y%m%d_%H%M%S}{dst.suffix}")
            dst.rename(antiga)
            guardados += 1
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if dst.stat().st_size != st.st_size:
            raise ErroM5(f"cópia incompleta: {dst}")
        copiados.append(dst)
        bytes_copiados += st.st_size

    resumo = {"data": f"{agora:%Y-%m-%d %H:%M}", "canal": canal, "destino": str(raiz_destino),
              "copiados": len(copiados), "ja_iguais": iguais, "versoes_guardadas": guardados,
              "mb_copiados": round(bytes_copiados / 1024 ** 2, 1)}
    log = RAIZ / "logs" / "backups.csv"
    novo = not log.is_file()
    with open(log, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(resumo))
        if novo:
            w.writeheader()
        w.writerow(resumo)
    resumo["arquivos"] = copiados
    return resumo
