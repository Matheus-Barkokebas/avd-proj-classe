"""Simplificação de geometrias para exibição em mapa (malha de bairros do Recife).

Usado pelo território (tabela geo_bairro no Neon) e pela exportação do painel.
"""

import math
from typing import Any

TOLERANCIA_GRAUS = 0.00012  # ~13 m: suficiente para o mapa da cidade inteira

# A malha publica alguns nomes compostos que a tabela de distritos registra
# pelo nome curto. Mapeamento explícito, conferido em 2026-10 nos 94 bairros.
APELIDOS_MALHA = {"SITIO DOS PINTOS - SAO BRAS": "SITIO DOS PINTOS", "COHAB - IBURA DE CIMA": "COHAB"}


def douglas_peucker(pontos: list[list[float]], tol: float) -> list[list[float]]:
    if len(pontos) < 4:
        return pontos
    (ax, ay), (bx, by) = pontos[0], pontos[-1]
    dx, dy = bx - ax, by - ay
    comprimento = math.hypot(dx, dy) or 1e-12
    indice, maior = 0, 0.0
    for i in range(1, len(pontos) - 1):
        px, py = pontos[i]
        d = abs(dy * (px - ax) - dx * (py - ay)) / comprimento
        if d > maior:
            indice, maior = i, d
    if maior <= tol:
        return [pontos[0], pontos[-1]]
    return douglas_peucker(pontos[: indice + 1], tol)[:-1] + douglas_peucker(pontos[indice:], tol)


def simplificar_anel(anel: list[list[float]], tol: float = TOLERANCIA_GRAUS) -> list[list[float]]:
    meio = len(anel) // 2  # anel fechado: simplifica as duas metades
    pontos = douglas_peucker(anel[: meio + 1], tol)[:-1] + douglas_peucker(anel[meio:], tol)
    return [[round(x, 5), round(y, 5)] for x, y in pontos]


def poligonos_simplificados(geometria: dict[str, Any], tol: float = TOLERANCIA_GRAUS) -> list[list[list[float]]]:
    """Polygon ou MultiPolygon -> lista de anéis externos simplificados (furos descartados)."""
    poligonos = geometria["coordinates"] if geometria["type"] == "MultiPolygon" else [geometria["coordinates"]]
    return [a for a in (simplificar_anel(pol[0], tol) for pol in poligonos) if len(a) >= 4]


def multipoligono(aneis: list[list[list[float]]]) -> dict[str, Any]:
    """Anéis externos -> geometria GeoJSON MultiPolygon."""
    return {"type": "MultiPolygon", "coordinates": [[anel] for anel in aneis]}
