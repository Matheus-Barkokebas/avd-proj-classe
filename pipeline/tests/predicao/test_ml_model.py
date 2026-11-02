import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")
pytest.importorskip("matplotlib")

from src.predicao.ml_model import Classificador  # noqa: E402


@pytest.fixture
def base():
    horas = pd.date_range("2026-06-01", periods=200, freq="h")
    chuva = [float(i % 10) for i in range(200)]
    dados = {"hora": horas, "alagou_no_horizonte": [int(c >= 5) for c in chuva],
             "rotas_alagadas_futuro": [int(c >= 5) * 3 for c in chuva], "rotas_alagadas": [0] * 200}
    for coluna in Classificador.CHUVA + Classificador.MARE:
        dados[coluna] = chuva
    return pd.DataFrame(dados)


def test_sem_vazamento_coluna_do_futuro_nunca_e_variavel(base):
    X, _ = Classificador().preparar(base)
    assert "rotas_alagadas_futuro" not in X.columns and Classificador.ALVO not in X.columns


def test_divisao_e_a_do_exercicio_reproduzivel_e_estratificada(base):
    c = Classificador()
    X, y = c.preparar(base)
    X_t, X_e, y_t, y_e = c.dividir(X, y)
    assert len(X_e) == 40 and y_e.mean() == y.mean()
    assert list(c.dividir(X, y)[1].index) == list(X_e.index)


def test_o_modelo_e_uma_arvore_de_decisao_e_ajustar_nao_ve_o_teste(base):
    c = Classificador()
    X, y = c.preparar(base)
    X_t, _, y_t, _ = c.dividir(X, y)
    c.ajustar(X_t, y_t)
    assert type(c.modelo).__name__ == "DecisionTreeClassifier"
    assert c.modelo.n_features_in_ == X.shape[1] and sum(c.modelo.tree_.n_node_samples[:1]) == len(X_t)


def test_validacao_no_tempo_treina_antes_e_testa_depois(base):
    c = Classificador()
    X, y = c.preparar(base)
    c.treinar(X, y)
    resultado = c.validar_no_tempo(X, y)
    assert resultado["corte"] == X.index[150] and 0 <= resultado["acuracia"] <= 1


def test_metricas_do_teste_batem_com_a_matriz(base):
    c = Classificador()
    X, y = c.preparar(base)
    X_t, X_e, y_t, y_e = c.dividir(X, y)
    c.treinar(X_t, y_t)
    m = c.metricas(X_e, y_e)
    assert m["verdadeiros_positivos"] + m["falsos_negativos"] == y_e.sum()
    assert m["verdadeiros_positivos"] + m["falsos_positivos"] + m["falsos_negativos"] + m["verdadeiros_negativos"] == len(y_e)
    assert m["recall"] == m["verdadeiros_positivos"] / y_e.sum() and m["importancia"][0]["importancia"] > 0


def test_arvore_exportada_da_a_mesma_resposta_do_modelo(base):
    c = Classificador()
    X, y = c.preparar(base)
    X_t, X_e, y_t, _ = c.dividir(X, y)
    c.treinar(X_t, y_t)
    arvore = c.exportar_arvore()

    def percorre(no, linha):
        while "limiar" in no:
            no = no["esquerda"] if linha[no["variavel"]] <= no["limiar"] else no["direita"]
        return no["probabilidade"]

    esperado = c.modelo.predict_proba(X_e)[:, 1].round(4)
    assert [percorre(arvore, l) for _, l in X_e.iterrows()] == list(esperado)
    assert set(c.faixas(X_t)) == set(X.columns)
