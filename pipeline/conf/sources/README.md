# `conf/sources/` — fontes de dados

Só fontes públicas de governo. Cada arquivo é lido pelo módulo de mesmo nome em
[`aervita/ingestao/fontes/`](../../aervita/ingestao/fontes/).

| Arquivo | Fonte | Comando |
|---|---|---|
| `territorio.yml` | Dados Abertos Recife (CKAN): bairros, RPAs, distritos sanitários e as malhas em GeoJSON | `python -m aervita territorio` |
| `epidemiologia.yml` | Dados Abertos Recife (CKAN): notificações de dengue, zika e chikungunya do ano | `python -m aervita arboviroses` |
| `epidemiologia_historico.yml` | Dados Abertos Recife: arboviroses de 2013 a 2024 (carga única) | `python -m aervita arboviroses-historico` |
| `cop_recife.yml` | COP Recife (ArcGIS): indicadores, rios, maré, alagamento por rota e demais camadas | `python -m aervita cop` |
| `inmet.yml` | INMET: chuva horária da estação A301 (arquivos anuais) | `python -m aervita inmet` |

O COP exige login desde nov/2026 e só responde a IPs do Brasil; por isso fica fora da execução diária
até o acesso ser liberado (`python -m aervita diario --com-cop`).
