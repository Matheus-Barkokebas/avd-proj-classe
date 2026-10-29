"""Leitura de credenciais e parâmetros por variável de ambiente (decisão 0001).

Segredos nunca ficam no código nem em conf/ (ai-rules 5.2). Em desenvolvimento,
os valores vêm do arquivo .env na raiz do projeto (ignorado pelo Git); em
produção ou CI, das variáveis de ambiente do próprio sistema, que têm prioridade.
"""

import os
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[2]


def carregar_env(caminho: Path | None = None) -> None:
    """Carrega pares CHAVE=valor do .env sem sobrescrever variáveis já definidas."""
    caminho = caminho if caminho is not None else RAIZ_PROJETO / ".env"
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


def obrigatoria(nome: str) -> str:
    """Devolve a variável ou falha com mensagem clara — sem valor padrão para segredo."""
    carregar_env()
    valor = os.environ.get(nome, "").strip()
    if not valor:
        raise RuntimeError(
            f"Variável de ambiente {nome} não definida. "
            f"Copie .env.example para .env e preencha o valor."
        )
    return valor


def opcional(nome: str, padrao: str) -> str:
    carregar_env()
    return os.environ.get(nome, "").strip() or padrao


def config_mongo() -> dict[str, str]:
    """URI e nome do banco do MongoDB Atlas (camada RAW)."""
    return {"uri": obrigatoria("MONGODB_URI"), "banco": opcional("MONGODB_DB", "aervita")}


def mascarar(uri: str) -> str:
    """Esconde a senha de uma URI para poder registrar em log."""
    if "://" not in uri or "@" not in uri:
        return uri
    esquema, resto = uri.split("://", 1)
    credenciais, host = resto.rsplit("@", 1)
    usuario = credenciais.split(":", 1)[0]
    return f"{esquema}://{usuario}:***@{host}"
