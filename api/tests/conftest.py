"""Dublê do repositório: os testes da API não acessam o banco nem a rede.

Os dados de exemplo imitam linhas reais do Neon (conferidas em 2026-10-29),
com o fuso já aplicado como o repositório real faz.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import Configuracao
from app.main import criar_app

FUSO = timezone(timedelta(hours=-3))
AGORA = datetime.now(FUSO).replace(minute=0, second=0, microsecond=0)


class BancoFalso:
    def __init__(self, falhar=False):
        self.falhar = falhar

    def verificar(self):
        if self.falhar:
            raise RuntimeError("sem conexão")


class RepositorioFalso:
    def __init__(self, banco=None, vazio=False):
        self.banco = banco or BancoFalso()
        self.vazio = vazio
        self.chamadas = []

    def indicador_mais_recente(self):
        if self.vazio:
            return None
        return {"data_hora": datetime(2026, 10, 28, 21, 0, 45, tzinfo=FUSO), "estagio": "NORMALIDADE",
                "chuva_media_1h_mm": 0.0, "chuva_max_1h_mm": 0.0, "estacao_max_1h": None,
                "chuva_media_24h_mm": 6.2, "chuva_max_24h_mm": 15.2, "estacao_max_24h": "Areias",
                "mare_m": 1.1, "sentido_mare": "subindo", "ocorrencias": 9, "alagamentos": 0, "abrigos": 0,
                "abrigados": None, "ocorrencias_1h": 0, "data_coleta": date(2026, 10, 28)}

    def serie_indicadores(self, desde):
        self.chamadas.append(("serie_indicadores", desde))
        return [{"data_hora": AGORA - timedelta(hours=h), "chuva_media_1h_mm": 0.1 * h, "chuva_max_1h_mm": 0.2,
                 "chuva_media_24h_mm": 6.0, "chuva_max_24h_mm": 15.2, "mare_m": 1.0} for h in (2, 1)]

    def chuva_mensal(self, ano=None):
        if self.vazio:
            return []
        return [{"ano_referencia": 2026, "mes": m, "chuva_ano_atual_mm": a, "chuva_ano_anterior_mm": None,
                 "media_historica_mm": h} for m, a, h in ((9, 76.08, 77.82), (10, 12.1, 35.0))]

    def previsao(self, desde):
        return [{"data_hora_prevista": AGORA + timedelta(hours=1), "chuva_gfs_mm": 0.4, "chuva_ecmwf_mm": 0.0,
                 "chuva_icon_mm": None, "chuva_wrf_mm": 1.1}]

    def rios_ultima_leitura(self):
        base = {"data_hora": datetime(2026, 10, 28, 20, tzinfo=FUSO), "situacao": "Normal"}
        return [
            {**base, "codigo_estacao": "39145010", "estacao": "LIMOEIRO", "rio": "RIO CAPIBARIBE", "nivel": 177.0,
             "cota_pre_alerta": 600.0, "cota_alerta": 650.0, "cota_inundacao": 750.0},
            {**base, "codigo_estacao": "260790115", "estacao": "VILA NATAL", "rio": "RIO JABOATÃO", "nivel": 345.0,
             "cota_pre_alerta": 320.0, "cota_alerta": 340.0, "cota_inundacao": 440.0},
        ]

    def serie_rio(self, codigo, desde):
        return [{"data_hora": AGORA, "nivel": 177.0}]

    def estacao_existe(self, codigo):
        return codigo in ("39145010", "260790115")

    def arboviroses_por_semana(self, agravo=None):
        linhas = [{"semana": 202533, "agravo": "dengue", "notificacoes": 400, "nao_descartadas": 250},
                  {"semana": 202533, "agravo": "zika", "notificacoes": 20, "nao_descartadas": 15}]
        return [l for l in linhas if agravo in (None, l["agravo"])]

    def arboviroses_por_bairro_bruto(self):
        return [{"bairro": "PINA", "agravo": "dengue", "notificacoes": 30},
                {"bairro": "Pina", "agravo": "zika", "notificacoes": 2},
                {"bairro": "JIQU]", "agravo": "dengue", "notificacoes": 1}]

    def bairros(self):
        return [{"chave_bairro": "PINA", "nome_bairro": "Pina", "rpa": 6, "distrito_sanitario": 6, "descricao_distrito": "DS VI"},
                {"chave_bairro": "TORRE", "nome_bairro": "Torre", "rpa": 4, "distrito_sanitario": 4, "descricao_distrito": "DS IV"}]

    def distritos(self):
        return [{"distrito_sanitario": 6, "descricao_distrito": "DS VI", "bairros": 5}]

    def areas_alagaveis(self, distrito=None):
        self.chamadas.append(("areas_alagaveis", distrito))
        return [{"id_area": "1", "codigo": 106, "distrito_sanitario": 8, "area_m2": 170446.76,
                 "geometria_geojson": '{"type":"Polygon","coordinates":[[[-34.93,-8.1],[-34.92,-8.1],[-34.92,-8.11],[-34.93,-8.1]]]}'}]

    def pontos_alagamento(self):
        return [{"id_ponto": "1", "bairro": "ILHA JOANA BEZERRA", "rpa": 1, "logradouro": "RUA JARAGUARI", "trecho": None,
                 "status": "CONCLUÍDO", "classificacao": "RESOLVIDO", "percentual_concluido": 1.0,
                 "inicio_intervencao": date(2015, 12, 1), "termino_intervencao": None,
                 "longitude": -34.897, "latitude": -8.0714}]

    def ultimas_cargas(self):
        return [{"tabela": "cop_indicadores", "carregado_em": datetime(2026, 10, 28, 21, 5, tzinfo=timezone.utc), "linhas": 27}]


CONFIG = Configuracao(neon_url="postgresql://teste:x@localhost/teste", origens_cors=("http://localhost:5173",), cache_segundos=300)


@pytest.fixture
def repo():
    return RepositorioFalso()


@pytest.fixture
def cliente(repo):
    with TestClient(criar_app(CONFIG, repo), raise_server_exceptions=False) as c:
        yield c
