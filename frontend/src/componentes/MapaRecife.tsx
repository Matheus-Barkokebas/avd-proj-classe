/* Mapa do Recife (MapLibre GL): bairros coloridos, áreas alagáveis e pontos de alagamento.
   Só desenha — quem decide cores e o que mostrar é a tela (telas/Mapa.tsx). */

import {
  Map as MapaGL, NavigationControl, setWorkerUrl, type GeoJSONSource, type MapLayerMouseEvent, type StyleSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import urlWorker from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import { useEffect, useRef, useState } from "react";

type FC = GeoJSON.FeatureCollection;

// O MapLibre procura o worker ao lado do próprio arquivo, que o Vite move ao empacotar.
// Com `?url` o Vite publica o worker como asset e a URL certa vale em dev e no build.
setWorkerUrl(urlWorker);
const VAZIO: FC = { type: "FeatureCollection", features: [] };

// Mapa de fundo OpenStreetMap (raster). Para produção, trocar por um provedor de tiles próprio.
const ESTILO: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster", tileSize: 256, tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      attribution: "© colaboradores do OpenStreetMap",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm", paint: { "raster-saturation": -0.6, "raster-opacity": 0.85 } }],
};

export type PropsMapa = {
  /** Bairros já com a propriedade `cor` calculada pela tela. */
  bairros: FC;
  areas: FC;
  pontos: FC;
  mostrarAreas: boolean;
  mostrarPontos: boolean;
  selecionado: string | null;
  aoSelecionar: (chave: string | null) => void;
};

export function MapaRecife({ bairros, areas, pontos, mostrarAreas, mostrarPontos, selecionado, aoSelecionar }: PropsMapa) {
  const container = useRef<HTMLDivElement>(null);
  const mapa = useRef<MapaGL | null>(null);
  const [pronto, setPronto] = useState(false);
  const callback = useRef(aoSelecionar);
  callback.current = aoSelecionar;

  // cria o mapa uma vez
  useEffect(() => {
    if (!container.current) return;
    const m = new MapaGL({
      container: container.current, style: ESTILO, center: [-34.925, -8.05], zoom: 11, attributionControl: { compact: true },
    });
    m.addControl(new NavigationControl({ showCompass: false }), "top-right");
    m.on("load", () => {
      m.addSource("bairros", { type: "geojson", data: VAZIO });
      m.addSource("areas", { type: "geojson", data: VAZIO });
      m.addSource("pontos", { type: "geojson", data: VAZIO });
      m.addLayer({ id: "bairros-fill", type: "fill", source: "bairros",
                   paint: { "fill-color": ["get", "cor"], "fill-opacity": 0.6 } });
      m.addLayer({ id: "bairros-linha", type: "line", source: "bairros", paint: { "line-color": "#ffffff", "line-width": 0.8 } });
      m.addLayer({ id: "areas-fill", type: "fill", source: "areas",
                   paint: { "fill-color": "#1d4ed8", "fill-opacity": 0.35, "fill-outline-color": "#1e3a8a" } });
      m.addLayer({ id: "bairro-sel", type: "line", source: "bairros", filter: ["==", ["get", "chave_bairro"], ""],
                   paint: { "line-color": "#101828", "line-width": 3 } });
      m.addLayer({ id: "pontos", type: "circle", source: "pontos",
                   paint: { "circle-radius": 5, "circle-color": ["get", "cor"], "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.5 } });
      m.on("click", "bairros-fill", (e: MapLayerMouseEvent) => callback.current(String(e.features?.[0]?.properties?.chave_bairro ?? "") || null));
      m.on("mouseenter", "bairros-fill", () => { m.getCanvas().style.cursor = "pointer"; });
      m.on("mouseleave", "bairros-fill", () => { m.getCanvas().style.cursor = ""; });
      setPronto(true);
    });
    mapa.current = m;
    return () => { m.remove(); mapa.current = null; setPronto(false); };
  }, []);

  useEffect(() => {
    if (!pronto || !mapa.current) return;
    (mapa.current.getSource("bairros") as GeoJSONSource).setData(bairros);
  }, [pronto, bairros]);

  useEffect(() => {
    if (!pronto || !mapa.current) return;
    (mapa.current.getSource("areas") as GeoJSONSource).setData(areas);
    (mapa.current.getSource("pontos") as GeoJSONSource).setData(pontos);
  }, [pronto, areas, pontos]);

  useEffect(() => {
    if (!pronto || !mapa.current) return;
    mapa.current.setLayoutProperty("areas-fill", "visibility", mostrarAreas ? "visible" : "none");
    mapa.current.setLayoutProperty("pontos", "visibility", mostrarPontos ? "visible" : "none");
  }, [pronto, mostrarAreas, mostrarPontos]);

  useEffect(() => {
    if (!pronto || !mapa.current) return;
    mapa.current.setFilter("bairro-sel", ["==", ["get", "chave_bairro"], selecionado ?? ""]);
  }, [pronto, selecionado]);

  return <div ref={container} className="mapa-gl" role="region" aria-label="Mapa do Recife" />;
}
