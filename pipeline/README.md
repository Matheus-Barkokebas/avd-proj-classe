# `pipeline/` — coleta e padronização

Módulo Python que coleta as fontes públicas e monta as camadas do medallion.
Ver [decisão 0003](../docs/decisoes/0003-medallion-bronze-silver-gold.md).

```text
APIs públicas ──► Bronze (Atlas) ──► validação por contrato ──► Silver (Neon, public) ──► Gold (Neon, gold)
                                              └──► rejeitados (Neon), com o motivo
```

| Pasta | Conteúdo |
|---|---|
| [`src/ingestao/`](src/ingestao/README.md) | conectores (CKAN Recife, ArcGIS do COP, ANA), runner, contratos, armazenamento e camada padronizada |
| `src/processamento/` | montagem da camada Gold (`gold.py`, `gold_alagamento.py`) |
| [`src/predicao/`](src/predicao/README.md) | modelo de alagamento, com experimentos e resultados |
| [`src/serving/`](src/serving/README.md) | exportação dos dados reais para o protótipo do painel |
| [`conf/`](conf/README.md) | fontes (`sources/`) e contratos (`contracts/`) em YAML |
| [`tests/`](tests/README.md) | testes sem rede + `integracao/` (APIs, Atlas e Neon reais, opcionais) |
| [`data/`](data/README.md) | RAW e Bronze locais quando rodando em modo arquivo (ignorado pelo Git) |

## Como rodar

Todos os comandos partem **desta pasta**:

```bash
cd pipeline
python -m venv .venv && .venv\Scripts\activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                                   # MONGODB_URI e NEON_DATABASE_URL, só aqui

python src/ingestao/territorio.py    --armazenamento mongo --padronizada neon
python src/ingestao/epidemiologia.py --armazenamento mongo --padronizada neon
python src/ingestao/cop_recife.py    --armazenamento mongo --padronizada neon
python src/ingestao/epidemiologia_historico.py        # carga única: arboviroses de 2013 a 2024
python src/ingestao/inmet.py                          # chuva horária do INMET (arquivos anuais)
python src/processamento/gold.py                      # recalcula a Gold (as cargas de arboviroses já chamam)

pip install -r src/predicao/requirements.txt
python src/predicao/train.py                           # treina, avalia e grava as previsões na Gold

python src/serving/exporta_painel.py --armazenamento mongo   # regrava frontend/prototipo/dados/recife-real.js

pytest                    # sem rede
pytest -m integracao      # contra as APIs, o Atlas e o Neon reais
```
