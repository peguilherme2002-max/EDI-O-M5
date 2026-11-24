"""Efeitos sonoros (sfx) do roteiro: resolução do arquivo e posição no tempo. Sem IA, sem chute (F07).

- nome no roteiro = nome do arquivo sem extensão, em qualquer pasta sfx/ dentro de assets/ do canal
  (ex.: assets/acervo_extra/sfx/kit/pop.wav). Nenhum ou mais de um arquivo com o nome → erro F07
- pico: sons.json ao lado do arquivo ({nome: {dur, pico}}); o pico (s dentro do som) cai no evento.
  Sem sons.json ou sem o nome nele → pico 0 (o som começa no evento)
- evento: instante em que o texto_tela/grafismo do segmento entra; sem texto_tela, o início do
  segmento. Vários sfx no mesmo segmento caem no mesmo evento (kit: um som por grafismo que entra)
"""
import json
from pathlib import Path

from .canal import ErroM5, pasta_canal

EXTENSOES = (".wav", ".mp3", ".m4a", ".ogg", ".flac")


def arquivo_sfx(canal: str, nome: str) -> tuple[Path, float]:
    """(arquivo, pico_s) do sfx pedido pelo roteiro."""
    assets = pasta_canal(canal) / "assets"
    achados = sorted(f for f in assets.rglob(f"{nome}.*")
                     if f.suffix.lower() in EXTENSOES and "sfx" in f.relative_to(assets).parts[:-1])
    if not achados:
        raise ErroM5(f"sfx '{nome}' não existe em nenhuma pasta sfx/ de {assets} (F07)")
    if len(achados) > 1:
        raise ErroM5(f"sfx '{nome}' ambíguo: {', '.join(str(f.relative_to(assets)) for f in achados)} (F07)")
    arq = achados[0]
    sons = arq.with_name("sons.json")
    pico = json.loads(sons.read_text(encoding="utf-8")).get(nome, {}).get("pico", 0) if sons.is_file() else 0
    return arq, float(pico)


def inicio_s(evento_q: int, fps: int, pico_s: float) -> float:
    """Segundos do vídeo em que o som começa para o pico cair no evento (negativo: corta o começo do som)."""
    return round(evento_q / fps - pico_s, 3)


if __name__ == "__main__":      # autocheck: python -m m5.sfx
    assert inicio_s(30, 30, 0) == 1.0                      # sem pico: começa no evento
    assert inicio_s(90, 30, 0.011) == 2.989                # pop: pico 11 ms antes do evento
    assert inicio_s(30, 30, 3.137) == -2.137               # riser no início: corta a subida que não cabe
    arq, pico = arquivo_sfx("_amostras", "pop")               # assets/sfx/ das amostras (com sons.json)
    assert arq.name == "pop.wav" and pico == 0.011
    assert arquivo_sfx("_amostras", "dragon-studio-ding-sfx-472366")[1] == 0   # sem entrada no sons.json
    try:
        arquivo_sfx("_amostras", "nao-existe")
        raise AssertionError("devia recusar sfx inexistente")
    except ErroM5:
        pass
    print("sfx: ok")
