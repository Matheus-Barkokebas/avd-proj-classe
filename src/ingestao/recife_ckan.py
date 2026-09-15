import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import requests

API_URL = "https://dados.recife.pe.gov.br/pt_BR/api/action/datastore_search"
DEFAULT_LIMIT = 1000
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF = 1  # seconds


def _request_with_retry(params: Dict[str, Any], max_retries: int, backoff: int) -> Dict[str, Any]:
    """Execute GET with retry on network/HTTP errors."""
    attempt = 0
    while True:
        try:
            response = requests.get(API_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            attempt += 1
            if attempt > max_retries:
                raise RuntimeError(f"Falha ao acessar CKAN após {max_retries} tentativas: {exc}")
            time.sleep(backoff)


def fetch_all(
    resource_id: str,
    filtros: Dict[str, Any] | None = None,
    limit_per_page: int = DEFAULT_LIMIT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff: int = DEFAULT_BACKOFF,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Coleta todos os registros de um resource_id.

    Retorna (registros, metadados) onde metadados contém:
    - resource_id
    - total (quantidade total informada pela API)
    - coletado_em (ISO timestamp UTC)
    """
    if not resource_id:
        raise ValueError("resource_id é obrigatório")
    filtros = filtros or {}
    offset = 0
    all_records: List[Dict[str, Any]] = []
    total = None
    while True:
        params: Dict[str, Any] = {
            "resource_id": resource_id,
            "limit": limit_per_page,
            "offset": offset,
        }
        if filtros:
            params["filters"] = filtros
        data = _request_with_retry(params, max_retries, backoff)
        result = data.get("result", {})
        records = result.get("records", [])
        if total is None:
            total = result.get("total", len(records))
        all_records.extend(records)
        offset += limit_per_page
        if len(records) < limit_per_page or len(all_records) >= total:
            break
    metadata = {
        "resource_id": resource_id,
        "total": total,
        "coletado_em": datetime.now(timezone.utc).isoformat(),
    }
    return all_records, metadata
