/* Hooks de dados (TanStack Query): cada um com chave de cache e frequência de atualização.
   Os dados do COP mudam de hora em hora; a API já responde com cache de 5 minutos. */

import { useQuery } from "@tanstack/react-query";

import { buscar } from "./cliente";

const MINUTO = 60 * 1000;
const CINCO_MINUTOS = 5 * MINUTO;
const UMA_HORA = 60 * MINUTO;

export function useSaude() {
  return useQuery({
    queryKey: ["saude"],
    queryFn: ({ signal }) => buscar("/saude", undefined, signal),
    refetchInterval: MINUTO,
    retry: false,
  });
}

export function useAtualizacao() {
  return useQuery({
    queryKey: ["atualizacao"],
    queryFn: ({ signal }) => buscar("/v1/atualizacao", undefined, signal),
    refetchInterval: CINCO_MINUTOS,
  });
}

// ------------------------------------------------------------ chuva
export function useChuvaAtual() {
  return useQuery({
    queryKey: ["chuva", "atual"],
    queryFn: ({ signal }) => buscar("/v1/chuva/atual", undefined, signal),
    refetchInterval: CINCO_MINUTOS,
  });
}

export function useChuvaSerie(horas: number) {
  return useQuery({
    queryKey: ["chuva", "serie", horas],
    queryFn: ({ signal }) => buscar("/v1/chuva/serie", { horas }, signal),
    refetchInterval: CINCO_MINUTOS,
  });
}

export function usePrevisao() {
  return useQuery({
    queryKey: ["chuva", "previsao"],
    queryFn: ({ signal }) => buscar("/v1/chuva/previsao", undefined, signal),
    refetchInterval: UMA_HORA,
  });
}

export function useChuvaMensal() {
  return useQuery({
    queryKey: ["chuva", "mensal"],
    queryFn: ({ signal }) => buscar("/v1/chuva/mensal", undefined, signal),
    staleTime: UMA_HORA,
  });
}

// ------------------------------------------------------------ rios
export function useRios() {
  return useQuery({
    queryKey: ["rios"],
    queryFn: ({ signal }) => buscar("/v1/rios", undefined, signal),
    refetchInterval: CINCO_MINUTOS,
  });
}

export function useSerieRio(codigo: string | null, horas: number) {
  return useQuery({
    queryKey: ["rios", "serie", codigo, horas],
    // a rota tem parâmetro no caminho: monta a URL com o código já validado pela lista de estações
    queryFn: ({ signal }) =>
      buscar(`/v1/rios/${encodeURIComponent(codigo!)}/serie` as "/v1/rios/{codigo_estacao}/serie", { horas }, signal),
    enabled: !!codigo,
    refetchInterval: CINCO_MINUTOS,
  });
}

// ------------------------------------------------------------ arboviroses (dado estável: atualiza pouco)
export function useArboSemanas() {
  return useQuery({
    queryKey: ["arboviroses", "semanas"],
    queryFn: ({ signal }) => buscar("/v1/arboviroses/semanas", undefined, signal),
    staleTime: UMA_HORA,
  });
}

export function useArboBairros() {
  return useQuery({
    queryKey: ["arboviroses", "bairros"],
    queryFn: ({ signal }) => buscar("/v1/arboviroses/bairros", undefined, signal),
    staleTime: UMA_HORA,
  });
}

// ------------------------------------------------------------ território (cadastral: quase não muda)
export function useBairrosGeo() {
  return useQuery({
    queryKey: ["territorio", "bairros-geo"],
    queryFn: ({ signal }) => buscar("/v1/territorio/bairros-geo", undefined, signal),
    staleTime: Infinity,
  });
}

export function useAreasAlagaveis() {
  return useQuery({
    queryKey: ["territorio", "areas-alagaveis"],
    queryFn: ({ signal }) => buscar("/v1/territorio/areas-alagaveis", undefined, signal),
    staleTime: Infinity,
  });
}

export function usePontosAlagamento() {
  return useQuery({
    queryKey: ["territorio", "pontos-alagamento"],
    queryFn: ({ signal }) => buscar("/v1/territorio/pontos-alagamento", undefined, signal),
    staleTime: Infinity,
  });
}
