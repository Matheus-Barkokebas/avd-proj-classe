"""Utilitários de tipagem compartilhados pelos coletores de ingestão.

Centraliza a normalização de datas e números para que cada fonte não tenha
a sua própria versão (a divergência entre cópias causou o BUG-03).
"""

from datetime import datetime
import re
from typing import Any

FORMATO_PADRAO = "%Y-%m-%d %H:%M:%S"  # PADROES §3

# Formatos aceitos, do mais comum ao menos comum. Datas brasileiras são sempre
# dia/mês/ano — as fontes do Recife nunca usam mês/dia.
_FORMATOS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)


def _vazio(valor: Any) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())


def normalizar_timestamp(valor: Any) -> str | None:
    """Converte uma data/hora de qualquer formato conhecido para 'YYYY-MM-DD HH:MM:SS'.

    Vazio -> None. Formato desconhecido -> devolve o texto original (sem
    adivinhar), para que a validação do contrato acuse o problema.
    """
    if _vazio(valor):
        return None
    if isinstance(valor, datetime):
        return valor.strftime(FORMATO_PADRAO)
    texto = str(valor).strip()
    # Frações de segundo e fuso (ex.: '2025-04-03T00:00:00.000+00:00') não
    # mudam a data/hora de referência das fontes atuais; são descartados.
    texto_base = re.sub(r"(\.\d+)?([+-]\d{2}:?\d{2}|Z)?$", "", texto)
    for formato in _FORMATOS:
        try:
            return datetime.strptime(texto_base, formato).strftime(FORMATO_PADRAO)
        except ValueError:
            continue
    return texto


def para_int(valor: Any) -> int | None:
    """Converte para int tolerando texto, float inteiro ('202502', 2025.0) e vazio.

    Valor não numérico é devolvido como veio, para a validação do contrato acusar.
    """
    if _vazio(valor):
        return None
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int):
        return valor
    try:
        numero = float(str(valor).strip())
    except ValueError:
        return valor
    return int(numero) if numero.is_integer() else valor


def para_texto(valor: Any) -> str | None:
    """Texto sem espaços nas pontas; vazio vira None. Números inteiros sem '.0'."""
    if _vazio(valor):
        return None
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()
