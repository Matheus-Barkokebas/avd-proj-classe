"""Testes automatizados para o módulo de contratos de dados (FND-02).

Sem chamadas à rede; utiliza apenas dados mockados e arquivos de contrato do repositório.
"""

from datetime import datetime
from pathlib import Path
import pytest

from src.ingestao.contratos import Violacao, carregar_contrato, validar


CONTRATO_SIMPLES = {
    "tabela": "teste_simples",
    "chave_negocio": ["id"],
    "campo_data_referencia": "data_evento",
    "campos": [
        {"nome": "id", "tipo": "int", "obrigatorio": True, "descricao": "ID único"},
        {"nome": "nome", "tipo": "string", "obrigatorio": True, "descricao": "Nome da entidade"},
        {"nome": "valor", "tipo": "float", "obrigatorio": True, "descricao": "Valor numérico"},
        {"nome": "data_evento", "tipo": "datetime", "obrigatorio": True, "descricao": "Data e hora"},
        {"nome": "categoria", "tipo": "string", "obrigatorio": True, "valores_permitidos": ["alta", "baixa"]},
        {"nome": "observacao", "tipo": "string", "obrigatorio": False, "descricao": "Campo opcional"},
    ],
}


def test_validar_lote_valido_retorna_vazio():
    """Lote em conformidade estrita com o contrato deve retornar lista vazia."""
    lote = [
        {
            "id": 1,
            "nome": "Registro A",
            "valor": 12.5,
            "data_evento": "2026-09-15 14:00:00",
            "categoria": "alta",
            "observacao": "Tudo certo",
        },
        {
            "id": 2,
            "nome": "Registro B",
            "valor": 0.0,
            "data_evento": datetime(2026, 9, 15, 14, 30),
            "categoria": "BAIXA",  # case-insensitive
            "observacao": None,  # opcional com nulo é válido
        },
    ]
    violacoes = validar(lote, CONTRATO_SIMPLES)
    assert violacoes == []


def test_validar_coluna_faltante():
    """Coluna obrigatória ausente em todo o lote gera violação de coluna_faltante."""
    lote = [
        {
            "id": 1,
            # "nome" está ausente!
            "valor": 10.0,
            "data_evento": "2026-09-15 10:00:00",
            "categoria": "alta",
        }
    ]
    violacoes = validar(lote, CONTRATO_SIMPLES)
    colunas_faltantes = [v for v in violacoes if v.tipo == "coluna_faltante"]

    assert len(colunas_faltantes) == 1
    assert colunas_faltantes[0].campo == "nome"
    assert colunas_faltantes[0].linha is None
    assert "Coluna obrigatória 'nome' não encontrada" in colunas_faltantes[0].mensagem


def test_validar_tipo_errado():
    """Valores com tipos incompatíveis com o contrato geram violação tipo_errado."""
    lote = [
        {
            "id": "nao_sou_inteiro",  # tipo errado: string em int
            "nome": "Registro X",
            "valor": "cem",           # tipo errado: string em float
            "data_evento": "data_invalida",  # tipo errado: string não parseável como datetime
            "categoria": "alta",
        }
    ]
    violacoes = validar(lote, CONTRATO_SIMPLES)
    tipos_errados = [v for v in violacoes if v.tipo == "tipo_errado"]

    campos_com_tipo_errado = {v.campo for v in tipos_errados}
    assert "id" in campos_com_tipo_errado
    assert "valor" in campos_com_tipo_errado
    assert "data_evento" in campos_com_tipo_errado
    assert all(v.linha == 1 for v in tipos_errados)


def test_validar_booleano_rejeitado_em_inteiro_e_float():
    """Em Python bool herda de int, mas não deve ser aceito como int ou float."""
    lote = [
        {
            "id": True,  # booleano em campo int
            "nome": "Registro",
            "valor": False,  # booleano em campo float
            "data_evento": "2026-09-15 10:00:00",
            "categoria": "alta",
        }
    ]
    violacoes = validar(lote, CONTRATO_SIMPLES)
    tipos_errados = [v for v in violacoes if v.tipo == "tipo_errado"]
    campos = {v.campo for v in tipos_errados}
    assert "id" in campos
    assert "valor" in campos


def test_validar_nulo_em_campo_obrigatorio():
    """Valor nulo (None ou NaN) em campo obrigatório gera violação nulo_obrigatorio."""
    lote = [
        {
            "id": 1,
            "nome": None,  # nulo em campo obrigatório
            "valor": float("nan"),  # NaN em campo obrigatório
            "data_evento": "2026-09-15 10:00:00",
            "categoria": "alta",
        }
    ]
    violacoes = validar(lote, CONTRATO_SIMPLES)
    nulos = [v for v in violacoes if v.tipo == "nulo_obrigatorio"]

    campos_nulos = {v.campo for v in nulos}
    assert "nome" in campos_nulos
    assert "valor" in campos_nulos
    assert all(v.linha == 1 for v in nulos)


