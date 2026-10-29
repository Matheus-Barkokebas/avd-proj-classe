import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { Carregando } from "./componentes/Estados";
import { Layout } from "./layout/Layout";
import { MENU } from "./layout/menu";
import { Arboviroses } from "./telas/Arboviroses";
import { ChuvaRios } from "./telas/ChuvaRios";
import { EmBreve, NaoEncontrada } from "./telas/Paginas";
import { VisaoGeral } from "./telas/VisaoGeral";

// O MapLibre é a maior dependência: a tela do mapa só é baixada quando alguém abre a aba.
const Mapa = lazy(() => import("./telas/Mapa").then((m) => ({ default: m.Mapa })));

export function criarClienteConsultas() {
  return new QueryClient({
    defaultOptions: {
      queries: { staleTime: 60 * 1000, refetchOnWindowFocus: true, retry: 1 },
    },
  });
}

export function Rotas() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<VisaoGeral />} />
        <Route path="/mapa" element={<Suspense fallback={<Carregando texto="Carregando o mapa…" />}><Mapa /></Suspense>} />
        <Route path="/chuva-rios" element={<ChuvaRios />} />
        <Route path="/arboviroses" element={<Arboviroses />} />
        {MENU.filter((m) => m.emBreve).map((m) => (
          <Route key={m.caminho} path={m.caminho} element={<EmBreve />} />
        ))}
        <Route path="/inicio" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NaoEncontrada />} />
      </Route>
    </Routes>
  );
}

export function App({ cliente = criarClienteConsultas() }: { cliente?: QueryClient }) {
  return (
    <QueryClientProvider client={cliente}>
      <Rotas />
    </QueryClientProvider>
  );
}
