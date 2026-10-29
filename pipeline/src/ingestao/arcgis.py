"""Cliente genérico para consulta de camadas ArcGIS REST (MapServer/<camada>/query).

Usado pelo COP Recife (cop_recife.py). Paginação por resultOffset — o
servidor devolve no máximo `maxRecordCount` feições por página (2000 no COP)
e sinaliza `exceededTransferLimit` quando há mais. Mesma política de retry
com backoff exponencial do cliente CKAN (BUG-10).
"""

import time
from typing import Any

import requests

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF = 2  # segundos, dobrando a cada nova tentativa; 0 desliga
DEFAULT_TIMEOUT = 60
TAMANHO_PAGINA = 2000


def _get(url: str, params: dict[str, Any], max_retries: int, backoff: int) -> dict[str, Any]:
    tentativa = 0
    while True:
        try:
            resposta = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            resposta.raise_for_status()
            dados = resposta.json()
            # O ArcGIS responde 200 com {"error": {...}} em consulta inválida
            if isinstance(dados, dict) and "error" in dados:
                raise RuntimeError(f"ArcGIS recusou a consulta: {dados['error']}")
            return dados
        except (requests.exceptions.RequestException, ValueError) as exc:
            tentativa += 1
            if tentativa > max_retries:
                raise RuntimeError(f"Falha ao consultar {url} após {max_retries} tentativas: {exc}")
            if backoff:
                time.sleep(backoff * 2 ** (tentativa - 1))


def consultar(
    url_camada: str,
    *,
    formato: str = "json",
    ordenar_por: str = "OBJECTID",
    onde: str = "1=1",
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff: int = DEFAULT_BACKOFF,
) -> list[dict[str, Any]]:
    """Todas as feições da camada, página a página.

    formato "json": feições ArcGIS ({"attributes": ..., "geometry": ...}), sem geometria.
    formato "geojson": feições GeoJSON com geometria em WGS84 (EPSG:4326).
    """
    if formato not in ("json", "geojson"):
        raise ValueError(f"Formato ArcGIS não suportado: {formato!r}")
    feicoes: list[dict[str, Any]] = []
    deslocamento = 0
    while True:
        params = {
            "f": formato, "where": onde, "outFields": "*", "orderByFields": ordenar_por,
            "resultOffset": deslocamento, "resultRecordCount": TAMANHO_PAGINA,
        }
        if formato == "json":
            params["returnGeometry"] = "false"
        else:
            params["outSR"] = 4326
        pagina = _get(f"{url_camada}/query", params, max_retries, backoff)
        lote = pagina.get("features") or []
        feicoes.extend(lote)
        deslocamento += len(lote)
        excedeu = pagina.get("exceededTransferLimit") or (pagina.get("properties") or {}).get("exceededTransferLimit")
        if not lote or not excedeu:
            return feicoes
