import type { NomeIcone } from "../componentes/Icone";

export type ItemMenu = {
  caminho: string;
  titulo: string;
  grupo: string;
  icone: NomeIcone;
  /** Tela ainda sem dado real na API: aparece no menu, mas abre a página "em breve". */
  emBreve?: boolean;
};

export const MENU: ItemMenu[] = [
  { caminho: "/", titulo: "Visão geral", grupo: "Operação", icone: "painel" },
  { caminho: "/mapa", titulo: "Mapa", grupo: "Operação", icone: "mapa" },
  { caminho: "/ocorrencias", titulo: "Ocorrências", grupo: "Operação", icone: "sirene", emBreve: true },
  { caminho: "/equipes", titulo: "Equipes de campo", grupo: "Operação", icone: "equipe", emBreve: true },
  { caminho: "/chuva-rios", titulo: "Chuva e rios", grupo: "Monitoramento", icone: "chuva" },
  { caminho: "/arboviroses", titulo: "Arboviroses", grupo: "Monitoramento", icone: "pulso" },
  { caminho: "/simulador", titulo: "Simulador", grupo: "Planejamento", icone: "ajustes", emBreve: true },
  { caminho: "/boletins", titulo: "Boletins", grupo: "Planejamento", icone: "doc", emBreve: true },
];

export function itemDaRota(caminho: string): ItemMenu | undefined {
  return MENU.find((item) => item.caminho === caminho);
}
