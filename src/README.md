# `src/` — código do pipeline

Código-fonte do AerVita, organizado pelas etapas do fluxo de dados descrito em
[`docs/ARQUITETURA.md`](../docs/ARQUITETURA.md).

| Pasta | Papel | Camadas que produz |
|---|---|---|
| [`ingestao/`](ingestao/) | conectores e coleta por fonte | RAW → Bronze |
| [`processamento/`](processamento/) | limpeza, padronização e integração | Bronze → Silver → Gold |
| [`indicadores/`](indicadores/) | cálculo de indicadores e classificação de risco | Gold |
| [`predicao/`](predicao/) | modelos preditivos e motor de alertas | Gold |
| [`serving/`](serving/) | geração de boletim, exportações e API interna | entrega |

## Convenções

- Um módulo por fonte ou por etapa (ex.: `ingestao/epidemiologia.py`, `processamento/silver_ocorrencias.py`).
- Identificadores em **português sem acento** (`resolver_territorio`, `classificar_risco`).
- Sem lógica de negócio em `conf/` — configuração é declarativa (YAML); regra fica no código.
- Cada módulo com teste correspondente em [`tests/`](../tests/), espelhando a estrutura desta pasta.
- Ver [`docs/PADROES.md`](../docs/PADROES.md) para nomes, datas, particionamento e Git.
