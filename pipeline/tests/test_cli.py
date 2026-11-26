"""O ponto de entrada python -m aervita resolve todos os comandos, sem rede."""

import json
import subprocess
import sys

import pytest

from aervita.__main__ import COMANDOS, SCRIPTS
from aervita.ambiente import RAIZ_PROJETO


def _rodar(*argumentos, cwd=RAIZ_PROJETO):
    return subprocess.run([sys.executable, "-m", "aervita", *argumentos], cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8", check=False)


@pytest.mark.parametrize("comando", sorted(set(COMANDOS) - SCRIPTS))
def test_comando_carrega_e_mostra_ajuda(comando):
    resultado = _rodar(comando, "--help")
    assert resultado.returncode == 0, resultado.stderr
    assert "ModuleNotFoundError" not in resultado.stderr


def test_comando_desconhecido_lista_os_comandos():
    resultado = _rodar("nao-existe")
    assert resultado.returncode == 2
    assert "gold" in resultado.stdout and "diario" in resultado.stdout


def test_coletar_dummy_grava_a_raw(tmp_path):
    resultado = _rodar("coletar", "dummy", "--diretorio-dados", str(tmp_path), "--armazenamento", "arquivo")
    registro = json.loads(resultado.stdout)
    assert registro["status"] == "ok" and registro["numero_registros"] == 1
    assert list((tmp_path / "raw" / "dummy").rglob("dummy.json"))
