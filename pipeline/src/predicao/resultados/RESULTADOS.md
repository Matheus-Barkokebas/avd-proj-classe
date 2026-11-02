# Resultados do modelo de alagamento

Modelo no formato do [`etl-vacinacao-recife`](https://github.com/MatmJr/etl-vacinacao-recife): `train.py` como receita,
classe `Classificador` e apenas `DecisionTreeClassifier`. Os dados são os do AerVita ([decisão 0003](../../../../docs/decisoes/0003-medallion-bronze-silver-gold.md)).

**Pergunta:** daqui a 3 horas, alguma rota monitorada do Recife terá alagamento reportado?

```text
[extract] 2424 horas lidas da gold, de 2026-05-28 15:00:00 a 2026-09-29 08:00:00
[model] linha de base: 69.7%
[model] melhores parâmetros: {'criterion': 'gini', 'max_depth': 4, 'min_samples_leaf': 20} (validação cruzada: 84.3%)
[model] acurácia no teste: 82.5%
```

| Classe | Precisão | Recall | F1 | Horas no teste |
|---|---|---|---|---|
| Sem alagamento | 86% | 89% | 88% | 338 |
| Com alagamento | 73% | 67% | 70% | 147 |

**O modelo erra cerca de 1 em cada 3 alagamentos** (recall de 67%). Para alerta de defesa civil, esse é o número a acompanhar,
mais do que a acurácia. A matriz está em [`matriz_confusao.png`](matriz_confusao.png).

## Dados

| Variável | Fonte | Camadas |
|---|---|---|
| Chuva acumulada até a hora (1 h a 7 dias) | INMET, estação A301 Recife | `inmet_chuva` → `gold.ml_alagamento_hora` |
| Maré na hora, sentido e máxima nas próximas 6 h | Tábua de maré do COP Recife | `cop_mare` → `gold.ml_alagamento_hora` |
| Alvo: alagamento em alguma rota na hora + 3 | Campo `alaga` do COP Recife | `cop_alagamento_rotas` → `gold.ml_alagamento_hora` |

A maré futura pode entrar porque a tábua é publicada com antecedência. Horas sem coleta do `alaga` ficam fora do treino.

## Experimentos

`python src/predicao/experimentos.py`. Todas as tentativas usam as mesmas 2.100 horas (com coleta do `alaga` na hora e 3 horas depois), com linha de
base de 69,3%. A escolha olhou só a validação cruzada, que usa apenas o treino.

| # | O que mudou | Acurácia (validação) | Acurácia (treino) | Acurácia (teste) |
|---|---|---|---|---|
| 0 | Só chuva de 24h, profundidade 4 | 79,4% | 79,9% | 82,4% |
| 1 | Todas as janelas de chuva, profundidade 4 | 83,2% | 85,4% | 86,2% |
| 2 | Só maré, profundidade 4 | 68,5% | 71,6% | 69,0% |
| 3 | Chuva + maré, profundidade 4 | 82,9% | 85,9% | 86,0% |
| 4 | Chuva + maré, sem limite de profundidade | 78,6% | 100,0% | 82,1% |
| 5 | Só chuva, parâmetros por validação cruzada | 83,8% | 94,6% | 84,8% |
| **6** | **Chuva + maré, parâmetros por validação cruzada (escolhida)** | **83,9%** | **86,1%** | **85,7%** |
| 7 | Chuva + maré + rotas alagadas agora, por validação cruzada | 83,1% | 85,9% | 86,9% |

O `train.py` usa a configuração 6 com todas as 2.424 horas com alvo; por isso o resultado final é outro (82,5%, com outra divisão das horas).
A diferença de 85,7% para 82,5% dá uma ideia de quanto o número varia só com a composição dos dados.

## Validação no tempo

A divisão aleatória exigida coloca horas vizinhas no treino e no teste. Para medir o efeito disso, treinei até 26/08/2026 e testei depois:

| | Linha de base | Acurácia | Acurácia balanceada |
|---|---|---|---|
| Treino no passado, teste no futuro | 80,5% | 86,0% | 69,1% |

O ganho sobre o chute cai para 5,5 pontos, e a acurácia balanceada mostra que o modelo acerta bem menos os alagamentos nesse fim de período, mais seco.

## A maré

`python src/predicao/analise_mare.py`. Taxa de alagamento 3 horas depois, por chuva nas últimas 12 h e maré máxima nas próximas 6 h:

| Chuva em 12 h | Maré até 1,8 m | Maré de 1,8 a 2,2 m | Maré acima de 2,2 m |
|---|---|---|---|
| Sem chuva | 5,9% | 7,3% | 10,9% |
| Até 1 mm | 11,6% | 19,6% | 20,9% |
| 1 a 5 mm | 37,7% | 35,1% | 37,5% |
| 5 a 20 mm | 81,2% | 70,8% | 66,7% |
| Acima de 20 mm | 96,2% | 97,0% | 100,0% (só 4 horas) |

**A maré não melhorou a previsão de forma mensurável:** a validação foi de 83,8% só com chuva para 83,9% com maré, e a maré sozinha fica abaixo do chute.
A chuva em 12 h concentra 73% da importância. A tabela sugere mais alagamento com maré alta quando chove pouco, mas com chuva moderada o padrão se inverte
e há poucas horas de maré alta. **Estes dados não confirmam nem descartam o efeito da maré.** Faltam mais meses, sobretudo abril e maio, e o registro é por
rota de trânsito, não por ponto de alagamento de maré.

## Limites

- **Período curto:** 4 meses de um único ano, porque o INMET só tem Recife a partir de 21/05/2026. Abril e parte de maio, os meses com mais alagamentos, ficam de fora.
- **O alvo é alagamento reportado:** o campo `alaga` parece vir de alertas de motoristas (Waze), a confirmar com o COP. Cobre só as rotas monitoradas e depende de
  haver gente passando e reportando, então não é uma medição direta de alagamento.
- **Sem horário como variável:** a hora do dia foi deixada de fora de propósito, para o modelo não aprender o horário de quem dirige no lugar do alagamento.
- **Ainda não prevê em tempo real:** o INMET publica com atraso. As previsões em `gold.previsao_alagamento` cobrem o período histórico. Para o painel, a chuva do momento
  teria de vir do COP ou do CEMADEN, e essa troca precisa ser validada.

## Perguntas para discussão

1. **Qual coluna entregaria a resposta?** `rotas_alagadas_futuro`, usada para calcular o alvo, acertaria 100% e não existe na hora de prever. Por isso ela nunca entra no modelo, e há testes
   que verificam que chuva e alagamento futuros não alteram as variáveis da hora.
2. **Acurácia de 80% significa que o modelo é bom em tudo?** Não. O recall de alagamento é de 67%, contra 89% de "sem alagamento": a acurácia de 82,5% esconde que ele perde um terço dos casos que mais importam.
3. **Por que a árvore sem limite não se repete no teste?** Ela chega a 100% no treino porque decora as horas, e cai para 78,6% na validação e 82,1% no teste. Com 4 níveis, as regras servem também para horas novas.
4. **Qual mudança teve maior impacto?** Usar várias janelas de chuva em vez de só 24 h: a validação subiu de 79,4% para 83,2%, com a chuva de 12 h como a variável mais importante. Maré e parâmetros mudaram menos de 1 ponto.
