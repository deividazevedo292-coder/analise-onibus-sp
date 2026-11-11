"""
Gera um CSV de EXEMPLO, no mesmo formato do coleta.py, para testar o
dashboard enquanto a coleta real ainda não começou.

Simula 7 dias de coleta (de hora em hora) para 80 linhas fictícias,
com pico de manhã e à tarde em dias úteis e frota menor no fim de semana.

Como rodar:
    python gerar_exemplo.py
"""

import math
import os
import random
from datetime import datetime, timedelta

import pandas as pd

ARQUIVO_SAIDA = os.path.join("dados", "exemplo_onibus_por_linha.csv")
DIAS_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
TERMINAIS = [
    "Term. Pq. D. Pedro II", "Term. Lapa", "Term. Pinheiros", "Term. Santo Amaro", "Metrô Jabaquara",
    "Term. Penha", "Term. Itaquera", "Metrô Vila Mariana", "Term. Pirituba", "Term. Capelinha",
    "Term. Grajaú", "Term. Sacomã", "Metrô Tatuapé", "Term. Bandeira", "Term. Princesa Isabel",
    "Term. Vila Carrão", "Term. Casa Verde", "Term. Campo Limpo", "Metrô Butantã", "Term. Cachoeirinha",
]

# Proporção da frota rodando em cada hora de um dia útil (0h até 23h)
PERFIL_DIA_UTIL = [0.12, 0.08, 0.06, 0.07, 0.35, 0.75, 0.98, 1.0, 0.92, 0.75, 0.68, 0.66,
                   0.67, 0.66, 0.68, 0.75, 0.9, 1.0, 0.97, 0.82, 0.62, 0.48, 0.32, 0.2]


def criar_linhas(quantidade):
    """Cria linhas fictícias, cada uma com letreiro, terminais e tamanho de frota."""
    linhas, usados = [], set()
    while len(linhas) < quantidade:
        letreiro = f"{random.randint(100, 999)}{random.choice(['', 'A', 'M', 'P'])}-{random.choice([10, 10, 21, 31])}"
        if letreiro in usados:
            continue
        usados.add(letreiro)
        terminal_0, terminal_1 = random.sample(TERMINAIS, 2)
        linhas.append({
            "letreiro": letreiro,
            "codigo_linha": 30000 + len(linhas) * 7,
            "terminal_0": terminal_0,
            "terminal_1": terminal_1,
            "frota": random.choice([4, 6, 8, 10, 12, 15, 18, 22, 28, 35, 42]),
            "noturna": random.random() < 0.15,
        })
    return linhas


def proporcao_rodando(data, hora, noturna):
    """Quanto da frota está na rua nesse dia e hora."""
    if data.weekday() < 5:  # dia útil
        proporcao = PERFIL_DIA_UTIL[hora]
    elif 5 <= hora <= 23:   # fim de semana: pico menor, perto do meio-dia
        fator = 0.72 if data.weekday() == 5 else 0.52
        proporcao = (0.25 + 0.6 * math.exp(-((hora - 13) ** 2) / 40)) * fator
    else:
        proporcao = PERFIL_DIA_UTIL[hora] * 0.6
    if noturna and hora < 5:
        proporcao = max(proporcao, 0.5)
    return proporcao


def gerar_registros(linhas, inicio, dias):
    registros = []
    for d in range(dias):
        data = inicio + timedelta(days=d)
        for hora in range(24):
            for linha in linhas:
                for sentido in (1, 2):
                    qtd = round(linha["frota"] * proporcao_rodando(data, hora, linha["noturna"]) * random.uniform(0.85, 1.15))
                    if qtd == 0:
                        continue
                    registros.append({
                        "data_hora": f"{data:%Y-%m-%d} {hora:02d}:00",
                        "dia_semana": DIAS_SEMANA[data.weekday()],
                        "hora": hora,
                        "letreiro": linha["letreiro"],
                        "codigo_linha": linha["codigo_linha"] + sentido - 1,
                        "sentido": sentido,
                        "terminal_0": linha["terminal_0"],
                        "terminal_1": linha["terminal_1"],
                        "qtd_onibus": qtd,
                    })
    return registros


def main():
    random.seed(42)  # sempre gera os mesmos dados de exemplo
    linhas = criar_linhas(80)
    inicio = datetime.now() - timedelta(days=7)
    registros = gerar_registros(linhas, inicio.replace(hour=0, minute=0), dias=7)

    os.makedirs("dados", exist_ok=True)
    pd.DataFrame(registros).to_csv(ARQUIVO_SAIDA, index=False)
    print(f"{len(registros)} registros de exemplo salvos em {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()
