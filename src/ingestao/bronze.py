"""Gravação da camada Bronze validada contra contrato, com quarentena (BUG-06).

Antes, qualquer violação descartava o dia inteiro: 19 notificações reais sem
bairro bloqueavam as outras 11.931. Agora:

- violação de LOTE (ex.: coluna obrigatória ausente em todas as linhas) indica
  mudança na fonte -> aborta, nada é gravado;
- violação de LINHA -> a linha vai para a quarentena com o motivo, e a Bronze
  é gravada com as linhas válidas;
- se TODAS as linhas forem rejeitadas -> aborta (provável mudança de formato,
  não dado ruim pontual).
"""

from datetime import date
import io
import json
from pathlib import Path
from typing import Any
import pyarrow as pa
import pyarrow.parquet as pq

from src.ingestao import contratos
from src.ingestao import runner


def _particao(diretorio_dados: Path, pasta: str, data_coleta: date) -> Path:
    return (
        Path(diretorio_dados) / "bronze" / pasta
        / f"{data_coleta.year:04d}" / f"{data_coleta.month:02d}" / f"{data_coleta.day:02d}"
    )


def caminho_quarentena(diretorio_dados: Path, fonte: str, data_coleta: date) -> Path:
    return _particao(diretorio_dados, f"{fonte}_rejeitados", data_coleta) / f"{fonte}_rejeitados.json"


def gravar_validado(
    lote: list[dict[str, Any]],
    nome_contrato: str,
    fonte: str,
    data_coleta: date,
    diretorio_dados: Path,
) -> Path:
    """Valida o lote contra o contrato e grava Bronze (válidas) + quarentena (rejeitadas).

    Devolve o caminho do Parquet da Bronze. Idempotente: a partição da Bronze é
    substituída atomicamente e uma quarentena antiga da mesma data é removida
    quando a reexecução não rejeita nada.
    """
    contrato = contratos.carregar_contrato(nome_contrato)
    violacoes = contratos.validar(lote, contrato)

    de_lote = [v for v in violacoes if v.linha is None]
    if de_lote:
        resumo = "; ".join(f"[{v.tipo}] {v.campo}: {v.mensagem}" for v in de_lote[:5])
        raise ValueError(f"Violações do contrato de {nome_contrato} no lote ({len(de_lote)}): {resumo}")

    motivos_por_linha: dict[int, list[str]] = {}
    for v in violacoes:
        motivos_por_linha.setdefault(v.linha, []).append(f"[{v.tipo}] {v.campo}: {v.mensagem}")

    # `linha` do validador é 1-based
    validas = [reg for i, reg in enumerate(lote, start=1) if i not in motivos_por_linha]
    rejeitadas = [
        {"linha": i, "motivos": motivos_por_linha[i], "registro": lote[i - 1]}
        for i in sorted(motivos_por_linha)
    ]

    if lote and not validas:
        resumo = "; ".join(rejeitadas[0]["motivos"][:3])
        raise ValueError(
            f"Violações do contrato de {nome_contrato}: todas as {len(lote)} linhas rejeitadas "
            f"(provável mudança de formato da fonte) — ex.: {resumo}"
        )

    buffer = io.BytesIO()
    pq.write_table(pa.Table.from_pylist(validas), buffer)
    caminho_bronze = _particao(diretorio_dados, fonte, data_coleta) / f"{fonte}.parquet"
    runner.gravar_atomico(caminho_bronze, buffer.getvalue())

    quarentena = caminho_quarentena(diretorio_dados, fonte, data_coleta)
    if rejeitadas:
        # JSON (não Parquet): rejeitadas podem ter tipos mistos na mesma coluna.
        runner.gravar_atomico(
            quarentena,
            json.dumps(rejeitadas, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
        )
    else:
        quarentena.unlink(missing_ok=True)

    return caminho_bronze


def contar_rejeitados(diretorio_dados: Path, fonte: str, data_coleta: date) -> int:
    """Quantas linhas foram para a quarentena na partição (0 se não houver)."""
    quarentena = caminho_quarentena(diretorio_dados, fonte, data_coleta)
    if not quarentena.is_file():
        return 0
    return len(json.loads(quarentena.read_text(encoding="utf-8")))
