import time
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Tuple

import requests

API_URL = "https://dados.recife.pe.gov.br/pt_BR/api/action/datastore_search"
DEFAULT_LIMIT = 1000
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF = 2  # segundos, dobrando a cada nova tentativa (2, 4, 8…); 0 desliga.
#                      Sem espera, as tentativas saíam em sequência e uma instabilidade
#                      de poucos segundos da API derrubava a coleta (BUG-10).


def _request_with_retry(params: Dict[str, Any], max_retries: int, backoff: int) -> Dict[str, Any]:
    """Executa GET com nova tentativa em erros de rede ou HTTP."""
    tentativa = 0
    while True:
        try:
            resposta = requests.get(API_URL, params=params, timeout=30)
            resposta.raise_for_status()
            return resposta.json()
        except requests.exceptions.RequestException as exc:
            tentativa += 1
            if tentativa > max_retries:
                raise RuntimeError(f"Falha ao acessar CKAN após {max_retries} tentativas: {exc}")
            if backoff:
                time.sleep(backoff * 2 ** (tentativa - 1))


def coletar_todos(
    resource_id: str,
    filtros: Dict[str, Any] | None = None,
    limite_por_pagina: int = DEFAULT_LIMIT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff: int = DEFAULT_BACKOFF,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Coleta todos os registros de um ``resource_id``.

    Retorna ``(registros, metadados)`` onde ``metadados`` contém:
    - ``resource_id``
    - ``total`` (quantidade total informada pela API ou ``float('inf')``)
    - ``coletado_em`` (timestamp ISO UTC)
    """
    if not resource_id:
        raise ValueError("resource_id é obrigatório")
    filtros = filtros or {}
    offset = 0
    todos_registros: List[Dict[str, Any]] = []
    total: int | float | None = None
    while True:
        params: Dict[str, Any] = {
            "resource_id": resource_id,
            "limit": limite_por_pagina,
            "offset": offset,
        }
        if filtros:
            # CKAN espera JSON serializado
            params["filters"] = json.dumps(filtros)
        dados = _request_with_retry(params, max_retries, backoff)
        resultado = dados.get("result", {})
        registros = resultado.get("records", [])
        if total is None:
            total = resultado.get("total", float('inf'))
        todos_registros.extend(registros)
        # O servidor pode devolver menos que o `limit` pedido (o CKAN do Recife
        # limita a 500 por página): avançar pelo que de fato veio e só parar com
        # página vazia ou total atingido — nunca por "página menor que o pedido".
        offset += len(registros)
        if not registros or offset >= total:
            break
    metadados = {
        "resource_id": resource_id,
        "total": total if total != float('inf') else len(todos_registros),
        "coletado_em": datetime.now(timezone.utc).isoformat(),
    }
    return todos_registros, metadados

def obter_url_download(
    resource_id: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff: int = DEFAULT_BACKOFF,
) -> str:
    """Resolve a URL de download de um recurso pelo `resource_show` do CKAN.

    Evita URLs montadas à mão: o caminho de download inclui o id do dataset,
    e um id errado dá 404 (causa do BUG-04).
    """
    if not resource_id:
        raise ValueError("resource_id é obrigatório")
    url_resource_show = API_URL.rsplit("/", 1)[0] + "/resource_show"
    tentativa = 0
    while True:
        try:
            resposta = requests.get(url_resource_show, params={"id": resource_id}, timeout=30)
            resposta.raise_for_status()
            url = resposta.json().get("result", {}).get("url")
            if not url:
                raise RuntimeError(f"Recurso {resource_id} sem URL de download no CKAN")
            return url
        except requests.exceptions.RequestException as exc:
            tentativa += 1
            if tentativa > max_retries:
                raise RuntimeError(f"Falha ao consultar resource_show de {resource_id} após {max_retries} tentativas: {exc}")
            if backoff:
                time.sleep(backoff * 2 ** (tentativa - 1))


# Compatibilidade legacy
fetch_all = coletar_todos
