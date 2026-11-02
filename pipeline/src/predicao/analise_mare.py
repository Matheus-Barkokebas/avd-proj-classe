"""Reproduz a análise da maré de resultados/RESULTADOS.md: a maré muda a chance de alagar quando chove?"""

from pathlib import Path
import sys

# Executado como script, o Python não põe a raiz do projeto no sys.path (BUG-02).
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from src.predicao.extract import Extract

sys.stdout.reconfigure(encoding="utf-8")
df = Extract().ler_gold().astype({"mare_m": float, "mare_max_futura_m": float})
print("correlação com rotas alagadas em H + 3:",
      {c: round(df[c].astype(float).corr(df.rotas_alagadas_futuro.astype(float)), 3)
       for c in ["chuva_12h_mm", "chuva_24h_mm", "mare_m", "mare_max_futura_m"]})
chuva = pd.cut(df.chuva_12h_mm.astype(float), [-1, 0.0, 1, 5, 20, 1000], labels=["seco (0)", "até 1 mm", "1 a 5 mm", "5 a 20 mm", "acima de 20 mm"])
mare = pd.cut(df.mare_max_futura_m, [-1, 1.8, 2.2, 5], labels=["até 1,8 m", "1,8 a 2,2 m", "acima de 2,2 m"])
print("\nmaré máxima nas próximas 6 h: distribuição das horas\n", mare.value_counts().sort_index().to_string())
print("\ntaxa de alagamento em H + 3 (%)\n", (df.groupby([chuva, mare], observed=False).alagou_no_horizonte.mean().astype(float) * 100).unstack().round(1).to_string())
print("\nnúmero de horas\n", df.groupby([chuva, mare], observed=False).size().unstack().to_string())
