"""Aceitação da FND-03 com coletores sintéticos, sem acesso à rede."""

from datetime import date, datetime
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest
import yaml

from src.ingestao import runner


def registros(diretorio):
    return [json.loads(arquivo.read_text(encoding="utf-8"))
            for arquivo in (diretorio / "_runs").glob("*.json")]


def test_dummy_grava_raw_e_registro_ok(tmp_path):
    registro = runner.executar("dummy", diretorio_dados=tmp_path)
    data_coleta = date.fromisoformat(registro["data_coleta"])
    caminho = tmp_path / "raw" / "dummy" / data_coleta.strftime("%Y/%m/%d") / "dummy.json"
    assert caminho.read_bytes() == runner.coletar_dummy(data_coleta)
    assert registros(tmp_path) == [registro]
    assert registro["fonte"] == "dummy"
    assert registro["numero_registros"] == 1
    assert registro["status"] == "ok"
    assert registro["mensagem"]
    assert datetime.strptime(registro["inicio"], "%Y-%m-%d %H:%M:%S") <= datetime.strptime(
        registro["fim"], "%Y-%m-%d %H:%M:%S"
    )


def test_excecao_do_coletor_registra_erro_sem_raw(tmp_path):
    coletar = Mock(side_effect=RuntimeError("falha simulada"))
    registro = runner.executar(
        "teste", diretorio_dados=tmp_path,
        coletores={"teste": runner.Coletor(coletar, len, "teste.json")},
    )
    assert registro["status"] == "erro"
    assert registro["numero_registros"] == 0
    assert "falha simulada" in registro["mensagem"]
    assert registros(tmp_path) == [registro]
    assert not (tmp_path / "raw").exists()


def test_reprocessamento_rele_raw_sem_recoletar(tmp_path):
    data_coleta = date(2026, 9, 1)
    coletar = Mock(return_value=b'[ { "id": 1 }, { "id": 2 } ]\n')
    catalogo = {"teste": runner.Coletor(coletar, lambda bruto: len(json.loads(bruto)), "teste.json")}
    primeiro = runner.executar("teste", data_coleta, diretorio_dados=tmp_path, coletores=catalogo)
    caminho = tmp_path / "raw/teste/2026/09/01/teste.json"
    original = caminho.read_bytes()
    segundo = runner.executar("teste", data_coleta, diretorio_dados=tmp_path, coletores=catalogo)
    coletar.assert_called_once_with(data_coleta)
    assert primeiro["status"] == segundo["status"] == "ok"
    assert segundo["numero_registros"] == 2
    assert segundo["mensagem"] == "RAW existente relida"
    assert caminho.read_bytes() == original
    assert len(list((tmp_path / "raw").rglob("*.json"))) == 1
    assert len(registros(tmp_path)) == 2


def test_falha_na_publicacao_preserva_raw_anterior(tmp_path, monkeypatch):
    runner.executar("dummy", diretorio_dados=tmp_path)
    caminho = next((tmp_path / "raw").rglob("*.json"))
    original = caminho.read_bytes()
    substituir = runner.os.replace

    def falhar_raw(origem, destino):
        if "raw" in Path(destino).parts:
            raise OSError("disco indisponivel")
        substituir(origem, destino)

    monkeypatch.setattr(runner.os, "replace", falhar_raw)
    registro = runner.executar("dummy", diretorio_dados=tmp_path)
    assert registro["status"] == "erro"
    assert "disco indisponivel" in registro["mensagem"]
    assert caminho.read_bytes() == original
    assert list(caminho.parent.iterdir()) == [caminho]
    assert len(registros(tmp_path)) == 2


@pytest.mark.parametrize("fonte", ["desconhecida", "../escape", "/absoluto"])
def test_fonte_invalida_registra_erro(tmp_path, fonte):
    assert runner.executar(fonte, diretorio_dados=tmp_path)["status"] == "erro"
    assert len(registros(tmp_path)) == 1
    assert not (tmp_path / "raw").exists()


@pytest.mark.parametrize("conteudo,contagem", [("nao_bytes", 1), (b"[]", -1), (b"[]", True)])
def test_contrato_invalido_nao_publica_raw(tmp_path, conteudo, contagem):
    coletor = runner.Coletor(lambda data: conteudo, lambda bruto: contagem, "teste.json")
    resultado = runner.executar("teste", diretorio_dados=tmp_path, coletores={"teste": coletor})
    assert resultado["status"] == "erro"
    assert not (tmp_path / "raw").exists()


def test_raw_csv_preserva_bytes_e_aceita_coleta_vazia(tmp_path):
    conteudo = b"id,nome\r\n"
    coletor = runner.Coletor(lambda data: conteudo, lambda bruto: 0, "teste.csv")
    resultado = runner.executar("teste", date(2026, 9, 1), diretorio_dados=tmp_path,
                               coletores={"teste": coletor})
    assert resultado["status"] == "ok"
    assert resultado["numero_registros"] == 0
    assert (tmp_path / "raw/teste/2026/09/01/teste.csv").read_bytes() == conteudo


def executar_cli(tmp_path, *argumentos):
    return subprocess.run(
        [sys.executable, str(Path(runner.__file__)), *argumentos,
         "--diretorio-dados", str(tmp_path)],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", check=False,
    )


def test_cli_coleta_e_reprocessa_particao(tmp_path):
    for argumentos in [("dummy",), ("dummy", "--data", "2026-09-01"),
                       ("dummy", "--data", "2026-09-01")]:
        resultado = executar_cli(tmp_path, *argumentos)
        assert resultado.returncode == 0, resultado.stderr
        assert json.loads(resultado.stdout)["status"] == "ok"
    assert json.loads(resultado.stdout)["mensagem"] == "RAW existente relida"
    assert len(registros(tmp_path)) == 3
    assert (tmp_path / "raw/dummy/2026/09/01/dummy.json").is_file()


@pytest.mark.parametrize("valor", ["20260901", "2026-9-1", "2026-02-30"])
def test_cli_rejeita_data_invalida(tmp_path, valor):
    resultado = executar_cli(tmp_path, "dummy", "--data", valor)
    assert resultado.returncode == 2
    assert "AAAA-MM-DD" in resultado.stderr
    assert not (tmp_path / "raw").exists()


def test_cli_erro_retorna_codigo_nao_zero(tmp_path):
    resultado = executar_cli(tmp_path, "inexistente")
    assert resultado.returncode == 1
    assert json.loads(resultado.stdout)["status"] == "erro"
    assert len(registros(tmp_path)) == 1


def test_schedule_cobre_fase_1():
    configuracao = yaml.safe_load((runner.RAIZ_PROJETO / "conf/schedule.yml").read_text(encoding="utf-8"))
    assert configuracao["fuso_horario"] == "America/Recife"
    assert configuracao["fontes"] == {
        "epidemiologia": {"periodicidade": "diaria"},
        "ocorrencias": {"periodicidade": "diaria", "periodicidade_contingencia": "horaria"},
        "territorio": {"periodicidade": "mensal"},
        "ana_chuva": {"periodicidade": "horaria"},
        "ana_nivel": {"periodicidade": "horaria"},
    }
