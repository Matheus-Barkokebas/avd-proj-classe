"""Camada Gold no Neon (decisão 0003): dados finais do painel e do modelo.

Bronze é a RAW no Atlas; Silver são as tabelas do schema `public`, validadas
pelos contratos. A Gold fica no schema `gold` e é a única camada que a API lê:

- views sobre a Silver, sempre atuais sem precisar de carga;
- tabelas reconstruídas aqui (base do modelo de alagamento, arboviroses por bairro
  e semana e suas referências).
  As cargas de arboviroses já chamam este script ao terminar.

Rodar de novo não duplica nada.
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import yaml

# Executado como script, o Python não põe a raiz do projeto no sys.path (BUG-02).
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestao import contratos
from src.ingestao import padronizada
from src.ingestao.territorio import chave_bairro
from src.processamento import gold_alagamento

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
CAMINHO_CONFIG = RAIZ_PROJETO / "conf" / "gold.yml"

TABELA_HISTORICO = "epidemiologia_historico"
CONTRATOS_ALAGAMENTO = ("inmet_chuva", "cop_mare", "cop_alagamento_rotas")

DDL_TABELAS = """
CREATE SCHEMA IF NOT EXISTS gold;
CREATE TABLE IF NOT EXISTS gold.de_para_bairro (
    bairro_fonte text PRIMARY KEY,
    chave_bairro text
);
CREATE TABLE IF NOT EXISTS gold.classificacao (
    agravo text NOT NULL,
    codigo text NOT NULL,
    descricao text NOT NULL,
    situacao text NOT NULL,
    PRIMARY KEY (agravo, codigo)
);
CREATE TABLE IF NOT EXISTS gold.previsao_alagamento (
    hora timestamp NOT NULL,
    hora_prevista timestamp NOT NULL,
    conjunto text NOT NULL,
    probabilidade double precision NOT NULL,
    previsto integer NOT NULL,
    observado integer,
    modelo text NOT NULL,
    gerado_em timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (hora, modelo)
);
"""

# Tirar as colunas de controle e limpar o texto "Não Informado" do COP é o que separa estas views da Silver.
VIEWS = {
    "chuva_hora": """
        SELECT data_hora, estagio, chuva_media_1h_mm, chuva_max_1h_mm,
               NULLIF(estacao_max_1h, 'Não Informado') AS estacao_max_1h,
               chuva_media_24h_mm, chuva_max_24h_mm,
               NULLIF(estacao_max_24h, 'Não Informado') AS estacao_max_24h,
               mare_m, sentido_mare, alagamentos, ocorrencias, ocorrencias_1h, abrigos, abrigados
        FROM public.cop_indicadores""",
    "chuva_inmet_hora": """
        SELECT estacao, data_hora, chuva_mm FROM public.inmet_chuva""",
    "mare": """
        SELECT data_hora, mare_m FROM public.cop_mare""",
    "alagamento_rota": """
        SELECT id_evento, cod_rota, rota, data_hora, alagamentos FROM public.cop_alagamento_rotas""",
    "chuva_mensal": """
        SELECT ano_referencia, mes, chuva_ano_atual_mm, chuva_ano_anterior_mm, media_historica_mm
        FROM public.cop_chuva_mensal""",
    "previsao_chuva": """
        SELECT data_hora_prevista, chuva_gfs_mm, chuva_ecmwf_mm, chuva_icon_mm, chuva_wrf_mm
        FROM public.cop_previsao_chuva""",
    "rio_leitura": """
        SELECT codigo_estacao, estacao, rio, data_hora, nivel, cota_pre_alerta, cota_alerta, cota_inundacao, situacao
        FROM public.cop_rios""",
    "bairro": """
        SELECT b.chave_bairro, b.nome_bairro, b.rpa, b.distrito_sanitario, d.descricao_distrito
        FROM public.dim_bairro b LEFT JOIN public.dim_distrito d USING (distrito_sanitario)""",
    "bairro_geo": """
        SELECT g.chave_bairro, b.nome_bairro, b.rpa, b.distrito_sanitario, d.descricao_distrito,
               g.area_km2, g.geometria_geojson
        FROM public.geo_bairro g LEFT JOIN public.dim_bairro b USING (chave_bairro)
        LEFT JOIN public.dim_distrito d USING (distrito_sanitario)""",
    "distrito": """
        SELECT d.distrito_sanitario, d.descricao_distrito, count(b.chave_bairro) AS bairros
        FROM public.dim_distrito d LEFT JOIN public.dim_bairro b USING (distrito_sanitario)
        GROUP BY 1, 2""",
    "area_alagavel": """
        SELECT id_area, codigo, distrito_sanitario, area_m2, geometria_geojson
        FROM public.cop_areas_alagaveis""",
    "ponto_alagamento": """
        SELECT id_ponto, bairro, rpa, logradouro, trecho, status, classificacao, percentual_concluido,
               inicio_intervencao, termino_intervencao, longitude, latitude
        FROM public.cop_pontos_alagamento""",
    "ultima_carga": " UNION ALL ".join(
        f"SELECT '{t}' AS tabela, max(carregado_em) AS carregado_em, count(*) AS linhas FROM public.{t}"
        for t in ("cop_indicadores", "cop_rios", "cop_previsao_chuva", "cop_chuva_mensal", "epidemiologia",
                  "cop_areas_alagaveis", "cop_pontos_alagamento")
    ),
}

# Tabela, não view: agregar cerca de 180 mil notificações a cada pedido deixaria a API lenta.
# A carga corrente tem prioridade quando a mesma notificação também aparece no histórico.
TABELA_ARBO = """
CREATE TABLE gold.arbo_bairro_semana AS
WITH notificacoes AS (
    SELECT agravo, ano, semana_epidemiologica, bairro, classificacao_final FROM public.epidemiologia
    UNION ALL
    SELECT h.agravo, h.ano, h.semana_epidemiologica, h.bairro, h.classificacao_final
    FROM public.epidemiologia_historico h
    WHERE NOT EXISTS (SELECT 1 FROM public.epidemiologia e WHERE e.agravo = h.agravo
                      AND e.protocolo = h.protocolo AND e.data_notificacao = h.data_notificacao)
)
SELECT n.ano, n.semana_epidemiologica AS semana, d.chave_bairro,
       CASE WHEN d.chave_bairro IS NULL THEN n.bairro END AS bairro_nao_reconhecido,
       n.agravo,
       count(*) AS notificacoes,
       count(*) FILTER (WHERE c.situacao IS DISTINCT FROM 'descartado') AS nao_descartadas,
       count(*) FILTER (WHERE c.situacao = 'confirmado') AS confirmadas
