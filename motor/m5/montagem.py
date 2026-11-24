"""Montagem do vídeo a partir do EDL: prévia 480p (P3) e render final (doc 9.3, passos 6 e 8).

Como funciona (tudo ffmpeg, determinístico):
1. cada corte vira um pedaço de vídeo com o número exato de quadros e um pedaço de áudio
   com o número exato de amostras (48000/30 = 1600 por quadro) → nada desalinha
   (corte de imagem: a imagem parada; corte gerado: a camada do template sobre a cor de fundo do kit)
2. os pedaços são concatenados sem nova codificação
3. passe final: texto na tela (texto simples: template texto_tela do kit; mapa: camada do template,
   .mov com alfa sobreposto de entrada_q a saida_q) + narração sobre o áudio do clipe
   + música de fundo (se o kit pede: audio.musica_volume_db; abaixa sob a voz), loudnorm (-14 LUFS)
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

from .canal import RAIZ, ErroM5, ler_yaml, pasta_canal
from .kit import Kit
from .templates import renderizar

AMOSTRAS_POR_QUADRO = 1600          # 48000 Hz / 30 fps
VOLUME_CLIPE = 0.18                 # áudio original do clipe por baixo da narração
# música abaixa ~10 dB quando a voz passa do limiar; volta em ~0,6 s nas pausas
DUCKING = "threshold=0.03:ratio=6:attack=30:release=600:makeup=1"
PERFIS = {
    "previa": {"altura": 480, "x264": ["-preset", "veryfast", "-crf", "28"], "audio": "128k"},
    "final": {"altura": None, "x264": ["-preset", "medium", "-crf", "18"], "audio": "192k"},
}


def _ff(args: list[str], cwd: Path | None = None) -> None:
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], cwd=cwd,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise ErroM5(f"ffmpeg falhou: {r.stderr.strip()[-400:]}")


def _tem_audio(video: Path) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    return bool(r.stdout.strip())


def _duracao(arq: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                        str(arq)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        raise ErroM5(f"faixa de música ilegível: {arq} (F07)")


def _musica(canal: str, kit_audio: dict, total_s: float, tmp: Path) -> bool:
    """Faixa de fundo contínua em tmp/mus.wav, no tamanho exato do vídeo.

    Só existe se o kit pede (audio.musica_volume_db). Faixas: assets/musica/ em ordem de nome,
    cada uma normalizada a -14 LUFS e emendada na seguinte com crossfade (volta à primeira se
    acabarem); fade in no início, fade out no fim. Nunca corte seco.
    """
    if "musica_volume_db" not in kit_audio:
        return False
    pasta = pasta_canal(canal) / "assets" / "musica"
    faixas = sorted(f for f in pasta.glob("*") if f.suffix.lower() in (".mp3", ".wav", ".m4a")) if pasta.is_dir() else []
    if not faixas:
        raise ErroM5(f"o kit do canal '{canal}' pede música, mas {pasta} não tem faixas (F07)")
    xf = float(kit_audio.get("musica_crossfade_s", 4))
    usadas, acumulado = [], 0.0
    while acumulado < total_s:
        f = faixas[len(usadas) % len(faixas)]
        d = _duracao(f)
        if d <= 2 * xf:
            raise ErroM5(f"faixa curta demais para o crossfade de {xf} s: {f} (F07)")
        usadas.append(f)
        acumulado += d - (xf if len(usadas) > 1 else 0)
    entradas, filtros = [], []
    for i, f in enumerate(usadas):
        entradas += ["-i", str(f)]
        filtros.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-14:TP=-1.5,"
                       f"aresample=48000[f{i}]")
    atual = "[f0]"
    for i in range(1, len(usadas)):
        filtros.append(f"{atual}[f{i}]acrossfade=d={xf}:c1=tri:c2=tri[x{i}]")
        atual = f"[x{i}]"
    amostras = round(total_s * 48000)
    fade_in, fade_out = float(kit_audio.get("musica_fade_in_s", 2)), float(kit_audio.get("musica_fade_out_s", 3))
    filtros.append(f"{atual}atrim=end_sample={amostras},asetpts=N/SR/TB,afade=t=in:d={fade_in},"
                   f"afade=t=out:st={max(0.0, total_s - fade_out):.3f}:d={fade_out},"
                   f"volume={float(kit_audio['musica_volume_db'])}dB[mus]")
    _ff([*entradas, "-filter_complex", ";".join(filtros), "-map", "[mus]", "-c:a", "pcm_s16le", "mus.wav"], cwd=tmp)
    return True


def _resolucao(edl: dict, perfil: str) -> tuple[int, int]:
    w, h = edl["resolucao"]
    alvo = PERFIS[perfil]["altura"]
    if alvo is None:
        return w, h
    if w >= h:                                  # 16:9 → 854x480
        return int(round(w * alvo / h / 2) * 2), alvo
    return alvo, int(round(h * alvo / w / 2) * 2)   # 9:16 → 480x854


def _kit(canal: str) -> dict:
    kit = ler_yaml(pasta_canal(canal) / "regras" / "kit_visual.yaml") or {}
    try:
        fonte = kit["fontes"]["titulo"]
        cores = kit["paleta"]
    except (KeyError, TypeError):
        raise ErroM5(f"kit_visual.yaml do canal '{canal}' sem fontes.titulo ou paleta")
    arq = pasta_canal(canal) / "assets" / "fontes" / f"{fonte.replace(' ', '-')}.ttf"
    if not arq.is_file():
        raise ErroM5(f"fonte do kit '{fonte}' não encontrada em {arq} (F07)")
    return {"fonte": arq, "texto": cores.get("texto", "#FFFFFF"), "fundo": cores.get("fundo", "#000000")}


def _quebrar(texto: str, max_chars: int) -> list[str]:
    """Quebra o texto em linhas de até max_chars, sem cortar palavras."""
    linhas, atual = [], ""
    for palavra in texto.split():
        if atual and len(atual) + 1 + len(palavra) > max_chars:
            linhas.append(atual)
            atual = palavra
        else:
            atual = f"{atual} {palavra}".strip()
    if atual:
        linhas.append(atual)
    return linhas or [texto]


def _usa_template(edl: dict) -> bool:
    return any(c.get("tipo") == "gerado" for s in edl["segmentos"] for c in s["cortes"]) or         any(isinstance(s["texto_tela"], dict) and "template" in s["texto_tela"] for s in edl["segmentos"])


def montar(edl: dict, perfil: str, destino: Path) -> Path:
    if perfil not in PERFIS:
        raise ErroM5(f"perfil desconhecido: {perfil}")
    W, H = _resolucao(edl, perfil)
    fps = edl["fps"]
    p = PERFIS[perfil]
    if H > W:
        # 9:16 (shorts): camada de layout do kit — preenche a tela cortando as laterais pelo centro
        escala = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                  f"crop={W}:{H},fps={fps},setsar=1")
    else:
        escala = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                  f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,fps={fps},setsar=1")

    with tempfile.TemporaryDirectory(prefix="m5_") as tmp:
        tmp = Path(tmp)
        lista_v, lista_a = [], []
        cortes = [c for s in edl["segmentos"] for c in s["cortes"]]
        templates_kit = None
        # áudio original dos clipes: kit audio.volume_clipe (0 = removido); sem a chave, o padrão
        kit_audio = (ler_yaml(pasta_canal(edl["canal"]) / "regras" / "kit_visual.yaml") or {}).get("audio") or {}
        vol_clipe = float(kit_audio.get("volume_clipe", VOLUME_CLIPE))
        if H > W and _usa_template(edl):
            raise ErroM5("os templates do kit ainda não têm layout 9:16 (capacidade nova: 9.5)")
        for i, c in enumerate(cortes):
            v, a = tmp / f"v{i:05d}.mp4", tmp / f"a{i:05d}.wav"
            amostras = c["quadros"] * AMOSTRAS_POR_QUADRO
            tipo = c.get("tipo", "video")
            if tipo in ("imagem", "gerado"):
                if tipo == "imagem":
                    _ff(["-loop", "1", "-framerate", str(fps), "-i", str(RAIZ / c["arquivo"]),
                         "-frames:v", str(c["quadros"]), "-vf", escala,
                         "-c:v", "libx264", *p["x264"], "-pix_fmt", "yuv420p", str(v)])
                else:
                    templates_kit = templates_kit or Kit(edl["canal"])
                    camada = renderizar(templates_kit, c["template"], c["campos"], c["quadros"] / fps,
                                        W, H, fps, tmp / f"g{i:05d}.mov")
                    r, g, b, _ = templates_kit.cor("fundo")
                    _ff(["-f", "lavfi", "-i", f"color=c=0x{r:02x}{g:02x}{b:02x}:s={W}x{H}:r={fps}",
                         "-i", str(camada), "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,setsar=1[v]",
                         "-map", "[v]", "-frames:v", str(c["quadros"]),
                         "-c:v", "libx264", *p["x264"], "-pix_fmt", "yuv420p", str(v)])
                _ff(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                     "-af", f"atrim=end_sample={amostras}", "-c:a", "pcm_s16le", str(a)])
                lista_v.append(f"file '{v.name}'")
                lista_a.append(f"file '{a.name}'")
                continue
            src = RAIZ / c["arquivo"]
            ini = c["origem_inicio_q"] / fps
            _ff(["-ss", f"{ini:.4f}", "-i", str(src), "-frames:v", str(c["quadros"]), "-an",
                 "-vf", escala, "-c:v", "libx264", *p["x264"], "-pix_fmt", "yuv420p", str(v)])
            if vol_clipe > 0 and _tem_audio(src):
                _ff(["-ss", f"{ini:.4f}", "-i", str(src), "-vn",
                     "-af", f"aresample=48000,aformat=channel_layouts=stereo,volume={vol_clipe},"
                            f"apad,atrim=end_sample={amostras}", "-c:a", "pcm_s16le", str(a)])
            else:
                _ff(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                     "-af", f"atrim=end_sample={amostras}", "-c:a", "pcm_s16le", str(a)])
            lista_v.append(f"file '{v.name}'")
            lista_a.append(f"file '{a.name}'")
        (tmp / "v.txt").write_text("\n".join(lista_v) + "\n", encoding="utf-8")
        (tmp / "a.txt").write_text("\n".join(lista_a) + "\n", encoding="utf-8")
        _ff(["-f", "concat", "-safe", "0", "-i", "v.txt", "-c", "copy", "base_v.mp4"], cwd=tmp)
        _ff(["-f", "concat", "-safe", "0", "-i", "a.txt", "-c", "copy", "base_a.wav"], cwd=tmp)

        # faixa de narração: um trecho por segmento, cortado/completado no tamanho exato do segmento.
        # Feita num comando à parte: no mesmo grafo do vídeo, o ffmpeg atrasava a fala quando um
        # segmento não tinha narração (logs/falhas.md, 24/11/2026)
        entradas = []
        filtros, rotulos = [], []
        k = 0
        for j, s in enumerate(edl["segmentos"]):
            amostras = (s["fim_q"] - s["inicio_q"]) * AMOSTRAS_POR_QUADRO
            if s["narracao"]:
                entradas += ["-i", str(RAIZ / s["narracao"]["arquivo"])]
                filtros.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,apad,"
                               f"atrim=end_sample={amostras},asetpts=N/SR/TB[n{j}]")
                k += 1
            else:
                filtros.append(f"anullsrc=r=48000:cl=stereo,atrim=end_sample={amostras}[n{j}]")
            rotulos.append(f"[n{j}]")
        filtros.append(f"{''.join(rotulos)}concat=n={len(rotulos)}:v=0:a=1[narr]")
        _ff([*entradas, "-filter_complex", ";".join(filtros), "-map", "[narr]", "-c:a", "pcm_s16le",
             "narr.wav"], cwd=tmp)
        entradas = ["-i", "base_v.mp4", "-i", "base_a.wav", "-i", "narr.wav"]
        total_s = sum(c["quadros"] for c in cortes) / fps
        if _musica(edl["canal"], kit_audio, total_s, tmp):
            entradas += ["-i", "mus.wav"]
            # ducking: a narração comprime a música enquanto fala; release longo = respira nas pausas
            filtros = ["[2:a]asplit=2[nv][ns]",
                       f"[3:a][ns]sidechaincompress={DUCKING}[md]" if kit_audio.get("ducking", True) else "[3:a]anull[md]",
                       "[1:a][nv][md]amix=inputs=3:normalize=0:duration=first,"
                       "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]"]
            k = 4
        else:
            filtros = ["[1:a][2:a]amix=inputs=2:normalize=0:duration=first,"
                       "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]"]
            k = 3

        # texto na tela (template texto_tela do kit)
        vchain = "[0:v]"
        kit = None
        fs = int(min(H * 0.065, W * 0.075))
        borda = int(fs * 0.38)
        # 16:9: faixa a 80% da altura; 9:16: a 68%, acima da área dos botões dos shorts
        centro_y = H * (0.68 if H > W else 0.80)
        camadas = []
        for j, s in enumerate(edl["segmentos"]):
            t = s["texto_tela"]
            if not t:
                continue
            if "template" in t:
                camadas.append(t)
                continue
            if kit is None:
                kit = _kit(edl["canal"])
                shutil.copyfile(kit["fonte"], tmp / "fonte.ttf")
            linhas = _quebrar(t["texto"], max(8, int(W * 0.88 / (fs * 0.62))))
            passo = fs * 1.55
            topo = centro_y - passo * (len(linhas) - 1) / 2
            a, b = t["entrada_q"] / fps, t["saida_q"] / fps
            for li, linha in enumerate(linhas):
                (tmp / f"t{j}_{li}.txt").write_text(linha, encoding="utf-8")
                vchain += (f"drawtext=fontfile=fonte.ttf:textfile=t{j}_{li}.txt:fontsize={fs}:"
                           f"fontcolor={kit['texto']}:box=1:boxcolor={kit['fundo']}@0.7:boxborderw={borda}:"
                           f"x=(w-text_w)/2:y={topo + li * passo:.1f}-text_h/2:"
                           f"enable='between(t,{a:.3f},{b:.3f})',")
        filtros.append((vchain.rstrip(",") if vchain != "[0:v]" else "[0:v]null") + "[vt]")
        # camadas de template (texto_tela como mapa): .mov com alfa, posto no tempo de entrada
        atual = "[vt]"
        for j, t in enumerate(camadas):
            templates_kit = templates_kit or Kit(edl["canal"])
            n_q = t["saida_q"] - t["entrada_q"]
            mov = renderizar(templates_kit, t["template"], t["campos"], n_q / fps, W, H, fps, tmp / f"c{j:04d}.mov")
            entradas += ["-i", str(mov)]
            filtros.append(f"[{k}:v]setpts=PTS-STARTPTS+{t['entrada_q'] / fps:.4f}/TB[c{j}]")
            filtros.append(f"{atual}[c{j}]overlay=0:0:eof_action=pass:format=auto[o{j}]")
            atual = f"[o{j}]"
            k += 1
        filtros.append(f"{atual}null[vout]")

        saida = tmp / "saida.mp4"
        _ff([*entradas, "-filter_complex", ";".join(filtros), "-map", "[vout]", "-map", "[aout]",
             "-c:v", "libx264", *p["x264"], "-pix_fmt", "yuv420p", "-r", str(fps),
             "-c:a", "aac", "-b:a", p["audio"], "-movflags", "+faststart", str(saida)], cwd=tmp)
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(saida), destino)
    return destino
