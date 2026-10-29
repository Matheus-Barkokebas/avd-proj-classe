"""Exporta o esquema OpenAPI da API para api/openapi.json (o contrato com o front).

O front gera os tipos TypeScript a partir desse arquivo, sem precisar da API no ar:
    python -m app.openapi
Há teste que falha se o arquivo versionado ficar diferente do código.
"""

import json
from pathlib import Path

from app.config import Configuracao
from app.main import criar_app

ARQUIVO = Path(__file__).resolve().parents[1] / "openapi.json"


def gerar() -> str:
    # configuração fictícia: gerar o esquema não abre conexão com o banco
    app = criar_app(Configuracao(neon_url="postgresql://esquema", origens_cors=(), cache_segundos=300),
                    repositorio=object())
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    ARQUIVO.write_text(gerar(), encoding="utf-8")
    print(f"OpenAPI gravado em {ARQUIVO}")
