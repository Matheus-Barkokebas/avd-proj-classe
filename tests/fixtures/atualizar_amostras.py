"""Gera as amostras reais reduzidas em tests/fixtures/amostras/ (QA-01).

ACESSA A REDE — rodar manualmente, não faz parte do `pytest`:

    python tests/fixtures/atualizar_amostras.py

Para cada fonte CKAN, guarda poucos registros reais preservando exatamente o
formato de cada campo (datas, tipos texto vs. número) — foi a diferença de
formato entre recursos que os fixtures escritos à mão não pegaram (BUG-03).

Privacidade: só os campos que o pipeline usa são mantidos (sem data de
nascimento, logradouro, CEP, etc.) e os identificadores (número de
notificação/processo) são trocados por sintéticos, mantendo o tipo original.
Inclui de propósito os casos-limite reais: bairro vazio e número de
notificação repetido.
"""

from pathlib import Path
import json
import sys

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from src.ingestao import recife_ckan  # noqa: E402

DESTINO = Path(__file__).resolve().parent / "amostras"

EPIDEMIOLOGIA = {
    "dengue": "45a675e2-d387-4019-bb6e-4b915b74b1bf",
    "zika": "cf7dc2c4-a050-454f-9404-465458baa988",
    "chikungunya": "b300a634-1ab7-49fc-8592-4b45227822a8",
}
CAMPOS_EPIDEMIOLOGIA = ["NU_NOTIFIC", "DT_NOTIFIC", "SEM_NOT", "NU_ANO", "NM_BAIRRO", "CLASSI_FIN", "ID_AGRAVO"]
CAMPOS_OCORRENCIAS = ["processo_numero", "solicitacao_data", "solicitacao_hora", "solicitacao_bairro",
                      "processo_solicitacao", "processo_situacao", "solicitacao_descricao"]


def _reduzir(registros, campos, campo_id, prefixo):
    saida = []
    for i, reg in enumerate(registros, start=1):
        novo = {c: reg.get(c) for c in campos}
        original = reg.get(campo_id)
        sintetico = 900000 + i
        novo[campo_id] = sintetico if isinstance(original, int) else f"{prefixo}{sintetico}"
        saida.append(novo)
    return saida


def _amostra_epidemiologia():
    amostra = {}
    for agravo, resource_id in EPIDEMIOLOGIA.items():
        registros, _ = recife_ckan.coletar_todos(resource_id)
        escolhidos = registros[:4]
        sem_bairro = [r for r in registros if not r.get("NM_BAIRRO")][:1]
        amostra[agravo] = _reduzir(escolhidos + sem_bairro, CAMPOS_EPIDEMIOLOGIA, "NU_NOTIFIC", "")
    # caso real: mesmo número de notificação em agravos diferentes (BUG-07)
    amostra["zika"][0]["NU_NOTIFIC"] = str(amostra["dengue"][0]["NU_NOTIFIC"])
    return amostra


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    arquivos = {
        "epidemiologia.json": _amostra_epidemiologia(),
        "ocorrencias.json": _reduzir(
            recife_ckan.coletar_todos("fa135ecc-101d-40d7-88df-f38aa709a7d1")[0][:5],
            CAMPOS_OCORRENCIAS, "processo_numero", ""),
        "territorio_bairros_rpa.json": recife_ckan.coletar_todos("a378d50a-5e55-4956-a28c-13305acfc2b3")[0][:5],
        "territorio_distritos_sanitarios.json": recife_ckan.coletar_todos("d8d649d6-5bf7-44af-9686-436162766037")[0][:5],
    }
    for nome, conteudo in arquivos.items():
        (DESTINO / nome).write_text(json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8")
        print("gravado", DESTINO / nome)


if __name__ == "__main__":
    main()
