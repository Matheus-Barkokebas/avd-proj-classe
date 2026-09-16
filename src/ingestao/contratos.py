"""Contratos de dados e validação de lotes na ingestão (FND-02)."""

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime
import math
from pathlib import Path
from typing import Any
import yaml


RAIZ_PROJETO = Path(__file__).resolve().parents[2]
DIRETORIO_CONTRATOS = RAIZ_PROJETO / "conf" / "contracts"


@dataclass(frozen=True)
class Violacao:
    """Representação imutável de uma inconformidade com o contrato de dados."""

    tipo: str
    campo: str
    mensagem: str
    linha: int | None = None
    valor: Any = None

    def __getitem__(self, item: str) -> Any:
        """Permite acesso compatível por chave (ex.: violacao['tipo'])."""
        try:
            return getattr(self, item)
        except AttributeError as err:
            raise KeyError(item) from err

    def para_dict(self) -> dict[str, Any]:
        """Converte a violação para dicionário padrão."""
        return asdict(self)


def carregar_contrato(fonte_ou_caminho: str | Path) -> dict[str, Any]:
    """Carrega contrato YAML a partir do nome da fonte ou de um caminho direto.

    Args:
        fonte_ou_caminho: nome da fonte (ex.: 'epidemiologia') ou caminho do arquivo YAML.

    Returns:
        Dicionário com a estrutura declarativa do contrato.
    """
    caminho = Path(fonte_ou_caminho)
    if not caminho.is_file():
        # Tenta resolver dentro de conf/contracts/<nome>.yml
        nome_arquivo = f"{fonte_ou_caminho}.yml" if not str(fonte_ou_caminho).endswith((".yml", ".yaml")) else str(fonte_ou_caminho)
        caminho = DIRETORIO_CONTRATOS / nome_arquivo

    if not caminho.is_file():
        raise FileNotFoundError(f"Arquivo de contrato não encontrado: {caminho}")

    with caminho.open(encoding="utf-8") as arquivo:
        dados = yaml.safe_load(arquivo)

    if not isinstance(dados, dict):
        raise ValueError(f"Conteúdo inválido no contrato {caminho}: esperava mapeamento YAML.")

    if "tabela" not in dados or "campos" not in dados:
        raise ValueError(f"Contrato {caminho} incompleto: 'tabela' e 'campos' são obrigatórios.")

    return dados


def _e_nulo(valor: Any) -> bool:
    """Identifica valores nulos (None, NaN numérico)."""
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    return False


def _validar_tipo(valor: Any, tipo_esperado: str) -> bool:
    """Verifica se um valor não nulo é compatível com o tipo do contrato."""
    tipo = tipo_esperado.lower().strip()

    if tipo in ("string", "str", "text", "varchar"):
        return isinstance(valor, str)

    if tipo in ("int", "integer"):
        # Em Python, isinstance(True, int) é True; bool deve ser rejeitado
        return isinstance(valor, int) and not isinstance(valor, bool)

    if tipo in ("float", "double", "decimal", "numeric", "number"):
        return isinstance(valor, (int, float)) and not isinstance(valor, bool)

    if tipo in ("bool", "boolean"):
        return isinstance(valor, bool)

    if tipo in ("datetime", "timestamp"):
        if isinstance(valor, datetime):
            return True
        if isinstance(valor, str):
            # Tenta parsing ISO ou formato padrão do projeto (PADROES §3)
            formatos = (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d",
            )
            for formato in formatos:
                try:
                    datetime.strptime(valor.strip(), formato)
                    return True
                except ValueError:
                    continue
            try:
                datetime.fromisoformat(valor.strip())
                return True
            except ValueError:
                return False
        return False

    if tipo in ("date",):
        if isinstance(valor, (date, datetime)):
            return True
        if isinstance(valor, str):
            try:
                date.fromisoformat(valor.strip())
                return True
            except ValueError:
                return False
        return False

    # Tipo não mapeado explicitamente aceita qualquer valor não nulo
    return True


