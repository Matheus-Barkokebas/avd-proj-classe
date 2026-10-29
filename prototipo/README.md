# Protótipo do painel

[`v3-aervita-console.html`](v3-aervita-console.html) — console de operação com menu lateral, gestão de
ocorrências e equipes, mapa dos bairros e arboviroses. As versões anteriores (v1 e v2) saíram do
repositório; a v1 está no histórico do Git.

## Como abrir

Dê dois cliques em `v3-aervita-console.html`. Não precisa de servidor nem de internet (só as fontes
tipográficas vêm do Google Fonts). O arquivo `dados/recife-real.js` precisa estar ao lado.

## O que é real e o que é simulado

| Real (gerado pelo pipeline) | Simulado na tela |
|---|---|
| Malha dos 94 bairros, bairro → distrito sanitário | Chuva, rios e maré exibidos |
| Notificações de arboviroses 2025 (camada padronizada no Neon) | Ocorrências, equipes, população exposta, previsões |

Chuva, rios, previsão e áreas alagáveis reais já estão no Neon (fonte COP Recife), mas o console
ainda não os lê — ligar a tela a esses dados é trabalho de front-end posterior.

## Atualizar os dados reais

```bash
python src/serving/exporta_painel.py --armazenamento mongo
```

Lê o Neon e a RAW do território no Atlas e regrava `dados/recife-real.js` (só contagens agregadas,
sem dado pessoal). Ver [`src/serving/README.md`](../src/serving/README.md).
