"""Base do modelo de alagamento na Gold (decisão 0003): uma linha por hora.

Regra contra vazamento de dados: tudo o que descreve a hora H usa só o que se
sabe em H. A chuva é acumulada até H, inclusive. A maré futura pode entrar porque
vem da tábua, publicada com antecedência. O alvo é o alagamento em H + horizonte,
e nada calculado a partir dele entra nas variáveis.
"""

from bisect import bisect_right
from datetime import datetime, timedelta
from typing import Any

UMA_HORA = timedelta(hours=1)


def mare_na_hora(extremos: list[tuple[datetime, float]], momento: datetime) -> tuple[float, int] | None:
    """Altura interpolada entre os dois extremos vizinhos e 1 se a maré está subindo."""
    tempos = [t for t, _ in extremos]
    i = bisect_right(tempos, momento)
    if i == 0 or i == len(extremos):
        return None
    (t0, v0), (t1, v1) = extremos[i - 1], extremos[i]
    fracao = (momento - t0) / (t1 - t0)
    return round(v0 + (v1 - v0) * fracao, 3), int(v1 > v0)


def montar_linhas(chuva: dict[datetime, float | None], extremos: list[tuple[datetime, float]],
                  rotas_alagadas: dict[datetime, int], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Variáveis e alvo por hora. Hora sem leitura de chuva conta como zero, e a falta fica registrada.

    Só entram horas com a maior janela de chuva completa. Hora sem coleta do `alaga`
    fica com rotas e alvo vazios, porque não dá para saber se houve alagamento.
    """
    janelas, horizonte, futuro_mare = config["janelas_chuva"], config["horizonte_horas"], config["mare_futura_horas"]
    leituras = sorted(t for t, v in chuva.items() if v is not None)
    if not leituras or not extremos:
        return []
    inicio, fim = leituras[0], leituras[-1]
    extremos = sorted(extremos)
    linhas = []
    hora = inicio + UMA_HORA * (max(janelas) - 1)
    while hora <= fim:
        mare = mare_na_hora(extremos, hora)
        proximas = [mare_na_hora(extremos, hora + UMA_HORA * k) for k in range(futuro_mare + 1)]
        if mare is not None and all(proximas):
            linha: dict[str, Any] = {"hora": hora, "mare_m": mare[0], "mare_subindo": mare[1],
                                     "mare_max_futura_m": max(p[0] for p in proximas)}
            for janela in janelas:
                faixa = [chuva.get(hora - UMA_HORA * k) for k in range(janela)]
                linha[f"chuva_{janela}h_mm"] = round(sum(v or 0.0 for v in faixa), 1)
            linha["horas_sem_leitura_24h"] = sum(chuva.get(hora - UMA_HORA * k) is None for k in range(24))
            linha["rotas_alagadas"] = rotas_alagadas.get(hora)
            futuro = rotas_alagadas.get(hora + UMA_HORA * horizonte)
            linha["rotas_alagadas_futuro"] = futuro
            linha["alagou_no_horizonte"] = None if futuro is None else int(futuro > 0)
            linhas.append(linha)
        hora += UMA_HORA
    return linhas


def colunas(config: dict[str, Any]) -> list[tuple[str, str]]:
    return ([("hora", "timestamp PRIMARY KEY"), ("mare_m", "double precision"), ("mare_subindo", "integer"),
             ("mare_max_futura_m", "double precision")]
            + [(f"chuva_{j}h_mm", "double precision") for j in config["janelas_chuva"]]
            + [("horas_sem_leitura_24h", "integer"), ("rotas_alagadas", "integer"),
               ("rotas_alagadas_futuro", "integer"), ("alagou_no_horizonte", "integer")])


def construir(cur: Any, config: dict[str, Any]) -> dict[str, Any]:
    """Recria gold.ml_alagamento_hora no cursor recebido (mesma transação da Gold)."""
    cur.execute("SELECT data_hora, chuva_mm FROM public.inmet_chuva WHERE estacao = %s", (config["estacao"],))
    chuva = {t: v for t, v in cur.fetchall()}
    cur.execute("SELECT data_hora, mare_m FROM public.cop_mare ORDER BY data_hora")
    extremos = list(cur.fetchall())
    cur.execute("SELECT date_trunc('hour', data_hora), count(*) FILTER (WHERE alagamentos > 0) "
                "FROM public.cop_alagamento_rotas GROUP BY 1")
    rotas = {t: int(n) for t, n in cur.fetchall()}

    linhas = montar_linhas(chuva, extremos, rotas, config)
    defs = colunas(config)
    nomes = [nome for nome, _ in defs]
    cur.execute("DROP TABLE IF EXISTS gold.ml_alagamento_hora")
    cur.execute("CREATE TABLE gold.ml_alagamento_hora (" + ", ".join(f"{n} {t}" for n, t in defs) + ")")
    with cur.copy(f"COPY gold.ml_alagamento_hora ({', '.join(nomes)}) FROM STDIN") as dados:
        for linha in linhas:
            dados.write_row([linha.get(n) for n in nomes])
    com_alvo = [l for l in linhas if l["alagou_no_horizonte"] is not None]
    return {"horas": len(linhas), "horas_com_alvo": len(com_alvo),
            "com_alagamento": sum(l["alagou_no_horizonte"] for l in com_alvo)}
