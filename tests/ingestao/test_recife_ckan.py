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
