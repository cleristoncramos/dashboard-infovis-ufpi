"""Perfil por Estado: como uma UF se compara ao restante do país."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from painel.base import (
    CINZA, CINZA_ESCURO, EIXO, MEDIDAS, NOME_UF, PRIMARIA, TINTA, TINTA_SECUNDARIA, VERMELHAO,
    aplicar_selecoes, barra_de_selecoes, cabecalho, colunas_mensais, exportar_csv, filtros_globais,
    fmt_brl, fmt_medida, fmt_num, fmt_pct, grafico_estatico, grafico_interativo, hover_medida,
    np_coluna, opacidades, prefixo_eixo, rotulo_mes, secao, sem_dados, valores_do_evento,
)

UF_PADRAO = "PI"


def _trocar_uf():
    # Clicar em outra UF no ranking passa a analisá-la (linking com todo o perfil)
    valores, _, _ = valores_do_evento("g_perfil_ranking")
    if valores:
        st.session_state.f_uf = sorted(valores)[0]


def _variacao_anual(df, medida):
    totais = df.groupby("ano")[medida].sum()
    if len(totais) < 2 or totais.iloc[-2] == 0:
        return None
    return (totais.iloc[-1] / totais.iloc[-2] - 1) * 100


def indicadores(uf, nacional, nacional_anos, medida):
    por_uf = nacional.groupby("estado")[medida].sum().sort_values(ascending=False)
    total_uf = por_uf.get(uf, 0)
    media_ufs = por_uf.mean()
    posicao = list(por_uf.index).index(uf) + 1 if uf in por_uf.index else None
    dados_uf = nacional[nacional["estado"] == uf]
    ticket_uf = dados_uf["valor"].sum() / dados_uf["atendimentos"].sum() if len(dados_uf) else 0
    ticket_br = nacional["valor"].sum() / nacional["atendimentos"].sum() if len(nacional) else 0
    var_uf = _variacao_anual(nacional_anos[nacional_anos["estado"] == uf], medida)
    var_br = _variacao_anual(nacional_anos, medida)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(MEDIDAS[medida], fmt_medida(total_uf, medida),
              delta=fmt_pct((total_uf / media_ufs - 1) * 100, sinal=True) if media_ufs else None,
              delta_description="vs média das UFs")
    c2.metric("Participação no país", fmt_pct(total_uf / por_uf.sum() * 100 if por_uf.sum() else 0),
              help="Fatia da UF no total nacional do recorte")
    c3.metric("Posição no ranking", f"{posicao}º de {len(por_uf)}" if posicao else "—")
    c4.metric("Custo por atendimento", fmt_brl(ticket_uf), delta_color="inverse",
              delta=fmt_pct((ticket_uf / ticket_br - 1) * 100, sinal=True) if ticket_br else None,
              delta_description="vs Brasil")
    c5.metric("Variação anual", fmt_pct(var_uf, sinal=True) if var_uf is not None else "—",
              delta=f"{var_uf - var_br:+.1f} p.p.".replace(".", ",", 1) if var_uf is not None and var_br is not None else None,
              delta_description="vs Brasil",
              help="Último ano frente ao anterior (ignora o filtro de ano)")
    return por_uf, posicao, ticket_uf, ticket_br, var_uf


def grafico_evolucao(uf, nacional, medida):
    mensal = nacional.groupby(["data", "mes"]).agg(total=(medida, "sum"), ufs=("estado", "nunique")).reset_index()
    mensal["media_ufs"] = mensal["total"] / mensal["ufs"]
    da_uf = nacional[nacional["estado"] == uf].groupby("data")[medida].sum()
    mensal["uf"] = mensal["data"].map(da_uf).fillna(0)
    if mensal.empty:
        cabecalho(f"{uf} acompanha a média do país?")
        return sem_dados()
    acima = int((mensal["uf"] > mensal["media_ufs"]).sum())
    cabecalho(f"{uf} acompanha a média do país?",
              f"<b>{uf}</b> ficou acima da média das UFs em <b>{acima} de {len(mensal)}</b> meses.")
    rotulos = [rotulo_mes(m) for m in mensal["mes"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=mensal["data"], y=mensal["media_ufs"], name="Média das UFs", mode="lines",
                             line=dict(color=CINZA_ESCURO, width=2, dash="dash"), customdata=rotulos,
                             hovertemplate=f"Média das UFs: {hover_medida(medida)}<extra></extra>"))
    fig.add_trace(go.Scatter(x=mensal["data"], y=mensal["uf"], name=NOME_UF[uf], mode="lines+markers",
                             line=dict(color=PRIMARIA, width=2), marker=dict(size=6),
                             hovertemplate=f"{uf}: {hover_medida(medida)}<extra></extra>"))
    valores, textos = colunas_mensais(mensal["data"])
    fig.update_layout(height=340, hovermode="x unified", margin=dict(l=10, r=10, t=30, b=10),
                      xaxis=dict(tickvals=valores, ticktext=textos),
                      yaxis=dict(tickformat="~s", tickprefix=prefixo_eixo(medida)))
    grafico_estatico(fig, "g_perfil_evolucao", nome_arquivo=f"evolucao_{uf}")
    exportar_csv(mensal.assign(mes=rotulos)[["mes", "uf", "media_ufs"]].rename(columns={"uf": uf}).round(2),
                 f"evolucao_{uf}")


def grafico_composicao(uf, base, medida):
    dados = base.groupby(["categoria"]).agg(brasil=(medida, "sum")).reset_index()
    dados["uf"] = dados["categoria"].map(base[base["estado"] == uf].groupby("categoria")[medida].sum()).fillna(0)
    if dados["uf"].sum() == 0:
        cabecalho(f"Em quais áreas {uf} se concentra?")
        return sem_dados()
    dados["pct_uf"] = dados["uf"] / dados["uf"].sum() * 100
    dados["pct_br"] = dados["brasil"] / dados["brasil"].sum() * 100
    dados["diferenca"] = dados["pct_uf"] - dados["pct_br"]
    dados = dados.sort_values("pct_uf")
    destaque_area = dados.loc[dados["diferenca"].abs().idxmax()]
    cabecalho(f"Em quais áreas {uf} se concentra?",
              f"Maior diferença: <b>{destaque_area['categoria']}</b> pesa {fmt_pct(destaque_area['pct_uf'])} em {uf} "
              f"contra {fmt_pct(destaque_area['pct_br'])} no Brasil "
              f"({fmt_num(destaque_area['diferenca'], 1)} p.p.). Clique numa área para filtrar o perfil.")
    opac = opacidades(dados["categoria"], "categorias")
    fig = go.Figure()
    for _, linha in dados.iterrows():
        fig.add_shape(type="line", x0=linha["pct_br"], x1=linha["pct_uf"], y0=linha["categoria"],
                      y1=linha["categoria"], line=dict(color=EIXO, width=2))
    fig.add_trace(go.Scatter(
        x=dados["pct_br"], y=dados["categoria"], mode="markers", name="Brasil",
        marker=dict(size=12, color="white", line=dict(color=CINZA_ESCURO, width=2), opacity=opac),
        customdata=np_coluna(dados["categoria"]),
        hovertemplate="<b>%{y}</b><br>Brasil: %{x:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dados["pct_uf"], y=dados["categoria"], mode="markers+text", name=uf,
        marker=dict(size=14, color=PRIMARIA, line=dict(color="white", width=2), opacity=opac),
        # Rótulo do lado oposto ao ponto do Brasil, para não sobrepor os marcadores
        text=[fmt_pct(v) for v in dados["pct_uf"]],
        textposition=["middle right" if u >= b else "middle left" for u, b in zip(dados["pct_uf"], dados["pct_br"])],
        textfont=dict(size=12, color=TINTA_SECUNDARIA), cliponaxis=False,
        customdata=np_coluna(dados["categoria"]),
        hovertemplate=f"<b>%{{y}}</b><br>{uf}: %{{x:.1f}}%<extra></extra>",
    ))
    amplitude = max(dados[["pct_uf", "pct_br"]].max().max() - dados[["pct_uf", "pct_br"]].min().min(), 1)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10),
                      xaxis=dict(ticksuffix="%", showgrid=True, gridcolor="#EEF1F4",
                                 range=[dados[["pct_uf", "pct_br"]].min().min() - amplitude * 0.25,
                                        dados[["pct_uf", "pct_br"]].max().max() + amplitude * 0.25]),
                      yaxis=dict(showgrid=False, tickfont=dict(color=TINTA)))
    grafico_interativo(fig, "g_perfil_composicao", "categorias", nome_arquivo=f"composicao_{uf}")
    exportar_csv(dados[["categoria", "pct_uf", "pct_br", "diferenca"]].rename(columns={"pct_uf": f"pct_{uf}"}).round(2),
                 f"composicao_{uf}")


def grafico_posicao(uf, por_uf, medida, posicao):
    if por_uf.empty:
        cabecalho("Onde a UF está entre as demais?")
        return sem_dados()
    cabecalho("Onde a UF está entre as demais?",
              f"<b>{uf}</b> ocupa a <b>{posicao}ª posição</b>. Clique em outra UF para analisá-la.")
    dados = por_uf.sort_values().reset_index()
    dados.columns = ["estado", "total"]
    fig = go.Figure(go.Bar(
        x=dados["total"], y=dados["estado"], orientation="h",
        marker=dict(color=[PRIMARIA if e == uf else CINZA for e in dados["estado"]]),
        text=[fmt_medida(v, medida) if e == uf else "" for e, v in zip(dados["estado"], dados["total"])],
        textposition="outside", textfont=dict(color=TINTA, size=12), cliponaxis=False,
        customdata=np_coluna(dados["estado"]),
        hovertemplate=f"<b>%{{y}}</b><br>{MEDIDAS[medida]}: {hover_medida(medida, 'x')}<extra></extra>",
    ))
    fig.update_layout(height=19 * len(dados) + 40, bargap=0.25, margin=dict(l=10, r=60, t=10, b=10),
                      xaxis=dict(visible=False),
                      yaxis=dict(showgrid=False, ticks="", tickfont=dict(color=TINTA)))
    grafico_interativo(fig, "g_perfil_ranking", modos=("points",), callback=_trocar_uf,
                       nome_arquivo="posicao_entre_ufs")
    exportar_csv(dados.sort_values("total", ascending=False).round(2), "posicao_entre_ufs")


def grafico_variacao_areas(uf, nacional_anos, medida):
    anos = sorted(nacional_anos["ano"].unique())
    if len(anos) < 2:
        cabecalho("Quais áreas cresceram na UF?")
        return st.info("São necessários dois anos para calcular a variação.")
    a0, a1 = anos[-2], anos[-1]

    def variacao(df):
        t = df.pivot_table(index="categoria", columns="ano", values=medida, aggfunc="sum")
        return (t[a1] / t[a0] - 1) * 100

    dados = pd.DataFrame({"uf": variacao(nacional_anos[nacional_anos["estado"] == uf]),
                          "brasil": variacao(nacional_anos)}).dropna().sort_values("uf").reset_index()
    if dados.empty:
        cabecalho("Quais áreas cresceram na UF?")
        return sem_dados()
    melhor = dados.iloc[-1]
    cabecalho(f"Quais áreas cresceram em {uf} de {a0} para {a1}?",
              f"Maior avanço: <b>{melhor['categoria']}</b> ({fmt_pct(melhor['uf'], sinal=True)}; "
              f"Brasil {fmt_pct(melhor['brasil'], sinal=True)}). Traço vertical = variação nacional da área.")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dados["uf"], y=dados["categoria"], orientation="h", name=uf, showlegend=False,
        marker=dict(color=[PRIMARIA if v >= 0 else VERMELHAO for v in dados["uf"]]),
        text=[fmt_pct(v, sinal=True) for v in dados["uf"]], textposition="outside",
        textfont=dict(size=12, color=TINTA_SECUNDARIA), cliponaxis=False,
        hovertemplate=f"<b>%{{y}}</b><br>{uf}: %{{x:+.1f}}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dados["brasil"], y=dados["categoria"], mode="markers", name="Brasil", showlegend=False,
        marker=dict(symbol="line-ns", size=22, line=dict(color=TINTA, width=2)),
        hovertemplate="<b>%{y}</b><br>Brasil: %{x:+.1f}%<extra></extra>",
    ))
    limite = max(dados[["uf", "brasil"]].abs().max().max(), 1) * 1.6
    fig.update_layout(height=340, bargap=0.35, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(visible=False, range=[-limite, limite]), yaxis=dict(visible=False),
                      shapes=[dict(type="line", x0=0, x1=0, y0=-0.5, y1=len(dados) - 0.5,
                                   line=dict(color=TINTA_SECUNDARIA, width=1))])
    # Nome da área do lado oposto à barra, junto à linha de base
    for cat, v in zip(dados["categoria"], dados["uf"]):
        fig.add_annotation(x=0, y=cat, text=cat, showarrow=False, xanchor="left" if v < 0 else "right",
                           xshift=6 if v < 0 else -6, font=dict(size=12, color=TINTA))
    grafico_estatico(fig, "g_perfil_variacao", nome_arquivo=f"variacao_areas_{uf}")
    exportar_csv(dados.rename(columns={"uf": f"variacao_{uf}", "brasil": "variacao_brasil"}).round(2),
                 f"variacao_areas_{uf}")


def tabela_uf(uf, nacional, medida):
    dados = nacional[nacional["estado"] == uf]
    tabela = dados.pivot_table(index="mes", columns="categoria", values=medida, aggfunc="sum").sort_index()
    tabela["Total"] = tabela.sum(axis=1)
    tabela.index = [rotulo_mes(m) for m in tabela.index]
    cabecalho(f"{MEDIDAS[medida]} de {uf} por mês e área")
    st.dataframe(tabela, height=320, width="stretch",
                 column_config={c: st.column_config.NumberColumn(c, format="localized") for c in tabela.columns})
    exportar_csv(tabela.reset_index().rename(columns={"index": "mes"}).round(2), f"tabela_mensal_{uf}",
                 rotulo="Baixar tabela (CSV)")


def render():
    medida, ano, base, base_todos_anos = filtros_globais(regioes=False, estados=False)
    st.session_state.setdefault("f_uf", UF_PADRAO)

    st.title("Perfil por Estado")
    st.caption("Como uma unidade federativa se posiciona frente às demais: volume, custo, áreas de "
               "concentração e crescimento.")
    uf = st.selectbox("Unidade federativa", options=sorted(NOME_UF), key="f_uf",
                      format_func=lambda s: f"{NOME_UF[s]} ({s})")
    barra_de_selecoes(("categorias",))

    # Apenas a seleção de áreas se aplica aqui; estados e meses são definidos pelo perfil
    nacional = aplicar_selecoes(base, somente={"categorias"})
    nacional_anos = aplicar_selecoes(base_todos_anos, somente={"categorias"})
    if nacional[nacional["estado"] == uf].empty:
        st.warning("Sem registros para esta UF no recorte atual.")
        return

    with secao("Indicadores-chave"):
        por_uf, posicao, ticket_uf, ticket_br, var_uf = indicadores(uf, nacional, nacional_anos, medida)
        lider_area = nacional[nacional["estado"] == uf].groupby("categoria")[medida].sum().idxmax()
        st.markdown(
            f"<div class='resumo'><b>{NOME_UF[uf]}</b> é a <b>{posicao}ª</b> UF em {MEDIDAS[medida].lower()} "
            f"no recorte, com maior peso em <b>{lider_area}</b>. O custo por atendimento é "
            f"<b>{fmt_pct(abs(ticket_uf / ticket_br - 1) * 100)} {'acima' if ticket_uf > ticket_br else 'abaixo'}</b> "
            f"da média nacional"
            + (f" e a demanda variou <b>{fmt_pct(var_uf, sinal=True)}</b> no último ano." if var_uf is not None else ".")
            + "</div>",
            unsafe_allow_html=True,
        )

    with secao("Evolução e composição"):
        c1, c2 = st.columns(2, gap="large")
        with c1:
            grafico_evolucao(uf, nacional, medida)
        with c2:
            grafico_composicao(uf, base, medida)

    with secao("Posição e crescimento" + (" · variação ignora o filtro de ano" if ano != "Todos" else "")):
        c1, c2 = st.columns(2, gap="large")
        with c1:
            grafico_posicao(uf, por_uf, medida, posicao)
        with c2:
            grafico_variacao_areas(uf, nacional_anos, medida)

    with secao("Detalhes sob demanda"):
        tabela_uf(uf, nacional, medida)
