from datetime import datetime, timedelta

from src.processamento import gold_alagamento as ga

T0 = datetime(2026, 6, 1, 0, 0)
HORA = timedelta(hours=1)
CONFIG = {"janelas_chuva": [1, 3], "horizonte_horas": 3, "mare_futura_horas": 2, "estacao": "A301"}
EXTREMOS = [(T0 - HORA * 6, 0.0), (T0, 2.0), (T0 + HORA * 6, 0.0), (T0 + HORA * 12, 2.0)]


def test_mare_interpolada_entre_extremos():
    assert ga.mare_na_hora(EXTREMOS, T0 + HORA * 3) == (1.0, 0)
    assert ga.mare_na_hora(EXTREMOS, T0 + HORA * 9) == (1.0, 1)
    assert ga.mare_na_hora(EXTREMOS, T0 - HORA * 7) is None
    assert ga.mare_na_hora(EXTREMOS, T0 + HORA * 13) is None


def test_chuva_acumula_so_ate_a_hora_e_alvo_e_do_horizonte():
    chuva = {T0 + HORA * k: float(k) for k in range(6)}
    rotas = {T0 + HORA * 2: 0, T0 + HORA * 5: 4}
    linhas = {l["hora"]: l for l in ga.montar_linhas(chuva, EXTREMOS, rotas, CONFIG)}
    linha = linhas[T0 + HORA * 2]  # chuva das horas 0, 1 e 2; alvo vem da hora 5
    assert linha["chuva_1h_mm"] == 2.0 and linha["chuva_3h_mm"] == 3.0
    assert linha["rotas_alagadas"] == 0 and linha["rotas_alagadas_futuro"] == 4 and linha["alagou_no_horizonte"] == 1


def test_sem_vazamento_chuva_futura_nao_muda_as_variaveis():
    chuva = {T0 + HORA * k: 1.0 for k in range(6)}
    antes = {l["hora"]: l for l in ga.montar_linhas(chuva, EXTREMOS, {}, CONFIG)}[T0 + HORA * 2]
    chuva[T0 + HORA * 3] = chuva[T0 + HORA * 5] = 500.0
    depois = {l["hora"]: l for l in ga.montar_linhas(chuva, EXTREMOS, {}, CONFIG)}[T0 + HORA * 2]
    assert antes == depois


def test_sem_vazamento_alagamento_futuro_so_muda_o_alvo():
    chuva = {T0 + HORA * k: 1.0 for k in range(6)}
    sem = {l["hora"]: l for l in ga.montar_linhas(chuva, EXTREMOS, {T0 + HORA * 5: 0}, CONFIG)}[T0 + HORA * 2]
    com = {l["hora"]: l for l in ga.montar_linhas(chuva, EXTREMOS, {T0 + HORA * 5: 9}, CONFIG)}[T0 + HORA * 2]
    alvo = {"rotas_alagadas_futuro", "alagou_no_horizonte"}
    assert {k: v for k, v in sem.items() if k not in alvo} == {k: v for k, v in com.items() if k not in alvo}


def test_hora_sem_coleta_fica_sem_alvo_e_falta_de_chuva_e_registrada():
    chuva = {T0 + HORA * k: 1.0 for k in range(6)}
    chuva[T0 + HORA] = None
    linha = {l["hora"]: l for l in ga.montar_linhas(chuva, EXTREMOS, {}, CONFIG)}[T0 + HORA * 2]
    assert linha["alagou_no_horizonte"] is None and linha["rotas_alagadas"] is None
    assert linha["chuva_3h_mm"] == 2.0 and linha["horas_sem_leitura_24h"] > 0
