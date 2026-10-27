"""Áreas de Atendimento: tendência, custo, sazonalidade, concentração e vocação regional."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from painel.base import (
    CATEGORIAS, CINZA, COR_CATEGORIA, EIXO, ESCALA_DIVERGENTE, GRADE, MEDIDAS, MESES_PT, PRIMARIA,
    REGIOES, TINTA, TINTA_SECUNDARIA, VERMELHAO, aplicar_selecoes, barra_de_selecoes, cabecalho,
    colunas_mensais, exportar_csv, filtros_globais, fmt_medida, fmt_num, fmt_pct,
    grafico_estatico, grafico_interativo, hover_medida, np_coluna, prefixo_eixo, rotulo_mes, secao,
    sem_dados,
)


def _selecionadas():
    return set(st.session_state.sel["categorias"])


def cartoes_areas(base, base_todos_anos, medida):
    anos = sorted(base_todos_anos["ano"].unique())
    total = base[medida].sum()
    colunas = st.columns(len(CATEGORIAS))
    for coluna, cat in zip(colunas, CATEGORIAS):
        dados = base[base["categoria"] == cat]
        mensal = dados.groupby("data")[medida].sum().sort_index()
        delta = None
        if len(anos) >= 2:
            por_ano = base_todos_anos[base_todos_anos["categoria"] == cat].groupby("ano")[medida].sum()
            if por_ano.get(anos[-2]):
                delta = fmt_pct((por_ano[anos[-1]] / por_ano[anos[-2]] - 1) * 100, sinal=True)
        coluna.metric(
            cat, fmt_medida(dados[medida].sum(), medida), delta=delta,
            delta_description=f"{anos[-1]} vs {anos[-2]}" if len(anos) >= 2 else None,
            chart_data=mensal.tolist(), chart_type="line",
            help=f"{fmt_pct(dados[medida].sum() / total * 100 if total else 0)} do total do recorte",
        )


def grafico_tendencias(base, medida):
    mensal = base.groupby(["categoria", "data", "mes"], as_index=False)[medida].sum()
    if mensal.empty:
        cabecalho("Como cada área evolui?")
        return sem_dados()
    # Tendência linear de cada área, em % da média mensal por mês
    tendencias = {}
    for cat, grupo in mensal.groupby("categoria"):
        y = grupo.sort_values("data")[medida].to_numpy()
        tendencias[cat] = np.polyfit(np.arange(len(y)), y, 1)[0] / y.mean() * 100 if len(y) > 1 else 0
    alta = max(tendencias, key=tendencias.get)
    baixa = min(tendencias, key=tendencias.get)
    cabecalho("Como cada área evolui?",
              f"Tendência mais forte de alta: <b>{alta}</b> ({fmt_pct(tendencias[alta], 2, sinal=True)} ao mês); "
              f"mais fraca: <b>{baixa}</b> ({fmt_pct(tendencias[baixa], 2, sinal=True)} ao mês). "
              "Clique numa área para cruzá-la com os demais gráficos.")

    selecionadas = _selecionadas()
    categorias = [c for c in CATEGORIAS if c in set(mensal["categoria"])]
    fig = make_subplots(rows=1, cols=len(categorias), shared_yaxes=True, horizontal_spacing=0.025,
                        subplot_titles=categorias)
    for i, cat in enumerate(categorias, start=1):
        s = mensal[mensal["categoria"] == cat].sort_values("data")
        ativa = not selecionadas or cat in selecionadas
        cor = COR_CATEGORIA[cat] if ativa else CINZA
        fig.add_trace(go.Scatter(
            x=s["data"], y=s[medida], mode="lines+markers", name=cat,
            line=dict(color=cor, width=2), marker=dict(size=5, color=cor),
            customdata=np_coluna([cat] * len(s), [rotulo_mes(m) for m in s["mes"]]),
            hovertemplate=f"<b>{cat}</b> · %{{customdata[1]}}<br>{hover_medida(medida)}<extra></extra>",
        ), row=1, col=i)
        fig.add_annotation(x=s["data"].iloc[-1], y=s[medida].iloc[-1], text=fmt_medida(s[medida].iloc[-1], medida),
                           showarrow=False, yshift=12, font=dict(size=11, color=TINTA_SECUNDARIA),
                           row=1, col=i)
    # Só janeiro de cada ano: os painéis são estreitos e compartilham a mesma escala de tempo
    janeiros = sorted(d for d in mensal["data"].unique() if pd.Timestamp(d).month == 1)
    fig.update_xaxes(showgrid=False, showline=True, linecolor=EIXO, tickvals=janeiros, tickangle=0,
                     ticktext=[str(pd.Timestamp(d).year) for d in janeiros],
                     ticks="outside", tickcolor=EIXO)
    fig.update_yaxes(showgrid=True, gridcolor=GRADE, zeroline=False, tickformat="~s",
                     tickprefix=prefixo_eixo(medida))
    fig.update_annotations(selector=dict(xref="paper"), font=dict(size=13, color=TINTA))
    fig.update_layout(height=300, showlegend=False, margin=dict(l=10, r=10, t=56, b=10))
    grafico_interativo(fig, "g_areas_tendencia", "categorias", modos=("points",), nome_arquivo="tendencia_por_area")
    exportar = mensal.pivot(index="mes", columns="categoria", values=medida).reset_index()
    exportar["mes"] = exportar["mes"].map(rotulo_mes)
    exportar_csv(exportar, "tendencia_por_area")


def grafico_custo(base):
    mensal = base.groupby(["categoria", "data"], as_index=False)[["valor", "atendimentos"]].sum()
    if mensal.empty:
        cabecalho("Quanto custa cada atendimento ao longo do tempo?")
        return sem_dados()
    mensal["ticket"] = mensal["valor"] / mensal["atendimentos"]
    mensal = mensal.sort_values("data")
    # Média móvel de 3 meses: remove o ruído mensal e deixa a tendência legível
    mensal["suavizado"] = mensal.groupby("categoria")["ticket"].transform(lambda s: s.rolling(3, min_periods=1).mean())
    volatil = mensal.groupby("categoria")["ticket"].agg(lambda s: s.std() / s.mean() * 100)
    cabecalho("Quanto custa cada atendimento ao longo do tempo?",
              f"Média móvel de 3 meses. Custo mais estável: <b>{volatil.idxmin()}</b> (variação típica de "
              f"{fmt_pct(volatil.min())}); mais oscilante: <b>{volatil.idxmax()}</b> ({fmt_pct(volatil.max())}).")
    selecionadas = _selecionadas()
    fig = go.Figure()
    finais = []
    for cat in CATEGORIAS:
        s = mensal[mensal["categoria"] == cat]
        if s.empty:
            continue
        ativa = not selecionadas or cat in selecionadas
        fig.add_trace(go.Scatter(
            x=s["data"], y=s["suavizado"], name=cat, mode="lines",
            line=dict(color=COR_CATEGORIA[cat] if ativa else CINZA, width=2 if ativa else 1),
            customdata=s["ticket"],
            hovertemplate=f"{cat}: R$ %{{y:,.2f}} (mês: R$ %{{customdata:,.2f}})<extra></extra>",
        ))
        finais.append([s["suavizado"].iloc[-1], cat, ativa, s["data"].iloc[-1]])
    # Rótulos diretos no fim das linhas, afastados para não se sobreporem
    finais.sort()
    folga = (mensal["suavizado"].max() - mensal["suavizado"].min()) * 0.07
    for k in range(1, len(finais)):
        finais[k][0] = max(finais[k][0], finais[k - 1][0] + folga)
    for y, cat, ativa, x in finais:
        fig.add_annotation(x=x, y=y, text=cat, showarrow=False, xanchor="left", xshift=6,
                           font=dict(size=11, color=TINTA if ativa else CINZA))
    valores, textos = colunas_mensais(sorted(mensal["data"].unique()))
    fig.update_layout(height=360, hovermode="x unified", margin=dict(l=10, r=100, t=30, b=10),
                      xaxis=dict(tickvals=valores, ticktext=textos),
                      yaxis=dict(tickprefix="R$ ", tickformat=",.0f"))
    grafico_estatico(fig, "g_areas_custo", nome_arquivo="custo_mensal_por_area")
    exportar = mensal.pivot(index="data", columns="categoria", values="ticket").reset_index()
    exportar["data"] = exportar["data"].dt.strftime("%m/%Y")
    exportar_csv(exportar.rename(columns={"data": "mes"}).round(2), "custo_mensal_por_area")


def grafico_sazonalidade(base, medida):
    dados = aplicar_selecoes(base, somente={"categorias"})
    mensal = dados.groupby("data")[medida].sum()
    if mensal.empty:
        cabecalho("Há meses de maior demanda?")
        return sem_dados()
    indice = (mensal.groupby(mensal.index.month).mean() / mensal.mean() * 100).reindex(range(1, 13))
    alto, baixo = indice.idxmax(), indice.idxmin()
    recorte = ", ".join(sorted(_selecionadas())) or "todas as áreas"
    cabecalho("Há meses de maior demanda?",
              f"Para {recorte}: demanda mais alta em <b>{MESES_PT[alto - 1]}</b> (índice {fmt_num(indice[alto])}) "
              f"e mais baixa em <b>{MESES_PT[baixo - 1]}</b> ({fmt_num(indice[baixo])}). 100 = mês típico.")
    fig = go.Figure(go.Bar(
        x=MESES_PT, y=indice - 100, base=100,
        marker=dict(color=[PRIMARIA if v >= 100 else VERMELHAO for v in indice]),
        text=[fmt_num(v) for v in indice], textposition="outside", textfont=dict(size=11, color=TINTA_SECUNDARIA),
        cliponaxis=False, hovertemplate="<b>%{x}</b><br>Índice sazonal: %{text}<extra></extra>",
    ))
    fig.add_hline(y=100, line=dict(color=TINTA_SECUNDARIA, width=1))
    fig.update_layout(height=320, bargap=0.3, margin=dict(l=10, r=10, t=30, b=10),
                      yaxis=dict(visible=False), xaxis=dict(showline=False, ticks=""))
    grafico_estatico(fig, "g_areas_sazonalidade", nome_arquivo="indice_sazonal")
    exportar_csv(pd.DataFrame({"mes": MESES_PT, "indice_sazonal": indice.round(1).to_numpy()}), "indice_sazonal")


def grafico_concentracao(base, medida):
    por_uf = base.groupby(["categoria", "estado"], as_index=False)[medida].sum()
    if por_uf.empty:
        cabecalho("Quão concentrada é cada área entre as UFs?")
        return sem_dados()
    curvas = {}
    for cat, grupo in por_uf.groupby("categoria"):
        valores = grupo[medida].sort_values(ascending=False).to_numpy()
        curvas[cat] = np.cumsum(valores) / valores.sum() * 100
    n = min(10, min(len(c) for c in curvas.values()))
    top = {cat: c[n - 1] for cat, c in curvas.items()}
    mais = max(top, key=top.get)
    uniforme = n / max(len(c) for c in curvas.values()) * 100
    cabecalho("Quão concentrada é cada área entre as UFs?",
              f"As {n} maiores UFs respondem por <b>{fmt_pct(top[mais])}</b> de <b>{mais}</b> (a mais concentrada), "
              f"frente a {fmt_pct(uniforme)} numa divisão igual: demanda "
              + ("bem distribuída pelo território." if top[mais] - uniforme < 15 else "concentrada em poucas UFs."))
    selecionadas = _selecionadas()
    fig = go.Figure()
    total_ufs = max(len(c) for c in curvas.values())
    fig.add_trace(go.Scatter(x=[0, total_ufs], y=[0, 100], mode="lines", showlegend=False, hoverinfo="skip",
                             line=dict(color=EIXO, width=1, dash="dot")))
    for cat in CATEGORIAS:
        if cat not in curvas:
            continue
        ativa = not selecionadas or cat in selecionadas
        c = curvas[cat]
        fig.add_trace(go.Scatter(
            x=np.arange(0, len(c) + 1), y=np.concatenate([[0], c]), name=cat, mode="lines",
            line=dict(color=COR_CATEGORIA[cat] if ativa else CINZA, width=2 if ativa else 1),
            hovertemplate=f"{cat}: %{{x}} UFs = %{{y:.1f}}%<extra></extra>",
        ))
    fig.add_vline(x=n, line=dict(color=EIXO, width=1))
    fig.update_layout(height=340, hovermode="x unified", margin=dict(l=10, r=10, t=30, b=10),
                      xaxis=dict(title=dict(text="Nº de UFs (da maior para a menor)", font=dict(size=12)),
                                 range=[0, total_ufs]),
                      yaxis=dict(ticksuffix="%", range=[0, 102]))
    grafico_estatico(fig, "g_areas_concentracao", nome_arquivo="concentracao_por_area")
    exportar = pd.DataFrame({cat: np.round(c, 2) for cat, c in curvas.items()})
    exportar.insert(0, "n_ufs", range(1, len(exportar) + 1))
    exportar_csv(exportar, "concentracao_por_area")


def grafico_vocacao(base, medida):
    tabela = base.pivot_table(index="regiao", columns="categoria", values=medida, aggfunc="sum")
    if tabela.empty:
        cabecalho("Qual a vocação de cada região?")
        return sem_dados()
    # Quociente locacional: peso da área na região ÷ peso da área no Brasil
    ql = tabela.div(tabela.sum(axis=1), axis=0) / (tabela.sum() / tabela.values.sum())
    ql = ql.reindex([r for r in REGIOES if r in ql.index])
    linha, coluna = np.unravel_index(np.nanargmax(ql.values), ql.shape)
    cabecalho("Qual a vocação de cada região?",
              f"Quociente locacional: acima de 1 indica especialização. Destaque: <b>{ql.index[linha]}</b> em "
              f"<b>{ql.columns[coluna]}</b> ({fmt_num(ql.values[linha, coluna], 2)}).")
    amplitude = max(abs(np.nanmax(ql.values) - 1), abs(1 - np.nanmin(ql.values)), 0.01)
    selecionadas = _selecionadas()
    fig = go.Figure(go.Heatmap(
        z=ql.values, x=list(ql.columns), y=list(ql.index), colorscale=ESCALA_DIVERGENTE,
        zmid=1, zmin=1 - amplitude, zmax=1 + amplitude, xgap=2, ygap=2,
        text=[[fmt_num(v, 2) for v in linha_] for linha_ in ql.values], texttemplate="%{text}",
        textfont=dict(size=12, color=TINTA),
        hovertemplate="<b>%{y}</b> · %{x}<br>Quociente locacional: %{text}<extra></extra>",
        colorbar=dict(thickness=10, len=0.8, outlinewidth=0),
    ))
    for j, cat in enumerate(ql.columns):
        if cat in selecionadas:
            fig.add_shape(type="rect", x0=j - 0.5, x1=j + 0.5, y0=-0.5, y1=len(ql) - 0.5,
                          line=dict(color=TINTA, width=1.5))
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(showline=False, ticks="", side="top", tickfont=dict(color=TINTA)),
                      yaxis=dict(showgrid=False, autorange="reversed", tickfont=dict(color=TINTA)))
    grafico_estatico(fig, "g_areas_vocacao", nome_arquivo="vocacao_regional")
    exportar_csv(ql.round(3).reset_index(), "vocacao_regional")


def tabela_areas(base, medida):
    tabela = base.pivot_table(index="mes", columns="categoria", values=medida, aggfunc="sum").sort_index()
    tabela["Total"] = tabela.sum(axis=1)
    tabela.index = [rotulo_mes(m) for m in tabela.index]
    cabecalho(f"{MEDIDAS[medida]} por mês e área")
    st.dataframe(tabela, height=320, width="stretch",
                 column_config={c: st.column_config.NumberColumn(c, format="localized") for c in tabela.columns})
    exportar_csv(tabela.reset_index().rename(columns={"index": "mes"}).round(2), "tabela_mensal_areas",
                 rotulo="Baixar tabela (CSV)")


def render():
    medida, ano, base, base_todos_anos = filtros_globais(categorias=False)

    st.title("Áreas de Atendimento")
    st.caption("Educação, Infraestrutura, Saúde, Segurança e Tecnologia: tendência, custo por atendimento, "
               "sazonalidade, concentração geográfica e vocação regional.")
    barra_de_selecoes(("categorias",))

    secao("Resumo por área" + (" · variação ignora o filtro de ano" if ano != "Todos" else ""))
    cartoes_areas(base, base_todos_anos, medida)

    secao("Tendência")
    grafico_tendencias(base, medida)

    secao("Custo e sazonalidade")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        grafico_custo(base)
    with c2:
        grafico_sazonalidade(base, medida)

    secao("Distribuição territorial")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        grafico_concentracao(base, medida)
    with c2:
        grafico_vocacao(base, medida)

    secao("Detalhes sob demanda")
    tabela_areas(base, medida)
