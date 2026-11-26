import pandas as pd

from aervita.ingestao.nucleo import padronizada


class Extract:
    """Lê os dados do modelo. Só a GOLD é consumida pela predição."""

    def ler_gold(self):
        with padronizada.DestinoNeon.do_ambiente().conexao() as conexao, conexao.cursor() as cur:
            cur.execute("SELECT * FROM gold.ml_alagamento_hora WHERE alagou_no_horizonte IS NOT NULL ORDER BY hora")
            colunas = [coluna.name for coluna in cur.description]
            df = pd.DataFrame(cur.fetchall(), columns=colunas)
        print(f"[extract] {len(df)} horas lidas da gold, de {df.hora.min()} a {df.hora.max()}")
        return df
