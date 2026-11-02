from src.ingestao import inmet

CABECALHO = "".join(f"LINHA {i}:;x\n" for i in range(8))
CSV = (CABECALHO + "Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm);PRESSAO\n"
       "2026/06/01;0000 UTC;1,4;1015\n2026/06/01;0100 UTC;;1015\n2026-06-01;02:00;-9999;1015\n").encode("latin-1")


def test_fica_o_recorte_mais_longo_da_estacao():
    nomes = ["2026/INMET_NE_PE_A301_RECIFE_01-01-2026_A_31-08-2026.CSV",
             "INMET_NE_PE_A301_RECIFE_01-01-2026_A_30-09-2026.CSV",
             "INMET_NE_PE_A307_PETROLINA_01-01-2026_A_31-10-2026.CSV"]
    assert inmet.arquivo_da_estacao(nomes, "A301") == nomes[1]
    assert inmet.arquivo_da_estacao(nomes, "A999") is None


def test_hora_utc_vira_recife_e_falta_de_leitura_fica_vazia():
    assert inmet.ler_csv(CSV, "A301") == [
        {"estacao": "A301", "data_hora": "2026-05-31 21:00:00", "chuva_mm": 1.4},
        {"estacao": "A301", "data_hora": "2026-05-31 22:00:00", "chuva_mm": None},
        {"estacao": "A301", "data_hora": "2026-05-31 23:00:00", "chuva_mm": None},
    ]
