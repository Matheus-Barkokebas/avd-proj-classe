# `pipeline/` — coleta e padronização

Módulo Python que coleta as fontes públicas, guarda a resposta original (RAW) e grava os dados
validados na camada padronizada. Ver [decisão 0001](../docs/decisoes/0001-raw-mongodb-padronizada-neon.md).

```text
APIs públicas ──► RAW (MongoDB Atlas) ──► validação por contrato ──► padronizada (Neon)
                                                   └──► rejeitados (Neon), com o motivo
```

| Pasta | Conteúdo |
|---|---|
| [`src/ingestao/`](src/ingestao/README.md) | conectores (CKAN Recife, ArcGIS do COP, ANA), runner, contratos, armazenamento e camada padronizada |
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
python src/serving/exporta_painel.py --armazenamento mongo   # regrava frontend/prototipo/dados/recife-real.js

pytest                    # sem rede
pytest -m integracao      # contra as APIs, o Atlas e o Neon reais
```
