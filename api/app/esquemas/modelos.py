"""Formato das respostas — o contrato com o front (vira o OpenAPI e os tipos TypeScript)."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SituacaoRio = Literal["normal", "pre_alerta", "alerta", "inundacao", "sem_cota"]


class Erro(BaseModel):
    erro: str = Field(description="Código curto do erro, estável para o front tratar")
    detalhe: str | None = None


class Saude(BaseModel):
    status: Literal["ok", "indisponivel"]
    banco: Literal["ok", "indisponivel"]


# ------------------------------------------------------------ chuva
class ComparacaoMensal(BaseModel):
    mes: int
    ano: int
    chuva_acumulada_mm: float | None = Field(description="Chuva acumulada no mês até agora")
    media_historica_mm: float | None
    percentual_da_media: float | None = Field(description="Acumulado do mês em % da média histórica do mês")


class ChuvaAtual(BaseModel):
    data_hora: datetime
    estagio: str | None
    chuva_media_1h_mm: float | None
    chuva_max_1h_mm: float | None
    estacao_max_1h: str | None
    chuva_media_24h_mm: float | None
    chuva_max_24h_mm: float | None
    estacao_max_24h: str | None
    mare_m: float | None
    sentido_mare: str | None
    ocorrencias: int | None
    alagamentos: int | None
    abrigos: int | None
    mes: ComparacaoMensal | None


class PontoSerieChuva(BaseModel):
    data_hora: datetime
    chuva_media_1h_mm: float | None
    chuva_max_1h_mm: float | None
    chuva_media_24h_mm: float | None
    chuva_max_24h_mm: float | None
    mare_m: float | None


class PrevisaoHora(BaseModel):
    data_hora_prevista: datetime
    gfs_mm: float | None
    ecmwf_mm: float | None
    icon_mm: float | None
    wrf_mm: float | None
    media_modelos_mm: float | None = Field(description="Média dos modelos com valor")


class ChuvaMes(BaseModel):
    mes: int
    chuva_ano_atual_mm: float | None
    chuva_ano_anterior_mm: float | None
    media_historica_mm: float | None


class ChuvaMensal(BaseModel):
    ano: int
    meses: list[ChuvaMes]


# ------------------------------------------------------------ rios
class Rio(BaseModel):
    codigo_estacao: str
    estacao: str
    rio: str
    data_hora: datetime
    nivel: float = Field(description="Na unidade da fonte (a confirmar com o COP; valores sugerem cm)")
    cota_pre_alerta: float | None
    cota_alerta: float | None
    cota_inundacao: float | None
    situacao: SituacaoRio = Field(description="Calculada pelo nível contra as cotas oficiais")
    situacao_fonte: str | None = Field(description="Situação informada pelo COP")
    percentual_da_cota_alerta: float | None


class PontoSerieRio(BaseModel):
    data_hora: datetime
    nivel: float


# ------------------------------------------------------------ arboviroses
class ArbovirosesSemana(BaseModel):
    semana: int = Field(description="Semana epidemiológica, ex.: 202533")
    agravo: str
    notificacoes: int
    nao_descartadas: int


class ArbovirosesBairro(BaseModel):
    chave_bairro: str
    nome_bairro: str
    distrito_sanitario: int | None
    descricao_distrito: str | None
    dengue: int
    chikungunya: int
    zika: int
    total: int


class ArbovirosesPorBairro(BaseModel):
    bairros: list[ArbovirosesBairro]
    nao_georreferenciadas: int = Field(description="Notificações cujo bairro não casou com a tabela oficial")
    grafias_nao_reconhecidas: list[str]


# ------------------------------------------------------------ território
class Bairro(BaseModel):
    chave_bairro: str
    nome_bairro: str
    rpa: int | None
    distrito_sanitario: int | None
    descricao_distrito: str | None


class Distrito(BaseModel):
    distrito_sanitario: int
    descricao_distrito: str
    bairros: int


class FeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[dict[str, Any]]


# ------------------------------------------------------------ atualização
class CargaTabela(BaseModel):
    tabela: str
    carregado_em: datetime | None
    linhas: int


class Atualizacao(BaseModel):
    gerado_em: datetime
    tabelas: list[CargaTabela]
    hoje: date


# ------------------------------------------------------------ maré e alagamento
class Mare(BaseModel):
    data_hora: datetime
    mare_m: float
    tipo: Literal["alta", "baixa"]


class AlagamentoRota(BaseModel):
    rota: str
    leituras_com_alagamento: int = Field(description="Leituras horárias em que a rota teve alagamento reportado")
    alertas: int = Field(description="Soma dos alertas de alagamento na rota")
    ultimo: datetime = Field(description="Último alagamento reportado na rota no período")


class AlagamentoDia(BaseModel):
    dia: date
    horas_com_alagamento: int
    rotas: int = Field(description="Rotas diferentes com alagamento reportado no dia")
    alertas: int


class VariavelImportante(BaseModel):
    variavel: str
    importancia: float


class AvaliacaoModelo(BaseModel):
    modelo: str
    treinado_em: datetime
    inicio: datetime = Field(description="Primeira hora usada no treino e no teste")
    fim: datetime = Field(description="Última hora usada no treino e no teste")
    horas: int
    horas_teste: int
    horizonte_horas: int
    linha_de_base: float = Field(description="Acurácia de chutar sempre a classe mais comum, de 0 a 1")
    acuracia: float
    precisao: float
    recall: float = Field(description="Parte dos alagamentos reais que o modelo encontra, de 0 a 1")
    validacao_cruzada: float
    tempo_linha_de_base: float = Field(description="Linha de base treinando no passado e testando no futuro")
    tempo_acuracia: float
    tempo_balanceada: float
    verdadeiros_positivos: int
    falsos_positivos: int
    falsos_negativos: int
    verdadeiros_negativos: int
    importancia: list[VariavelImportante]


class PassoSimulacao(BaseModel):
    variavel: str
    valor: float
    limiar: float
    menor_ou_igual: bool


class ForaDaFaixa(BaseModel):
    variavel: str
    valor: float
    minimo: float
    maximo: float


class Simulacao(BaseModel):
    probabilidade: float = Field(description="Parte das horas de treino parecidas com o cenário que tiveram alagamento")
    previsto: int
    horas_parecidas: int = Field(description="Horas de treino que caíram na mesma regra final")
    horizonte_horas: int
    caminho: list[PassoSimulacao] = Field(description="Regras da árvore aplicadas ao cenário, em ordem")
    fora_da_faixa: list[ForaDaFaixa] = Field(description="Valores fora do que o modelo viu no treino")


class PrevisaoAlagamento(BaseModel):
    hora: datetime
    hora_prevista: datetime
    probabilidade: float
    previsto: int
    observado: int | None