FROM notificacoes n
LEFT JOIN gold.de_para_bairro d ON d.bairro_fonte = n.bairro
LEFT JOIN gold.classificacao c ON c.agravo = n.agravo AND c.codigo = n.classificacao_final
GROUP BY 1, 2, 3, 4, 5;
CREATE INDEX ix_arbo_ano ON gold.arbo_bairro_semana (ano);
CREATE INDEX ix_arbo_bairro_semana ON gold.arbo_bairro_semana (chave_bairro, semana);
"""


def carregar_configuracao(caminho: Path = CAMINHO_CONFIG) -> dict[str, Any]:
    with caminho.open(encoding="utf-8") as arquivo:
        return yaml.safe_load(arquivo)


def mapear_bairros(fontes: list[str], validos: set[str], apelidos: dict[str, str]) -> list[tuple[str, str | None]]:
    """Cada grafia da fonte -> chave de dim_bairro, ou None quando não há correspondência."""
    resultado = []
    for fonte in fontes:
        chave = chave_bairro(fonte)
        chave = apelidos.get(chave, chave)
        resultado.append((fonte, chave if chave in validos else None))
    return resultado


def linhas_classificacao(config: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    return [(agravo, str(codigo), item["descricao"], item["situacao"])
            for agravo, codigos in config["classificacao"].items() for codigo, item in codigos.items()]


def construir(destino: padronizada.DestinoNeon, config: dict[str, Any]) -> dict[str, Any]:
    """Recria a Gold numa transação só: se algo falhar, a Gold anterior continua de pé."""
    with destino.conexao() as conexao, conexao.cursor() as cur:
        cur.execute(DDL_TABELAS)
        contrato = contratos.carregar_contrato("epidemiologia")
        cur.execute(padronizada.ddl_tabela({**contrato, "tabela": TABELA_HISTORICO}))
        for nome in CONTRATOS_ALAGAMENTO:
            cur.execute(padronizada.ddl_tabela(contratos.carregar_contrato(nome)))
        cur.execute(f"SELECT bairro FROM public.epidemiologia UNION SELECT bairro FROM public.{TABELA_HISTORICO}")
        fontes = [linha[0] for linha in cur.fetchall()]
        cur.execute("SELECT chave_bairro FROM public.dim_bairro")
        validos = {linha[0] for linha in cur.fetchall()}
        de_para = mapear_bairros(fontes, validos, config.get("apelidos_bairro") or {})

        cur.execute("DELETE FROM gold.de_para_bairro")
        with cur.copy("COPY gold.de_para_bairro (bairro_fonte, chave_bairro) FROM STDIN") as dados:
            for linha in de_para:
                dados.write_row(linha)
        cur.execute("DELETE FROM gold.classificacao")
        with cur.copy("COPY gold.classificacao (agravo, codigo, descricao, situacao) FROM STDIN") as dados:
            for linha in linhas_classificacao(config):
                dados.write_row(linha)

        for nome, consulta in VIEWS.items():
            cur.execute(f"DROP VIEW IF EXISTS gold.{nome}")
            cur.execute(f"CREATE VIEW gold.{nome} AS {consulta}")
        cur.execute("DROP TABLE IF EXISTS gold.arbo_bairro_semana")
        cur.execute(TABELA_ARBO)
        base_modelo = gold_alagamento.construir(cur, config["alagamento"])

        papel = padronizada._ident(config["papel_leitura"])
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (papel,))
        if cur.fetchone():
            cur.execute(f"GRANT USAGE ON SCHEMA gold TO {papel}")
            cur.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA gold TO {papel}")
            cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO {papel}")

    return {
        "views": sorted(VIEWS),
        "base_modelo_alagamento": base_modelo,
        "grafias_de_bairro": len(de_para),
        "grafias_nao_reconhecidas": sorted(fonte for fonte, chave in de_para if chave is None),
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    resultado = construir(padronizada.DestinoNeon.do_ambiente(), carregar_configuracao())
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
