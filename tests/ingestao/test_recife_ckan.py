"""Tests for recife_ckan client with pagination and retry."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import requests

from src.ingestao import recife_ckan


def make_response(records, total=None):
    return {
        "result": {
            "records": records,
            "total": total if total is not None else len(records),
        }
    }


def test_pagination_collects_all_records():
    # Simulate three pages: 1000, 1000, 500 records, total 2500
    page1 = [{"id": i} for i in range(1000)]
    page2 = [{"id": i} for i in range(1000, 2000)]
    page3 = [{"id": i} for i in range(2000, 2500)]
    responses = [make_response(page1, 2500), make_response(page2, 2500), make_response(page3, 2500)]

    def fake_get(url, params=None, timeout=None):
        offset = params.get("offset", 0)
        if offset == 0:
            json_data = responses[0]
        elif offset == 1000:
            json_data = responses[1]
        else:
            json_data = responses[2]
        mock_resp = type("Resp", (), {"json": lambda *args, **kwargs: json_data, "raise_for_status": lambda *args, **kwargs: None})()
        return mock_resp

    with patch("requests.get", side_effect=fake_get) as mock_get:
        records, meta = recife_ckan.fetch_all("dummy_id")
        assert len(records) == 2500
        assert meta["total"] == 2500
        assert meta["resource_id"] == "dummy_id"
        # timestamp is recent
        ts = datetime.fromisoformat(meta["coletado_em"]).replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        assert (now - ts).total_seconds() < 5
        # ensure three calls
        assert mock_get.call_count == 3


def _servidor_ckan(total_registros, teto_por_pagina, informa_total=True):
    """Simula o CKAN: fatia os dados pelo offset e ignora `limit` acima do teto."""
    dados = [{"id": i} for i in range(total_registros)]

    def fake_get(url, params=None, timeout=None):
        offset = params["offset"]
        tamanho = min(params["limit"], teto_por_pagina)
        resultado = {"records": dados[offset:offset + tamanho]}
        if informa_total:
            resultado["total"] = total_registros
        return type("Resp", (), {"json": lambda *a, **k: {"result": resultado},
                                 "raise_for_status": lambda *a, **k: None})()

    return fake_get


def test_paginacao_respeita_teto_do_servidor_menor_que_limit():
    """BUG-01: CKAN do Recife devolve no máximo 500 por página mesmo pedindo 1000."""
    with patch("requests.get", side_effect=_servidor_ckan(9187, teto_por_pagina=500)) as mock_get:
        registros, meta = recife_ckan.coletar_todos("dengue", limite_por_pagina=1000)

    assert len(registros) == 9187
    assert [r["id"] for r in registros] == list(range(9187))  # sem buraco nem repetição
    assert meta["total"] == 9187
    assert mock_get.call_count == 19  # ceil(9187 / 500)


def test_paginacao_sem_total_para_na_pagina_vazia():
    with patch("requests.get", side_effect=_servidor_ckan(1200, teto_por_pagina=500, informa_total=False)):
        registros, meta = recife_ckan.coletar_todos("x", limite_por_pagina=1000)

    assert len(registros) == 1200
    assert meta["total"] == 1200


def test_retry_on_transient_error():
    page = [{"id": 1}]
    good_resp = type("Resp", (), {"json": lambda *args, **kwargs: make_response(page, 1), "raise_for_status": lambda *args, **kwargs: None})()

    def side_effect(*args, **kwargs):
        # first call fails, second succeeds
        if side_effect.called:
            return good_resp
        side_effect.called = True
        raise requests.exceptions.ConnectionError("temporario")
    side_effect.called = False

    with patch("requests.get", side_effect=side_effect) as mock_get:
        records, meta = recife_ckan.fetch_all("id")
        assert len(records) == 1
        assert mock_get.call_count == 2


def test_exceeds_max_retries_raises():
    def always_fail(*args, **kwargs):
        raise requests.exceptions.Timeout("timeout")

    with patch("requests.get", side_effect=always_fail):
        with pytest.raises(RuntimeError):
            recife_ckan.fetch_all("id", max_retries=2)


def test_obter_url_download_usa_resource_show():
    """BUG-04: URL de download vem do CKAN (resource_show), não montada à mão."""
    resp = type("Resp", (), {
        "json": lambda *a, **k: {"success": True, "result": {"url": "https://dados.exemplo/download/bairros.geojson"}},
        "raise_for_status": lambda *a, **k: None,
    })()
    with patch("requests.get", return_value=resp) as mock_get:
        url = recife_ckan.obter_url_download("5c67ce14")

    assert url == "https://dados.exemplo/download/bairros.geojson"
    assert mock_get.call_args.args[0].endswith("/api/action/resource_show")
    assert mock_get.call_args.kwargs["params"] == {"id": "5c67ce14"}
