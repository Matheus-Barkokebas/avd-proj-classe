from datetime import timedelta

from src.ingestao import padronizada


class Load:
    """Grava as previsões do modelo na GOLD."""

    def salvar_previsoes(self, X, y, teste, classificador, nome_modelo, horizonte_horas=3):
        """Substitui as previsões deste modelo. `conjunto` diz se a hora foi usada no treino ou só no teste."""
        probabilidades = classificador.modelo.predict_proba(X)[:, 1]
        previstos = classificador.modelo.predict(X)
        with padronizada.DestinoNeon.do_ambiente().conexao() as conexao, conexao.cursor() as cur:
            cur.execute("DELETE FROM gold.previsao_alagamento WHERE modelo = %s", (nome_modelo,))
            with cur.copy("COPY gold.previsao_alagamento (hora, hora_prevista, conjunto, probabilidade, previsto, observado, modelo) "
                          "FROM STDIN") as dados:
                for hora, prob, prev, obs in zip(X.index, probabilidades, previstos, y):
                    dados.write_row((hora, hora + timedelta(hours=horizonte_horas), "teste" if hora in teste else "treino",
                                     round(float(prob), 4), int(prev), int(obs), nome_modelo))
        print(f"[load] {len(X)} previsões gravadas em gold.previsao_alagamento")
