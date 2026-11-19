"""
Mapa ao vivo dos ônibus de São Paulo (API Olho Vivo da SPTrans)

Mostra num mapa onde cada ônibus está AGORA e atualiza sozinho a cada 30 segundos.

Como funciona, em 3 passos:
    1. Faz login na API com o seu token (igual ao coleta.py)
    2. Pede a posição de todos os ônibus (endpoint /Posicao)
    3. Transforma a resposta numa tabela e desenha os pontos no mapa

Onde colocar este arquivo:
    projeto analise de dados/
        dashboard.py
        pages/
            1_Mapa_ao_vivo.py   <- aqui

O Streamlit cria sozinho um menu lateral com a página nova.
"""

import os

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

# ------------------------------------------------------------
# CONFIGURAÇÕES
# ------------------------------------------------------------
URL_BASE = "https://api.olhovivo.sptrans.com.br/v2.1"
SEGUNDOS_ENTRE_ATUALIZACOES = 30
CENTRO_SP = {"latitude": -23.55, "longitude": -46.63}


# ------------------------------------------------------------
# 1. LOGIN NA API
# ------------------------------------------------------------
def pegar_token():
    """Procura o token primeiro nos secrets do Streamlit, depois na variável de ambiente."""
    try:
        return st.secrets["SPTRANS_TOKEN"]
    except Exception:
        return os.getenv("SPTRANS_TOKEN")


class ErroAPI(Exception):
    """Erro com uma mensagem explicando o que deu errado."""


@st.cache_resource
def criar_sessao():
    """
    Faz login uma vez e guarda a sessão.
    A API guarda o login num cookie, e o requests.Session() manda esse cookie
    de volta em todo pedido seguinte.

    Quando dá erro, a função LANÇA uma exceção em vez de devolver None.
    Assim o Streamlit não guarda o erro no cache e tenta de novo na próxima vez.
    """
    token = pegar_token()
    if not token:
        raise ErroAPI("Token não encontrado. Crie o arquivo .streamlit/secrets.toml com SPTRANS_TOKEN.")

    sessao = requests.Session()
    try:
        resposta = sessao.post(f"{URL_BASE}/Login/Autenticar", params={"token": token}, timeout=15)
    except requests.RequestException as erro:
        raise ErroAPI(f"Não consegui conectar na API: {erro}")

    # A API responde o texto "true" quando o login dá certo
    if resposta.text.strip().lower() != "true":
        raise ErroAPI(f"A API recusou o login (resposta: {resposta.text[:100]!r}). Confira se o token está certo.")
    return sessao


# ------------------------------------------------------------
# 2. BUSCAR AS POSIÇÕES
# ------------------------------------------------------------
@st.cache_data(ttl=SEGUNDOS_ENTRE_ATUALIZACOES)
def buscar_posicoes():
    """
    Pede a posição de todos os ônibus e devolve uma tabela (DataFrame).

    A resposta da API tem este formato (resumido):
    {
      "hr": "08:35",                      <- horário da informação
      "l": [                              <- lista de linhas
        {
          "c": "875A-10",                 <- letreiro
          "sl": 1,                        <- sentido
          "lt0": "...", "lt1": "...",     <- terminais
          "vs": [                         <- ônibus dessa linha
            {"p": 12345, "py": -23.5, "px": -46.6, "ta": "...", "a": true}
          ]
        }
      ]
    }
    """
    sessao = criar_sessao()

    try:
        resposta = sessao.get(f"{URL_BASE}/Posicao", timeout=30)
    except requests.RequestException as erro:
        raise ErroAPI(f"Não consegui buscar as posições: {erro}")

    # Se o login expirou, a API devolve erro: limpa a sessão pra logar de novo na próxima vez
    if resposta.status_code != 200:
        criar_sessao.clear()
        raise ErroAPI(f"A API devolveu o código {resposta.status_code} ao buscar as posições.")

    dados = resposta.json()

    # "Achatar" a resposta: uma linha da tabela para cada ônibus
    onibus = []
    for linha in dados.get("l", []):
        destino = linha["lt1"] if linha["sl"] == 1 else linha["lt0"]
        for veiculo in linha.get("vs", []):
            onibus.append({
                "letreiro": linha["c"],
                "destino": destino,
                "prefixo": veiculo["p"],
                "latitude": veiculo["py"],
                "longitude": veiculo["px"],
                "acessivel": "Sim" if veiculo.get("a") else "Não",
            })

    return pd.DataFrame(onibus), dados.get("hr")



# ------------------------------------------------------------
# 3. TELA SIMPLES, PENSADA PARA QUEM NÃO MEXE MUITO COM TECNOLOGIA
#    Ideia: uma pergunta de cada vez, letra grande, nada de número técnico.
# ------------------------------------------------------------
CSS_LETRA_GRANDE = """
<style>
    html, body, [class*="css"], p, label, div { font-size: 20px; }
    h1 { font-size: 40px !important; }
    h2, h3 { font-size: 28px !important; }
    /* Opções da escolha de sentido maiores e espaçadas */
    div[role="radiogroup"] label { padding: 10px 0; font-size: 22px; }
    /* Botões "Ver no mapa" grandes, fáceis de tocar no celular */
    a[data-testid="stBaseLinkButton-secondary"], a[data-testid="stBaseLinkButton-primary"] {
        font-size: 20px; padding: 14px; width: 100%;
    }
</style>
"""


