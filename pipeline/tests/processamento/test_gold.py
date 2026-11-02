from src.processamento import gold


def test_grafias_viram_chave_do_bairro_e_o_resto_fica_sem_chave():
    apelidos = {"COHAB - IBURA DE CIMA": "COHAB"}
    resultado = gold.mapear_bairros(["Várzea", " boa  viagem", "COHAB - IBURA DE CIMA", "JIQU]"],
                                    {"VARZEA", "BOA VIAGEM", "COHAB"}, apelidos)
    assert resultado == [("Várzea", "VARZEA"), (" boa  viagem", "BOA VIAGEM"),
                         ("COHAB - IBURA DE CIMA", "COHAB"), ("JIQU]", None)]


def test_classificacao_do_yaml_tem_o_descartado_e_nao_inventa_codigo_sem_documentacao():
    linhas = gold.linhas_classificacao(gold.carregar_configuracao())
    assert ("dengue", "5", "Descartado", "descartado") in linhas
    assert ("dengue", "11", "Dengue com sinais de alarme", "confirmado") in linhas
    codigos = {(agravo, codigo) for agravo, codigo, _, _ in linhas}
    assert ("zika", "2") not in codigos and ("chikungunya", "13") not in codigos


def test_views_leem_a_silver_com_schema_explicito_e_sem_coluna_de_controle():
    for nome, consulta in gold.VIEWS.items():
        assert "data_coleta" not in consulta, nome
        assert "FROM public." in consulta, nome


def test_contagem_de_arboviroses_nao_conta_duas_vezes_o_que_esta_nos_dois_anos():
    assert "UNION ALL" in gold.TABELA_ARBO and "NOT EXISTS" in gold.TABELA_ARBO
