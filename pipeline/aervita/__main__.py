"""Ponto de entrada do pipeline: python -m aervita <comando> [opções].

Cada comando aponta para um módulo; novos comandos entram só neste mapa.
"""

from importlib import import_module
import runpy
import sys

COMANDOS = {
    "territorio": ("aervita.ingestao.fontes.territorio", "bairros, RPAs e distritos sanitários (Dados Abertos Recife)"),
    "arboviroses": ("aervita.ingestao.fontes.epidemiologia", "notificações de dengue, zika e chikungunya do ano"),
    "arboviroses-historico": ("aervita.ingestao.fontes.epidemiologia_historico", "carga única das arboviroses de 2013 a 2024"),
    "cop": ("aervita.ingestao.fontes.cop_recife", "camadas do COP Recife (exige acesso liberado e IP do Brasil)"),
    "inmet": ("aervita.ingestao.fontes.inmet", "chuva horária do INMET, estação A301"),
    "coletar": ("aervita.ingestao.nucleo.runner", "só grava a RAW de uma fonte registrada"),
    "gold": ("aervita.processamento.gold", "recalcula a camada Gold"),
    "treino": ("aervita.predicao.train", "treina e avalia o modelo de alagamento e grava na Gold"),
    "experimentos": ("aervita.predicao.experimentos", "compara as tentativas de modelo"),
    "analise-mare": ("aervita.predicao.analise_mare", "efeito da maré no modelo"),
    "diario": ("aervita.diario", "execução agendada: fontes + Gold, com registro em gold.execucao_pipeline"),
}
SCRIPTS = {"treino", "experimentos", "analise-mare"}


def ajuda() -> str:
    largura = max(map(len, COMANDOS))
    linhas = [f"  {nome.ljust(largura)}  {descricao}" for nome, (_, descricao) in COMANDOS.items()]
    return "uso: python -m aervita <comando> [opções]\n\ncomandos:\n" + "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        fluxo.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help") or argv[0] not in COMANDOS:
        print(ajuda())
        return 0 if not argv or argv[0] in ("-h", "--help") else 2
    comando, resto = argv[0], argv[1:]
    modulo = COMANDOS[comando][0]
    if comando in SCRIPTS:
        sys.argv = [f"aervita {comando}", *resto]
        runpy.run_module(modulo, run_name="__main__")
        return 0
    return import_module(modulo).main(resto)


if __name__ == "__main__":
    raise SystemExit(main())
