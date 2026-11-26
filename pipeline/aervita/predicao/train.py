from pathlib import Path

from aervita.predicao.extract import Extract
from aervita.predicao.load import Load
from aervita.predicao.ml_model import Classificador

NOME_MODELO = "arvore_alagamento_3h"
extract = Extract()
classificador = Classificador()
df = extract.ler_gold()
X, y = classificador.preparar(df)
X_treino, X_teste, y_treino, y_teste = classificador.dividir(X, y)

linha_de_base = classificador.linha_de_base(X_treino, y_treino, X_teste, y_teste)
validacao = classificador.ajustar(X_treino, y_treino)
classificador.treinar(X_treino, y_treino)
classificador.avaliar(X_teste, y_teste)
classificador.explicar()
classificador.matriz_confusao(X_teste, y_teste, Path(__file__).parent / "resultados" / "matriz_confusao.png")
tempo = classificador.validar_no_tempo(X, y)
load = Load()
load.salvar_previsoes(X, y, set(X_teste.index), classificador, NOME_MODELO)
load.salvar_execucao(NOME_MODELO, X, X_teste, classificador.metricas(X_teste, y_teste), linha_de_base, validacao, tempo,
                     classificador.exportar_arvore(), classificador.faixas(X_treino))
