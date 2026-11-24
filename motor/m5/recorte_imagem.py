"""Recorte de imagem da web (m5 recortar): busca a foto de maior resolução, tira o fundo, registra.

1. busca: Bing Imagens por scraping, sem chave (decisão de Pedro). Frágil: se a página mudar ou não
   vier resultado, ErroM5 claro (F07). Regra fixa, sem IA: dos primeiros CANDIDATOS resultados, baixa
   os que forem imagem válida com lado menor ≥ MINIMO_PX e fica com a de mais pixels (empate: a
   primeira na ordem da busca). --url pula a busca e usa a imagem indicada.
2. recorte: rembg com o modelo BiRefNet (birefnet-general). O modelo (~900 MB) fica fora do Git,
   na pasta do rembg (~/.u2net).
3. registro: PNG com fundo transparente em canais/<canal>/assets/recortes/<nome>.png, original em
   recortes/originais/, e uma linha no grupo "recortes" do assets/manifest.yaml
   {arquivo, origem (URL da imagem), pagina, data, etiquetas, busca}.
O template recorte_surpresa acha o PNG pelas etiquetas (mesma regra da mídia web).
"""
import html
import io
import json
import re
from datetime import date
from pathlib import Path

import requests
from PIL import Image

from .canal import ErroM5, pasta_canal

CANDIDATOS = 8
MINIMO_PX = 600
MAX_BYTES = 40 * 1024 * 1024
MODELO = "birefnet-general"
AGENTE = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"}


def buscar(busca: str) -> list[dict]:
    """[{imagem, pagina}] na ordem do Bing Imagens (filtro de tamanho grande). ErroM5 se falhar."""
    try:
        r = requests.get("https://www.bing.com/images/search", headers=AGENTE, timeout=20,
                         params={"q": busca, "qft": "+filterui:imagesize-large", "form": "IRFLTR"})
        r.raise_for_status()
    except requests.RequestException as e:
        raise ErroM5(f"busca de imagem falhou (Bing fora do ar ou bloqueou): {e}")
    achados = []
    for m in re.findall(r'class="iusc"[^>]*?\sm="([^"]+)"', r.text):
        try:
            d = json.loads(html.unescape(m))
        except json.JSONDecodeError:
            continue
        if d.get("murl"):
            achados.append({"imagem": d["murl"], "pagina": d.get("purl", "")})
    if not achados:
        raise ErroM5(f"busca de imagem sem resultado para '{busca}' (a página do Bing pode ter mudado) (F07)")
    return achados


def baixar(url: str) -> tuple[bytes, Image.Image] | None:
    """(bytes, imagem) se a URL for uma imagem válida; None se não."""
    try:
        with requests.get(url, headers=AGENTE, timeout=25, stream=True) as r:
            r.raise_for_status()
            dados = r.raw.read(MAX_BYTES + 1, decode_content=True)
        if len(dados) > MAX_BYTES:
            return None
        img = Image.open(io.BytesIO(dados))
        img.load()
        return dados, img
    except Exception:
        return None


def escolher(achados: list[dict]) -> tuple[dict, bytes, Image.Image, list[str]]:
    """A de mais pixels entre os primeiros CANDIDATOS válidos. Devolve também o relato de cada um."""
    melhor, relato = None, []
    for a in achados[:CANDIDATOS]:
        b = baixar(a["imagem"])
        if b is None:
            relato.append(f"  falhou   {a['imagem']}")
            continue
        w, h = b[1].size
        relato.append(f"  {w}x{h}  {a['imagem']}")
        if min(w, h) >= MINIMO_PX and (melhor is None or w * h > melhor[2].size[0] * melhor[2].size[1]):
            melhor = (a, *b)
    if melhor is None:
        raise ErroM5(f"nenhuma imagem válida com lado menor ≥ {MINIMO_PX} px nos {CANDIDATOS} primeiros "
                     "resultados (F07)\n" + "\n".join(relato))
    return (*melhor, relato)


def tirar_fundo(img: Image.Image) -> Image.Image:
    """PNG RGBA com o assunto recortado (rembg + BiRefNet), aparado na caixa do assunto."""
    from rembg import new_session, remove
    rgba = remove(img.convert("RGB"), session=new_session(MODELO))
    caixa = rgba.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if caixa is None:
        raise ErroM5("o recorte não achou nenhum assunto na imagem (F07)")
    return rgba.crop(caixa)


def _registrar(manifest: Path, entrada: dict) -> None:
    """Acrescenta a entrada no grupo 'recortes' do manifest.yaml, sem mexer no resto do arquivo."""
    linha = "  - " + json.dumps(entrada, ensure_ascii=False)        # JSON em uma linha é YAML válido
    texto = manifest.read_text(encoding="utf-8") if manifest.is_file() else ""
    linhas = texto.splitlines()
    if "recortes:" not in linhas:
        linhas += ["", "recortes:", linha]
    else:
        i = linhas.index("recortes:") + 1
        while i < len(linhas) and linhas[i].startswith("  "):
            i += 1
        linhas.insert(i, linha)
    manifest.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def recortar(canal: str, busca: str, nome: str, etiquetas: list[str], url: str | None = None) -> Path:
    if not re.fullmatch(r"[a-z0-9_-]+", nome):
        raise ErroM5(f"nome do recorte '{nome}': use só letras minúsculas, números, - e _")
    if not etiquetas:
        raise ErroM5("o recorte precisa de etiquetas (é por elas que o roteiro o encontra)")
    assets = pasta_canal(canal) / "assets"
    destino = assets / "recortes" / f"{nome}.png"
    if destino.exists():
        raise ErroM5(f"já existe {destino}; escolha outro nome (nada é apagado — F20)")
    if url:
        b = baixar(url)
        if b is None:
            raise ErroM5(f"a URL não trouxe uma imagem válida: {url} (F07)")
        escolhido, (dados, img), relato = {"imagem": url, "pagina": ""}, b, [f"  {b[1].size[0]}x{b[1].size[1]}  {url}"]
    else:
        escolhido, dados, img, relato = escolher(buscar(busca))
    print("candidatos:\n" + "\n".join(relato))
    print(f"escolhida: {img.size[0]}x{img.size[1]}  {escolhido['imagem']}")
    ext = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}.get(img.format or "", ".img")
    original = assets / "recortes" / "originais" / f"{nome}{ext}"
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(dados)
    recorte = tirar_fundo(img)
    recorte.save(destino)
    _registrar(assets / "manifest.yaml", {
        "arquivo": f"recortes/{nome}.png", "original": f"recortes/originais/{nome}{ext}",
        "origem": escolhido["imagem"], "pagina": escolhido["pagina"], "data": date.today().isoformat(),
        "etiquetas": etiquetas, "busca": busca if not url else "", "modelo": MODELO,
        "tamanho": f"{recorte.size[0]}x{recorte.size[1]}"})
    return destino
