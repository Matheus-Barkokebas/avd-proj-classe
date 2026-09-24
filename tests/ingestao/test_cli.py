"""Regressão do BUG-02: os comandos documentados nos READMEs precisam funcionar
quando os módulos são executados como script (`python src/ingestao/<modulo>.py`),
não só via `python -m`. Sem acesso à rede.
"""

import json
import subprocess
import sys

import pytest

from src.ingestao import runner

MODULOS = ["runner", "epidemiologia", "ocorrencias", "ana_hidroweb", "territorio"]


def _rodar_script(modulo, *argumentos, cwd):
    return subprocess.run(
        [sys.executable, str(runner.RAIZ_PROJETO / "src" / "ingestao" / f"{modulo}.py"), *argumentos],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False,
    )


@pytest.mark.parametrize("modulo", MODULOS)
def test_script_importa_sem_modulenotfounderror(modulo, tmp_path):
    """`--help` exige que todos os imports `src.*` do módulo resolvam."""
    resultado = _rodar_script(modulo, "--help", cwd=tmp_path)
    assert resultado.returncode == 0, resultado.stderr
    assert "ModuleNotFoundError" not in resultado.stderr


def test_runner_como_script_resolve_import_tardio_de_fonte_real(tmp_path):
    """runner.py <fonte real> precisa conseguir importar o módulo da fonte.

    Usa a releitura de uma RAW já existente (--data), que chama o
    contar_registros da fonte via import tardio, sem ir à rede."""
    raw = tmp_path / "raw" / "ocorrencias" / "2026" / "09" / "24" / "datastore_search.json"
    raw.parent.mkdir(parents=True)
    raw.write_text(json.dumps({"records": [{"processo_numero": 1}], "total": 1}), encoding="utf-8")

    resultado = _rodar_script(
        "runner", "ocorrencias", "--data", "2026-09-24", "--diretorio-dados", str(tmp_path), cwd=tmp_path,
    )
    registro = json.loads(resultado.stdout)
    assert registro["status"] == "ok", registro["mensagem"]
    assert registro["numero_registros"] == 1
