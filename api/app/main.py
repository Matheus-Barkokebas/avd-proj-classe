"""API do AerVita — lê a camada padronizada no Neon e entrega JSON ao front (decisão 0002).

Rodar em desenvolvimento (de dentro de api/):
    uvicorn app.main:app --reload
Documentação interativa: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from datetime import datetime
import logging

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException

from app import config as cfg
from app.esquemas.modelos import Atualizacao, Erro, Saude
from app.repositorios.neon import FUSO_RECIFE, RepositorioNeon, hoje_recife
from app.rotas import arboviroses, chuva, rios, territorio
from app.rotas.dependencias import obter_repositorio

log = logging.getLogger("aervita.api")
RESPOSTAS_ERRO = {404: {"model": Erro}, 422: {"model": Erro}, 503: {"model": Erro}}


def _erro(status: int, codigo: str, detalhe: str | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"erro": codigo, "detalhe": detalhe})


def criar_app(configuracao: cfg.Configuracao | None = None, repositorio: RepositorioNeon | None = None) -> FastAPI:
    """Fábrica do app. Os testes passam um repositório falso; em produção o banco é o Neon."""

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        banco = None
        if repositorio is None:
            from app.banco import BancoNeon

            banco = BancoNeon(app.state.config.neon_url)
            banco.abrir()
            app.state.repositorio = RepositorioNeon(banco)
            log.info("Conectando ao Neon em %s", cfg.mascarar(app.state.config.neon_url))
        yield
        if banco is not None:
            banco.fechar()

    configuracao = configuracao or cfg.carregar()
    app = FastAPI(
        title="AerVita API",
        version="0.1.0",
        description="Dados de chuva, rios, arboviroses e território do Recife, lidos da camada padronizada "
                    "(Neon). Só leitura. Datas no horário do Recife (-03:00).",
        lifespan=ciclo_de_vida,
        responses=RESPOSTAS_ERRO,
    )
    app.state.config = configuracao
    if repositorio is not None:
        app.state.repositorio = repositorio

    if configuracao.origens_cors:
        app.add_middleware(CORSMiddleware, allow_origins=list(configuracao.origens_cors),
                           allow_methods=["GET"], allow_headers=["*"])

    @app.middleware("http")
    async def cache(request: Request, call_next):
        resposta = await call_next(request)
        if request.method == "GET" and request.url.path.startswith("/v1/") and resposta.status_code == 200:
            resposta.headers["Cache-Control"] = f"public, max-age={configuracao.cache_segundos}"
        return resposta

    # ------------------------------------------------------------ erros num formato único
    # HTTPException do Starlette (a classe-mãe) também cobre rota inexistente e método não permitido.
    @app.exception_handler(HTTPException)
    async def erro_http(_: Request, exc: HTTPException):
        codigos = {404: "nao_encontrado", 400: "requisicao_invalida", 405: "metodo_nao_permitido", 503: "indisponivel"}
        return _erro(exc.status_code, codigos.get(exc.status_code, "erro"), str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def erro_validacao(_: Request, exc: RequestValidationError):
        campos = "; ".join(f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors())
        return _erro(422, "parametro_invalido", campos)

    @app.exception_handler(Exception)
    async def erro_inesperado(_: Request, exc: Exception):
        # erro de conexão com o banco vira 503; o resto, 500 sem vazar detalhe interno
        nome = type(exc).__module__ + "." + type(exc).__name__
        if nome.startswith(("psycopg", "psycopg_pool")):
            log.exception("Falha no banco")
            return _erro(503, "banco_indisponivel", "Não foi possível consultar o banco agora")
        log.exception("Erro inesperado")
        return _erro(500, "erro_interno", None)

    # ------------------------------------------------------------ rotas
    @app.get("/", include_in_schema=False)
    def raiz():
        return RedirectResponse("/docs")

    @app.get("/saude", response_model=Saude, tags=["operacao"], summary="Verifica a API e a conexão com o banco")
    def saude(repo: RepositorioNeon = Depends(obter_repositorio)):
        try:
            repo.banco.verificar()
            return {"status": "ok", "banco": "ok"}
        except Exception:
            log.exception("Saúde: banco indisponível")
            return JSONResponse(status_code=503, content={"status": "indisponivel", "banco": "indisponivel"})

    @app.get("/v1/atualizacao", response_model=Atualizacao, tags=["operacao"],
             summary="Quando cada tabela foi carregada pela última vez")
    def atualizacao(repo: RepositorioNeon = Depends(obter_repositorio)):
        return {"gerado_em": datetime.now(FUSO_RECIFE), "tabelas": repo.ultimas_cargas(), "hoje": hoje_recife()}

    for modulo in (chuva, rios, arboviroses, territorio):
        app.include_router(modulo.roteador)
    return app


_APP: FastAPI | None = None


# `uvicorn app.main:app` — criado sob demanda (uma vez só) para os testes não exigirem o .env
def __getattr__(nome: str):
    global _APP
    if nome == "app":
        if _APP is None:
            _APP = criar_app()
        return _APP
    raise AttributeError(nome)
