"""Execução de coletores e persistência de RAW sem transformação (FND-03)."""

import argparse
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
import json
from pathlib import Path
import re
from uuid import uuid4
import sys

# Executado como script (`python src/ingestao/<modulo>.py`), o Python põe
# src/ingestao/ no sys.path em vez da raiz do projeto — sem isto os imports
# `src.*` falham com ModuleNotFoundError (BUG-02).
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


from src.ingestao import armazenamento as armaz
# Reexportados: bronze.py e territorio.py usam runner.gravar_atomico.
from src.ingestao.armazenamento import FUSO_RECIFE, gravar_atomico  # noqa: F401

RAIZ_PROJETO = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Coletor:
    """Contrato: devolver bytes originais e contar registros sem alterar a RAW."""

    coletar: Callable[[date], bytes]
    contar_registros: Callable[[bytes], int]
    nome_arquivo: str
    # Fonte que só devolve o estado atual (não consulta por data) não pode
    # coletar para outra data: gravaria o retrato de hoje com a data errada.
    # Para ela, --data só relê uma RAW já gravada (BUG-09).
    suporta_historico: bool = True


def _hoje() -> date:
    """Data corrente em America/Recife (isolada para os testes poderem fixá-la)."""
    return datetime.now(FUSO_RECIFE).date()


def coletar_dummy(data_coleta: date) -> bytes:
    """Fonte sintética exclusiva para testes e demonstração local, sem rede."""
    return json.dumps([{"data": data_coleta.isoformat(), "simulado": True}]).encode()


def coletar_epidemiologia(data_coleta: date) -> bytes:
    """Invoca o coletor de arboviroses da API CKAN do Recife."""
    from src.ingestao import epidemiologia

    return epidemiologia.coletar_dados(data_coleta)


def contar_epidemiologia(conteudo: bytes) -> int:
    """Contagem de registros do payload combinado de arboviroses."""
    from src.ingestao import epidemiologia

    return epidemiologia.contar_registros(conteudo)


def coletar_ocorrencias(data_coleta: date) -> bytes:
    """Invoca o coletor de ocorrências/Defesa Civil (SEDEC) da API CKAN do Recife."""
    from src.ingestao import ocorrencias

    return ocorrencias.coletar_dados(data_coleta)


def contar_ocorrencias(conteudo: bytes) -> int:
    """Contagem de registros do payload de ocorrências."""
    from src.ingestao import ocorrencias

    return ocorrencias.contar_registros(conteudo)


def coletar_ana_chuva(data_coleta: date) -> bytes:
    """Invoca o coletor de chuva das estações ANA (HidroWebService)."""
    from src.ingestao import ana_hidroweb

    return ana_hidroweb.coletar_dados_chuva(data_coleta)


def coletar_ana_nivel(data_coleta: date) -> bytes:
    """Invoca o coletor de nível/vazão das estações ANA (HidroWebService)."""
    from src.ingestao import ana_hidroweb

    return ana_hidroweb.coletar_dados_nivel(data_coleta)


def contar_ana_hidroweb(conteudo: bytes) -> int:
    """Contagem de registros do payload combinado de estações ANA (chuva ou nível)."""
    from src.ingestao import ana_hidroweb

    return ana_hidroweb.contar_registros(conteudo)


def coletar_territorio(data_coleta: date) -> bytes:
    """Invoca o coletor das bases cadastrais territoriais do Recife."""
    from src.ingestao import territorio

    return territorio.coletar_dados(data_coleta)


def contar_territorio(conteudo: bytes) -> int:
    """Contagem combinada das bases territoriais (linhas tabulares + 1 por arquivo geométrico)."""
    from src.ingestao import territorio

    return territorio.contar_registros(conteudo)


def _coletor_cop(fonte: str) -> Coletor:
    """Uma camada do COP Recife (conf/sources/cop_recife.yml) como fonte do runner."""

    def coletar(data_coleta: date) -> bytes:
        from src.ingestao import cop_recife

        return cop_recife.coletar_dados(fonte, data_coleta)

    def contar(conteudo: bytes) -> int:
        from src.ingestao import cop_recife

        return cop_recife.contar_registros(conteudo)

    # O ArcGIS do COP só devolve o estado atual (sem consulta por data).
    return Coletor(coletar, contar, "arcgis.json", suporta_historico=False)


