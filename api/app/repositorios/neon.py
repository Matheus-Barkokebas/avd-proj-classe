"""Consultas à camada Gold no Neon — único lugar da API com SQL.

A API só lê, e só o schema `gold` (decisão 0003), montado por
pipeline/src/processamento/gold.py. Datas no Neon estão no horário do
Recife sem fuso; aqui recebem o -03:00 para o front nunca ter dúvida.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.banco import Banco

FUSO_RECIFE = timezone(timedelta(hours=-3), name="America/Recife")
# O painel mostra o ano mais recente; os anteriores ficam na Gold para o histórico e o modelo.
_ULTIMO_ANO_ARBO = "SELECT max(ano) FROM gold.arbo_bairro_semana"


def _com_fuso(linhas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for linha in linhas:
        for chave, valor in linha.items():
            if isinstance(valor, datetime) and valor.tzinfo is None:
                linha[chave] = valor.replace(tzinfo=FUSO_RECIFE)
    return linhas


class RepositorioNeon:
    def __init__(self, banco: Banco):
        self.banco = banco

    def _q(self, sql: str, parametros: tuple | dict | None = None) -> list[dict[str, Any]]:
        return _com_fuso(self.banco.consultar(sql, parametros))

    # ------------------------------------------------------------ chuva (COP)
    def indicador_mais_recente(self) -> dict[str, Any] | None:
        linhas = self._q("SELECT * FROM gold.chuva_hora ORDER BY data_hora DESC LIMIT 1")
        return linhas[0] if linhas else None

    def serie_indicadores(self, desde: datetime) -> list[dict[str, Any]]:
        return self._q(
            "SELECT data_hora, chuva_media_1h_mm, chuva_max_1h_mm, chuva_media_24h_mm, chuva_max_24h_mm, mare_m "
            "FROM gold.chuva_hora WHERE data_hora >= %s ORDER BY data_hora",
            (desde.replace(tzinfo=None),),
        )

    def chuva_mensal(self, ano: int | None = None) -> list[dict[str, Any]]:
        if ano is None:
            return self._q(
                "SELECT * FROM gold.chuva_mensal "
                "WHERE ano_referencia = (SELECT max(ano_referencia) FROM gold.chuva_mensal) ORDER BY mes"
            )
        return self._q("SELECT * FROM gold.chuva_mensal WHERE ano_referencia = %s ORDER BY mes", (ano,))

    def previsao(self, desde: datetime) -> list[dict[str, Any]]:
        return self._q(
            "SELECT data_hora_prevista, chuva_gfs_mm, chuva_ecmwf_mm, chuva_icon_mm, chuva_wrf_mm "
            "FROM gold.previsao_chuva WHERE data_hora_prevista >= %s ORDER BY data_hora_prevista",
            (desde.replace(tzinfo=None),),
        )

    # ------------------------------------------------------------ rios (COP)
    def rios_ultima_leitura(self) -> list[dict[str, Any]]:
        return self._q(
            "SELECT DISTINCT ON (codigo_estacao) codigo_estacao, estacao, rio, data_hora, nivel, "
            "cota_pre_alerta, cota_alerta, cota_inundacao, situacao "
            "FROM gold.rio_leitura ORDER BY codigo_estacao, data_hora DESC"
        )

    def serie_rio(self, codigo_estacao: str, desde: datetime) -> list[dict[str, Any]]:
        return self._q(
            "SELECT data_hora, nivel FROM gold.rio_leitura WHERE codigo_estacao = %s AND data_hora >= %s ORDER BY data_hora",
            (codigo_estacao, desde.replace(tzinfo=None)),
        )

    def estacao_existe(self, codigo_estacao: str) -> bool:
        return bool(self._q("SELECT 1 FROM gold.rio_leitura WHERE codigo_estacao = %s LIMIT 1", (codigo_estacao,)))

    # ------------------------------------------------------------ arboviroses
    def arboviroses_por_semana(self, agravo: str | None = None) -> list[dict[str, Any]]:
        filtro, params = ("AND agravo = %s", (agravo,)) if agravo else ("", None)
        return self._q(
            "SELECT semana, agravo, sum(notificacoes)::bigint AS notificacoes, "
            "sum(nao_descartadas)::bigint AS nao_descartadas "
            f"FROM gold.arbo_bairro_semana WHERE ano = ({_ULTIMO_ANO_ARBO}) {filtro} GROUP BY 1, 2 ORDER BY 1, 2",
            params,
        )

    def arboviroses_por_bairro_bruto(self) -> list[dict[str, Any]]:
        """Contagem por bairro; o que não tem chave vem com a grafia da fonte, para o serviço listar."""
        return self._q(
            "SELECT COALESCE(chave_bairro, bairro_nao_reconhecido) AS bairro, agravo, "
            "sum(notificacoes)::bigint AS notificacoes "
            f"FROM gold.arbo_bairro_semana WHERE ano = ({_ULTIMO_ANO_ARBO}) GROUP BY 1, 2"
        )

    # ------------------------------------------------------------ território
    def bairros(self) -> list[dict[str, Any]]:
        return self._q("SELECT * FROM gold.bairro ORDER BY nome_bairro")

    def bairros_geo(self) -> list[dict[str, Any]]:
        return self._q("SELECT * FROM gold.bairro_geo ORDER BY chave_bairro")

    def distritos(self) -> list[dict[str, Any]]:
        return self._q("SELECT * FROM gold.distrito ORDER BY distrito_sanitario")

    def areas_alagaveis(self, distrito: int | None = None) -> list[dict[str, Any]]:
        filtro, params = ("WHERE distrito_sanitario = %s", (distrito,)) if distrito else ("", None)
        return self._q(f"SELECT * FROM gold.area_alagavel {filtro} ORDER BY id_area::int", params)

    def pontos_alagamento(self) -> list[dict[str, Any]]:
        return self._q("SELECT * FROM gold.ponto_alagamento ORDER BY id_ponto::int")

    # ------------------------------------------------------------ maré e alagamento
    def mare_entre(self, inicio: datetime, fim: datetime) -> list[dict[str, Any]]:
        return self._q(
            "SELECT data_hora, mare_m, anterior FROM (SELECT data_hora, mare_m, "
            "lag(mare_m) OVER (ORDER BY data_hora) AS anterior FROM gold.mare) tabua "
            "WHERE data_hora BETWEEN %s AND %s ORDER BY data_hora",
            (inicio.replace(tzinfo=None), fim.replace(tzinfo=None)),
        )

    def alagamento_por_rota(self, desde: datetime) -> list[dict[str, Any]]:
        return self._q(
            "SELECT rota, count(*) AS leituras_com_alagamento, sum(alagamentos)::bigint AS alertas, max(data_hora) AS ultimo "
            "FROM gold.alagamento_rota WHERE alagamentos > 0 AND data_hora >= %s "
            "GROUP BY rota ORDER BY 2 DESC, 3 DESC, rota",
            (desde.replace(tzinfo=None),),
        )

    def alagamento_por_dia(self, desde: datetime) -> list[dict[str, Any]]:
        return self._q(
            "SELECT data_hora::date AS dia, count(DISTINCT date_trunc('hour', data_hora)) AS horas_com_alagamento, "
            "count(DISTINCT rota) AS rotas, sum(alagamentos)::bigint AS alertas "
            "FROM gold.alagamento_rota WHERE alagamentos > 0 AND data_hora >= %s GROUP BY 1 ORDER BY 1",
            (desde.replace(tzinfo=None),),
        )

    def rotas_com_alagamento(self, desde: datetime) -> list[dict[str, Any]]:
        return self._q(
            "SELECT r.rota, r.cod_rota, r.geometria_geojson, COALESCE(a.leituras, 0) AS leituras_com_alagamento "
            "FROM gold.rota r LEFT JOIN (SELECT rota, count(*) AS leituras FROM gold.alagamento_rota "
            "WHERE alagamentos > 0 AND data_hora >= %s GROUP BY rota) a USING (rota) ORDER BY r.rota",
            (desde.replace(tzinfo=None),),
        )

    def modelo_mais_recente(self) -> dict[str, Any] | None:
        linhas = self._q("SELECT * FROM gold.modelo_execucao ORDER BY treinado_em DESC LIMIT 1")
        return linhas[0] if linhas else None

    def previsoes_de_teste(self) -> list[dict[str, Any]]:
        return self._q(
            "SELECT hora, hora_prevista, probabilidade, previsto, observado FROM gold.previsao_alagamento "
            "WHERE conjunto = 'teste' ORDER BY hora"
        )

    # ------------------------------------------------------------ atualização
    def ultimas_cargas(self) -> list[dict[str, Any]]:
        """Quando cada tabela da Silver foi carregada pela última vez (coluna de controle do pipeline)."""
        return self._q("SELECT * FROM gold.ultima_carga")


def hoje_recife() -> date:
    return datetime.now(FUSO_RECIFE).date()
