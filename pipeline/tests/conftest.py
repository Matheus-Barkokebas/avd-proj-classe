"""Configuração compartilhada dos testes."""

import time

import pytest


@pytest.fixture(autouse=True)
def _sem_espera_entre_tentativas(request, monkeypatch):
    """Produção espera entre novas tentativas HTTP (backoff exponencial, BUG-10);
    os testes unitários simulam falhas e não devem dormir. Os de integração
    (`-m integracao`) mantêm a espera real, porque falam com as APIs de verdade."""
    if request.node.get_closest_marker("integracao") is None:
        monkeypatch.setattr(time, "sleep", lambda segundos: None)
