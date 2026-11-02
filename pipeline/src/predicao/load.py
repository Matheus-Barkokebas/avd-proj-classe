from datetime import timedelta
import json

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

    def salvar_execucao(self, nome_modelo, X, X_teste, metricas, linha_de_base, validacao, tempo, arvore, faixas, horizonte_horas=3):
        """Guarda a avaliação deste treino. Cada treino vira uma linha, e a API mostra a mais recente."""
        with padronizada.DestinoNeon.do_ambiente().conexao() as conexao, conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO gold.modelo_execucao (modelo, inicio, fim, horas, horas_teste, horizonte_horas, linha_de_base, "
                "acuracia, precisao, recall, validacao_cruzada, tempo_linha_de_base, tempo_acuracia, tempo_balanceada, "
                "verdadeiros_positivos, falsos_positivos, falsos_negativos, verdadeiros_negativos, importancia, arvore, faixas) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)",
                (nome_modelo, X.index.min(), X.index.max(), len(X), len(X_teste), horizonte_horas, float(linha_de_base),
                 float(metricas["acuracia"]), float(metricas["precisao"]), float(metricas["recall"]), float(validacao),
                 float(tempo["linha_de_base"]), float(tempo["acuracia"]), float(tempo["acuracia_balanceada"]),
                 metricas["verdadeiros_positivos"], metricas["falsos_positivos"], metricas["falsos_negativos"],
                 metricas["verdadeiros_negativos"], json.dumps(metricas["importancia"]), json.dumps(arvore), json.dumps(faixas)))
        print("[load] avaliação gravada em gold.modelo_execucao")
