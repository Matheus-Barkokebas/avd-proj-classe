"""Chuva: leitura atual, série horária, previsão e acumulado mensal (fonte: COP Recife)."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app.esquemas.modelos import ChuvaAtual, ChuvaMensal, PontoSerieChuva, PrevisaoHora
from app.repositorios.neon import FUSO_RECIFE, RepositorioNeon
from app.rotas.dependencias import obter_repositorio
from app.servicos import regras

roteador = APIRouter(prefix="/v1/chuva", tags=["chuva"])


@roteador.get("/atual", response_model=ChuvaAtual, summary="Leitura mais recente de chuva, maré e estágio")
def chuva_atual(repo: RepositorioNeon = Depends(obter_repositorio)):
    leitura = repo.indicador_mais_recente()
    if leitura is None:
        raise HTTPException(404, "Ainda não há leituras de chuva no banco")
    mes = regras.comparacao_mensal(repo.chuva_mensal(leitura["data_hora"].year), leitura["data_hora"])
    return {**leitura, "mes": mes}


@roteador.get("/serie", response_model=list[PontoSerieChuva], summary="Série horária de chuva e maré")
def chuva_serie(horas: int = Query(72, ge=1, le=24 * 31, description="Janela, em horas, até agora"),
                repo: RepositorioNeon = Depends(obter_repositorio)):
    return repo.serie_indicadores(datetime.now(FUSO_RECIFE) - timedelta(hours=horas))


@roteador.get("/previsao", response_model=list[PrevisaoHora], summary="Previsão hora a hora por modelo")
def chuva_previsao(repo: RepositorioNeon = Depends(obter_repositorio)):
    linhas = repo.previsao(datetime.now(FUSO_RECIFE) - timedelta(hours=1))
    return [{
        "data_hora_prevista": l["data_hora_prevista"],
        "gfs_mm": l["chuva_gfs_mm"], "ecmwf_mm": l["chuva_ecmwf_mm"],
        "icon_mm": l["chuva_icon_mm"], "wrf_mm": l["chuva_wrf_mm"],
        "media_modelos_mm": regras.media_modelos(l["chuva_gfs_mm"], l["chuva_ecmwf_mm"], l["chuva_icon_mm"], l["chuva_wrf_mm"]),
    } for l in linhas]


@roteador.get("/mensal", response_model=ChuvaMensal, summary="Chuva por mês contra a média histórica")
def chuva_mensal(ano: int | None = Query(None, ge=2000, le=2100),
                 repo: RepositorioNeon = Depends(obter_repositorio)):
    meses = repo.chuva_mensal(ano)
    if not meses:
        raise HTTPException(404, f"Sem dados de chuva mensal{f' para {ano}' if ano else ''}")
    return {"ano": meses[0]["ano_referencia"], "meses": meses}
