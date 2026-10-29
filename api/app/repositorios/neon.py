"""Consultas à camada padronizada no Neon — único lugar da API com SQL.

As tabelas são as geradas pelo pipeline a partir dos contratos
(pipeline/conf/contracts/). A API só lê. Datas no Neon estão no horário do
Recife sem fuso; aqui recebem o -03:00 para o front nunca ter dúvida.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.banco import Banco

FUSO_RECIFE = timezone(timedelta(hours=-3), name="America/Recife")


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
        linhas = self._q("SELECT * FROM cop_indicadores ORDER BY data_hora DESC LIMIT 1")
        return linhas[0] if linhas else None

    def serie_indicadores(self, desde: datetime) -> list[dict[str, Any]]:
        return self._q(
            "SELECT data_hora, chuva_media_1h_mm, chuva_max_1h_mm, chuva_media_24h_mm, chuva_max_24h_mm, mare_m "
            "FROM cop_indicadores WHERE data_hora >= %s ORDER BY data_hora",
            (desde.replace(tzinfo=None),),
        )

    def chuva_mensal(self, ano: int | None = None) -> list[dict[str, Any]]:
        if ano is None:
            return self._q(
                "SELECT * FROM cop_chuva_mensal "
                "WHERE ano_referencia = (SELECT max(ano_referencia) FROM cop_chuva_mensal) ORDER BY mes"
            )
        return self._q("SELECT * FROM cop_chuva_mensal WHERE ano_referencia = %s ORDER BY mes", (ano,))

    def previsao(self, desde: datetime) -> list[dict[str, Any]]:
        return self._q(
            "SELECT data_hora_prevista, chuva_gfs_mm, chuva_ecmwf_mm, chuva_icon_mm, chuva_wrf_mm "
            "FROM cop_previsao_chuva WHERE data_hora_prevista >= %s ORDER BY data_hora_prevista",
            (desde.replace(tzinfo=None),),
        )

    # ------------------------------------------------------------ rios (COP)
    def rios_ultima_leitura(self) -> list[dict[str, Any]]:
        return self._q(
            "SELECT DISTINCT ON (codigo_estacao) codigo_estacao, estacao, rio, data_hora, nivel, "
            "cota_pre_alerta, cota_alerta, cota_inundacao, situacao "
            "FROM cop_rios ORDER BY codigo_estacao, data_hora DESC"
        )

    def serie_rio(self, codigo_estacao: str, desde: datetime) -> list[dict[str, Any]]:
        return self._q(
            "SELECT data_hora, nivel FROM cop_rios WHERE codigo_estacao = %s AND data_hora >= %s ORDER BY data_hora",
            (codigo_estacao, desde.replace(tzinfo=None)),
        )

    def estacao_existe(self, codigo_estacao: str) -> bool:
        return bool(self._q("SELECT 1 FROM cop_rios WHERE codigo_estacao = %s LIMIT 1", (codigo_estacao,)))

    # ------------------------------------------------------------ arboviroses
    def arboviroses_por_semana(self, agravo: str | None = None) -> list[dict[str, Any]]:
        filtro, params = ("WHERE agravo = %s", (agravo,)) if agravo else ("", None)
        return self._q(
            "SELECT semana_epidemiologica AS semana, agravo, count(*) AS notificacoes, "
            "count(*) FILTER (WHERE classificacao_final IS DISTINCT FROM '5') AS nao_descartadas "
            f"FROM epidemiologia {filtro} GROUP BY 1, 2 ORDER BY 1, 2",
            params,
        )

    def arboviroses_por_bairro_bruto(self) -> list[dict[str, Any]]:
        """Contagem pelo texto de bairro da fonte — o cruzamento com dim_bairro é feito no serviço."""
        return self._q("SELECT bairro, agravo, count(*) AS notificacoes FROM epidemiologia GROUP BY 1, 2")

    # ------------------------------------------------------------ território
    def bairros(self) -> list[dict[str, Any]]:
        return self._q(
            "SELECT b.chave_bairro, b.nome_bairro, b.rpa, b.distrito_sanitario, d.descricao_distrito "
            "FROM dim_bairro b LEFT JOIN dim_distrito d USING (distrito_sanitario) ORDER BY b.nome_bairro"
        )

    def distritos(self) -> list[dict[str, Any]]:
        return self._q(
            "SELECT d.distrito_sanitario, d.descricao_distrito, count(b.chave_bairro) AS bairros "
            "FROM dim_distrito d LEFT JOIN dim_bairro b USING (distrito_sanitario) "
            "GROUP BY 1, 2 ORDER BY 1"
        )

    def areas_alagaveis(self, distrito: int | None = None) -> list[dict[str, Any]]:
        filtro, params = ("WHERE distrito_sanitario = %s", (distrito,)) if distrito else ("", None)
        return self._q(
            "SELECT id_area, codigo, distrito_sanitario, area_m2, geometria_geojson "
            f"FROM cop_areas_alagaveis {filtro} ORDER BY id_area::int",
            params,
        )

    def pontos_alagamento(self) -> list[dict[str, Any]]:
        return self._q(
            "SELECT id_ponto, bairro, rpa, logradouro, trecho, status, classificacao, percentual_concluido, "
            "inicio_intervencao, termino_intervencao, longitude, latitude "
            "FROM cop_pontos_alagamento ORDER BY id_ponto::int"
        )

    # ------------------------------------------------------------ atualização
    def ultimas_cargas(self) -> list[dict[str, Any]]:
        """Quando cada tabela foi carregada pela última vez (coluna de controle do pipeline)."""
        tabelas = ("cop_indicadores", "cop_rios", "cop_previsao_chuva", "cop_chuva_mensal", "epidemiologia",
                   "cop_areas_alagaveis", "cop_pontos_alagamento")
        sql = " UNION ALL ".join(
            f"SELECT '{t}' AS tabela, max(carregado_em) AS carregado_em, count(*) AS linhas FROM {t}" for t in tabelas
        )
        return self._q(sql)


def hoje_recife() -> date:
    return datetime.now(FUSO_RECIFE).date()
