"""Testes de integração contra as APIs REAIS (QA-01).

Fora do `pytest` padrão e do CI (acessam a rede). Rodar explicitamente:

    pytest -m integracao

Cobrem o que só aparece com a fonte de verdade: teto de página do CKAN
(BUG-01), URLs de download resolvidas (BUG-04) e a coleta de ponta a ponta
gravando Bronze (BUG-03/06).
"""

import json

import pytest

from src.ingestao import epidemiologia, recife_ckan, runner, territorio

pytestmark = pytest.mark.integracao

DENGUE = "45a675e2-d387-4019-bb6e-4b915b74b1bf"


def test_ckan_pagina_ate_o_total_informado():
    """BUG-01: o servidor limita a página a 500; a coleta precisa trazer tudo."""
    registros, meta = recife_ckan.coletar_todos(DENGUE)
    assert len(registros) == meta["total"] > 500


@pytest.mark.parametrize("nome_base", ["bairros_geo", "rpa_geo"])
def test_bases_geometricas_tem_url_de_download_valida(nome_base):
    """BUG-04: a URL vem do resource_show e o arquivo baixa sem 404."""
    cfg = territorio.carregar_configuracao_fonte()["bases_geometricas"][nome_base]
    url = recife_ckan.obter_url_download(cfg["resource_id"])
    conteudo = territorio._baixar_arquivo(url)
    assert json.loads(conteudo)["type"] == "FeatureCollection"


def test_epidemiologia_ponta_a_ponta_grava_bronze(tmp_path):
    resultado = epidemiologia.coletar_e_materializar(diretorio_dados=tmp_path)
    assert resultado["execucao"]["status"] == "ok", resultado["execucao"]["mensagem"]
    assert resultado["bronze"]
    assert resultado["execucao"]["numero_registros"] > 500


def test_territorio_ponta_a_ponta_sem_base_com_erro(tmp_path):
    resultado = territorio.coletar_e_materializar(diretorio_dados=tmp_path)
    assert resultado["execucao"]["status"] == "ok", resultado["execucao"]["mensagem"]
    assert resultado["bases_com_erro"] == {}
    assert set(resultado["bronze"]) == {"bairros_rpa", "distritos_sanitarios", "bairros_geo", "rpa_geo"}


def test_registro_de_execucao_real_no_runner(tmp_path):
    registro = runner.executar("territorio", diretorio_dados=tmp_path)
    assert registro["status"] == "ok"
    assert (tmp_path / "raw" / "territorio").is_dir()
