"""Panorama Nacional: quanto, onde, em quais áreas e quando os atendimentos ocorrem."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from painel.base import (
    CINZA, CINZA_ESCURO, COR_CATEGORIA, EIXO, ESCALA_SEQUENCIAL, MEDIDAS, MESES_PT, PRIMARIA,
    TINTA, TINTA_SECUNDARIA, VERMELHAO, aplicar_selecoes, barra_de_selecoes, cabecalho,
    colunas_mensais, destaque, exportar_csv, filtros_globais, fmt_brl, fmt_compacto, fmt_medida,
    fmt_num, fmt_pct, geojson_brasil, grafico_estatico, grafico_interativo, hover_medida,
    np_coluna, opacidades, prefixo_eixo, rotulo_mes, secao, sem_dados,
)


def indicadores(df, medida):
    mensal = df.groupby("data")[["atendimentos", "valor"]].sum().sort_index()

    def delta(serie):
        if len(serie) < 2 or serie.iloc[-2] == 0:
            return None
        return fmt_pct((serie.iloc[-1] / serie.iloc[-2] - 1) * 100, sinal=True)

    ticket_mensal = (mensal["valor"] / mensal["atendimentos"]).fillna(0)
    total_atend = df["atendimentos"].sum()
    total_valor = df["valor"].sum()
    ticket = total_valor / total_atend if total_atend else 0

    if len(mensal):
        mes_pico = mensal[medida].idxmax()
        pico_txt = f"{MESES_PT[mes_pico.month - 1]}/{mes_pico.year}"
        pico_valor = fmt_medida(mensal[medida].max(), medida)
    else:
        pico_txt, pico_valor = "—", None

    descricao = "vs mês anterior"
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Atendimentos", fmt_compacto(total_atend), delta=delta(mensal["atendimentos"]),
              delta_description=descricao, chart_data=mensal["atendimentos"].tolist(), chart_type="area",
              help=fmt_num(total_atend))
    c2.metric("Recursos aplicados", "R$ " + fmt_compacto(total_valor), delta=delta(mensal["valor"]),
              delta_description=descricao, chart_data=mensal["valor"].tolist(), chart_type="area",
              help=fmt_brl(total_valor))
    c3.metric("Custo por atendimento", fmt_brl(ticket), delta=delta(ticket_mensal), delta_color="inverse",
              delta_description=descricao, chart_data=ticket_mensal.round(2).tolist(), chart_type="line",
              help="Recursos aplicados ÷ atendimentos (ticket médio)")
    c4.metric("Mês de pico", pico_txt, delta=pico_valor, delta_color="off", delta_arrow="off",
              help=f"Mês com maior {MEDIDAS[medida].lower()} no recorte atual")
    c5.metric("Cobertura", f"{df['estado'].nunique()} UFs",
              delta=f"{df['categoria'].nunique()} áreas", delta_color="off", delta_arrow="off")


def grafico_temporal(base, medida):
    dados = aplicar_selecoes(base, exceto={"meses"})
    serie = dados.groupby(["data", "mes"], as_index=False)[medida].sum().sort_values("data")
    if serie.empty:
        cabecalho("Como a demanda evoluiu mês a mês?")
        return sem_dados()
    media = serie[medida].mean()
    pico = serie.loc[serie[medida].idxmax()]
    vale = serie.loc[serie[medida].idxmin()]
    cabecalho(
        "Como a demanda evoluiu mês a mês?",
        f"Média de <b>{fmt_medida(media, medida)}</b> por mês. Pico em <b>{rotulo_mes(pico['mes'])}</b> "
        f"({fmt_pct((pico[medida] / media - 1) * 100, sinal=True)} sobre a média) e menor valor em "
        f"<b>{rotulo_mes(vale['mes'])}</b> ({fmt_pct((vale[medida] / media - 1) * 100, sinal=True)}).",
    )
    selecionados = set(st.session_state.sel["meses"])
    rotulos = [rotulo_mes(m) for m in serie["mes"]]

    fig = go.Figure(go.Scatter(
        x=serie["data"], y=serie[medida], mode="lines+markers",
        line=dict(color=CINZA_ESCURO if selecionados else PRIMARIA, width=2),
        marker=dict(color=destaque(serie["mes"], "meses"),
                    size=[12 if m in selecionados else 8 for m in serie["mes"]],
                    line=dict(color="white", width=2)),
        customdata=np_coluna(serie["mes"], rotulos),
        hovertemplate=f"<b>%{{customdata[1]}}</b><br>{MEDIDAS[medida]}: {hover_medida(medida)}<extra></extra>",
    ))
    fig.add_hline(y=media, line=dict(color=EIXO, width=1, dash="dot"),
                  annotation=dict(text="média", font=dict(size=11, color=TINTA_SECUNDARIA)),
                  annotation_position="right")
    fig.add_annotation(x=pico["data"], y=pico[medida], text=f"pico {fmt_medida(pico[medida], medida)}",
                       showarrow=False, yshift=16, font=dict(size=12, color=TINTA))
    valores, textos = colunas_mensais(serie["data"])
    fig.update_layout(
        height=300, showlegend=False, margin=dict(l=10, r=40, t=24, b=10),
        xaxis=dict(tickvals=valores, ticktext=textos),
        yaxis=dict(rangemode="tozero", tickformat="~s", tickprefix=prefixo_eixo(medida)),
    )
    grafico_interativo(fig, "g_temporal", "meses", nome_arquivo="demanda_mensal")
    exportar_csv(serie.assign(mes=rotulos)[["mes", medida]], "demanda_mensal")


def grafico_mapa(base, medida):
    dados = aplicar_selecoes(base, exceto={"estados"})
    mapa = dados.groupby("estado", as_index=False)[medida].sum()
    if mapa.empty:
        cabecalho("Onde se concentra a demanda?")
        return sem_dados()
    mapa["participacao"] = mapa[medida] / mapa[medida].sum() * 100
    top3 = mapa.nlargest(3, medida)
    cabecalho(
        "Onde se concentra a demanda?",
        f"<b>{', '.join(top3['estado'])}</b> lideram e somam <b>{fmt_pct(top3['participacao'].sum())}</b> do total. "
        f"A maior UF tem {fmt_pct((mapa[medida].max() / mapa[medida].min() - 1) * 100)} a mais que a menor.",
    )
    selecionados = set(st.session_state.sel["estados"])
    em_destaque = mapa["estado"].isin(selecionados) if selecionados else pd.Series(True, index=mapa.index)

    # Duas camadas com a mesma escala: o contexto (fora da seleção) fica translúcido,
    # já que o coroplético não aceita opacidade por estado.
    fig = go.Figure()
    for camada, opacidade, contorno in ((mapa[~em_destaque], 0.3, ("white", 0.6)),
                                        (mapa[em_destaque], 1.0, (TINTA, 2) if selecionados else ("white", 0.6))):
        if camada.empty:
            continue
        fig.add_trace(go.Choropleth(
            geojson=geojson_brasil, featureidkey="properties.sigla",
            locations=camada["estado"], z=camada[medida], colorscale=ESCALA_SEQUENCIAL,
            zmin=mapa[medida].min(), zmax=mapa[medida].max(), showscale=opacidade == 1.0,
            marker=dict(opacity=opacidade, line=dict(color=contorno[0], width=contorno[1])),
            customdata=np_coluna(camada["estado"], camada["participacao"]),
            hovertemplate=(f"<b>%{{location}}</b><br>{MEDIDAS[medida]}: {hover_medida(medida, 'z')}"
                           "<br>Participação: %{customdata[1]:.1f}%<extra></extra>"),
            colorbar=dict(thickness=10, len=0.55, x=0.98, outlinewidth=0, tickformat="~s",
                          title=dict(text=MEDIDAS[medida], side="right", font=dict(size=12))),
        ))
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)", projection_type="mercator")
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0))
    grafico_interativo(fig, "g_mapa", "estados", nome_arquivo="mapa_por_uf")
    exportar_csv(mapa.round(2), "mapa_por_uf")


def barras_horizontais(dados, chave_col, valor_col, medida, chave, dimensao, altura, nome_arquivo):
    dados = dados.sort_values(valor_col)
    fig = go.Figure(go.Bar(
        x=dados[valor_col], y=dados[chave_col], orientation="h",
        marker=dict(color=destaque(dados[chave_col], dimensao)),
        text=[fmt_medida(v, medida) for v in dados[valor_col]], textposition="outside",
        textfont=dict(color=TINTA_SECUNDARIA, size=12), cliponaxis=False,
        customdata=np_coluna(dados[chave_col]),
        hovertemplate=f"<b>%{{y}}</b><br>{MEDIDAS[medida]}: {hover_medida(medida, 'x')}<extra></extra>",
    ))
    fig.update_layout(
        height=altura, bargap=0.25, margin=dict(l=10, r=60, t=10, b=10),
        xaxis=dict(visible=False), yaxis=dict(showgrid=False, ticks="", tickfont=dict(color=TINTA)),
    )
    grafico_interativo(fig, chave, dimensao, nome_arquivo=nome_arquivo)
    exportar_csv(dados.sort_values(valor_col, ascending=False).round(2), nome_arquivo)


def grafico_ranking_estados(base, medida):
    dados = aplicar_selecoes(base, exceto={"estados"}).groupby("estado", as_index=False)[medida].sum()
    if dados.empty:
        cabecalho("Ranking das UFs")
        return sem_dados()
    mediana = dados[medida].median()
    acima = int((dados[medida] > mediana * 1.05).sum())
    cabecalho("Ranking das UFs", f"{acima} UFs ficam mais de 5% acima da mediana nacional "
                                 f"({fmt_medida(mediana, medida)}).")
    barras_horizontais(dados, "estado", medida, medida, "g_ranking", "estados",
                       altura=max(220, 19 * len(dados) + 40), nome_arquivo="ranking_ufs")


def grafico_regioes(base, medida):
    dados = aplicar_selecoes(base, exceto={"regioes"})
    agregado = dados.groupby("regiao", as_index=False).agg(total=(medida, "sum"), ufs=("estado", "nunique"))
    if agregado.empty:
        cabecalho("Quanto cada região representa?")
        return sem_dados()
    agregado["por_uf"] = agregado["total"] / agregado["ufs"]
    lider = agregado.loc[agregado["total"].idxmax()]
    por_uf = agregado.loc[agregado["por_uf"].idxmax()]
    cabecalho(
        "Quanto cada região representa?",
        f"<b>{lider['regiao']}</b> concentra {fmt_pct(lider['total'] / agregado['total'].sum() * 100)} "
        f"({int(lider['ufs'])} UFs); por UF, a maior média é do <b>{por_uf['regiao']}</b>.",
    )
    barras_horizontais(agregado.rename(columns={"total": medida}), "regiao", medida, medida,
                       "g_regioes", "regioes", altura=300, nome_arquivo="total_por_regiao")


def grafico_categorias(base, medida):
    dados = (aplicar_selecoes(base, exceto={"categorias"})
             .groupby("categoria", as_index=False)[medida].sum()
             .sort_values(medida, ascending=False))
    if dados.empty:
        cabecalho("Quais áreas mais demandam?")
        return sem_dados()
    dados["participacao"] = dados[medida] / dados[medida].sum() * 100
    lider = dados.iloc[0]
    cabecalho("Quais áreas mais demandam?",
              f"<b>{lider['categoria']}</b> lidera com {fmt_pct(lider['participacao'])}; a distribuição entre "
              f"as áreas é equilibrada (amplitude de {fmt_pct(dados['participacao'].max() - dados['participacao'].min())} p.p.).")
    fig = go.Figure(go.Bar(
        x=dados["categoria"], y=dados[medida],
        marker=dict(color=[COR_CATEGORIA[c] for c in dados["categoria"]],
                    opacity=opacidades(dados["categoria"], "categorias")),
        text=[f"{fmt_medida(v, medida)}<br>{fmt_pct(p)}" for v, p in zip(dados[medida], dados["participacao"])],
        textposition="outside", textfont=dict(color=TINTA_SECUNDARIA, size=12), cliponaxis=False,
        customdata=np_coluna(dados["categoria"]),
        hovertemplate=f"<b>%{{x}}</b><br>{MEDIDAS[medida]}: {hover_medida(medida)}<extra></extra>",
    ))
    fig.update_layout(
        height=300, bargap=0.35, margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(visible=False), xaxis=dict(showline=False, ticks="", tickfont=dict(color=TINTA)),
    )
    grafico_interativo(fig, "g_categorias", "categorias", nome_arquivo="demanda_por_area")
    exportar_csv(dados.round(2), "demanda_por_area")


def grafico_ticket_categoria(base):
    dados = (aplicar_selecoes(base, exceto={"categorias"})
             .groupby("categoria", as_index=False)[["valor", "atendimentos"]].sum())
    if dados.empty:
        cabecalho("Qual área custa mais por atendimento?")
        return sem_dados()
    dados["ticket"] = dados["valor"] / dados["atendimentos"]
    dados = dados.sort_values("ticket")
    media = dados["valor"].sum() / dados["atendimentos"].sum()
    caro = dados.iloc[-1]
    cabecalho("Qual área custa mais por atendimento?",
              f"<b>{caro['categoria']}</b>: {fmt_brl(caro['ticket'])} por atendimento, "
              f"{fmt_pct((caro['ticket'] / media - 1) * 100, sinal=True)} frente à média ({fmt_brl(media)}).")

    fig = go.Figure(go.Scatter(
        x=dados["ticket"], y=dados["categoria"], mode="markers+text",
        marker=dict(size=14, color=[COR_CATEGORIA[c] for c in dados["categoria"]],
                    opacity=opacidades(dados["categoria"], "categorias"), line=dict(color="white", width=2)),
        text=[fmt_brl(v) for v in dados["ticket"]], textposition="middle right",
        textfont=dict(color=TINTA_SECUNDARIA, size=12), cliponaxis=False,
        customdata=np_coluna(dados["categoria"]),
        hovertemplate="<b>%{y}</b><br>Custo por atendimento: R$ %{x:,.2f}<extra></extra>",
    ))
    fig.add_vline(x=media, line=dict(color=CINZA_ESCURO, width=1, dash="dot"),
                  annotation=dict(text="média", font=dict(size=11, color=TINTA_SECUNDARIA)),
                  annotation_position="top")
    amplitude = dados["ticket"].max() - dados["ticket"].min() or 1
    fig.update_layout(
        height=300, showlegend=False, margin=dict(l=10, r=30, t=30, b=10),
        # Eixo X oculto: os rótulos diretos já informam o valor de cada ponto
        xaxis=dict(visible=False,
                   range=[dados["ticket"].min() - amplitude * 0.3, dados["ticket"].max() + amplitude * 0.9]),
        yaxis=dict(showgrid=False, tickfont=dict(color=TINTA)),
    )
    grafico_interativo(fig, "g_ticket", "categorias", nome_arquivo="custo_por_area")
    exportar_csv(dados.round(2), "custo_por_area")


def grafico_dispersao_estados(base):
    dados = (aplicar_selecoes(base, exceto={"estados"})
             .groupby("estado", as_index=False)[["atendimentos", "valor"]].sum())
    if len(dados) < 3:
        cabecalho("Quem atende mais também gasta mais por atendimento?")
        return sem_dados()
    dados["ticket"] = dados["valor"] / dados["atendimentos"]
    r = np.corrcoef(dados["atendimentos"], dados["ticket"])[0, 1]
    forca = "fraca" if abs(r) < 0.3 else "moderada" if abs(r) < 0.6 else "forte"
    cabecalho("Quem atende mais também gasta mais por atendimento?",
              f"Correlação {forca} entre volume e custo (r = {fmt_num(r, 2)}). Quadrante superior direito: "
              "UFs com alto volume <i>e</i> alto custo; use o laço para selecioná-las.")
    selecionados = set(st.session_state.sel["estados"])

    fig = go.Figure(go.Scatter(
        x=dados["atendimentos"], y=dados["ticket"], mode="markers+text",
        text=dados["estado"], textposition="top center",
        textfont=dict(size=11, color=[TINTA if (not selecionados or e in selecionados) else CINZA
                                      for e in dados["estado"]]),
        marker=dict(size=11, color=destaque(dados["estado"], "estados"), line=dict(color="white", width=2)),
        customdata=np_coluna(dados["estado"], dados["valor"]),
        hovertemplate=("<b>%{customdata[0]}</b><br>Atendimentos: %{x:,.0f}"
                       "<br>Custo por atendimento: R$ %{y:,.2f}<extra></extra>"),
    ))
    fig.add_vline(dados["atendimentos"].median(), line=dict(color=EIXO, width=1, dash="dot"))
    fig.add_hline(dados["ticket"].median(), line=dict(color=EIXO, width=1, dash="dot"))
    fig.update_layout(
        height=420, showlegend=False,
        xaxis=dict(title=dict(text="Atendimentos", font=dict(size=12)), tickformat="~s"),
        yaxis=dict(title=dict(text="Custo por atendimento (R$)", font=dict(size=12)),
                   tickprefix="R$ ", tickformat=",.0f"),
    )
    grafico_interativo(fig, "g_dispersao", "estados", modos=("points", "box", "lasso"),
                       nome_arquivo="volume_x_custo_por_uf")
    exportar_csv(dados.round(2), "volume_x_custo_por_uf")


def grafico_calor(base, medida):
    dados = aplicar_selecoes(base, exceto={"meses", "categorias"})
    tabela = dados.pivot_table(index="categoria", columns="mes", values=medida, aggfunc="sum").sort_index(ascending=False)
    if tabela.empty:
        cabecalho("Quando cada área tem mais demanda?")
        return sem_dados()
    meses = list(tabela.columns)
    rotulos = [rotulo_mes(m) for m in meses]
    linha, coluna = np.unravel_index(np.nanargmax(tabela.values), tabela.shape)
    cabecalho("Quando cada área tem mais demanda?",
              f"Maior concentração: <b>{tabela.index[linha]}</b> em <b>{rotulos[coluna]}</b> "
              f"({fmt_medida(tabela.values[linha, coluna], medida)}). Contornos marcam a seleção atual.")
    fig = go.Figure(go.Heatmap(
        z=tabela.values, x=rotulos, y=tabela.index, colorscale=ESCALA_SEQUENCIAL, xgap=2, ygap=2,
        hovertemplate=f"<b>%{{y}}</b> · %{{x}}<br>{MEDIDAS[medida]}: {hover_medida(medida, 'z')}<extra></extra>",
        colorbar=dict(thickness=10, len=0.8, outlinewidth=0, tickformat="~s"),
    ))
    # Destaque (linking) das seleções feitas em outros gráficos
    for i, mes in enumerate(meses):
        if mes in st.session_state.sel["meses"]:
            fig.add_shape(type="rect", x0=i - 0.5, x1=i + 0.5, y0=-0.5, y1=len(tabela) - 0.5,
                          line=dict(color=TINTA, width=1.5))
    for j, cat in enumerate(tabela.index):
        if cat in st.session_state.sel["categorias"]:
            fig.add_shape(type="rect", x0=-0.5, x1=len(meses) - 0.5, y0=j - 0.5, y1=j + 0.5,
                          line=dict(color=TINTA, width=1.5))
    fig.update_layout(
        height=420, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showline=False, ticks="", tickvals=rotulos[::3]),
        yaxis=dict(showgrid=False, tickfont=dict(color=TINTA)),
    )
    grafico_estatico(fig, "g_calor", nome_arquivo="area_x_mes")
    exportar = tabela.copy()
    exportar.columns = rotulos
    exportar_csv(exportar.reset_index().rename(columns={"categoria": "area"}), "area_x_mes")


def grafico_comparativo_anual(base_todos_anos, medida):
    dados = aplicar_selecoes(base_todos_anos, exceto={"meses"})
    serie = dados.groupby(["ano", dados["data"].dt.month])[medida].sum().reset_index()
    serie.columns = ["ano", "mes_num", medida]
    anos = sorted(serie["ano"].unique())
    if serie.empty:
        cabecalho("2025 superou 2024?")
        return sem_dados()
    totais = serie.groupby("ano")[medida].sum()
    insight = None
    if len(anos) >= 2:
        var = (totais[anos[-1]] / totais[anos[-2]] - 1) * 100
        meses_acima = int((serie[serie["ano"] == anos[-1]].set_index("mes_num")[medida]
                           > serie[serie["ano"] == anos[-2]].set_index("mes_num")[medida]).sum())
        insight = (f"{anos[-1]} fechou com <b>{fmt_medida(totais[anos[-1]], medida)}</b> "
                   f"({fmt_pct(var, sinal=True)} vs {anos[-2]}), superando o ano anterior em {meses_acima} de 12 meses.")
    cabecalho(f"{anos[-1]} superou {anos[0]}?" if len(anos) >= 2 else "Evolução anual", insight)
    cores = {ano: (PRIMARIA if ano == anos[-1] else CINZA_ESCURO) for ano in anos}

    fig = go.Figure()
    for ano in anos:
        s = serie[serie["ano"] == ano]
        fig.add_trace(go.Scatter(
            x=s["mes_num"], y=s[medida], name=str(ano), mode="lines",
            line=dict(color=cores[ano], width=2, dash="solid" if ano == anos[-1] else "dash"),
            hovertemplate=f"{ano}: {hover_medida(medida)}<extra></extra>",
        ))
        fim = s.iloc[-1]
        fig.add_annotation(x=fim["mes_num"], y=fim[medida], text=f"<b>{ano}</b>", showarrow=False,
                           xanchor="left", xshift=6, font=dict(color=cores[ano], size=12))
    fig.update_layout(
        height=360, hovermode="x unified", margin=dict(l=10, r=40, t=30, b=10),
        xaxis=dict(tickvals=list(range(1, 13)), ticktext=MESES_PT),
        yaxis=dict(tickformat="~s", tickprefix=prefixo_eixo(medida)),
    )
    grafico_estatico(fig, "g_anual", nome_arquivo="comparativo_anual")
    exportar = serie.pivot(index="mes_num", columns="ano", values=medida).reset_index()
    exportar["mes_num"] = exportar["mes_num"].map(lambda m: MESES_PT[m - 1])
    exportar_csv(exportar.rename(columns={"mes_num": "mes"}), "comparativo_anual")


def grafico_variacao_estados(base_todos_anos, medida):
    dados = aplicar_selecoes(base_todos_anos, exceto={"estados"})
    tabela = dados.pivot_table(index="estado", columns="ano", values=medida, aggfunc="sum")
    anos = sorted(tabela.columns)
    if len(anos) < 2:
        cabecalho("Quais UFs cresceram?")
        return st.info("São necessários dois anos para calcular a variação.")
    a0, a1 = anos[-2], anos[-1]
    var = ((tabela[a1] / tabela[a0] - 1) * 100).dropna().sort_values().reset_index()
    var.columns = ["estado", "variacao"]
    cresceram = int((var["variacao"] > 0).sum())
    cabecalho(f"Quais UFs cresceram de {a0} para {a1}?",
              f"<b>{cresceram} de {len(var)}</b> UFs cresceram. Maior alta: <b>{var.iloc[-1]['estado']}</b> "
              f"({fmt_pct(var.iloc[-1]['variacao'], sinal=True)}); maior queda: <b>{var.iloc[0]['estado']}</b> "
              f"({fmt_pct(var.iloc[0]['variacao'], sinal=True)}).")
    cor_base = [PRIMARIA if v >= 0 else VERMELHAO for v in var["variacao"]]

    fig = go.Figure(go.Bar(
        x=var["variacao"], y=var["estado"], orientation="h",
        marker=dict(color=cor_base, opacity=opacidades(var["estado"], "estados")),
        text=[fmt_pct(v, sinal=True) for v in var["variacao"]], textposition="outside",
        textfont=dict(size=11, color=TINTA_SECUNDARIA), cliponaxis=False,
        customdata=np_coluna(var["estado"]),
        hovertemplate=f"<b>%{{y}}</b><br>Variação {a1} vs {a0}: %{{x:+.1f}}%<extra></extra>",
    ))
    fig.update_layout(
        height=max(240, 19 * len(var) + 40), bargap=0.25, margin=dict(l=10, r=50, t=10, b=10),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        shapes=[dict(type="line", x0=0, x1=0, y0=-0.5, y1=len(var) - 0.5, line=dict(color=TINTA_SECUNDARIA, width=1))],
    )
    # Siglas do lado oposto à barra, junto à linha de base, para não colidir com os valores
    for estado, v in zip(var["estado"], var["variacao"]):
        fig.add_annotation(x=0, y=estado, text=estado, showarrow=False,
                           xanchor="left" if v < 0 else "right", xshift=5 if v < 0 else -5,
                           font=dict(size=11, color=TINTA))
    grafico_interativo(fig, "g_variacao", "estados", nome_arquivo="variacao_anual_por_uf")
    exportar_csv(var.sort_values("variacao", ascending=False).round(2), "variacao_anual_por_uf")


def tabela_detalhes(df):
    detalhe = (df[["data", "regiao", "estado", "categoria", "atendimentos", "valor"]]
               .sort_values(["data", "estado", "categoria"]).copy())
    detalhe["ticket"] = detalhe["valor"] / detalhe["atendimentos"]
    cabecalho("Registros do recorte atual", f"{fmt_num(len(detalhe))} registros (UF × área × mês).")
    st.dataframe(
        detalhe, hide_index=True, height=380, width="stretch",
        column_config={
            "data": st.column_config.DateColumn("Mês", format="MM/YYYY"),
            "regiao": "Região", "estado": "UF", "categoria": "Área",
            "atendimentos": st.column_config.NumberColumn("Atendimentos", format="localized"),
            "valor": st.column_config.NumberColumn("Recursos (R$)", format="localized"),
            "ticket": st.column_config.NumberColumn("Custo por atendimento (R$)", format="localized"),
        },
    )
    exportar = detalhe.assign(data=detalhe["data"].dt.strftime("%m/%Y")).round(2)
    exportar_csv(exportar, "registros_filtrados", rotulo="Baixar registros (CSV)")


def render():
    medida, ano, base, base_todos_anos = filtros_globais()

    st.title("Panorama Nacional de Atendimentos")
    st.caption("Quanto, onde, em quais áreas e quando: atendimentos e recursos aplicados em Educação, "
               "Infraestrutura, Saúde, Segurança e Tecnologia nas 27 UFs (2024–2025).")
    barra_de_selecoes()

    df_contexto = aplicar_selecoes(base)
    if df_contexto.empty:
        st.warning("Nenhum registro corresponde à combinação de filtros e seleções. Limpe alguma seleção.")

    with secao("Indicadores-chave"):
        indicadores(df_contexto, medida)

    with secao("Evolução no tempo"):
        grafico_temporal(base, medida)

    with secao("Distribuição geográfica"):
        col_mapa, col_rank = st.columns([3, 2], gap="large")
        with col_mapa:
            grafico_mapa(base, medida)
        with col_rank:
            grafico_ranking_estados(base, medida)

    with secao("Áreas e regiões"):
        c1, c2, c3 = st.columns(3, gap="large")
        with c1:
            grafico_categorias(base, medida)
        with c2:
            grafico_ticket_categoria(base)
        with c3:
            grafico_regioes(base, medida)

    with secao("Volume, custo e sazonalidade"):
        c1, c2 = st.columns(2, gap="large")
        with c1:
            grafico_dispersao_estados(base)
        with c2:
            grafico_calor(base, medida)

    with secao("Comparativo anual" + (" · ignora o filtro de ano" if ano != "Todos" else "")):
        c1, c2 = st.columns(2, gap="large")
        with c1:
            grafico_comparativo_anual(base_todos_anos, medida)
        with c2:
            grafico_variacao_estados(base_todos_anos, medida)

    with secao("Detalhes sob demanda"):
        tabela_detalhes(df_contexto)