# Mantida igual às camadas de conf/sources/cop_recife.yml (há teste que confere).
FONTES_COP = (
    "cop_indicadores", "cop_rios", "cop_previsao_chuva", "cop_chuva_mensal",
    "cop_pluviometros", "cop_areas_alagaveis", "cop_pontos_alagamento",
)


# Epidemiologia, ocorrências e território sempre devolvem o estado atual da
# fonte; só a ANA consulta séries por data (suporta_historico padrão).
COLETORES = {
    "dummy": Coletor(coletar_dummy, lambda conteudo: len(json.loads(conteudo)), "dummy.json"),
    "epidemiologia": Coletor(coletar_epidemiologia, contar_epidemiologia, "datastore_search.json",
                             suporta_historico=False),
    "ocorrencias": Coletor(coletar_ocorrencias, contar_ocorrencias, "datastore_search.json",
                           suporta_historico=False),
    "ana_chuva": Coletor(coletar_ana_chuva, contar_ana_hidroweb, "hidroweb.json"),
    "ana_nivel": Coletor(coletar_ana_nivel, contar_ana_hidroweb, "hidroweb.json"),
    "territorio": Coletor(coletar_territorio, contar_territorio, "territorio.json", suporta_historico=False),
    **{fonte: _coletor_cop(fonte) for fonte in FONTES_COP},
}


def executar(
    fonte: str,
    data_coleta: date | None = None,
    *,
    diretorio_dados: Path = RAIZ_PROJETO / "data",
    coletores: Mapping[str, Coletor] | None = None,
    armazenamento: armaz.ArmazenamentoRaw | None = None,
) -> dict:
    """Relê a RAW para data explícita, ou coleta; registra sucesso e falha.

    Novas fontes devem registrar seu Coletor no mapa, sem importações dinâmicas.
    Falhas no armazenamento do próprio registro são propagadas ao chamador.
    Sem `armazenamento`, grava em arquivo sob `diretorio_dados` (nunca consulta
    o ambiente aqui: os testes não podem cair no MongoDB por causa de um .env).
    """
    if armazenamento is None:
        armazenamento = armaz.ArmazenamentoArquivo(diretorio_dados)
    inicio = datetime.now(FUSO_RECIFE)
    data_particao = data_coleta if data_coleta is not None else inicio.date()
    identificador = uuid4().hex
    registro = {
        "id": identificador,
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
    """Valida o formato estrito exigido pela interface de reprocessamento."""
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
            raise ValueError
        return date.fromisoformat(valor)
    except ValueError as erro:
        raise argparse.ArgumentTypeError("Use uma data valida no formato AAAA-MM-DD") from erro


def main() -> int:
    # Saída redirecionada no Windows usa cp1252 e quebra com caracteres fora
    # dessa tabela (ex.: "↔" nas docstrings) — forçar UTF-8 (BUG-02).
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("fonte", help="Nome do coletor registrado (teste: dummy)")
    argumentos.add_argument("--data", type=interpretar_data, dest="data_coleta")
    argumentos.add_argument(
        "--diretorio-dados", type=Path, default=RAIZ_PROJETO / "data",
        help="Raiz de armazenamento; padrao: data/ do projeto",
    )
    argumentos.add_argument(
        "--armazenamento", choices=armaz.TIPOS, default=None,
        help="Onde gravar a RAW; padrao: AERVITA_ARMAZENAMENTO ou arquivo",
    )
    opcoes = argumentos.parse_args()
    try:
        registro = executar(
            opcoes.fonte, opcoes.data_coleta, diretorio_dados=opcoes.diretorio_dados,
            armazenamento=armaz.criar(opcoes.armazenamento, opcoes.diretorio_dados),
        )
    except OSError as erro:
        argumentos.exit(1, f"Falha ao persistir registro de execucao: {erro}\n")
    print(json.dumps(registro, ensure_ascii=False))
    return 0 if registro["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
