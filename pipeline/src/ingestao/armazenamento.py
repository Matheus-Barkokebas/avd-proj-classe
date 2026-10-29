"""Onde a RAW é guardada: arquivo local ou MongoDB Atlas (decisão 0001).

A RAW é sempre o conteúdo original da fonte, em bytes, sem transformação.
Dois adaptadores implementam a mesma interface:

- ArmazenamentoArquivo: data/raw/<fonte>/AAAA/MM/DD/<arquivo> (comportamento
  original; padrão nos testes, que não acessam a rede).
- ArmazenamentoMongo: conteúdo no GridFS (preserva os bytes e passa do limite
  de 16 MB por documento) + metadados na coleção raw_coletas, com índice único
  em (fonte, data_coleta, arquivo). Regravar o mesmo conteúdo não duplica nada.
"""

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Protocol

from src.ingestao import ambiente

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
# America/Recife é UTC-03, sem horário de verão (PADROES §3).
FUSO_RECIFE = timezone(timedelta(hours=-3), name="America/Recife")
TIPOS = ("arquivo", "mongo")


def gravar_atomico(caminho: Path, conteudo: bytes) -> None:
    """Publica somente o arquivo completo; preserva o anterior se a escrita falhar."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(dir=caminho.parent, delete=False) as arquivo:
            temporario = Path(arquivo.name)
            arquivo.write(conteudo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)


def _agora() -> str:
    return datetime.now(FUSO_RECIFE).strftime("%Y-%m-%d %H:%M:%S")


class ArmazenamentoRaw(Protocol):
    def ler(self, fonte: str, data_coleta: date, arquivo: str) -> bytes | None: ...
    def gravar(self, fonte: str, data_coleta: date, arquivo: str, conteudo: bytes) -> bool: ...
    def registrar_execucao(self, registro: dict[str, Any]) -> None: ...
    def descrever(self, fonte: str, data_coleta: date, arquivo: str) -> str: ...


class ArmazenamentoArquivo:
    """RAW em arquivos particionados por data, como desde a FND-03."""

    def __init__(self, diretorio_dados: Path = RAIZ_PROJETO / "data"):
        self.diretorio = Path(diretorio_dados)

    def caminho(self, fonte: str, data_coleta: date, arquivo: str) -> Path:
        return (self.diretorio / "raw" / fonte / f"{data_coleta.year:04d}"
                / f"{data_coleta.month:02d}" / f"{data_coleta.day:02d}" / arquivo)

    def ler(self, fonte: str, data_coleta: date, arquivo: str) -> bytes | None:
        caminho = self.caminho(fonte, data_coleta, arquivo)
        return caminho.read_bytes() if caminho.is_file() else None

    def gravar(self, fonte: str, data_coleta: date, arquivo: str, conteudo: bytes) -> bool:
        gravar_atomico(self.caminho(fonte, data_coleta, arquivo), conteudo)
        return True

    def registrar_execucao(self, registro: dict[str, Any]) -> None:
        gravar_atomico(self.diretorio / "_runs" / f"{registro['id']}.json",
                       json.dumps(registro, ensure_ascii=False, indent=2).encode("utf-8"))

    def descrever(self, fonte: str, data_coleta: date, arquivo: str) -> str:
        return str(self.caminho(fonte, data_coleta, arquivo))


class ArmazenamentoMongo:
    """RAW no MongoDB Atlas: GridFS para o conteúdo, raw_coletas para os metadados."""

    def __init__(self, banco: Any = None, *, coletas: Any = None, bucket: Any = None, execucoes: Any = None):
        # `banco` é um pymongo Database; os parâmetros nomeados existem para os
        # testes injetarem dublês sem rede.
        if banco is not None:
            import gridfs

            coletas = banco["raw_coletas"]
            execucoes = banco["execucoes"]
            bucket = gridfs.GridFSBucket(banco, bucket_name="raw_conteudo")
        self._coletas, self._bucket, self._execucoes = coletas, bucket, execucoes
        self._coletas.create_index(
            [("fonte", 1), ("data_coleta", 1), ("arquivo", 1)], unique=True, name="uq_fonte_data_arquivo"
        )

    @classmethod
    def do_ambiente(cls) -> "ArmazenamentoMongo":
        """Conecta com MONGODB_URI / MONGODB_DB lidos do ambiente ou do .env."""
        from pymongo import MongoClient

        config = ambiente.config_mongo()
        cliente = MongoClient(config["uri"], serverSelectionTimeoutMS=15000, appname="aervita-ingestao")
        return cls(cliente[config["banco"]])

    @staticmethod
    def _chave(fonte: str, data_coleta: date, arquivo: str) -> dict[str, str]:
        return {"fonte": fonte, "data_coleta": data_coleta.isoformat(), "arquivo": arquivo}

    def ler(self, fonte: str, data_coleta: date, arquivo: str) -> bytes | None:
        documento = self._coletas.find_one(self._chave(fonte, data_coleta, arquivo))
        if documento is None:
            return None
        return self._bucket.open_download_stream(documento["conteudo_id"]).read()

    def gravar(self, fonte: str, data_coleta: date, arquivo: str, conteudo: bytes) -> bool:
        """Grava a coleta da data. Devolve False quando o conteúdo já era idêntico."""
        chave = self._chave(fonte, data_coleta, arquivo)
        sha256 = hashlib.sha256(conteudo).hexdigest()
        agora = _agora()
        atual = self._coletas.find_one(chave)
        if atual is not None and atual.get("sha256") == sha256:
            self._coletas.update_one(chave, {"$set": {"verificado_em": agora}})
            return False
        # Sobe o conteúdo novo antes de trocar o ponteiro: se o upload falhar,
        # a coleta anterior continua íntegra (mesma garantia do gravar_atomico).
        novo_id = self._bucket.upload_from_stream(
            f"{fonte}/{chave['data_coleta']}/{arquivo}", conteudo, metadata={**chave, "sha256": sha256}
        )
        self._coletas.replace_one(chave, {
            **chave, "sha256": sha256, "tamanho_bytes": len(conteudo), "conteudo_id": novo_id,
            "gravado_em": agora, "verificado_em": agora,
        }, upsert=True)
        if atual is not None:
            self._bucket.delete(atual["conteudo_id"])
        return True

    def registrar_execucao(self, registro: dict[str, Any]) -> None:
        self._execucoes.replace_one({"_id": registro["id"]}, {"_id": registro["id"], **registro}, upsert=True)

    def descrever(self, fonte: str, data_coleta: date, arquivo: str) -> str:
        chave = self._chave(fonte, data_coleta, arquivo)
        return f"MongoDB raw_coletas {chave['fonte']}/{chave['data_coleta']}/{chave['arquivo']}"


def ler_json(armazenamento: ArmazenamentoRaw, fonte: str, data_coleta: date, arquivo: str) -> Any:
    """Lê uma RAW JSON já gravada, de qualquer adaptador; erro claro se não existir."""
    bruto = armazenamento.ler(fonte, data_coleta, arquivo)
    if bruto is None:
        raise FileNotFoundError(
            f"RAW não encontrada para a data {data_coleta}: {armazenamento.descrever(fonte, data_coleta, arquivo)}"
        )
    return json.loads(bruto.decode("utf-8"))


def criar(tipo: str | None = None, diretorio_dados: Path = RAIZ_PROJETO / "data") -> ArmazenamentoRaw:
    """Escolhe o adaptador: argumento explícito, senão AERVITA_ARMAZENAMENTO, senão arquivo."""
    tipo = tipo or ambiente.opcional("AERVITA_ARMAZENAMENTO", "arquivo")
    if tipo not in TIPOS:
        raise ValueError(f"Armazenamento desconhecido: {tipo!r}. Use um de: {', '.join(TIPOS)}")
    return ArmazenamentoMongo.do_ambiente() if tipo == "mongo" else ArmazenamentoArquivo(diretorio_dados)
