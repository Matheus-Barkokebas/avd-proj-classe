"""Exporta os dados reais do painel a partir do pipeline (decisão 0001, etapa F).

Gera prototipo/dados/recife-real.js — o mesmo formato que o console v3 já lê —
com origem no pipeline, não mais direto do portal:

- arboviroses: tabela `epidemiologia` da camada padronizada no Neon (só linhas
  que passaram no contrato), agregada por semana e por bairro;
- bairro -> distrito: `dim_bairro` / `dim_distrito` no Neon;
- malha dos bairros: GeoJSON guardado na RAW do território (Atlas ou arquivo),
  simplificado para o navegador.

Uso:
    python src/serving/exporta_painel.py --armazenamento mongo --data-territorio 2026-10-28
"""

import argparse
import base64
from collections import Counter, defaultdict
from datetime import date
import json
import math
from pathlib import Path
import sys
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestao import armazenamento as armaz
from src.ingestao import padronizada
from src.ingestao import runner
from src.ingestao.territorio import chave_bairro

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
SAIDA_PADRAO = RAIZ_PROJETO / "prototipo" / "dados" / "recife-real.js"
AGRAVOS = ("dengue", "zika", "chikungunya")
CLASSIFICACAO_DESCARTADO = "5"
TOLERANCIA_GRAUS = 0.00012  # ~13 m: suficiente para o mapa da cidade inteira

# A malha publica alguns nomes compostos que a tabela de distritos registra
# pelo nome curto. Mapeamento explícito, conferido em 2026-10 nos 94 bairros.
APELIDOS_MALHA = {"SITIO DOS PINTOS - SAO BRAS": "SITIO DOS PINTOS", "COHAB - IBURA DE CIMA": "COHAB"}


# ------------------------------------------------------------------ geometria
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


# ------------------------------------------------------------------ leitura
def ler_dimensoes(conexao: Any) -> dict[str, str]:
    """chave_bairro -> código do distrito ('DS I'...), a partir do Neon."""
    linhas = conexao.execute(
        "SELECT b.chave_bairro, d.descricao_distrito "
        "FROM dim_bairro b LEFT JOIN dim_distrito d USING (distrito_sanitario)"
    ).fetchall()
    return {chave: ds for chave, ds in linhas}


def agregar_epidemiologia(conexao: Any, bairro_para_ds: dict[str, str]) -> dict[str, Any]:
    """Séries semanais e contagem por bairro, só com as linhas válidas do Neon."""
    semanais = conexao.execute(
        "SELECT agravo, semana_epidemiologica, count(*), "
        "count(*) FILTER (WHERE classificacao_final IS DISTINCT FROM %s) "
        "FROM epidemiologia GROUP BY 1, 2",
        (CLASSIFICACAO_DESCARTADO,),
    ).fetchall()
    por_bairro_bruto = conexao.execute(
        "SELECT bairro, agravo, count(*) FROM epidemiologia GROUP BY 1, 2"
    ).fetchall()
    rejeitadas = conexao.execute(
        "SELECT count(*) FROM rejeitados WHERE fonte = 'epidemiologia' "
        "AND data_coleta = (SELECT max(data_coleta) FROM epidemiologia)"
    ).fetchone()[0]

    notificacoes, nao_descartadas, totais = defaultdict(Counter), defaultdict(Counter), Counter()
    for agravo, semana, total, validas in semanais:
        notificacoes[agravo][int(semana)] += total
        nao_descartadas[agravo][int(semana)] += validas
        totais[agravo] += total

    por_bairro: dict[str, Counter] = defaultdict(Counter)
    nao_geo: Counter = Counter()
    for bairro, agravo, total in por_bairro_bruto:
        chave = chave_bairro(bairro)
        if chave in bairro_para_ds:
            por_bairro[chave][agravo] += total
        else:
            nao_geo[agravo] += total  # registrado, não descartado em silêncio

    semanas = sorted({s for c in notificacoes.values() for s in c})
    agravos = [a for a in AGRAVOS if a in totais] + sorted(set(totais) - set(AGRAVOS))
    return {
        "fonte": "Pipeline AerVita — camada padronizada (Neon), dados do Portal de Dados Abertos do Recife",
        "coletado_em": date.today().isoformat(),
        "semanas": semanas,
        "notificacoes": {a: [notificacoes[a][s] for s in semanas] for a in agravos},
        "nao_descartadas": {a: [nao_descartadas[a][s] for s in semanas] for a in agravos},
        "por_bairro": {b: dict(c) for b, c in por_bairro.items()},
        "nao_georreferenciadas": dict(nao_geo),
        "totais": dict(totais),
        "rejeitadas_no_contrato": int(rejeitadas),
    }


