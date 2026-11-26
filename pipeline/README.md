# `pipeline/` — coleta, camadas de dados e modelo

Pacote Python `aervita`: coleta as fontes públicas, monta as camadas do medallion e treina o modelo
de alagamento. Ver [decisão 0003](../docs/decisoes/0003-medallion-bronze-silver-gold.md).

```text
APIs públicas ──► Bronze (Atlas) ──► validação por contrato ──► Silver (Neon, public) ──► Gold (Neon, gold)
                                              └──► rejeitados (Neon), com o motivo
```

## Estrutura

```text
pipeline/
├── aervita/                    pacote do pipeline
│   ├── __main__.py             ponto de entrada: python -m aervita <comando>
│   ├── ambiente.py             caminhos do projeto e variáveis de ambiente
│   ├── diario.py               execução agendada (fontes + Gold) com registro em gold.execucao_pipeline
│   ├── ingestao/
│   │   ├── nucleo/             runner, armazenamento da RAW, contratos, Bronze, camada padronizada
│   │   ├── clientes/           clientes HTTP genéricos: CKAN do Recife e ArcGIS
│   │   └── fontes/             uma fonte por módulo: território, arboviroses, COP, INMET
│   ├── processamento/          camada Gold (views e base horária do modelo)
│   └── predicao/               modelo de alagamento (formato etl-vacinacao-recife) e resultados
├── conf/                       fontes (sources/), contratos (contracts/) e gold.yml, em YAML
├── agendamento/                scripts da VM: instalação e execução diária
├── tests/                      espelha aervita/; integracao/ acessa os serviços reais
└── data/                       RAW e Bronze locais em modo arquivo (ignorado pelo Git)
```

Regras de dependência: `fontes` usam `nucleo` e `clientes`; `processamento` só lê a Silver e escreve a Gold;
`predicao` só lê a Gold. Fontes novas entram registrando um `Coletor` no `runner` e um comando em `__main__.py`.

## Como rodar

Todos os comandos partem **desta pasta**:

```bash
python -m venv .venv && .venv\Scripts\activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt -r requirements-modelo.txt
cp .env.example .env                                 # MONGODB_URI e NEON_DATABASE_URL, só aqui

python -m aervita                                    # lista os comandos
python -m aervita territorio  --armazenamento mongo --padronizada neon
python -m aervita arboviroses --armazenamento mongo --padronizada neon
python -m aervita inmet                              # chuva horária do INMET (arquivos anuais)
python -m aervita gold                               # recalcula a Gold
python -m aervita treino                             # treina, avalia e grava o modelo na Gold
python -m aervita diario                             # tudo acima, como a VM roda todo dia

pytest                    # sem rede
pytest -m integracao      # contra as APIs, o Atlas e o Neon reais
ruff check .              # estilo
```

O COP Recife (`python -m aervita cop`) exige login desde nov/2026 e só responde a IPs do Brasil.
