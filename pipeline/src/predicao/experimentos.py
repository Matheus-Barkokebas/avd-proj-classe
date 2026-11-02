"""Reproduz a tabela de experimentos de resultados/RESULTADOS.md.

A escolha do modelo final olha só a coluna de validação cruzada, que usa apenas o
treino. O teste aparece para registro, como pede a tabela do exercício.
Todas as tentativas usam as mesmas horas: as que têm coleta do `alaga` em H e em H + 3.
"""

from pathlib import Path
import sys

# Executado como script, o Python não põe a raiz do projeto no sys.path (BUG-02).
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_score

from src.predicao.extract import Extract
from src.predicao.ml_model import Classificador

sys.stdout.reconfigure(encoding="utf-8")
extract = Extract()
df = extract.ler_gold().dropna(subset=["rotas_alagadas"])
C, M = Classificador.CHUVA, Classificador.MARE
AGORA = ["rotas_alagadas"]
CV = StratifiedKFold(5, shuffle=True, random_state=42)

TENTATIVAS = [
    ("Só chuva de 24h, profundidade 4", ["chuva_24h_mm"], dict(profundidade=4), False),
    ("Todas as janelas de chuva, profundidade 4", C, dict(profundidade=4), False),
    ("Só maré, profundidade 4", M, dict(profundidade=4), False),
    ("Chuva + maré, profundidade 4", C + M, dict(profundidade=4), False),
    ("Chuva + maré, sem limite de profundidade", C + M, dict(profundidade=None), False),
    ("Só chuva, parâmetros por validação cruzada", C, {}, True),
    ("Chuva + maré, parâmetros por validação cruzada", C + M, {}, True),
    ("Chuva + maré + rotas alagadas agora, por validação cruzada", C + M + AGORA, {}, True),
]

print("| # | O que mudou | Acurácia (validação) | Acurácia (treino) | Acurácia (teste) |")
print("|---|---|---|---|---|")
for numero, (nome, colunas, parametros, buscar) in enumerate(TENTATIVAS):
    classificador = Classificador(colunas=colunas, **parametros)
    X, y = classificador.preparar(df)
    X_treino, X_teste, y_treino, y_teste = classificador.dividir(X, y)
    if numero == 0:
        base = max(y_teste.mean(), 1 - y_teste.mean())
        print(f"[linha de base no teste: {base:.1%}; {len(X)} horas, {y.mean():.1%} com alagamento]", file=sys.stderr)
    if buscar:
        validacao = classificador.ajustar(X_treino, y_treino)
    else:
        validacao = cross_val_score(classificador.modelo, X_treino, y_treino, cv=CV).mean()
    classificador.treinar(X_treino, y_treino)
    treino = accuracy_score(y_treino, classificador.modelo.predict(X_treino))
    teste = accuracy_score(y_teste, classificador.modelo.predict(X_teste))
    print(f"| {numero} | {nome} | {validacao:.1%} | {treino:.1%} | {teste:.1%} |")