def test_validar_campo_opcional_aceita_nulos():
    """Campos marcados com obrigatorio: False podem ter None sem gerar violação."""
    lote = [
        {
            "id": 1,
            "nome": "Valido",
            "valor": 5.0,
            "data_evento": "2026-09-15 10:00:00",
            "categoria": "alta",
            "observacao": None,
        }
    ]
    violacoes = validar(lote, CONTRATO_SIMPLES)
    assert violacoes == []


def test_validar_campo_opcional_ausente_nao_gera_coluna_faltante():
    """Coluna com obrigatorio: False não deve ser reportada como coluna_faltante se omitida."""
    lote = [
        {
            "id": 1,
            "nome": "Valido",
            "valor": 5.0,
            "data_evento": "2026-09-15 10:00:00",
            "categoria": "alta",
            # observacao omitida
        }
    ]
    violacoes = validar(lote, CONTRATO_SIMPLES)
    assert violacoes == []


def test_validar_dominio_valores_permitidos():
    """Valor fora da lista de valores_permitidos gera violação valor_invalido."""
    lote = [
        {
            "id": 1,
            "nome": "Registro",
            "valor": 1.0,
            "data_evento": "2026-09-15 10:00:00",
            "categoria": "invalida",  # esperado: alta ou baixa
        }
    ]
    violacoes = validar(lote, CONTRATO_SIMPLES)
    invalidos = [v for v in violacoes if v.tipo == "valor_invalido"]
    assert len(invalidos) == 1
    assert invalidos[0].campo == "categoria"
    assert invalidos[0].valor == "invalida"
    assert invalidos[0].linha == 1


def test_violacao_dataclass_acesso_e_serializacao():
    """Violacao suporta acesso por atributo, acesso por chave e conversão para dict."""
    v = Violacao(tipo="coluna_faltante", campo="teste", mensagem="Msg", linha=2, valor=123)
    assert v.tipo == "coluna_faltante"
    assert v["campo"] == "teste"
    assert v["linha"] == 2
    d = v.para_dict()
    assert d["tipo"] == "coluna_faltante"
    assert d["valor"] == 123
    with pytest.raises(KeyError):
        _ = v["chave_inexistente"]


def test_carregar_contrato_sucesso():
    """Carregamento por nome lógico e por caminho direto."""
    c1 = carregar_contrato("epidemiologia")
    assert c1["tabela"] == "epidemiologia"
    assert len(c1["campos"]) > 0

    caminho = Path("conf/contracts/ocorrencias.yml")
    c2 = carregar_contrato(caminho)
    assert c2["tabela"] == "ocorrencias"


