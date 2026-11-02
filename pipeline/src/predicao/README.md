# `predicao/` — modelo de alagamento

Prevê se alguma rota monitorada do Recife terá alagamento reportado daqui a 3 horas. Só lê a camada Gold.
Formato de [`etl-vacinacao-recife`](https://github.com/MatmJr/etl-vacinacao-recife); resultados e limites em
[`resultados/RESULTADOS.md`](resultados/RESULTADOS.md).

| Arquivo | Papel |
|---|---|
| `train.py` | a receita: treina, avalia e grava as previsões em `gold.previsao_alagamento` |
| `ml_model.py` | classe `Classificador` (`preparar`, `dividir`, `linha_de_base`, `ajustar`, `treinar`, `avaliar`, `explicar`, `matriz_confusao`, `validar_no_tempo`) |
| `extract.py` / `load.py` | leitura e gravação na Gold |
| `experimentos.py` | reproduz a tabela de experimentos |
| `analise_mare.py` | reproduz a análise da maré |
| `requirements.txt` | dependências só do treino |
| `resultados/` | `RESULTADOS.md` e `matriz_confusao.png` |

De dentro de `pipeline/`, com o `.env` preenchido:

```bash
pip install -r requirements.txt -r src/predicao/requirements.txt
python src/predicao/train.py
```
