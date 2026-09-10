"""Execução de coletores e persistência de RAW sem transformação (FND-03)."""

import argparse
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from uuid import uuid4


RAIZ_PROJETO = Path(__file__).resolve().parents[2]
# America/Recife é UTC-03, sem horário de verão (PADROES §3).
FUSO_RECIFE = timezone(timedelta(hours=-3), name="America/Recife")


@dataclass(frozen=True)
class Coletor:
    """Contrato: devolver bytes originais e contar registros sem alterar a RAW."""

    coletar: Callable[[date], bytes]
    contar_registros: Callable[[bytes], int]
    nome_arquivo: str


def coletar_dummy(data_coleta: date) -> bytes:
    """Fonte sintética exclusiva para testes e demonstração local, sem rede."""
    return json.dumps([{"data": data_coleta.isoformat(), "simulado": True}]).encode()


COLETORES = {
    "dummy": Coletor(coletar_dummy, lambda conteudo: len(json.loads(conteudo)), "dummy.json")
}


def gravar_atomico(caminho: Path, conteudo: bytes) -> None:
    """Publica somente o arquivo completo; preserva o anterior se a escrita falhar."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(dir=caminho.parent, delete=False) as arquivo:
            temporario = Path(arquivo.name)
            arquivo.write(conteudo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)


def executar(
    fonte: str,
    data_coleta: date | None = None,
    *,
    diretorio_dados: Path = RAIZ_PROJETO / "data",
    coletores: Mapping[str, Coletor] | None = None,
) -> dict:
    """Relê a RAW para data explícita, ou coleta; registra sucesso e falha.

    Novas fontes devem registrar seu Coletor no mapa, sem importações dinâmicas.
    Falhas no armazenamento do próprio registro são propagadas ao chamador.
    """
    inicio = datetime.now(FUSO_RECIFE)
    data_particao = data_coleta if data_coleta is not None else inicio.date()
    identificador = uuid4().hex
    registro = {
        "id": identificador,
        "fonte": fonte,
        "inicio": inicio.strftime("%Y-%m-%d %H:%M:%S"),
        "fim": None,
        "data_coleta": data_particao.isoformat(),
        "numero_registros": 0,
        "status": "erro",
        "mensagem": "",
    }
    try:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", fonte):
            raise ValueError("Nome de fonte deve usar snake_case sem acento")
        catalogo = COLETORES if coletores is None else coletores
        if fonte not in catalogo:
            raise ValueError(f"Coletor nao registrado: {fonte}")
        coletor = catalogo[fonte]
        if not re.fullmatch(r"[a-z0-9_]+\.(json|csv)", coletor.nome_arquivo):
            raise ValueError("Arquivo RAW deve ter nome simples e extensao json ou csv")
        caminho = (
            Path(diretorio_dados) / "raw" / fonte
            / f"{data_particao.year:04d}" / f"{data_particao.month:02d}"
            / f"{data_particao.day:02d}" / coletor.nome_arquivo
        )
        reutilizar = data_coleta is not None and caminho.is_file()
        conteudo = caminho.read_bytes() if reutilizar else coletor.coletar(data_particao)
        if not isinstance(conteudo, bytes):
            raise TypeError("Coletor deve devolver bytes originais")
        quantidade = coletor.contar_registros(conteudo)
        if type(quantidade) is not int or quantidade < 0:
            raise ValueError("Contagem de registros deve ser inteiro nao negativo")
        if not reutilizar:
            gravar_atomico(caminho, conteudo)
        registro.update(
            numero_registros=quantidade,
            status="ok",
            mensagem="RAW existente relida" if reutilizar else "Coleta concluida",
        )
    except Exception as erro:
        registro["mensagem"] = f"{type(erro).__name__}: {erro}"
    registro["fim"] = datetime.now(FUSO_RECIFE).strftime("%Y-%m-%d %H:%M:%S")
    gravar_atomico(
        Path(diretorio_dados) / "_runs" / f"{identificador}.json",
        json.dumps(registro, ensure_ascii=False, indent=2).encode("utf-8"),
    )
    return registro


def interpretar_data(valor: str) -> date:
    """Valida o formato estrito exigido pela interface de reprocessamento."""
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
            raise ValueError
        return date.fromisoformat(valor)
    except ValueError as erro:
        raise argparse.ArgumentTypeError("Use uma data valida no formato AAAA-MM-DD") from erro


def main() -> int:
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("fonte", help="Nome do coletor registrado (teste: dummy)")
    argumentos.add_argument("--data", type=interpretar_data, dest="data_coleta")
    argumentos.add_argument(
        "--diretorio-dados", type=Path, default=RAIZ_PROJETO / "data",
        help="Raiz de armazenamento; padrao: data/ do projeto",
    )
    opcoes = argumentos.parse_args()
    try:
        registro = executar(**vars(opcoes))
    except OSError as erro:
        argumentos.exit(1, f"Falha ao persistir registro de execucao: {erro}\n")
    print(json.dumps(registro, ensure_ascii=False))
    return 0 if registro["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
