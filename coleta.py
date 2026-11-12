"""
Coleta de dados da API Olho Vivo (SPTrans)

Passo 1 do projeto: perguntar à API onde estão todos os ônibus de SP
agora e salvar um resumo (quantos ônibus estão rodando em cada linha)
num arquivo CSV. Cada vez que o script roda, ele ADICIONA novas linhas
ao CSV, e é assim que o histórico vai crescendo dia após dia.

Como rodar:
    1. pip install requests
    2. Defina a variável de ambiente SPTRANS_TOKEN com o seu token
    3. python coleta.py
"""

import csv
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

# ---------------------------------------------------------------
# CONFIGURAÇÕES (coisas que não mudam enquanto o programa roda)
# ---------------------------------------------------------------
URL_BASE ="https://api.olhovivo.sptrans.com.br/v2.1"
PASTA_DADOS = "dados"
ARQUIVO_CSV = os.path.join(PASTA_DADOS, "onibus_por_linha.csv")
FUSO_SP = ZoneInfo("America/Sao_Paulo")
DIAS_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]

COLUNAS = [
    "data_hora",     # momento da coleta (horário de SP)
    "dia_semana",    # segunda, terça...
    "hora",          # 0 a 23, facilita ver horário de pico depois
    "letreiro",      # ex: 875A-10
    "codigo_linha",  # código interno da SPTrans
    "sentido",       # 1 ou 2 (ida/volta)
    "terminal_0",    # letreiro de um lado da linha
    "terminal_1",    # letreiro do outro lado
    "qtd_onibus",    # quantos ônibus da linha estão rodando agora
]


# ---------------------------------------------------------------
# FUNÇÕES (cada uma faz UMA coisa só)
# ---------------------------------------------------------------
def pegar_token():
    """Lê o token da variável de ambiente (nunca escreva o token no código!)."""
    token = os.environ.get("SPTRANS_TOKEN", "").strip().strip('"')
    if not token:
        print("Erro: defina a variável de ambiente SPTRANS_TOKEN com o seu token.")
        sys.exit(1)
    return token


def autenticar(sessao, token):
    """A API exige um login antes de qualquer consulta. Ela responde true ou false."""
    resposta = sessao.post(f"{URL_BASE}/Login/Autenticar", params={"token": token}, timeout=30)
    resposta.raise_for_status()  # dá erro se a API respondeu com falha (ex: 500)
    if resposta.json() is not True:
        print("Erro: a autenticação falhou. Confira se o token está certo.")
        sys.exit(1)


def buscar_posicoes(sessao):
    """Pega a posição de TODOS os ônibus da cidade neste momento."""
    resposta = sessao.get(f"{URL_BASE}/Posicao", timeout=60)
    resposta.raise_for_status()
    return resposta.json()


def montar_registros(dados, agora):
    """Transforma o JSON da API em uma lista de dicionários (uma linha do CSV cada)."""
    registros = []
    for linha in dados["l"]:  # "l" é a lista de linhas que a API devolve
        registros.append({
            "data_hora": agora.strftime("%Y-%m-%d %H:%M"),
            "dia_semana": DIAS_SEMANA[agora.weekday()],
            "hora": agora.hour,
            "letreiro": linha["c"],
            "codigo_linha": linha["cl"],
            "sentido": linha["sl"],
            "terminal_0": linha["lt0"],
            "terminal_1": linha["lt1"],
            "qtd_onibus": linha["qv"],
        })
    return registros


def salvar_csv(registros):
    """Adiciona os registros no final do CSV. Se o arquivo não existe, cria com cabeçalho."""
    os.makedirs(PASTA_DADOS, exist_ok=True)
    arquivo_ja_existe = os.path.exists(ARQUIVO_CSV)

    with open(ARQUIVO_CSV, "a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        if not arquivo_ja_existe:
            escritor.writeheader()
        escritor.writerows(registros)


# ---------------------------------------------------------------
# PROGRAMA PRINCIPAL (só chama as funções na ordem certa)
# ---------------------------------------------------------------
def main():
    token = pegar_token()
    agora = datetime.now(FUSO_SP)

    sessao = requests.Session()  # a sessão guarda o "login" entre as chamadas
    autenticar(sessao, token)
    dados = buscar_posicoes(sessao)

    registros = montar_registros(dados, agora)
    salvar_csv(registros)

    total_onibus = sum(r["qtd_onibus"] for r in registros)
    print(f"[{agora:%d/%m %H:%M}] {len(registros)} linhas, {total_onibus} ônibus rodando. Salvo em {ARQUIVO_CSV}")


if __name__ == "__main__":
    main()