def ICONE_ONIBUS():
    """Emoji de ônibus dentro de um círculo branco com borda azul, para destacar no mapa."""
    return folium.DivIcon(
        html=(
            "<div style='font-size:26px; width:42px; height:42px; line-height:38px; text-align:center;"
            " background:white; border:3px solid #1d6fcc; border-radius:50%;"
            " box-shadow:0 2px 6px rgba(0,0,0,0.35);'>🚌</div>"
        ),
        icon_size=(42, 42),
        icon_anchor=(21, 21),   # o centro do círculo fica exatamente onde o ônibus está
    )


def desenhar_mapa(tabela):
    """
    Mapa no estilo que todo mundo já conhece (parecido com o Google Maps):
    ruas com nome e um emoji 🚌 em cada ônibus.
    Tocando no emoji aparece o número do ônibus.
    """
    mapa = folium.Map(tiles="OpenStreetMap", control_scale=False)

    for _, onibus in tabela.iterrows():
        folium.Marker(
            location=[onibus["latitude"], onibus["longitude"]],
            tooltip=f"Ônibus {onibus['numero']}",
            popup=folium.Popup(f"<b style='font-size:18px'>Ônibus {onibus['numero']}</b>", max_width=220),
            icon=ICONE_ONIBUS(),
        ).add_to(mapa)

    # Dá zoom automático para mostrar todos os ônibus da linha na tela
    canto_sudoeste = [tabela["latitude"].min(), tabela["longitude"].min()]
    canto_nordeste = [tabela["latitude"].max(), tabela["longitude"].max()]
    mapa.fit_bounds([canto_sudoeste, canto_nordeste], padding=(40, 40), max_zoom=16)

    # returned_objects=[] -> o mapa não recarrega a página quando a pessoa mexe nele
    st_folium(mapa, height=450, use_container_width=True, returned_objects=[], key="mapa_onibus")


def link_google_maps(onibus):
    return f"https://www.google.com/maps?q={onibus['latitude']},{onibus['longitude']}"


# ------------------------------------------------------------
# PÁGINA
# ------------------------------------------------------------
st.set_page_config(page_title="Onde está meu ônibus?", layout="centered", initial_sidebar_state="collapsed")
st.markdown(CSS_LETRA_GRANDE, unsafe_allow_html=True)
st.title("Onde está meu ônibus?")

try:
    tabela_inicial, _ = buscar_posicoes()
except ErroAPI:
    st.error("O serviço de ônibus não respondeu agora. Tente de novo em alguns minutos.")
    st.stop()

# --- PERGUNTA 1: qual linha? ---------------------------------
st.subheader("1. Qual ônibus você vai pegar?")
linhas = sorted(tabela_inicial["letreiro"].unique())
linha = st.selectbox(
    "Toque aqui e digite o número que aparece na frente do ônibus",
    linhas,
    index=None,
    placeholder="Exemplo: 875A",
)

if linha is None:
    st.info("O número fica no letreiro, na frente do ônibus. Exemplo: **875A-10**.")
    st.stop()

# --- PERGUNTA 2: para onde? ----------------------------------
destinos = sorted(tabela_inicial.loc[tabela_inicial["letreiro"] == linha, "destino"].unique())

st.subheader("2. Para onde você vai?")
if len(destinos) == 1:
    destino = destinos[0]
    st.write(f"Esse ônibus vai para **{destino.title()}**.")
else:
    destino = st.radio(
        "Escolha o final da linha",
        destinos,
        format_func=lambda d: f"Indo para {d.title()}",
        label_visibility="collapsed",
    )


# --- RESPOSTA: onde estão os ônibus (atualiza sozinho) --------
@st.fragment(run_every=SEGUNDOS_ENTRE_ATUALIZACOES)
def resposta():
    try:
        tabela, horario = buscar_posicoes()
    except ErroAPI:
        st.error("O serviço de ônibus não respondeu agora. Tente de novo em alguns minutos.")
        return

    onibus = tabela[(tabela["letreiro"] == linha) & (tabela["destino"] == destino)]
    # Numera os ônibus 1, 2, 3... (mais fácil que o número de frota, tipo 16079)
    onibus = onibus.reset_index(drop=True)
    onibus["numero"] = onibus.index + 1

    st.subheader("3. Onde eles estão agora")

    if onibus.empty:
        st.warning("Nenhum ônibus dessa linha está rodando nesse sentido agora.")
        return

    quantidade = len(onibus)
    texto = "1 ônibus está" if quantidade == 1 else f"{quantidade} ônibus estão"
    st.success(f"**{texto} indo para {destino.title()} agora.** Cada 🚌 no mapa é um ônibus de verdade, onde ele está agora.")

    desenhar_mapa(onibus)

    st.write("**Quer ver mais de perto?** Toque em um ônibus para abrir no Google Maps:")
    for _, cada in onibus.iterrows():
        rotulo = f"📍 Abrir o ônibus {cada['numero']} no Google Maps"
        if cada["acessivel"] == "Sim":
            rotulo += " ♿ acessível para cadeira de rodas"
        st.link_button(rotulo, link_google_maps(cada), use_container_width=True)

    st.write(f"🔄 Os ônibus mudam de lugar sozinhos no mapa. Última atualização: **{horario}**.")


resposta()
