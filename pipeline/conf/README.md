# `conf/` — configuração declarativa

O *o quê* coletar e *como* interpretar cada fonte fica aqui, em YAML; a regra de negócio fica em
[`aervita/`](../aervita/). Segredos nunca entram aqui: só o nome da variável de ambiente.

| Caminho | Conteúdo |
|---|---|
| [`sources/`](sources/README.md) | uma fonte por arquivo: endereço, `resource_id`, camadas e mapa de colunas |
| [`contracts/`](contracts/README.md) | schema esperado por tabela: campos, tipos, obrigatoriedade e chave de negócio |
| `gold.yml` | parâmetros da camada Gold e da base do modelo (janelas de chuva, horizonte, estação) |

Nomes de arquivo e chaves em `snake_case`, sem acento.
