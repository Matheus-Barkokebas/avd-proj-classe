"""Arboviroses: notificações por semana e por bairro (fonte: Dados Abertos Recife, via pipeline)."""

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.esquemas.modelos import ArbovirosesPorBairro, ArbovirosesSemana
from app.repositorios.neon import RepositorioNeon
from app.rotas.dependencias import obter_repositorio
from app.servicos import regras

roteador = APIRouter(prefix="/v1/arboviroses", tags=["arboviroses"])


@roteador.get("/semanas", response_model=list[ArbovirosesSemana], summary="Notificações por semana epidemiológica")
def por_semana(agravo: Literal["dengue", "chikungunya", "zika"] | None = Query(None),
               repo: RepositorioNeon = Depends(obter_repositorio)):
    return repo.arboviroses_por_semana(agravo)


@roteador.get("/bairros", response_model=ArbovirosesPorBairro, summary="Notificações por bairro e distrito")
def por_bairro(repo: RepositorioNeon = Depends(obter_repositorio)):
    return regras.arboviroses_por_bairro(repo.arboviroses_por_bairro_bruto(), repo.bairros())
