"""Testes da gravação da Bronze com quarentena (src/ingestao/bronze.py) — BUG-06."""

from datetime import date
import json

import pyarrow.parquet as pq
import pytest

from src.ingestao import bronze

DATA = date(2026, 9, 24)


def _notificacao(protocolo, bairro="PINA", **extra):
    reg = {
        "protocolo": protocolo,
        "data_notificacao": "2025-04-03 00:00:00",
        "semana_epidemiologica": 202514,
        "ano": 2025,
        "bairro": bairro,
        "agravo": "dengue",
        "classificacao_final": "10",
        "contagem": 1,
    }
    reg.update(extra)
    return reg


def test_linha_invalida_vai_para_quarentena_e_validas_para_bronze(tmp_path):
    lote = [_notificacao("1"), _notificacao("2", bairro=None), _notificacao("3")]

    caminho = bronze.gravar_validado(lote, "epidemiologia", "epidemiologia", DATA, tmp_path)

    tabela = pq.read_table(caminho)
    assert tabela["protocolo"].to_pylist() == ["1", "3"]

    rejeitadas = json.loads(bronze.caminho_quarentena(tmp_path, "epidemiologia", DATA).read_text(encoding="utf-8"))
    assert len(rejeitadas) == 1
    assert rejeitadas[0]["linha"] == 2
    assert rejeitadas[0]["registro"]["protocolo"] == "2"
    assert any("nulo_obrigatorio" in m and "bairro" in m for m in rejeitadas[0]["motivos"])
    assert bronze.contar_rejeitados(tmp_path, "epidemiologia", DATA) == 1


def test_violacao_de_lote_aborta_sem_gravar(tmp_path):
    """Coluna obrigatória ausente em todo o lote = fonte mudou: aborta."""
    lote = [{k: v for k, v in _notificacao(str(i)).items() if k != "bairro"} for i in range(3)]

    with pytest.raises(ValueError, match="no lote"):
        bronze.gravar_validado(lote, "epidemiologia", "epidemiologia", DATA, tmp_path)

    assert not (tmp_path / "bronze").exists()


def test_todas_as_linhas_rejeitadas_aborta(tmp_path):
    lote = [_notificacao("1", agravo="malaria"), _notificacao("2", agravo="malaria")]

    with pytest.raises(ValueError, match="todas as 2 linhas rejeitadas"):
        bronze.gravar_validado(lote, "epidemiologia", "epidemiologia", DATA, tmp_path)

    assert not (tmp_path / "bronze").exists()


def test_quarentena_antiga_e_removida_quando_reexecucao_nao_rejeita(tmp_path):
    bronze.gravar_validado([_notificacao("1"), _notificacao("2", bairro="")], "epidemiologia", "epidemiologia", DATA, tmp_path)
    assert bronze.contar_rejeitados(tmp_path, "epidemiologia", DATA) == 1

    bronze.gravar_validado([_notificacao("1"), _notificacao("2")], "epidemiologia", "epidemiologia", DATA, tmp_path)

    assert bronze.contar_rejeitados(tmp_path, "epidemiologia", DATA) == 0
    assert not bronze.caminho_quarentena(tmp_path, "epidemiologia", DATA).exists()


def test_quarentena_aceita_tipos_mistos(tmp_path):
    """Rejeitadas podem ter tipos mistos na mesma coluna — por isso JSON, não Parquet."""
    lote = [_notificacao("1"), _notificacao("2", semana_epidemiologica="abc"), _notificacao("3", semana_epidemiologica=None)]

    bronze.gravar_validado(lote, "epidemiologia", "epidemiologia", DATA, tmp_path)

    assert bronze.contar_rejeitados(tmp_path, "epidemiologia", DATA) == 2