def bairros_da_malha(geojson: dict[str, Any], bairro_para_ds: dict[str, str]) -> list[dict[str, Any]]:
    bairros = []
    for feicao in geojson["features"]:
        p, geom = feicao["properties"], feicao["geometry"]
        nome = p["EBAIRRNOMEOF"]
        chave = APELIDOS_MALHA.get(chave_bairro(nome), chave_bairro(nome))
        poligonos = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        bairros.append({
            "nome": nome, "chave": chave, "ds": bairro_para_ds.get(chave), "rpa": p.get("CRPAAACODI"),
            "area_km2": round(p.get("DB2GSE.ST_Area(SHAPE)", 0) / 1e6, 2),
            "poligonos": [a for a in (simplificar_anel(pol[0]) for pol in poligonos) if len(a) >= 4],
        })
    return bairros


def malha_da_raw(armazenamento: armaz.ArmazenamentoRaw, data_territorio: date) -> dict[str, Any]:
    raw = armaz.ler_json(armazenamento, "territorio", data_territorio, "territorio.json")
    bloco = raw.get("bairros_geo")
    if not isinstance(bloco, dict) or "conteudo_base64" not in bloco:
        raise ValueError(f"A RAW do território de {data_territorio} não tem a malha de bairros (bairros_geo)")
    return json.loads(base64.b64decode(bloco["conteudo_base64"]))


# ------------------------------------------------------------------ saída
def montar(conexao: Any, geojson: dict[str, Any]) -> dict[str, Any]:
    bairro_para_ds = ler_dimensoes(conexao)
    if not bairro_para_ds:
        raise ValueError("dim_bairro vazia no Neon: rode antes o território com --padronizada neon")
    bairros = bairros_da_malha(geojson, bairro_para_ds)
    return {"bairros": bairros, "epidemiologia": agregar_epidemiologia(conexao, bairro_para_ds)}


def escrever_js(dados: dict[str, Any], saida: Path) -> None:
    cabecalho = (
        f"/* Gerado por src/serving/exporta_painel.py em {date.today().isoformat()} a partir do pipeline:\n"
        " * camada padronizada no Neon (arboviroses, bairro -> distrito) e RAW do território (malha).\n"
        " * Só contagens agregadas, sem dado pessoal. Fonte original: Portal de Dados Abertos do Recife. */\n"
    )
    corpo = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    armaz.gravar_atomico(saida, (cabecalho + f"window.AERVITA_DADOS = {corpo};\n").encode("utf-8"))


def exportar(destino: padronizada.DestinoNeon, armazenamento: armaz.ArmazenamentoRaw,
             data_territorio: date, saida: Path = SAIDA_PADRAO) -> dict[str, Any]:
    geojson = malha_da_raw(armazenamento, data_territorio)
    with destino.conexao() as conexao:
        dados = montar(conexao, geojson)
    escrever_js(dados, saida)
    epi = dados["epidemiologia"]
    sem_ds = [b["nome"] for b in dados["bairros"] if not b["ds"]]
    return {"saida": str(saida), "bairros": len(dados["bairros"]), "bairros_sem_distrito": sem_ds,
            "notificacoes": sum(epi["totais"].values()), "nao_georreferenciadas": epi["nao_georreferenciadas"],
            "rejeitadas_no_contrato": epi["rejeitadas_no_contrato"]}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--armazenamento", choices=armaz.TIPOS, default=None,
                        help="Onde está a RAW do território; padrão: AERVITA_ARMAZENAMENTO ou arquivo")
    parser.add_argument("--data-territorio", type=runner.interpretar_data, default=runner._hoje(),
                        help="Data da coleta do território a usar (AAAA-MM-DD); padrão: hoje")
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    opcoes = parser.parse_args()
    resultado = exportar(padronizada.DestinoNeon.do_ambiente(), armaz.criar(opcoes.armazenamento),
                         opcoes.data_territorio, opcoes.saida)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
