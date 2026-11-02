import matplotlib

matplotlib.use("Agg")  # só grava a imagem: não abre janela
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, balanced_accuracy_score, classification_report,
                             confusion_matrix, precision_score, recall_score)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text


class Classificador:
    """Prevê se alguma rota do Recife estará alagada daqui a 3 horas (dados da GOLD)."""

    ALVO = "alagou_no_horizonte"
    # Tudo aqui é conhecido na hora da previsão. Colunas do futuro, como rotas_alagadas_futuro, nunca entram.
    CHUVA = ["chuva_1h_mm", "chuva_3h_mm", "chuva_6h_mm", "chuva_12h_mm", "chuva_24h_mm", "chuva_72h_mm", "chuva_168h_mm"]
    MARE = ["mare_m", "mare_subindo", "mare_max_futura_m"]
    GRADE = {"max_depth": [3, 4, 5, 6, 8, 10, 12], "min_samples_leaf": [1, 5, 20, 50], "criterion": ["gini", "entropy"]}

    def __init__(self, profundidade=4, min_folha=1, criterio="gini", colunas=None):
        self.colunas_modelo = colunas or (self.CHUVA + self.MARE)
        self.modelo = DecisionTreeClassifier(max_depth=profundidade, min_samples_leaf=min_folha, criterion=criterio, random_state=42)

    def preparar(self, df):
        df = df.dropna(subset=self.colunas_modelo + [self.ALVO]).sort_values("hora").set_index("hora")
        return df[self.colunas_modelo], df[self.ALVO].astype(int)

    def dividir(self, X, y):
        return train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    def linha_de_base(self, X_treino, y_treino, X_teste, y_teste):
        chute = DummyClassifier(strategy="most_frequent").fit(X_treino, y_treino)
        acuracia = accuracy_score(y_teste, chute.predict(X_teste))
        print(f"[model] linha de base: {acuracia:.1%}")
        return acuracia

    def ajustar(self, X_treino, y_treino):
        """Escolhe os hiperparâmetros só com validação cruzada no treino: o teste não participa."""
        busca = GridSearchCV(DecisionTreeClassifier(random_state=42), self.GRADE, scoring="accuracy",
                             cv=StratifiedKFold(5, shuffle=True, random_state=42)).fit(X_treino, y_treino)
        self.modelo = busca.best_estimator_
        print(f"[model] melhores parâmetros: {busca.best_params_} (validação cruzada: {busca.best_score_:.1%})")
        return busca.best_score_

    def treinar(self, X_treino, y_treino):
        self.modelo.fit(X_treino, y_treino)
        self.colunas = list(X_treino.columns)

    def avaliar(self, X_teste, y_teste):
        previsto = self.modelo.predict(X_teste)
        print(f"[model] acurácia no teste: {accuracy_score(y_teste, previsto):.1%}")
        print(classification_report(y_teste, previsto, zero_division=0, target_names=["sem alagamento", "com alagamento"]))
        return previsto

    def metricas(self, X_teste, y_teste):
        """Números do teste para gravar na GOLD e o painel mostrar."""
        previsto = self.modelo.predict(X_teste)
        vn, fp, fn, vp = confusion_matrix(y_teste, previsto, labels=[0, 1]).ravel()
        importancia = pd.Series(self.modelo.feature_importances_, index=self.colunas).sort_values(ascending=False)
        return {"acuracia": accuracy_score(y_teste, previsto), "precisao": precision_score(y_teste, previsto, zero_division=0),
                "recall": recall_score(y_teste, previsto, zero_division=0), "verdadeiros_positivos": int(vp),
                "falsos_positivos": int(fp), "falsos_negativos": int(fn), "verdadeiros_negativos": int(vn),
                "importancia": [{"variavel": v, "importancia": round(float(i), 3)} for v, i in importancia.items() if i > 0]}

    def exportar_arvore(self):
        """A árvore treinada em JSON, para a API simular cenários sem depender do scikit-learn."""
        arvore = self.modelo.tree_

        def no(i):
            if arvore.children_left[i] == -1:
                return {"probabilidade": round(float(arvore.value[i][0][1]), 4), "horas": int(arvore.n_node_samples[i])}
            return {"variavel": self.colunas[arvore.feature[i]], "limiar": round(float(arvore.threshold[i]), 6),
                    "esquerda": no(arvore.children_left[i]), "direita": no(arvore.children_right[i])}

        return no(0)

    def faixas(self, X_treino):
        """Menor e maior valor visto no treino, para avisar quando um cenário sai do que o modelo conheceu."""
        return {c: [float(X_treino[c].min()), float(X_treino[c].max())] for c in X_treino.columns}

    def explicar(self):
        importancia = pd.Series(self.modelo.feature_importances_, index=self.colunas)
        print("[model] colunas mais importantes:")
        print(importancia.sort_values(ascending=False).head(5).round(3))
        print(export_text(self.modelo, feature_names=self.colunas, max_depth=3))

    def matriz_confusao(self, X_teste, y_teste, arquivo="matriz_confusao.png"):
        ConfusionMatrixDisplay.from_estimator(self.modelo, X_teste, y_teste, display_labels=["sem alagamento", "com alagamento"],
                                              xticks_rotation=45, cmap="Oranges")
        plt.tight_layout()
        plt.savefig(arquivo, dpi=150)
        plt.close()
        print(f"[model] matriz de confusão salva em {arquivo}")

    def validar_no_tempo(self, X, y, fracao_treino=0.75):
        """Treina no começo do período e testa no fim. Mostra o que a divisão aleatória não mostra:
        nela, horas vizinhas caem no treino e no teste, e o modelo chega a ver horas posteriores às testadas."""
        corte = int(len(X) * fracao_treino)
        copia = DecisionTreeClassifier(**self.modelo.get_params()).fit(X.iloc[:corte], y.iloc[:corte])
        y_fim = y.iloc[corte:]
        previsto = copia.predict(X.iloc[corte:])
        resultado = {"linha_de_base": max(y_fim.mean(), 1 - y_fim.mean()), "acuracia": accuracy_score(y_fim, previsto),
                     "acuracia_balanceada": balanced_accuracy_score(y_fim, previsto), "corte": X.index[corte]}
        print(f"[model] treino antes de {resultado['corte']}: linha de base {resultado['linha_de_base']:.1%}, "
              f"acurácia {resultado['acuracia']:.1%}, balanceada {resultado['acuracia_balanceada']:.1%}")
        return resultado
