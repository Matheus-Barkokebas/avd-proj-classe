"""Maré e alagamento: próximas marés, alagamentos reportados por rota e o modelo de previsão."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app.esquemas.modelos import AlagamentoDia, AlagamentoRota, AvaliacaoModelo, FeatureCollection, Mare, PrevisaoAlagamento, Simulacao
from app.repositorios.neon import FUSO_RECIFE, RepositorioNeon
from app.rotas.dependencias import obter_repositorio
from app.servicos import regras

roteador_mare = APIRouter(prefix="/v1/mare", tags=["mare"])
roteador = APIRouter(prefix="/v1/alagamento", tags=["alagamento"])


@roteador_mare.get("/proximas", response_model=list[Mare], summary="Próximas marés altas e baixas, da tábua do COP")
def proximas(horas: int = Query(48, ge=1, le=24 * 31), repo: RepositorioNeon = Depends(obter_repositorio)):
    agora = datetime.now(FUSO_RECIFE)
    return [{"data_hora": l["data_hora"], "mare_m": l["mare_m"], "tipo": regras.tipo_mare(l["mare_m"], l["anterior"])}
            for l in repo.mare_entre(agora, agora + timedelta(hours=horas))]


@roteador.get("/rotas", response_model=list[AlagamentoRota],
              summary="Rotas com alagamento reportado no período, da mais afetada para a menos")
def rotas(dias: int = Query(90, ge=1, le=730), repo: RepositorioNeon = Depends(obter_repositorio)):
    return repo.alagamento_por_rota(datetime.now(FUSO_RECIFE) - timedelta(days=dias))


@roteador.get("/serie", response_model=list[AlagamentoDia], summary="Alagamentos reportados por dia")
def serie(dias: int = Query(90, ge=1, le=730), repo: RepositorioNeon = Depends(obter_repositorio)):
    return repo.alagamento_por_dia(datetime.now(FUSO_RECIFE) - timedelta(days=dias))


@roteador.get("/modelo", response_model=AvaliacaoModelo,
              summary="Avaliação do modelo mais recente: acurácia no teste, linha de base e limites")
def modelo(repo: RepositorioNeon = Depends(obter_repositorio)):
    avaliacao = repo.modelo_mais_recente()
    if avaliacao is None:
        raise HTTPException(404, "Ainda não há modelo treinado no banco")
    return avaliacao


@roteador.get("/previsoes", response_model=list[PrevisaoAlagamento],
              summary="Previsto e observado nas horas de teste do modelo (período histórico, não é tempo real)")
def previsoes(repo: RepositorioNeon = Depends(obter_repositorio)):
    return repo.previsoes_de_teste()


@roteador.get("/rotas-geo", response_model=FeatureCollection,
              summary="Traçado das rotas em GeoJSON, com as horas de alagamento reportado no período")
def rotas_geo(dias: int = Query(90, ge=1, le=730), repo: RepositorioNeon = Depends(obter_repositorio)):
    desde = datetime.now(FUSO_RECIFE) - timedelta(days=dias)
    return regras.feature_collection(repo.rotas_com_alagamento(desde), campo_geometria="geometria_geojson")


@roteador.get("/simular", response_model=Simulacao,
              summary="Aplica o modelo a um cenário hipotético de chuva e maré (não é previsão real)")
def simular(chuva_1h_mm: float = Query(0, ge=0), chuva_3h_mm: float = Query(0, ge=0), chuva_6h_mm: float = Query(0, ge=0),
            chuva_12h_mm: float = Query(0, ge=0), chuva_24h_mm: float = Query(0, ge=0), chuva_72h_mm: float = Query(0, ge=0),
            chuva_168h_mm: float = Query(0, ge=0), mare_m: float = Query(1, ge=-1, le=5),
            mare_subindo: int = Query(0, ge=0, le=1), mare_max_futura_m: float = Query(1.5, ge=-1, le=5),
            repo: RepositorioNeon = Depends(obter_repositorio)):
    modelo_atual = repo.modelo_mais_recente()
    if modelo_atual is None or not modelo_atual.get("arvore"):
        raise HTTPException(404, "Ainda não há modelo com regras exportadas no banco")
    valores = {"chuva_1h_mm": chuva_1h_mm, "chuva_3h_mm": chuva_3h_mm, "chuva_6h_mm": chuva_6h_mm,
               "chuva_12h_mm": chuva_12h_mm, "chuva_24h_mm": chuva_24h_mm, "chuva_72h_mm": chuva_72h_mm,
               "chuva_168h_mm": chuva_168h_mm, "mare_m": mare_m, "mare_subindo": mare_subindo,
               "mare_max_futura_m": mare_max_futura_m}
    return {**regras.avaliar_arvore(modelo_atual["arvore"], valores), "horizonte_horas": modelo_atual["horizonte_horas"],
            "fora_da_faixa": regras.fora_da_faixa(valores, modelo_atual.get("faixas") or {})}
