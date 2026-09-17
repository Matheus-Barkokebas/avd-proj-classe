"""Testa serialização de filtros no cliente CKAN."""

from unittest.mock import patch
import json

from src.ingestao import recife_ckan


def test_filtros_serializados_como_json():
    filtros = {"bairro": "Boa Viagem", "tipo": 1}
    # Simular resposta única
    resp = type("Resp", (), {"json": lambda *args, **kwargs: {"result": {"records": [], "total": 0}}, "raise_for_status": lambda *args, **kwargs: None})()
    captured_params = {}
    def fake_get(url, params=None, timeout=None):
        captured_params.update(params)
        return resp
    with patch("requests.get", side_effect=fake_get) as mock_get:
        recife_ckan.fetch_all("dummy_id", filtros=filtros)
        # Verifica que o parâmetro filters foi enviado como string JSON
        assert "filters" in captured_params
        assert captured_params["filters"] == json.dumps(filtros)
        mock_get.assert_called_once()
