"""Regras de negócio da API — funções puras, sem banco (testáveis isoladamente)."""

from collections import defaultdict
from datetime import datetime
import json
from typing import Any
import unicodedata

AGRAVOS = ("dengue", "chikungunya", "zika")

# Mesmos nomes compostos que o pipeline trata (pipeline/src/serving/exporta_painel.py).
APELIDOS_BAIRRO = {"SITIO DOS PINTOS - SAO BRAS": "SITIO DOS PINTOS", "COHAB - IBURA DE CIMA": "COHAB"}


def chave_bairro(nome: Any) -> str:
    """Nome de bairro normalizado: sem acento, maiúsculo, espaço único.

    Mesma regra de pipeline/src/ingestao/territorio.py::chave_bairro, que gerou
    dim_bairro.chave_bairro. Repetida aqui porque a API não importa o pipeline
    (a fronteira entre os dois é o banco); há teste que confere as duas.
    """
    texto = unicodedata.normalize("NFKD", str(nome or "")).encode("ascii", "ignore").decode()
    chave = " ".join(texto.upper().split())
    return APELIDOS_BAIRRO.get(chave, chave)


def situacao_rio(nivel: float | None, pre_alerta: float | None, alerta: float | None,
                 inundacao: float | None) -> str:
    """Compara o nível com as cotas oficiais do COP (da mais grave para a menos grave)."""
    if nivel is None or (pre_alerta is None and alerta is None and inundacao is None):
        return "sem_cota"
    if inundacao is not None and nivel >= inundacao:
        return "inundacao"
    if alerta is not None and nivel >= alerta:
        return "alerta"
    if pre_alerta is not None and nivel >= pre_alerta:
        return "pre_alerta"
    return "normal"


def percentual(parte: float | None, todo: float | None) -> float | None:
    if parte is None or not todo:
        return None
    return round(parte / todo * 100, 1)


def comparacao_mensal(meses: list[dict[str, Any]], momento: datetime) -> dict[str, Any] | None:
    """Acumulado do mês da leitura contra a média histórica daquele mês."""
    linha = next((m for m in meses if m["mes"] == momento.month and m["ano_referencia"] == momento.year), None)
    if linha is None:
        return None
    return {
        "mes": momento.month, "ano": momento.year,
        "chuva_acumulada_mm": linha["chuva_ano_atual_mm"],
        "media_historica_mm": linha["media_historica_mm"],
        "percentual_da_media": percentual(linha["chuva_ano_atual_mm"], linha["media_historica_mm"]),
    }


def media_modelos(*valores: float | None) -> float | None:
    presentes = [v for v in valores if v is not None]
    return round(sum(presentes) / len(presentes), 2) if presentes else None


def arboviroses_por_bairro(contagens: list[dict[str, Any]], bairros: list[dict[str, Any]]) -> dict[str, Any]:
    """Cruza as contagens pelo texto da fonte com dim_bairro. Nada é descartado em silêncio:
    o que não casa entra em `nao_georreferenciadas`, com as grafias listadas."""
    por_chave = {b["chave_bairro"]: b for b in bairros}
    soma: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(AGRAVOS, 0))
    sem_casamento, grafias = 0, set()
    for linha in contagens:
        chave = chave_bairro(linha["bairro"])
        if chave in por_chave and linha["agravo"] in AGRAVOS:
            soma[chave][linha["agravo"]] += int(linha["notificacoes"])
        else:
            sem_casamento += int(linha["notificacoes"])
            grafias.add(str(linha["bairro"]))
    resultado = []
    for chave, bairro in por_chave.items():
        contagem = soma.get(chave, dict.fromkeys(AGRAVOS, 0))
        resultado.append({
            "chave_bairro": chave, "nome_bairro": bairro["nome_bairro"],
            "distrito_sanitario": bairro["distrito_sanitario"], "descricao_distrito": bairro["descricao_distrito"],
            **contagem, "total": sum(contagem.values()),
        })
    resultado.sort(key=lambda b: (-b["total"], b["nome_bairro"]))
    return {"bairros": resultado, "nao_georreferenciadas": sem_casamento,
            "grafias_nao_reconhecidas": sorted(grafias)}


def feature_collection(linhas: list[dict[str, Any]], campo_geometria: str | None = None,
                       lon: str = "longitude", lat: str = "latitude") -> dict[str, Any]:
    """Linhas do banco -> GeoJSON. Geometria vem de um campo GeoJSON em texto ou de lon/lat."""
    features = []
    for linha in linhas:
        props = dict(linha)
        if campo_geometria:
            texto = props.pop(campo_geometria)
            geometria = json.loads(texto) if texto else None
        else:
            x, y = props.pop(lon, None), props.pop(lat, None)
            geometria = {"type": "Point", "coordinates": [x, y]} if x is not None and y is not None else None
        for chave, valor in props.items():
            if hasattr(valor, "isoformat"):
                props[chave] = valor.isoformat()
        features.append({"type": "Feature", "geometry": geometria, "properties": props})
    return {"type": "FeatureCollection", "features": features}
