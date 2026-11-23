"""Validação do roteiro contra o registro de capacidades (doc 7.3). Sem IA."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .canal import RAIZ, ErroM5, conferir_formato, fornecedor_voz, ler_ficha
from .registro import Gerador, buscar, ler_registro
from .roteiro import Roteiro, Segmento

# marcações da 7.3, da menos para a mais grave
OK, BAIXAR, AVISO, PENDENCIA = 0, 1, 2, 3
ROTULO = {
    OK: "ok",
    BAIXAR: "baixar material",
    AVISO: "teto conhecido → aviso",
    PENDENCIA: "sem gerador → pendência",
}
TIPO_POR_FONTE = {"catalogo": "clipe_catalogo", "web": "midia_web"}


@dataclass
class Item:
    tipo: str
    descricao: str
    marca: int
    nota: str = ""


@dataclass
class ResultadoSegmento:
    segmento: Segmento
    itens: list[Item] = field(default_factory=list)

    @property
    def marca(self) -> int:
        return max((i.marca for i in self.itens), default=OK)


@dataclass
class Resultado:
    canal: str
    formato: str
    roteiro: Roteiro
    registro: Path
    segmentos: list[ResultadoSegmento]
    gerado_em: str

    @property
    def pendencias(self) -> int:
        return sum(1 for s in self.segmentos if s.marca == PENDENCIA)


def _material_disponivel(canal: str, segmento: Segmento) -> bool:
    """Material já presente no catálogo/assets do canal.
    O índice do catálogo e o manifest de assets nascem na C4; até lá, nada está disponível."""
    return False


def _necessidades(seg: Segmento, fornecedor: str | None) -> list[tuple[str, str, bool]]:
    """(tipo, descrição, exige_material) de cada coisa que o segmento pede."""
    nec = []
    if seg.narracao:
        nec.append(("narracao", f"narração, {len(seg.narracao)} caracteres, fornecedor {fornecedor or '?'}", False))
    v = seg.visual
    if v.fonte == "gerado":
        nec.append((v.busca, f"visual gerado: {v.busca}", False))
    else:
        nec.append((TIPO_POR_FONTE[v.fonte], f"visual {v.fonte}: \"{v.busca}\"", True))
    if seg.texto_tela:
        nec.append(("texto_tela", f"texto na tela: \"{seg.texto_tela}\"", False))
    for s in seg.sfx:
        nec.append(("sfx", f"sfx: {s}", True))
    return nec


def _avaliar(tipo: str, exige_material: bool, ger: Gerador | None, em_teste: bool,
             formato: str, disponivel: bool) -> tuple[int, str]:
    if ger is None:
        extra = " (existe só em teste, sem amostra aprovada — F09)" if em_teste else ""
        return PENDENCIA, f"nenhum gerador aprovado para '{tipo}' no formato {formato}{extra}"
    if ger.teto:
        baixar = "; material será baixado" if exige_material and not disponivel else ""
        return AVISO, f"{ger.gerador}: {ger.teto}{baixar}"
    if exige_material and not disponivel:
        return BAIXAR, f"{ger.gerador}: material não está no canal; será baixado"
    return OK, ger.gerador


def validar(canal: str, formato: str, roteiro: Roteiro, registro_path: Path) -> Resultado:
    ficha = ler_ficha(canal)
    conferir_formato(ficha, canal, formato)
    if formato == "short_recorte":
        raise ErroM5("short_recorte não passa por validação: o P2 vem do longo de origem (7.6)")
    registro = ler_registro(registro_path)
    fornecedor = fornecedor_voz(ficha, formato)

    resultados = []
    for seg in roteiro.segmentos:
        rs = ResultadoSegmento(seg)
        for tipo, desc, exige in _necessidades(seg, fornecedor):
            if tipo == "narracao" and not fornecedor:
                rs.itens.append(Item(tipo, desc, PENDENCIA, f"a ficha do canal não define fornecedor de voz para {formato}"))
                continue
            ger, em_teste = buscar(registro, tipo, formato)
            marca, nota = _avaliar(tipo, exige, ger, em_teste, formato,
                                   _material_disponivel(canal, seg) if exige else True)
            rs.itens.append(Item(tipo, desc, marca, nota))
        resultados.append(rs)
    return Resultado(canal, formato, roteiro, registro_path, resultados,
                     datetime.now().strftime("%Y-%m-%d %H:%M"))


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return str(p)


def relatorio_md(r: Resultado) -> str:
    contagem = {m: sum(1 for s in r.segmentos if s.marca == m) for m in ROTULO}
    pode_fechar = "sim" if r.pendencias == 0 else f"não — {r.pendencias} segmento(s) com pendência (F06; decisão de Pedro: 9.5)"
    linhas = [
        "# Relatório de validação",
        "",
        f"- canal: {r.canal}",
        f"- formato: {r.formato}",
        f"- roteiro: {_rel(r.roteiro.caminho)}" + (f" (versão {r.roteiro.versao})" if r.roteiro.versao else ""),
        f"- sha1 do roteiro: {r.roteiro.sha1}",
        f"- registro: {_rel(r.registro)}",
        f"- gerado em: {r.gerado_em}",
        f"- segmentos: {len(r.segmentos)} · duração-alvo total: {r.roteiro.duracao_total_s:g} s",
        "",
        "## Resumo",
        "",
        "| marcação | segmentos |",
        "|---|---|",
        *[f"| {ROTULO[m]} | {contagem[m]} |" for m in ROTULO],
        "",
        f"**O P2 pode fechar?** {pode_fechar}",
        "",
        "## Segmentos",
        "",
        "| segmento | intenção | duração (s) | marcação |",
        "|---|---|---|---|",
        *[f"| {s.segmento.id} | {s.segmento.intencao} | {s.segmento.duracao_alvo_s:g} | {ROTULO[s.marca]} |" for s in r.segmentos],
        "",
        "## Detalhes",
    ]
    for s in r.segmentos:
        linhas += ["", f"### {s.segmento.id} — {ROTULO[s.marca]}", ""]
        for i in s.itens:
            linhas.append(f"- [{ROTULO[i.marca]}] {i.descricao}" + (f" — {i.nota}" if i.nota else ""))
    return "\n".join(linhas) + "\n"


def escrever_relatorio(r: Resultado, destino: Path | None = None) -> Path:
    destino = destino or r.roteiro.caminho.with_name("relatorio_validacao.md")
    destino.write_text(relatorio_md(r), encoding="utf-8")
    return destino
