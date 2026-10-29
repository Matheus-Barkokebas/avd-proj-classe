"""Testes da coleta do COP Recife — sem rede: o ArcGIS é simulado.

Os valores de exemplo vêm de leituras reais conferidas em 2026-10-28; as
datas esperadas batem com os textos que a própria fonte publica ao lado
(TXT_DT/HORAS, DATACOLETA/HORACOLETA, ID_UNICO).
"""

from datetime import date
import json
from unittest.mock import patch

import pytest

from src.ingestao import arcgis
from src.ingestao import armazenamento as armaz
from src.ingestao import contratos
from src.ingestao import cop_recife
from src.ingestao import padronizada
from src.ingestao import runner

DIA = date(2026, 10, 28)
CONFIG = cop_recife.carregar_configuracao_fonte()


def _linha(fonte, atributos=None, geometria=None, geojson=False):
    feicao = ({"type": "Feature", "properties": atributos or {}, "geometry": geometria} if geojson
              else {"attributes": atributos or {}})
    return cop_recife.transformar({"features": [feicao]}, CONFIG["camadas"][fonte], DIA)[0]


def test_fontes_do_runner_batem_com_o_yaml():
    assert set(runner.FONTES_COP) == set(CONFIG["camadas"])
    for fonte in runner.FONTES_COP:
        assert runner.COLETORES[fonte].suporta_historico is False
        contratos.carregar_contrato(fonte)  # todo contrato existe e carrega


@pytest.mark.parametrize("fonte", list(CONFIG["camadas"]))
def test_campos_do_yaml_sao_os_campos_do_contrato(fonte):
    contrato = contratos.carregar_contrato(fonte)
    assert list(CONFIG["camadas"][fonte]["campos"]) == [c["nome"] for c in contrato["campos"]]
    padronizada.ddl_tabela(contrato)


def test_indicadores_data_em_utc_verdadeiro_vira_horario_do_recife():
    linha = _linha("cop_indicadores", {"DATA": 1793224927636, "DATA_UTC": 1793214127636, "ESTAGIO": "NORMALIDADE",
                                       "PREC_MEDIA24H": 6.2, "PREC_24H_MAX": 15.2, "PREC_ESTACAO_24H": "Areias",
                                       "MARE": 1.7, "OCORRENCIA": 9, "ABRIGADOS": None})
    assert linha["data_hora"] == "2026-10-28 19:02:07"
    assert linha["chuva_media_24h_mm"] == 6.2 and linha["estacao_max_24h"] == "Areias"
    assert linha["ocorrencias"] == 9 and linha["abrigados"] is None


def test_rios_usam_data_e_hora_em_texto():
    linha = _linha("cop_rios", {"IDSTATION": 39145010, "NAMESTATION": "LIMOEIRO", "RIVER": "RIO CAPIBARIBE",
                                "DATACOLETA": "28/10/2026", "HORACOLETA": "18:00:00", "DATACOMPLETA": 1793210400000,
                                "LEVELNOW": 177.0, "PREALERTLEVEL": 600.0, "ALERTLEVEL": 650.0, "FLOODLEVEL": 750.0,
                                "SITUACAO": "Normal"})
    assert linha["data_hora"] == "2026-10-28 18:00:00"
    assert linha["codigo_estacao"] == "39145010"
    assert (linha["nivel"], linha["cota_alerta"], linha["cota_inundacao"]) == (177.0, 650.0, 750.0)


def test_previsao_bate_com_o_texto_da_fonte():
    # na fonte: TXT_DT "27-10-2026", HORAS 21
    linha = _linha("cop_previsao_chuva", {"DATAS": 1793145600000, "GFS": 0.4, "ECMWF": 0.0, "ICON": None, "WRF": 1.2})
    assert linha["data_hora_prevista"] == "2026-10-27 21:00:00"
    assert (linha["chuva_gfs_mm"], linha["chuva_icon_mm"], linha["chuva_wrf_mm"]) == (0.4, None, 1.2)


def test_pluviometro_horario_local_gravado_como_utc():
    # IDUNICO 01064_1772149071000 é o instante verdadeiro (20:37:51 no Recife)
    linha = _linha("cop_pluviometros", {"OBJECTID": 1156870, "CODESTACAO": "01064", "NOME": "01064 - Estação Meteorológica",
                                        "TIPO": "Estação", "CHUVA": 0.2, "DATAHORA": 1772138271000,
                                        "LATITUDE": -8.04554, "LONGITUDE": -34.92065})
    assert linha["data_hora"] == "2026-02-26 20:37:51"
    assert linha["id_leitura"] == "1156870" and linha["chuva_mm"] == 0.2


