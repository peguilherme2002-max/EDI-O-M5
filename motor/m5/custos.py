"""Registro contínuo de custos: logs/custos.csv (doc 10.2, 7.4, 9.5).

Uma linha por gasto, por vídeo e por construção. Material para a curadoria de Pedro;
não trava nenhuma decisão. Só se acrescenta; nada é apagado (F20).

Colunas:
  data        AAAA-MM-DD HH:MM
  canal       pasta do canal (ou "-" quando não se aplica)
  video       pasta do vídeo em roteiros/ (ou "-")
  formato     longo | short_roteiro_novo | short_recorte | "-"
  etapa       producao | construcao (amostras da 9.1 e geradores novos da 9.5)
  item        narracao | claude | tempo_pedro | outro
  fornecedor  elevenlabs | dark_planner | claude_pro | pedro | …
  quantidade  número
  unidade     creditos | audios | minutos | % do limite | …
  refacao     1 = regeneração de algo já gerado no mesmo vídeo; 0 = primeira vez
  obs         texto livre (segmento, origem do número…)
"""
import csv
from datetime import datetime

from .canal import RAIZ

CAMPOS = ["data", "canal", "video", "formato", "etapa", "item", "fornecedor",
          "quantidade", "unidade", "refacao", "obs"]


def registrar(canal: str, video: str, formato: str, etapa: str, item: str, fornecedor: str,
              quantidade: float, unidade: str, refacao: bool = False, obs: str = "",
              data: str | None = None) -> dict:
    arq = RAIZ / "logs" / "custos.csv"           # RAIZ lido na hora (permite testar em cópia)
    linha = {
        "data": data or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "canal": canal or "-", "video": video or "-", "formato": formato or "-",
        "etapa": etapa, "item": item, "fornecedor": fornecedor,
        "quantidade": f"{quantidade:g}" if isinstance(quantidade, (int, float)) else str(quantidade),
        "unidade": unidade, "refacao": "1" if refacao else "0", "obs": obs,
    }
    novo = not arq.is_file() or arq.stat().st_size == 0
    arq.parent.mkdir(parents=True, exist_ok=True)
    with open(arq, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo:
            w.writeheader()
        w.writerow(linha)
    return linha


def etapa_do_canal(canal: str) -> str:
    return "construcao" if canal == "_amostras" else "producao"
