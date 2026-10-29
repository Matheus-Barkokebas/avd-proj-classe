# `frontend/` — painel AerVita

Painel em **React 18 + TypeScript (Vite)** que consome somente a [`api/`](../api/README.md) — nunca o banco.
Ver [decisão 0002](../docs/decisoes/0002-api-fastapi-e-front-react.md).

## Como rodar

Com a API rodando (ver `api/README.md`), de dentro desta pasta:

```bash
cd frontend
npm install
cp .env.example .env.local      # VITE_API_URL — padrão http://localhost:8000
npm run dev                     # http://localhost:5173
```

| Comando | O que faz |
|---|---|
| `npm run dev` | servidor de desenvolvimento com recarga instantânea |
| `npm test` | testes (Vitest + Testing Library), sem API real: o `fetch` é simulado |
| `npm run tipos` | checagem de tipos (`tsc`) |
| `npm run lint` | ESLint |
| `npm run build` | checagem de tipos + build de produção em `dist/` |
| `npm run gerar:tipos` | regenera `src/api/esquema.d.ts` a partir de `api/openapi.json` |

## Contrato com a API

Os tipos de todas as respostas vêm de [`api/openapi.json`](../api/openapi.json), gerado pela API
(`python -m app.openapi`, dentro de `api/`). Quando a API mudar uma rota:

1. em `api/`: `python -m app.openapi` (há teste na API que falha se o arquivo ficar desatualizado);
2. aqui: `npm run gerar:tipos` — o TypeScript passa a acusar qualquer uso de campo que mudou.

## Estrutura

```text
src/
├── api/           cliente HTTP tipado (cliente.ts), hooks de dados (consultas.ts), tipos gerados (esquema.d.ts)
├── layout/        menu lateral, barra superior, tema claro/escuro
├── componentes/   peças reaproveitáveis: ícones, estados de carregando/erro/vazio
├── telas/         uma tela por item do menu
├── estilos/       tokens do protótipo v3 e estilos globais
└── test/          configuração e utilitários de teste
prototipo/         console v3 em HTML puro — referência visual e funcional
```

## Telas

| Tela | O que mostra (tudo dado real, via API) |
|---|---|
| Visão geral | Chuva das últimas 24 h, chuva do mês contra a média histórica, pior situação entre os rios, estágio do COP, gráficos de chuva e arboviroses, última carga de cada tabela |
| Mapa | Malha dos 94 bairros (MapLibre) colorida por distrito sanitário ou por notificações de arboviroses, áreas alagáveis e pontos de alagamento; clicar num bairro abre o detalhe |
| Chuva e rios | Série de chuva (24 h a 30 dias), previsão por modelo, chuva mensal do ano contra o anterior e a média, nível de cada estação de rio contra as cotas |
| Arboviroses | Totais, semana de pico, descartadas, série por semana epidemiológica, totais por distrito e tabela de bairros com filtro e ordenação |
| Ocorrências, Equipes, Simulador, Boletins | "Em breve": dependem de dados que ainda não existem — a tela diz isso em vez de mostrar dado simulado |

Quando a leitura de chuva mais recente tem mais de 3 horas, as telas mostram um aviso: hoje isso acontece
porque a coleta horária do COP ainda não está agendada.

## Detalhes que valem saber

- **Mapa sob demanda:** o MapLibre é a maior dependência (~1 MB); a tela do mapa só é baixada quando alguém
  abre a aba. O worker do MapLibre é importado com `?url` (`componentes/MapaRecife.tsx`) para funcionar em dev e no build.
- **Mapa de fundo:** tiles do OpenStreetMap, bons para desenvolvimento e demonstração; para produção, usar um
  provedor de tiles próprio (a política de uso do OSM não permite tráfego alto).
- **Testes do mapa:** o jsdom não tem WebGL, então `telas/telas.test.tsx` troca o MapLibre por um dublê.
