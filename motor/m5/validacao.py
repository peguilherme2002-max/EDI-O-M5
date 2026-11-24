"""Validação do roteiro contra o registro de capacidades (doc 7.3). Sem IA."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .canal import RAIZ, ErroM5, conferir_formato, fornecedor_voz, ler_ficha
from . import camadas
from .catalogo import clipes_com_etiquetas
from .kit import Kit
from .midia_web import midias_com_etiquetas
from .registro import Gerador, buscar, ler_registro
from .roteiro import Roteiro, Segmento
from .sfx import arquivo_sfx

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


def _material_disponivel(canal: str, tipo: str, segmento: Segmento) -> bool:
    """Material já presente no canal. Catálogo: algum clipe com todas as etiquetas do visual (C4).
    Mídia web: alguma entrada do manifest de assets com todas as etiquetas. """
    if tipo == "clipe_catalogo":
        return bool(clipes_com_etiquetas(canal, segmento.visual.etiquetas))
    if tipo == "midia_web":
        return any(arq.is_file() for _, arq in midias_com_etiquetas(canal, segmento.visual.etiquetas))
    return False


def _kit(canal: str) -> Kit | None:
    try:
        return Kit(canal)
    except ErroM5:
        return None


def _problemas_texto_simples(canal: str) -> list[str]:
    from .montagem import _kit as kit_texto_simples
    try:
        kit_texto_simples(canal)
        return []
    except ErroM5 as e:
        return [f"texto simples precisa do template texto_tela do kit: {e}"]


def _necessidades(seg: Segmento, fornecedor: str | None, canal: str,
                  kit: Kit | None) -> list[tuple[str, str, bool, list[str]]]:
    """(tipo, descrição, exige_material, problemas) de cada coisa que o segmento pede.
    problemas: o que impede a montagem de fazer o item (vira pendência; o motor não chuta, F07)."""
    nec = []
    if seg.narracao:
        nec.append(("narracao", f"narração, {len(seg.narracao)} caracteres, fornecedor {fornecedor or '?'}", False, []))
    v = seg.visual
    if v.fonte == "gerado":
        prob = ["o kit do canal não pôde ser lido"] if kit is None else []
        if kit is not None:
            try:
                nome, campos = camadas.campos_gerado(kit, seg)
                prob = camadas.problemas(kit, nome, campos, seg.narracao, segue_fala_ok=False)
            except ErroM5 as e:
                prob = [str(e)]
        nec.append((v.busca, f"visual gerado: {v.busca}", False, prob))
    else:
        nec.append((TIPO_POR_FONTE[v.fonte], f"visual {v.fonte}: \"{v.busca}\"", True, []))
    if isinstance(seg.texto_tela, dict):
        nome, campos = camadas.campos_texto_tela(seg)
        prob = (["o kit do canal não pôde ser lido"] if kit is None
                else camadas.problemas(kit, nome, campos, seg.narracao))
        nec.append((nome, f"texto na tela: template {nome}", False, prob))
    elif seg.texto_tela:
        nec.append(("texto_tela", f"texto na tela: \"{seg.texto_tela}\"", False, _problemas_texto_simples(canal)))
    for s in seg.sfx:
        try:
            arquivo_sfx(canal, s)
            prob = []
        except ErroM5 as e:
            prob = [str(e)]                # sfx inexistente ou ambíguo: o motor não chuta (F07)
        nec.append(("sfx", f"sfx: {s}", False, prob))
    return nec


def _avaliar(tipo: str, exige_material: bool, ger: Gerador | None, em_teste: Gerador | None,
             formato: str, disponivel: bool, aceitar_em_teste: bool) -> tuple[int, str]:
    if ger is None and em_teste and aceitar_em_teste:
        baixar = "; material será baixado" if exige_material and not disponivel else ""
        return AVISO, f"{em_teste.gerador}: em teste — aceito só nas amostras da construção (9.1){baixar}"
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

    kit = _kit(canal)
    resultados = []
    for seg in roteiro.segmentos:
        rs = ResultadoSegmento(seg)
        for tipo, desc, exige, problemas in _necessidades(seg, fornecedor, canal, kit):
            if tipo == "narracao" and not fornecedor:
                rs.itens.append(Item(tipo, desc, PENDENCIA, f"a ficha do canal não define fornecedor de voz para {formato}"))
                continue
            ger, em_teste = buscar(registro, tipo, formato)
            marca, nota = _avaliar(tipo, exige, ger, em_teste, formato,
                                   _material_disponivel(canal, tipo, seg) if exige else True,
                                   aceitar_em_teste=(canal == "_amostras"))
            if problemas and marca != PENDENCIA:
                marca, nota = PENDENCIA, "a montagem não consegue: " + "; ".join(problemas) + " (corrigir o roteiro ou 9.5)"
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
