from fastapi import Request

from app.repositorios.neon import RepositorioNeon


def obter_repositorio(request: Request) -> RepositorioNeon:
    return request.app.state.repositorio