def validar(
    lote: Sequence[Mapping[str, Any]] | Mapping[str, Any],
    contrato: Mapping[str, Any] | str | Path,
) -> list[Violacao]:
    """Valida um lote de dados contra um contrato por fonte.

    Detecta colunas obrigatórias faltantes, tipos incompatíveis, nulos em
    campos obrigatórios e valores fora do domínio permitido.

    Args:
        lote: sequência de dicionários (1 dict por registro) ou único dicionário.
        contrato: dicionário do contrato, nome da fonte ou caminho do YAML.

    Returns:
        Lista de instâncias de Violacao. Lista vazia indica lote plenamente válido.
    """
    if isinstance(contrato, (str, Path)):
        contrato_dados = carregar_contrato(contrato)
    elif isinstance(contrato, Mapping):
        contrato_dados = dict(contrato)
    else:
        raise TypeError(f"Contrato deve ser dicionário, str ou Path, recebido: {type(contrato)}")

    registros: list[Mapping[str, Any]]
    if isinstance(lote, (str, bytes)):
        raise TypeError(f"Lote deve ser uma lista de dicionários, recebido: {type(lote).__name__}")
    elif isinstance(lote, Mapping):
        registros = [lote]
    elif isinstance(lote, Sequence):
        registros = list(lote)
        for r in registros:
            if not isinstance(r, Mapping):
                raise TypeError(f"Cada item do lote deve ser um dicionário/Mapping, recebido: {type(r).__name__}")
    else:
        raise TypeError(f"Lote deve ser uma lista de dicionários, recebido: {type(lote).__name__}")

    campos_contrato: list[dict[str, Any]] = contrato_dados.get("campos", [])
    violacoes: list[Violacao] = []

    if not registros:
        return violacoes

    # 1. Conjunto de colunas presentes no lote completo
    colunas_lote = set().union(*(r.keys() for r in registros))

    # 2. Verificação de colunas obrigatórias faltantes no lote
    for campo in campos_contrato:
        nome_campo = campo.get("nome", "")
        obrigatorio = campo.get("obrigatorio", True)

        if obrigatorio and nome_campo not in colunas_lote:
            violacoes.append(
                Violacao(
                    tipo="coluna_faltante",
                    campo=nome_campo,
                    mensagem=f"Coluna obrigatória '{nome_campo}' não encontrada no lote.",
                )
            )

    # 3. Verificação registro a registro (tipos, nulos e valores permitidos)
    for indice, registro in enumerate(registros, start=1):
        for campo in campos_contrato:
            nome_campo = campo.get("nome", "")
            tipo_esperado = campo.get("tipo", "string")
            obrigatorio = campo.get("obrigatorio", True)
            valores_permitidos = campo.get("valores_permitidos")

            # Campo ausente neste registro específico
            if nome_campo not in registro:
                # Se a coluna inteira estava ausente do lote, já foi reportada em coluna_faltante
                if nome_campo in colunas_lote and obrigatorio:
                    violacoes.append(
                        Violacao(
                            tipo="nulo_obrigatorio",
                            campo=nome_campo,
                            linha=indice,
                            mensagem=f"Campo obrigatório '{nome_campo}' ausente no registro da linha {indice}.",
                        )
                    )
                continue

            valor = registro[nome_campo]

            # Verificação de nulo
            if _e_nulo(valor):
                if obrigatorio:
                    violacoes.append(
                        Violacao(
                            tipo="nulo_obrigatorio",
                            campo=nome_campo,
                            linha=indice,
                            valor=valor,
                            mensagem=f"Campo obrigatório '{nome_campo}' contém valor nulo na linha {indice}.",
                        )
                    )
                continue

            # Verificação de tipo
            if not _validar_tipo(valor, tipo_esperado):
                violacoes.append(
                    Violacao(
                        tipo="tipo_errado",
                        campo=nome_campo,
                        linha=indice,
                        valor=valor,
                        mensagem=(
                            f"Campo '{nome_campo}' na linha {indice} tem tipo incompatível: "
                            f"esperava '{tipo_esperado}', obteve '{type(valor).__name__}' ({valor!r})."
                        ),
                    )
                )
                continue

            # Verificação de valores permitidos (domínio)
            if valores_permitidos is not None:
                valor_comparacao = valor.lower() if isinstance(valor, str) else valor
                valores_normalizados = [
                    v.lower() if isinstance(v, str) else v for v in valores_permitidos
                ]
                if valor_comparacao not in valores_normalizados:
                    violacoes.append(
                        Violacao(
                            tipo="valor_invalido",
                            campo=nome_campo,
                            linha=indice,
                            valor=valor,
                            mensagem=(
                                f"Campo '{nome_campo}' na linha {indice} contém valor '{valor}', "
                                f"fora do domínio permitido: {valores_permitidos}."
                            ),
                        )
                    )

    return violacoes
