from src.ingestao import epidemiologia_historico as historico

CONFIG = historico.carregar_configuracao()


def test_seleciona_so_casos_ate_o_ano_maximo():
    recursos = [{"name": n} for n in (
        "Casos de Dengue 2025", " Casos de Dengue 2022", "Casos de Dengue em 2015", "Casos confirmados de Zika 2021",
        "Casos confirmados de Chikungunya em 2016", "Tabela de Bairros", "Metadados dos Casos Confirmados de Dengue 2013-2015")]
    selecionados = historico.recursos_historicos(recursos, 2024)
    assert [r["ano"] for r in selecionados] == [2015, 2016, 2021, 2022]


def test_agravo_vem_do_cid_em_qualquer_grafia():
    mapa = CONFIG["cid_agravo"]
    assert historico.agravo_do_cid("A90", mapa) == "dengue"
    assert historico.agravo_do_cid("A92.0", mapa) == "chikungunya"
    assert historico.agravo_do_cid("A928", mapa) == "zika"
    assert historico.agravo_do_cid("Z99", mapa) is None
    assert historico.agravo_do_cid(None, mapa) is None


def test_layout_a_partir_de_2021_mesmo_em_minusculas():
    # "Zika 2021" do portal é chikungunya pelo CID; o título não decide.
    for chaves in (str.upper, str.lower):
        registro = {chaves(k): v for k, v in {
            "NU_NOTIFIC": 4724661, "ID_AGRAVO": "A92.0", "DT_NOTIFIC": "2021-01-01T00:00:00", "SEM_NOT": 202053,
            "NU_ANO": 2021, "NM_BAIRRO": "ARRUDA", "CLASSI_FIN": 5, "NM_PACIENT": "não deve passar"}.items()}
        assert historico.padronizar(registro, CONFIG) == {
            "protocolo": "4724661", "data_notificacao": "2021-01-01 00:00:00", "semana_epidemiologica": 202053,
            "ano": 2021, "bairro": "ARRUDA", "agravo": "chikungunya", "classificacao_final": "5", "contagem": 1}


def test_layout_antigo_e_csv_com_codigo_decimal():
    conteudo = ("nu_notificacao,co_cid,dt_notificacao,ds_semana_notificacao,notificacao_ano,"
                "no_bairro_residencia,tp_classificacao_final,dt_nascimento\n"
                "1552181,A90,2014-01-17,201403,2014,JORDAO,5.0,1990-01-01\n").encode("utf-8")
    linha = historico.padronizar(historico.ler_csv(conteudo)[0], CONFIG)
    assert linha == {"protocolo": "1552181", "data_notificacao": "2014-01-17 00:00:00", "semana_epidemiologica": 201403,
                     "ano": 2014, "bairro": "JORDAO", "agravo": "dengue", "classificacao_final": "5", "contagem": 1}
