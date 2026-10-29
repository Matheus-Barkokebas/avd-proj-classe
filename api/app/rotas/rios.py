"""Rios: última leitura por estação com situação contra as cotas oficiais (fonte: COP Recife)."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app.esquemas.modelos import PontoSerieRio, Rio
from app.repositorios.neon import FUSO_RECIFE, RepositorioNeon
from app.rotas.dependencias import obter_repositorio
from app.servicos import regras

roteador = APIRouter(prefix="/v1/rios", tags=["rios"])


@roteador.get("", response_model=list[Rio], summary="Última leitura de cada estação, com situação")
def rios(repo: RepositorioNeon = Depends(obter_repositorio)):
    resposta = []
    for l in repo.rios_ultima_leitura():
        resposta.append({
            **l,
            "situacao": regras.situacao_rio(l["nivel"], l["cota_pre_alerta"], l["cota_alerta"], l["cota_inundacao"]),
            "situacao_fonte": l["situacao"],
            "percentual_da_cota_alerta": regras.percentual(l["nivel"], l["cota_alerta"]),
        })
    # mais grave primeiro, para o front destacar
    gravidade = ["inundacao", "alerta", "pre_alerta", "normal", "sem_cota"]
    return sorted(resposta, key=lambda r: (gravidade.index(r["situacao"]), r["rio"], r["estacao"]))


@roteador.get("/{codigo_estacao}/serie", response_model=list[PontoSerieRio], summary="Série do nível de uma estação")
def serie_rio(codigo_estacao: str, horas: int = Query(72, ge=1, le=24 * 31),
              repo: RepositorioNeon = Depends(obter_repositorio)):
    if not repo.estacao_existe(codigo_estacao):
        raise HTTPException(404, f"Estação {codigo_estacao} não encontrada")
    return repo.serie_rio(codigo_estacao, datetime.now(FUSO_RECIFE) - timedelta(hours=horas))
