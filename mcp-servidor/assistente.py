"""GPT que transforma perguntas em SQL e explica o resultado."""

from openai import OpenAI

CONTEXTO = (
    "Os dados são do AerVita, painel de chuva e risco de alagamento do Recife. "
    "Fontes: chuva do INMET, maré e alagamentos por rota do COP Recife, arboviroses e território "
    "dos Dados Abertos do Recife. Datas estão no horário do Recife."
)


class AssistenteGPT:
    def __init__(self, chave_api: str, modelo: str):
        self.cliente = OpenAI(api_key=chave_api)
        self.modelo = modelo

    def perguntar(self, instrucao: str, pergunta: str) -> str:
        """Envia uma pergunta ao GPT e devolve o texto da resposta."""
        resposta = self.cliente.chat.completions.create(
            model=self.modelo,
            messages=[
                {"role": "system", "content": instrucao},
                {"role": "user", "content": pergunta},
            ],
        )
        return resposta.choices[0].message.content.strip()

    def gerar_sql(self, pergunta: str, esquema: str) -> str:
        """Transforma uma pergunta em português em um comando SELECT."""
        instrucao = (
            f"Você é especialista em PostgreSQL. {CONTEXTO} "
            "Com base nas tabelas abaixo, escreva UM comando SELECT que responda à pergunta, "
            "usando o nome completo das tabelas (schema.tabela). "
            "Responda somente com o SQL, sem explicações e sem ```.\n\n"
            f"Tabelas:\n{esquema}"
        )
        sql = self.perguntar(instrucao, pergunta)
        return sql.replace("```sql", "").replace("```", "").strip()

    def explicar_resultado(self, pergunta: str, dados: list[dict]) -> str:
        """Escreve uma resposta curta a partir dos dados do banco."""
        instrucao = (
            f"{CONTEXTO} Responda à pergunta do usuário em português, de forma curta, "
            "usando apenas os dados fornecidos. Se os dados não bastarem, diga isso."
        )
        return self.perguntar(instrucao, f"Pergunta: {pergunta}\nDados: {dados}")
