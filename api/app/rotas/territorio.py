"""Território: bairros, distritos, áreas alagáveis e pontos de alagamento."""

from fastapi import APIRouter, Depends, Query

from app.esquemas.modelos import Bairro, Distrito, FeatureCollection
from app.repositorios.neon import RepositorioNeon
from app.rotas.dependencias import obter_repositorio
from app.servicos import regras

roteador = APIRouter(prefix="/v1/territorio", tags=["territorio"])


@roteador.get("/bairros", response_model=list[Bairro], summary="Bairros com RPA e distrito sanitário")
def bairros(repo: RepositorioNeon = Depends(obter_repositorio)):
    return repo.bairros()


@roteador.get("/bairros-geo", response_model=FeatureCollection,
              summary="Malha dos 94 bairros em GeoJSON (WGS84), com distrito e RPA")
def bairros_geo(repo: RepositorioNeon = Depends(obter_repositorio)):
    return regras.feature_collection(repo.bairros_geo(), campo_geometria="geometria_geojson")


@roteador.get("/distritos", response_model=list[Distrito], summary="Distritos sanitários")
def distritos(repo: RepositorioNeon = Depends(obter_repositorio)):
    return repo.distritos()


@roteador.get("/areas-alagaveis", response_model=FeatureCollection,
              summary="Áreas alagáveis em GeoJSON (WGS84)")
def areas_alagaveis(distrito: int | None = Query(None, ge=1, le=8, description="Filtra por distrito sanitário"),
                    repo: RepositorioNeon = Depends(obter_repositorio)):
    return regras.feature_collection(repo.areas_alagaveis(distrito), campo_geometria="geometria_geojson")


@roteador.get("/pontos-alagamento", response_model=FeatureCollection,
              summary="Pontos de alagamento com obra de drenagem (EMLURB), em GeoJSON")
def pontos_alagamento(repo: RepositorioNeon = Depends(obter_repositorio)):
    return regras.feature_collection(repo.pontos_alagamento())
