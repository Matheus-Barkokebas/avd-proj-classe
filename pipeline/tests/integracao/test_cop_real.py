"""COP Recife de verdade: o ArcGIS público ainda responde no formato esperado.

Opcional: roda só com `pytest -m integracao`. Não grava nada — só consulta e
confere que as linhas passam no contrato. Se a prefeitura mudar um campo,
este teste é o primeiro a avisar.
"""

from datetime import date

import pytest

from src.ingestao import contratos
from src.ingestao import cop_recife

pytestmark = pytest.mark.integracao


@pytest.mark.parametrize("fonte", ["cop_indicadores", "cop_rios", "cop_previsao_chuva", "cop_chuva_mensal"])
def test_camada_real_passa_no_contrato(fonte):
    import json

    bruto = json.loads(cop_recife.coletar_dados(fonte, date.today()))
    assert bruto["features"], f"{fonte}: a camada veio vazia"
    linhas = cop_recife.transformar(bruto, cop_recife.carregar_configuracao_fonte()["camadas"][fonte], date.today())
    violacoes = contratos.validar(linhas, contratos.carregar_contrato(fonte))
    assert not [v for v in violacoes if v.linha is None], "violação de lote: a fonte mudou de formato"
    assert len({v.linha for v in violacoes}) < len(linhas), "todas as linhas rejeitadas"