def test_carregar_contrato_inexistente():
    """Tentativa de carregar contrato inexistente lança FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        carregar_contrato("fonte_totalmente_inexistente")


def test_validar_lote_vazio():
    """Lote vazio retorna lista vazia de violações."""
    assert validar([], CONTRATO_SIMPLES) == []


def test_validar_tipo_entrada_invalida():
    """Entradas com tipo incompatível lançam TypeError."""
    with pytest.raises(TypeError):
        validar("nao_sou_lista_nem_dict", CONTRATO_SIMPLES)

    with pytest.raises(TypeError):
        validar([{"id": 1}], 12345)


# ---------------------------------------------------------------------------
# Testes com os 5 contratos reais do repositório (conf/contracts/*.yml)
# ---------------------------------------------------------------------------

def test_contrato_real_epidemiologia_valido_e_invalido():
    contrato = carregar_contrato("epidemiologia")
    lote_valido = [
        {
            "protocolo": "NOT-2026-001",
            "data_notificacao": "2026-09-01 10:00:00",
            "semana_epidemiologica": 202635,
            "ano": 2026,
            "bairro": "Boa Vista",
            "agravo": "dengue",
            "classificacao_final": "confirmado",
            "contagem": 1,
        }
    ]
    assert validar(lote_valido, contrato) == []

    # Violação 1: coluna obrigatória faltante
    lote_sem_coluna = [{"protocolo": "NOT-001"}]
    violacoes = validar(lote_sem_coluna, contrato)
    tipos = {v.tipo for v in violacoes}
    assert "coluna_faltante" in tipos

    # Violação 2: agravo fora do domínio permitido
    lote_agravo_invalido = [
        {
            **lote_valido[0],
            "agravo": "febre_amarela",
        }
    ]
    violacoes_agravo = validar(lote_agravo_invalido, contrato)
    assert any(v.tipo == "valor_invalido" and v.campo == "agravo" for v in violacoes_agravo)


def test_contrato_real_ocorrencias_valido_e_invalido():
    contrato = carregar_contrato("ocorrencias")
    lote_valido = [
        {
            "protocolo": "OCO-2026-1234",
            "data_ocorrencia": "2026-09-02 08:30:00",
            "tipo_ocorrencia": "deslizamento",
            "bairro": "Ibura",
            "latitude": -8.12345,
            "longitude": -34.98765,
            "status": "em_atendimento",
            "descricao": "Deslizamento de barreira sem vítimas",
        },
        {
            "protocolo": "OCO-2026-1235",
            "data_ocorrencia": "2026-09-02 09:00:00",
            "tipo_ocorrencia": "alagamento",
            "bairro": "Afogados",
            "latitude": None,  # opcional
            "longitude": None,  # opcional
            "status": "concluida",
            "descricao": None,
        }
    ]
    assert validar(lote_valido, contrato) == []

    # Nulo em campo obrigatório
    lote_nulo = [{**lote_valido[0], "tipo_ocorrencia": None}]
    violacoes = validar(lote_nulo, contrato)
    assert any(v.tipo == "nulo_obrigatorio" and v.campo == "tipo_ocorrencia" for v in violacoes)


def test_contrato_real_ana_nivel_valido_e_invalido():
    contrato = carregar_contrato("ana_nivel")
    lote_valido = [
        {
            "codigo_estacao": "39130000",
            "data_hora_medicao": "2026-09-01 12:00:00",
            "nivel_cm": 245.5,
            "vazao_m3s": 12.8,
            "status_leitura": "consistido",
        }
    ]
    assert validar(lote_valido, contrato) == []

    # Tipo incorreto em nível (string em float)
    lote_tipo_errado = [{**lote_valido[0], "nivel_cm": "duzentos"}]
    violacoes = validar(lote_tipo_errado, contrato)
    assert any(v.tipo == "tipo_errado" and v.campo == "nivel_cm" for v in violacoes)


def test_contrato_real_ana_chuva_valido_e_invalido():
    contrato = carregar_contrato("ana_chuva")
    lote_valido = [
        {
            "codigo_estacao": "00834001",
            "data_hora_medicao": "2026-09-01 12:00:00",
            "chuva_mm": 18.4,
            "status_leitura": "bruto",
        }
    ]
    assert validar(lote_valido, contrato) == []

    # Coluna faltante: chuva_mm ausente
    lote_incompleto = [
        {
            "codigo_estacao": "00834001",
            "data_hora_medicao": "2026-09-01 12:00:00",
        }
    ]
    violacoes = validar(lote_incompleto, contrato)
    assert any(v.tipo == "coluna_faltante" and v.campo == "chuva_mm" for v in violacoes)


def test_contrato_real_territorio_valido_e_invalido():
    contrato = carregar_contrato("territorio")
    lote_valido = [
        {
            "codigo_bairro": 24,
            "nome_bairro": "Pina",
            "rpa": 6,
            "distrito_sanitario": 6,
            "populacao": 30500,
            "area_km2": 4.12,
            "data_atualizacao": "2026-01-01",
        }
    ]
    assert validar(lote_valido, contrato) == []

    # Nulo em código_bairro (obrigatório)
    lote_nulo = [{**lote_valido[0], "codigo_bairro": None}]
    violacoes = validar(lote_nulo, contrato)
    assert any(v.tipo == "nulo_obrigatorio" and v.campo == "codigo_bairro" for v in violacoes)


@pytest.mark.parametrize("vazio", ["", "   ", "\t"])
def test_texto_vazio_em_campo_obrigatorio_e_nulo(vazio):
    """BUG-08: "" (comum no CKAN) não pode passar como valor preenchido."""
    contrato = {"tabela": "t", "campos": [{"nome": "bairro", "tipo": "string", "obrigatorio": True}]}
    violacoes = validar([{"bairro": vazio}], contrato)
    assert [v.tipo for v in violacoes] == ["nulo_obrigatorio"]


def test_texto_vazio_em_campo_opcional_e_aceito():
    contrato = {"tabela": "t", "campos": [{"nome": "descricao", "tipo": "string", "obrigatorio": False}]}
    assert validar([{"descricao": ""}], contrato) == []


def test_chave_negocio_epidemiologia_inclui_agravo_e_data():
    """BUG-07: protocolo sozinho se repete entre agravos e dentro do mesmo agravo."""
    contrato = carregar_contrato("epidemiologia")
    assert contrato["chave_negocio"] == ["agravo", "protocolo", "data_notificacao"]
    nomes_campos = {c["nome"] for c in contrato["campos"]}
    assert set(contrato["chave_negocio"]) <= nomes_campos  # chave só com campos do contrato
