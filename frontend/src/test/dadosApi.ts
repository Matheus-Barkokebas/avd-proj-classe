/* Respostas falsas da API, com a forma real de cada rota (valores inspirados nos dados de 2026-10-28). */

import type { RespostasFalsas } from "./utilitarios";

const agora = new Date();
const isoHorasAtras = (h: number) => new Date(agora.getTime() - h * 3_600_000).toISOString();

export function respostasApi({ chuvaHorasAtras = 1 }: { chuvaHorasAtras?: number } = {}): RespostasFalsas {
  const quadrado = (x: number) => [[[[x, -8.05], [x + 0.01, -8.05], [x + 0.01, -8.04], [x, -8.05]]]];
  return {
    "/saude": { status: "ok", banco: "ok" },
    "/v1/atualizacao": {
      gerado_em: agora.toISOString(), hoje: "2026-10-29",
      tabelas: [{ tabela: "cop_indicadores", carregado_em: isoHorasAtras(chuvaHorasAtras), linhas: 27 }],
    },
    "/v1/chuva/atual": {
      data_hora: isoHorasAtras(chuvaHorasAtras), estagio: "NORMALIDADE",
      chuva_media_1h_mm: 0.4, chuva_max_1h_mm: 1.2, estacao_max_1h: "Não Informado",
      chuva_media_24h_mm: 6.2, chuva_max_24h_mm: 15.2, estacao_max_24h: "Areias",
      mare_m: 1.1, sentido_mare: "subindo", ocorrencias: 11, alagamentos: 0, abrigos: 0,
      mes: { mes: 10, ano: 2026, chuva_acumulada_mm: 12.1, media_historica_mm: 35, percentual_da_media: 34.6 },
    },
    "/v1/chuva/serie": [1, 2, 3].map((h) => ({
      data_hora: isoHorasAtras(h), chuva_media_1h_mm: 0.2 * h, chuva_max_1h_mm: 1, chuva_media_24h_mm: 6, chuva_max_24h_mm: 15, mare_m: 1,
    })),
    "/v1/chuva/previsao": [{ data_hora_prevista: isoHorasAtras(-1), gfs_mm: 0.4, ecmwf_mm: 0, icon_mm: null, wrf_mm: 1.1, media_modelos_mm: 0.5 }],
    "/v1/chuva/mensal": { ano: 2026, meses: [{ mes: 10, chuva_ano_atual_mm: 12.1, chuva_ano_anterior_mm: 40, media_historica_mm: 35 }] },
    "/v1/rios": [
      { codigo_estacao: "260790115", estacao: "VILA NATAL", rio: "RIO JABOATÃO", data_hora: isoHorasAtras(1), nivel: 345,
        cota_pre_alerta: 320, cota_alerta: 340, cota_inundacao: 440, situacao: "alerta", situacao_fonte: "Normal", percentual_da_cota_alerta: 101.5 },
      { codigo_estacao: "39145010", estacao: "LIMOEIRO", rio: "RIO CAPIBARIBE", data_hora: isoHorasAtras(1), nivel: 177,
        cota_pre_alerta: 600, cota_alerta: 650, cota_inundacao: 750, situacao: "normal", situacao_fonte: "Normal", percentual_da_cota_alerta: 27.2 },
    ],
    "/v1/rios/260790115/serie": [{ data_hora: isoHorasAtras(2), nivel: 340 }, { data_hora: isoHorasAtras(1), nivel: 345 }],
    "/v1/rios/39145010/serie": [{ data_hora: isoHorasAtras(1), nivel: 177 }],
    "/v1/mare/proximas": [
      { data_hora: isoHorasAtras(-2), mare_m: 2.1, tipo: "alta" },
      { data_hora: isoHorasAtras(-8), mare_m: 0.4, tipo: "baixa" },
    ],
    "/v1/alagamento/rotas": [
      { rota: "AV. NORTE >> CENTRO", leituras_com_alagamento: 120, alertas: 300, ultimo: isoHorasAtras(5) },
      { rota: "AV. RECIFE >> BOA VIAGEM", leituras_com_alagamento: 40, alertas: 60, ultimo: isoHorasAtras(50) },
    ],
    "/v1/alagamento/serie": [
      { dia: "2026-05-01", horas_com_alagamento: 6, rotas: 4, alertas: 20 },
      { dia: "2026-05-02", horas_com_alagamento: 3, rotas: 1, alertas: 4 },
    ],
    "/v1/alagamento/modelo": {
      modelo: "arvore_alagamento_3h", treinado_em: isoHorasAtras(1), inicio: "2026-05-28T15:00:00-03:00", fim: "2026-09-29T08:00:00-03:00",
      horas: 2424, horas_teste: 485, horizonte_horas: 3, linha_de_base: 0.697, acuracia: 0.825, precisao: 0.731, recall: 0.667,
      validacao_cruzada: 0.843, tempo_linha_de_base: 0.805, tempo_acuracia: 0.86, tempo_balanceada: 0.691,
      verdadeiros_positivos: 98, falsos_positivos: 36, falsos_negativos: 49, verdadeiros_negativos: 302,
      importancia: [{ variavel: "chuva_12h_mm", importancia: 0.732 }, { variavel: "mare_max_futura_m", importancia: 0.01 }],
    },
    "/v1/alagamento/rotas-geo": {
      type: "FeatureCollection",
      features: [{ type: "Feature", geometry: { type: "Polygon", coordinates: [[[-34.9, -8.0], [-34.8, -8.0], [-34.8, -8.1], [-34.9, -8.0]]] },
                   properties: { rota: "AV. NORTE >> CENTRO", cod_rota: 101, leituras_com_alagamento: 120 } }],
    },
    "/v1/alagamento/simular": (url: URL) => ({
      probabilidade: Number(url.searchParams.get("chuva_12h_mm")) > 300 ? 0.2 : 0.83, previsto: Number(url.searchParams.get("chuva_12h_mm")) > 300 ? 0 : 1,
      horas_parecidas: 136, horizonte_horas: 3,
      caminho: [{ variavel: "chuva_12h_mm", valor: 12, limiar: 2.7, menor_ou_igual: false }],
      fora_da_faixa: Number(url.searchParams.get("chuva_12h_mm")) > 100 ? [{ variavel: "chuva_12h_mm", valor: 150, minimo: 0, maximo: 80 }] : [],
    }),
    "/v1/alagamento/previsoes": [
      { hora: "2026-05-28T17:00:00-03:00", hora_prevista: "2026-05-28T20:00:00-03:00", probabilidade: 0.9, previsto: 1, observado: 1 },
      { hora: "2026-05-29T17:00:00-03:00", hora_prevista: "2026-05-29T20:00:00-03:00", probabilidade: 0.1, previsto: 0, observado: 1 },
      { hora: "2026-06-02T17:00:00-03:00", hora_prevista: "2026-06-02T20:00:00-03:00", probabilidade: 0.8, previsto: 1, observado: 0 },
    ],
    "/v1/arboviroses/semanas": [
      { semana: 202532, agravo: "dengue", notificacoes: 300, nao_descartadas: 200 },
      { semana: 202533, agravo: "dengue", notificacoes: 400, nao_descartadas: 250 },
      { semana: 202533, agravo: "zika", notificacoes: 20, nao_descartadas: 15 },
      { semana: 202533, agravo: "chikungunya", notificacoes: 39, nao_descartadas: 10 },
    ],
    "/v1/arboviroses/bairros": {
      nao_georreferenciadas: 21, grafias_nao_reconhecidas: ["JIQU]", "BREJ"],
      bairros: [
        { chave_bairro: "COHAB", nome_bairro: "Cohab", distrito_sanitario: 7, descricao_distrito: "DS VII", dengue: 515, chikungunya: 218, zika: 78, total: 811 },
        { chave_bairro: "PINA", nome_bairro: "Pina", distrito_sanitario: 6, descricao_distrito: "DS VI", dengue: 30, chikungunya: 0, zika: 2, total: 32 },
        { chave_bairro: "TORRE", nome_bairro: "Torre", distrito_sanitario: 4, descricao_distrito: "DS IV", dengue: 0, chikungunya: 0, zika: 0, total: 0 },
      ],
    },
    "/v1/territorio/bairros-geo": {
      type: "FeatureCollection",
      features: [
        { type: "Feature", geometry: { type: "MultiPolygon", coordinates: quadrado(-34.9) },
          properties: { chave_bairro: "PINA", nome_bairro: "Pina", rpa: 6, distrito_sanitario: 6, descricao_distrito: "DS VI", area_km2: 2 } },
        { type: "Feature", geometry: { type: "MultiPolygon", coordinates: quadrado(-34.95) },
          properties: { chave_bairro: "COHAB", nome_bairro: "Cohab", rpa: 6, distrito_sanitario: 7, descricao_distrito: "DS VII", area_km2: 3.4 } },
      ],
    },
    "/v1/territorio/areas-alagaveis": { type: "FeatureCollection", features: [] },
    "/v1/territorio/pontos-alagamento": {
      type: "FeatureCollection",
      features: [{ type: "Feature", geometry: { type: "Point", coordinates: [-34.89, -8.08] },
                   properties: { id_ponto: "7", bairro: "PINA", logradouro: "RUA DO PINA", status: "EM ANDAMENTO" } }],
    },
  };
}
