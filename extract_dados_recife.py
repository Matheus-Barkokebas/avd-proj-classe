import csv
import io
import json
import requests as rq

# URL do recurso CSV da Prefeitura do Recife
url = "https://dados.recife.pe.gov.br/dataset/dca76666-842e-48cb-b005-6670d7212b46/resource/d6f586c3-34c5-4414-9804-6fdfbd75c7db/download/solicitacoes-de-atendimento-2026.csv"

# download do conteudo
response = rq.get(url)
response.encoding = "utf-8"

# leitura e conversao de CSV para lista de dicionarios
f = io.StringIO(response.text)
leitor_csv = csv.DictReader(f, delimiter=";")
dados_json = list(leitor_csv)

# exportacao para arquivo JSON formatado
with open("solicitacoes-de-atendimento-2026.json", "w", encoding="utf-8") as f_out:
    json.dump(dados_json, f_out, ensure_ascii=False, indent=4)

print(f"Sucesso! {len(dados_json)} registros exportados.")