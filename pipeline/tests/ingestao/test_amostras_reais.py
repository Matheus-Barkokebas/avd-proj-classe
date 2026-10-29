"""Testes com amostras REAIS reduzidas das fontes CKAN (QA-01).

Diferente dos fixtures escritos à mão, estas amostras vêm da API real
(tests/fixtures/atualizar_amostras.py) e preservam o formato de cada campo.
Usam os YAMLs reais de conf/sources/ — configuração, código e formato real
testados juntos. Os fixtures à mão não pegaram BUG-03, BUG-06 e BUG-08;
estes pegariam. Sem rede.
"""

from collections import Counter
from datetime import date
import json
from pathlib import Path

import pyarrow.parquet as pq

from src.ingestao import bronze, comum, epidemiologia, ocorrencias, territorio

AMOSTRAS = Path(__file__).resolve().parents[1] / "fixtures" / "amostras"
DATA = date(2026, 9, 24)


def _amostra(nome):
    return json.loads((AMOSTRAS / nome).read_text(encoding="utf-8"))


def _lote_epidemiologia():
    config = epidemiologia.carregar_configuracao_fonte()
    lote = []
    for agravo, registros in _amostra("epidemiologia.json").items():
        lote += epidemiologia._transformar_para_bronze(registros, config["mapeamento_colunas"], agravo)
    return lote


def test_epidemiologia_datas_reais_de_todos_os_agravos_normalizam():
    """BUG-03: dengue (ISO) e zika/chikungunya (DD/MM/AAAA) viram o formato padrão."""
    for linha in _lote_epidemiologia():
        assert linha["data_notificacao"] == comum.normalizar_timestamp(linha["data_notificacao"])
        assert len(linha["data_notificacao"]) == 19 and linha["data_notificacao"][4] == "-"


def test_epidemiologia_real_bronze_com_validas_e_quarentena_com_bairro_vazio(tmp_path):
    """BUG-06/BUG-08: bairro vazio real vai para a quarentena, o resto para a Bronze."""
    lote = _lote_epidemiologia()
    sem_bairro = sum(1 for linha in lote if not linha["bairro"])
    assert sem_bairro >= 1  # a amostra inclui de propósito o caso real

    caminho = bronze.gravar_validado(lote, "epidemiologia", "epidemiologia", DATA, tmp_path)

    assert pq.read_table(caminho).num_rows == len(lote) - sem_bairro
    assert bronze.contar_rejeitados(tmp_path, "epidemiologia", DATA) == sem_bairro


def test_epidemiologia_real_protocolo_se_repete_mas_chave_do_contrato_nao():
    """BUG-07: a amostra tem o mesmo número de notificação em agravos diferentes."""
    lote = _lote_epidemiologia()
    assert max(Counter(l["protocolo"] for l in lote).values()) > 1
    chave = Counter((l["agravo"], l["protocolo"], l["data_notificacao"]) for l in lote)
    assert max(chave.values()) == 1


def test_ocorrencias_amostra_real_passa_no_contrato(tmp_path):
    config = ocorrencias.carregar_configuracao_fonte()
    lote = ocorrencias._transformar_para_bronze(
        _amostra("ocorrencias.json"), config["mapeamento_colunas"], config.get("mapa_status", {}))

    caminho = bronze.gravar_validado(lote, "ocorrencias", "ocorrencias", DATA, tmp_path)

    assert pq.read_table(caminho).num_rows == len(lote)
    assert all(l["data_ocorrencia"] and len(l["data_ocorrencia"]) == 19 for l in lote)


def test_territorio_amostras_reais_tipam_rpa_e_distrito():
    config = territorio.carregar_configuracao_fonte()["bases_tabulares"]

    bairros = territorio._transformar_tabular(
        _amostra("territorio_bairros_rpa.json"), config["bairros_rpa"]["mapeamento_colunas"])
    distritos = territorio._transformar_tabular(
        _amostra("territorio_distritos_sanitarios.json"), config["distritos_sanitarios"]["mapeamento_colunas"])

    assert all(isinstance(b["rpa"], int) and 1 <= b["rpa"] <= 6 for b in bairros)
    assert all(isinstance(d["distrito_sanitario"], int) and 1 <= d["distrito_sanitario"] <= 8 for d in distritos)
    assert all(b["nome_bairro"] for b in bairros + distritos)
