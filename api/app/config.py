"""Configuração da API lida do ambiente (ou do api/.env em desenvolvimento).

Segredo só por variável de ambiente (ai-rules 5.2): a API usa o usuário
SÓ DE LEITURA do Neon (aervita_api), nunca o dono do banco.
"""

from dataclasses import dataclass
import os
from pathlib import Path

RAIZ_API = Path(__file__).resolve().parents[1]


def carregar_env(caminho: Path | None = None) -> None:
    """Carrega pares CHAVE=valor do .env sem sobrescrever variáveis já definidas."""
    caminho = caminho if caminho is not None else RAIZ_API / ".env"
    if not caminho.is_file():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave, valor = chave.strip(), valor.strip().strip('"').strip("'")
        if chave and chave not in os.environ:
            os.environ[chave] = valor


@dataclass(frozen=True)
class Configuracao:
    neon_url: str
    origens_cors: tuple[str, ...]
    cache_segundos: int


def carregar(caminho_env: Path | None = None) -> Configuracao:
    carregar_env(caminho_env)
    url = os.environ.get("NEON_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("NEON_DATABASE_URL não definida. Copie api/.env.example para api/.env e preencha.")
    origens = tuple(o.strip() for o in os.environ.get("API_ORIGENS_CORS", "").split(",") if o.strip())
    cache = int(os.environ.get("API_CACHE_SEGUNDOS", "300") or 300)
    return Configuracao(neon_url=url, origens_cors=origens, cache_segundos=cache)


def mascarar(url: str) -> str:
    """URI com a senha trocada por *** — para log e mensagem de erro."""
    if "://" not in url or "@" not in url:
        return url
    esquema, resto = url.split("://", 1)
    credenciais, host = resto.rsplit("@", 1)
    return f"{esquema}://{credenciais.split(':', 1)[0]}:***@{host}"
