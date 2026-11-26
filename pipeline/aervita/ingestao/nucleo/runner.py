"""Execução de coletores: grava a RAW sem transformação e registra cada execução."""

import argparse
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
import json
from pathlib import Path
import re
from uuid import uuid4

from aervita.ambiente import DIR_DADOS
from aervita.ingestao.nucleo import armazenamento as armaz
from aervita.ingestao.nucleo.armazenamento import FUSO_RECIFE


@dataclass(frozen=True)
class Coletor:
    """Devolve os bytes originais da fonte e conta os registros, sem alterar a RAW."""

    coletar: Callable[[date], bytes]
    contar_registros: Callable[[bytes], int]
    nome_arquivo: str
    suporta_historico: bool = True


def _hoje() -> date:
    return datetime.now(FUSO_RECIFE).date()


def coletar_dummy(data_coleta: date) -> bytes:
    """Fonte sintética para testes, sem rede."""
    return json.dumps([{"data": data_coleta.isoformat(), "simulado": True}]).encode()


def _coletor_de_modulo(modulo: str, nome_arquivo: str) -> Coletor:
    """Coletor de uma fonte em aervita.ingestao.fontes, importada só quando usada."""

    def fonte():
        from importlib import import_module
        return import_module(f"aervita.ingestao.fontes.{modulo}")

    return Coletor(lambda data: fonte().coletar_dados(data), lambda conteudo: fonte().contar_registros(conteudo),
                   nome_arquivo, suporta_historico=False)


def _coletor_cop(camada: str) -> Coletor:
    """Uma camada do COP Recife como fonte própria. O ArcGIS só devolve o estado atual."""

    def coletar(data_coleta: date) -> bytes:
        from aervita.ingestao.fontes import cop_recife
        return cop_recife.coletar_dados(camada, data_coleta)

    def contar(conteudo: bytes) -> int:
        from aervita.ingestao.fontes import cop_recife
        return cop_recife.contar_registros(conteudo)

    return Coletor(coletar, contar, "arcgis.json", suporta_historico=False)


FONTES_COP = (
    "cop_indicadores", "cop_rios", "cop_previsao_chuva", "cop_chuva_mensal",
    "cop_pluviometros", "cop_areas_alagaveis", "cop_pontos_alagamento",
    "cop_mare", "cop_alagamento_rotas", "cop_rotas",
)

COLETORES = {
    "dummy": Coletor(coletar_dummy, lambda conteudo: len(json.loads(conteudo)), "dummy.json"),
    "epidemiologia": _coletor_de_modulo("epidemiologia", "datastore_search.json"),
    "territorio": _coletor_de_modulo("territorio", "territorio.json"),
    **{camada: _coletor_cop(camada) for camada in FONTES_COP},
}


def executar(
    fonte: str,
    data_coleta: date | None = None,
    *,
    diretorio_dados: Path = DIR_DADOS,
    coletores: Mapping[str, Coletor] | None = None,
    armazenamento: armaz.ArmazenamentoRaw | None = None,
) -> dict:
    """Coleta (ou relê a RAW de uma data explícita) e registra sucesso ou falha.

    Sem `armazenamento`, grava em arquivo: nunca consulta o ambiente aqui, para
    os testes não caírem no MongoDB por causa de um .env.
    """
    if armazenamento is None:
        armazenamento = armaz.ArmazenamentoArquivo(diretorio_dados)
    inicio = datetime.now(FUSO_RECIFE)
    data_particao = data_coleta if data_coleta is not None else inicio.date()
    registro = {
        "id": uuid4().hex,
        "fonte": fonte,
        "inicio": inicio.strftime("%Y-%m-%d %H:%M:%S"),
        "fim": None,
        "data_coleta": data_particao.isoformat(),
        "numero_registros": 0,
        "status": "erro",
        "mensagem": "",
    }
    try:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", fonte):
            raise ValueError("Nome de fonte deve usar snake_case sem acento")
        catalogo = COLETORES if coletores is None else coletores
        if fonte not in catalogo:
            raise ValueError(f"Coletor nao registrado: {fonte}")
        coletor = catalogo[fonte]
        if not re.fullmatch(r"[a-z0-9_]+\.(json|csv)", coletor.nome_arquivo):
            raise ValueError("Arquivo RAW deve ter nome simples e extensao json ou csv")
        existente = (armazenamento.ler(fonte, data_particao, coletor.nome_arquivo)
                     if data_coleta is not None else None)
        reutilizar = existente is not None
        if (not reutilizar and not coletor.suporta_historico
                and data_coleta is not None and data_coleta != _hoje()):
            raise ValueError(
                f"Fonte '{fonte}' não tem histórico por data: com --data só é possível "
                f"reler uma RAW já gravada, e "
                f"{armazenamento.descrever(fonte, data_particao, coletor.nome_arquivo)} não existe. "
                f"Para coletar o estado atual, rode sem --data."
            )
        conteudo = existente if reutilizar else coletor.coletar(data_particao)
        if not isinstance(conteudo, bytes):
            raise TypeError("Coletor deve devolver bytes originais")
        quantidade = coletor.contar_registros(conteudo)
        if type(quantidade) is not int or quantidade < 0:
            raise ValueError("Contagem de registros deve ser inteiro nao negativo")
        alterou = False if reutilizar else armazenamento.gravar(
            fonte, data_particao, coletor.nome_arquivo, conteudo)
        registro.update(
            numero_registros=quantidade,
            status="ok",
            mensagem=("RAW existente relida" if reutilizar
                      else "Coleta concluida" if alterou
                      else "Coleta concluida; conteudo identico ao ja gravado"),
        )
    except Exception as erro:
        registro["mensagem"] = f"{type(erro).__name__}: {erro}"
    registro["fim"] = datetime.now(FUSO_RECIFE).strftime("%Y-%m-%d %H:%M:%S")
    armazenamento.registrar_execucao(registro)
    return registro


def interpretar_data(valor: str) -> date:
    """Data no formato estrito AAAA-MM-DD, para o argumento --data."""
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
            raise ValueError
        return date.fromisoformat(valor)
    except ValueError as erro:
        raise argparse.ArgumentTypeError("Use uma data valida no formato AAAA-MM-DD") from erro


def main(argv: list[str] | None = None) -> int:
    argumentos = argparse.ArgumentParser(prog="aervita coletar", description=__doc__)
    argumentos.add_argument("fonte", help="Nome do coletor registrado (teste: dummy)")
    argumentos.add_argument("--data", type=interpretar_data, dest="data_coleta")
    argumentos.add_argument("--diretorio-dados", type=Path, default=DIR_DADOS)
    argumentos.add_argument("--armazenamento", choices=armaz.TIPOS, default=None,
                            help="Onde gravar a RAW; padrão: AERVITA_ARMAZENAMENTO ou arquivo")
    opcoes = argumentos.parse_args(argv)
    try:
        registro = executar(
            opcoes.fonte, opcoes.data_coleta, diretorio_dados=opcoes.diretorio_dados,
            armazenamento=armaz.criar(opcoes.armazenamento, opcoes.diretorio_dados),
        )
    except OSError as erro:
        argumentos.exit(1, f"Falha ao persistir registro de execucao: {erro}\n")
    print(json.dumps(registro, ensure_ascii=False))
    return 0 if registro["status"] == "ok" else 1
