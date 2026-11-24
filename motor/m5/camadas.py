"""Templates do kit usados pelo roteiro: texto_tela como mapa e visual.fonte=gerado (sem IA, F07).

- texto_tela: {template: <nome>, <campos do kit>..., inicio_s?, duracao_s?}
  inicio_s/duracao_s: em segundos, a partir do início do segmento (padrão: o segmento inteiro).
  Template que segue a fala (FALA: legenda_karaoke.texto, citacao.frase): o texto do campo precisa
  estar, palavra por palavra e em sequência, na narração do segmento; entra quando a fala diz a
  primeira palavra e sai pouco depois da última. Esses não aceitam inicio_s/duracao_s.
- visual.fonte=gerado: visual.busca = nome do template; visual.etiquetas = campos "nome=valor"
  (ex.: [modo=abertura]). A camada é desenhada sobre a cor de fundo do kit, o segmento inteiro.
Usado pela validação (problemas) e pelo EDL (tempos). A montagem só desenha o que passou aqui.
"""
import re
import unicodedata

from .canal import ErroM5
from .kit import Kit
from .roteiro import Segmento, Visual
from .templates import CONFERIR, FALA, RENDERERS, conferir_campos
from .templates.amostra import converter_campos

TEMPO = ("inicio_s", "duracao_s")


def norm(palavra: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", palavra).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sem_acento.lower())


def palavras_da_narracao(texto: str) -> list[str]:
    """Palavras faladas do texto do roteiro (sem as tags de voz, ex.: <break time="1s"/>)."""
    return re.sub(r"<[^>]*>", " ", texto).split()


def achar_sequencia(alvo: list[str], fala: list[str]) -> int | None:
    """Índice em fala (normalizada) onde alvo (normalizado, sem vazios) aparece inteiro; None se não."""
    n = len(alvo)
    if not n:
        return None
    for i in range(len(fala) - n + 1):
        if fala[i:i + n] == alvo:
            return i
    return None


def campos_texto_tela(seg: Segmento) -> tuple[str, dict]:
    t = dict(seg.texto_tela)
    return t.pop("template"), t


def campos_gerado(kit: Kit, v: Visual) -> tuple[str, dict]:
    return v.busca, converter_campos(kit.template(v.busca), v.etiquetas)


def problemas(kit: Kit, nome: str, campos: dict, narracao: str, segue_fala_ok: bool = True) -> list[str]:
    """O que impede a montagem de desenhar este template neste segmento (vazio = pode)."""
    if nome not in RENDERERS:
        return [f"o motor não sabe desenhar o template '{nome}'"]
    try:
        spec = kit.template(nome)
    except ErroM5 as e:
        return [str(e)]
    erros = conferir_campos(spec, campos)
    if nome in CONFERIR and not erros:
        erros += CONFERIR[nome](kit, campos)
    for c in TEMPO:
        v = campos.get(c)
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0
                              or (c == "duracao_s" and v == 0)):
            erros.append(f"campo '{c}' deve ser número de segundos (duracao_s > 0)")
    if nome in FALA:
        if not segue_fala_ok:
            erros.append(f"'{nome}' segue a fala: não serve como visual gerado")
        if any(c in campos for c in TEMPO):
            erros.append(f"'{nome}' segue a fala: o tempo vem da narração (sem inicio_s/duracao_s)")
        campo = FALA[nome]
        if isinstance(campos.get(campo), str):
            alvo = [w for w in (norm(x) for x in campos[campo].split()) if w]
            fala = [norm(x) for x in palavras_da_narracao(narracao)]
            if not narracao:
                erros.append(f"'{nome}' segue a fala, mas o segmento não tem narração")
            elif achar_sequencia(alvo, fala) is None:
                erros.append(f"o texto de '{campo}' não está, em sequência, na narração do segmento")
    return erros


def tempos_da_fala(nome: str, campos: dict, palavras: list[dict]) -> list[list[float]]:
    """[[inicio_s, fim_s], ...] de cada palavra do campo que segue a fala, nos tempos da narração
    (segundos desde o início da narração). Palavra sem letras (ex.: "—") herda o tempo da vizinha."""
    ditas = str(campos[FALA[nome]]).split()
    normais = [norm(x) for x in ditas]
    alvo = [w for w in normais if w]
    i = achar_sequencia(alvo, [norm(p["palavra"]) for p in palavras])
    if i is None:
        raise ErroM5(f"template '{nome}': o texto não aparece nos tempos da narração gerada (F07)")
    tempos, k = [], i
    for w in normais:
        if w:
            tempos.append([palavras[k]["inicio_s"], palavras[k]["fim_s"]])
            k += 1
        else:
            tempos.append(None)
    for j, t in enumerate(tempos):                 # vazias: tempo da anterior (ou da próxima)
        if t is None:
            viz = next((tempos[x] for x in range(j - 1, -1, -1) if tempos[x]), None) or \
                  next(tempos[x] for x in range(j + 1, len(tempos)) if tempos[x])
            tempos[j] = list(viz)
    return tempos
