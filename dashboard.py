"""
Dashboard da frota de ônibus de São Paulo (Streamlit)

Lê o CSV gerado pelo coleta.py e mostra:
- números gerais da última coleta
- em que horário há mais ônibus rodando (dia útil x fim de semana)
- a frota média por dia da semana
- as linhas com mais ônibus
- a evolução de uma linha escolhida

Enquanto não existirem dados reais, usa um arquivo de EXEMPLO.

Como rodar:
    pip install -r requirements.txt
    streamlit run dashboard.py
"""

import os

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------
# CONFIGURAÇÕES
# ---------------------------------------------------------------
ARQUIVO_REAL = os.path.join("dados", "onibus_por_linha.csv")
ARQUIVO_EXEMPLO = os.path.join("dados", "exemplo_onibus_por_linha.csv")
ORDEM_DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


# ---------------------------------------------------------------
# FUNÇÕES
# ---------------------------------------------------------------
@st.cache_data(ttl=600)  # guarda os dados por 10 minutos para não reler o CSV toda hora
def carregar_dados():
    """Lê o CSV real; se ainda não existir, usa o de exemplo."""
    if os.path.exists(ARQUIVO_REAL):
        caminho, eh_exemplo = ARQUIVO_REAL, False
    else:
        caminho, eh_exemplo = ARQUIVO_EXEMPLO, True

    df = pd.read_csv(caminho)
    df["data_hora"] = pd.to_datetime(df["data_hora"])
    df["data"] = df["data_hora"].dt.date
    df["tipo_dia"] = df["dia_semana"].apply(
        lambda dia: "Fim de semana" if dia in ("sábado", "domingo") else "Dia útil"
    )
    return df, eh_exemplo


def total_por_coleta(df):
    """Soma os ônibus de todas as linhas em cada coleta (cada hora registrada)."""
    return (
        df.groupby(["data_hora", "data", "hora", "dia_semana", "tipo_dia"], as_index=False)["qtd_onibus"]
        .sum()
        .rename(columns={"qtd_onibus": "total_onibus"})
    )


def mostrar_aviso_coleta(totais):
    """Avisa que o histórico ainda é curto (menos de 2 dias de coleta)."""
    inicio = totais["data_hora"].min()
    fim = totais["data_hora"].max()
    horas_de_coleta = (fim - inicio).total_seconds() / 3600
    quantidade_coletas = totais["data_hora"].nunique()

    if horas_de_coleta < 48:
        st.info(
            f"⏳ Coletando dados desde {inicio:%d/%m às %H:%M} "
            f"({quantidade_coletas} coletas até agora). "
            "Os gráficos ficam completos após alguns dias de histórico."
        )



def mostrar_numeros_gerais(df, totais):
    ultima = totais.sort_values("data_hora").iloc[-1]
    linhas_ativas = df[df["data_hora"] == ultima["data_hora"]]["letreiro"].nunique()

    col1, col2, col3 = st.columns(3)
    col1.metric("Ônibus na última coleta", f"{int(ultima['total_onibus']):,}".replace(",", "."))
    col2.metric("Linhas rodando", linhas_ativas)
    col3.metric("Dias de histórico", df["data"].nunique())
    st.caption(f"Última coleta: {ultima['data_hora']:%d/%m/%Y às %H:%M}")


def mostrar_horario_de_pico(totais):
    st.subheader("Em que horário há mais ônibus na rua?")
    media = totais.groupby(["hora", "tipo_dia"])["total_onibus"].mean().unstack()
    st.line_chart(media, x_label="Hora do dia", y_label="Média de ônibus rodando")

    pico = media["Dia útil"].idxmax() if "Dia útil" in media else media.iloc[:, 0].idxmax()
    st.write(f"Em dias úteis, o pico da frota acontece por volta das **{pico}h**.")


def mostrar_por_dia_da_semana(totais):
    st.subheader("Frota média por dia da semana")
    por_dia = (
        totais.groupby("dia_semana")["total_onibus"].mean()
        .reindex(ORDEM_DIAS)
        .dropna()
        .round()
    )
    st.bar_chart(por_dia, x_label="Dia da semana", y_label="Média de ônibus por hora")


def mostrar_top_linhas(df):
    st.subheader("Linhas com mais ônibus em circulação")
    top = (
        df.groupby("letreiro")["qtd_onibus"].mean()
        .sort_values(ascending=False)
        .head(10)
        .round(1)
    )
    st.bar_chart(top, horizontal=True, x_label="Média de ônibus", y_label="Linha")


def mostrar_linha_escolhida(df):
    st.subheader("Acompanhe uma linha")

    # Monta um nome legível para cada linha: "875A-10 | Term. Lapa ↔ Metrô Butantã"
    nomes = (
        df.drop_duplicates("letreiro")
        .assign(nome=lambda d: d["letreiro"] + " | " + d["terminal_0"] + " ↔ " + d["terminal_1"])
        .sort_values("letreiro")
    )
    escolhida = st.selectbox(
        "Digite o código da linha ou o nome de um bairro/terminal",
        nomes["nome"],
    )
    letreiro = escolhida.split(" | ")[0]

    evolucao = df[df["letreiro"] == letreiro].groupby("data_hora")["qtd_onibus"].sum()
    st.line_chart(evolucao, x_label="Data e hora", y_label="Ônibus rodando")

# ---------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ---------------------------------------------------------------
def main():
    st.set_page_config(page_title="Ônibus de SP", page_icon="🚌", layout="wide")
    st.title("🚌 Frota de ônibus de São Paulo")
    st.write("Dados coletados automaticamente a cada hora da API Olho Vivo (SPTrans).")

    df, eh_exemplo = carregar_dados()
    if eh_exemplo:
        st.warning("Exibindo **dados de exemplo** enquanto a coleta real ainda não começou.")

    totais = total_por_coleta(df)
    if not eh_exemplo:
        mostrar_aviso_coleta(totais)

    mostrar_numeros_gerais(df, totais)
    st.divider()
    mostrar_horario_de_pico(totais)
    col_esq, col_dir = st.columns(2)
    with col_esq:
        mostrar_por_dia_da_semana(totais)
    with col_dir:
        mostrar_top_linhas(df)
    st.divider()
    mostrar_linha_escolhida(df)


if __name__ == "__main__":
    main()