def test_chuva_mensal_converte_mes_e_usa_o_ano_da_coleta():
    linha = _linha("cop_chuva_mensal", {"MESES": "MARÇO", "PREC_ATUAL": 124.4, "PREC_ANTERIOR": 160.65, "MEDIA": 159.56})
    assert (linha["ano_referencia"], linha["mes"], linha["media_historica_mm"]) == (2026, 3, 159.56)


def test_areas_alagaveis_guardam_o_poligono_em_geojson():
    poligono = {"type": "Polygon", "coordinates": [[[-34.93, -8.10], [-34.92, -8.10], [-34.92, -8.11], [-34.93, -8.10]]]}
    linha = _linha("cop_areas_alagaveis", {"OBJECTID": 1, "DS": 8, "LOTE": 1, "CODIGO": 106,
                                           "DB2GSE.ST_Area(SHAPE)": 170446.76}, poligono, geojson=True)
    assert linha["distrito_sanitario"] == 8 and linha["area_m2"] == 170446.76
    assert json.loads(linha["geometria_geojson"]) == poligono


def test_pontos_de_alagamento_com_coordenadas_e_datas():
    ponto = {"type": "Point", "coordinates": [-34.897, -8.0714]}
    linha = _linha("cop_pontos_alagamento", {"OBJECTID": 1, "RPA": 1.0, "BAIRRO": "ILHA JOANA BEZERRA",
                                             "STATUS": "CONCLUÍDO", "CLASSIFICA": "RESOLVIDO", "F__CONCLU": 1,
                                             "INICIO_RE": 1448928000000, "TERMINO_R": None}, ponto, geojson=True)
    assert (linha["longitude"], linha["latitude"]) == (-34.897, -8.0714)
    assert linha["rpa"] == 1 and linha["inicio_intervencao"] == "2015-12-01" and linha["termino_intervencao"] is None


def test_valor_invalido_passa_intacto_para_o_contrato_rejeitar():
    linha = _linha("cop_indicadores", {"DATA": 1793224927636, "PREC_MEDIA24H": "n/d"})
    assert linha["chuva_media_24h_mm"] == "n/d"
    violacoes = contratos.validar([linha], contratos.carregar_contrato("cop_indicadores"))
    assert any(v.campo == "chuva_media_24h_mm" for v in violacoes)


def test_ponta_a_ponta_raw_e_padronizada_local(tmp_path):
    feicoes = [{"attributes": {"IDSTATION": 1, "NAMESTATION": "A", "RIVER": "RIO X", "DATACOLETA": "28/10/2026",
                               "HORACOLETA": f"{h:02d}:00:00", "LEVELNOW": 100.0 + h}} for h in range(3)]
    feicoes.append({"attributes": {"IDSTATION": 2, "NAMESTATION": None, "RIVER": "RIO X", "DATACOLETA": "28/10/2026",
                                   "HORACOLETA": "01:00:00", "LEVELNOW": 1.0}})  # sem nome: quarentena
    with patch.object(arcgis, "consultar", return_value=feicoes):
        r = cop_recife.coletar_e_materializar("cop_rios", diretorio_dados=tmp_path)
    assert r["execucao"]["status"] == "ok" and r["execucao"]["numero_registros"] == 4
    assert r["padronizada"].endswith("cop_rios.parquet") and r["rejeitados"] == 1
    dia = date.fromisoformat(r["execucao"]["data_coleta"])
    raw = armaz.ler_json(armaz.ArmazenamentoArquivo(tmp_path), "cop_rios", dia, "arcgis.json")
    assert raw["formato"] == "json" and len(raw["features"]) == 4  # RAW guarda a resposta inteira


def test_consulta_arcgis_pagina_ate_o_fim():
    paginas = [
        {"features": [{"attributes": {"OBJECTID": i}} for i in range(2000)], "exceededTransferLimit": True},
        {"features": [{"attributes": {"OBJECTID": i}} for i in range(2000, 2500)]},
    ]
    respostas = iter(paginas)

    def falso_get(url, params=None, timeout=None):
        dados = next(respostas)
        return type("R", (), {"raise_for_status": lambda s: None, "json": lambda s: dados})()

    with patch("requests.get", side_effect=falso_get) as get:
        feicoes = arcgis.consultar("https://x/MapServer/0")
    assert len(feicoes) == 2500
    assert [c.kwargs["params"]["resultOffset"] for c in get.call_args_list] == [0, 2000]


def test_erro_do_arcgis_com_status_200_e_tratado_como_falha():
    resposta = type("R", (), {"raise_for_status": lambda s: None, "json": lambda s: {"error": {"code": 400}}})()
    with patch("requests.get", return_value=resposta):
        with pytest.raises(RuntimeError, match="ArcGIS recusou"):
            arcgis.consultar("https://x/MapServer/0", max_retries=0)
