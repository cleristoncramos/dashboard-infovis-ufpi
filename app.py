import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import urllib.request
import json

st.set_page_config(
    page_title="Dashboard Analítico Interativo",
    page_icon="📊",
    layout="wide"
)

PALETA_ACESSIVEL = [
    "#0072B2",  # azul
    "#E69F00",  # laranja
    "#009E73",  # verde
    "#CC79A7",  # rosa
    "#56B4E9"   # azul claro
]

@st.cache_data
def carregar_dados():
    df = pd.read_csv("data/vendas.csv", parse_dates=["data"])
    return df

@st.cache_data
def carregar_geojson():
    url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())

geojson_brasil = carregar_geojson()
df_original = carregar_dados()

# ==========================================
# MENU DE NAVEGAÇÃO LATERAL
# ==========================================
st.sidebar.title("Navegação")
pagina_selecionada = st.sidebar.radio(
    "Ir para:", 
    [
        "📊 Dashboard Analítico", 
        "🧩 Arquitetura de Interação",
        "🎓 Informações Acadêmicas"
    ]
)
st.sidebar.divider()

# ==========================================
# PÁGINA 1: DASHBOARD
# ==========================================
if pagina_selecionada == "📊 Dashboard Analítico":
    
    # Restaura o título e o subtexto
    st.title("📊 Dashboard Analítico Interativo")
    st.caption(
        "Visão gerencial de atendimentos e valores por estado, categoria e período. "
        "Selecione elementos nos gráficos para filtrar e destacar as demais visões."
    )
    
    # Mantém a estilização CSS dos cartões com a altura padronizada
    st.markdown("""
        <style>
        div[data-testid="stMetric"] {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 10px;
            padding: 15px 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            transition: box-shadow 0.3s ease;
            height: 135px; /* Define uma altura fixa para igualar todos os cartões */
            display: flex;
            flex-direction: column;
            justify-content: center; /* Centraliza o conteúdo verticalmente no espaço vazio */
        }
        div[data-testid="stMetric"]:hover {
            box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Filtros globais (Sidebar) ---
    with st.sidebar:
        st.header("Filtros globais")
        anos = sorted(df_original["ano"].unique())
        ano_selecionado = st.selectbox("Ano", options=["Todos"] + anos, index=0)

        categorias_disponiveis = sorted(df_original["categoria"].unique())
        categorias_selecionadas = st.multiselect(
            "Categorias", options=categorias_disponiveis, default=categorias_disponiveis
        )

        estados_disponiveis = sorted(df_original["estado"].unique())
        estados_selecionados = st.multiselect(
            "Estados", options=estados_disponiveis, default=estados_disponiveis
        )

    # --- Captura de Seleções Interativas (Estado Global) ---
    sel_data = None
    sel_estado = None
    sel_categoria = None

    if "grafico_temporal" in st.session_state:
        pontos_temp = st.session_state["grafico_temporal"].get("selection", {}).get("points", [])
        if pontos_temp:
            sel_data = pontos_temp[0].get("x")

    if "grafico_mapa" in st.session_state:
        pontos_mapa = st.session_state["grafico_mapa"].get("selection", {}).get("points", [])
        if pontos_mapa:
            sel_estado = pontos_mapa[0].get("location")

    if "grafico_barras" in st.session_state:
        pontos_barras = st.session_state["grafico_barras"].get("selection", {}).get("points", [])
        if pontos_barras:
            sel_categoria = pontos_barras[0].get("x")

    # --- Aplicação de Filtros ---
    df_filtrado = df_original.copy()

    if ano_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["ano"] == ano_selecionado]
    if categorias_selecionadas:
        df_filtrado = df_filtrado[df_filtrado["categoria"].isin(categorias_selecionadas)]
    if estados_selecionados:
        df_filtrado = df_filtrado[df_filtrado["estado"].isin(estados_selecionados)]

    if sel_data:
        df_filtrado = df_filtrado[df_filtrado["data"] == pd.to_datetime(sel_data)]
        st.info(f"Filtro ativo pelo gráfico: Mês **{pd.to_datetime(sel_data).strftime('%m/%Y')}** (Clique em uma área vazia para limpar)")
    if sel_estado:
        df_filtrado = df_filtrado[df_filtrado["estado"] == sel_estado]
        st.info(f"Filtro ativo pelo mapa: Estado **{sel_estado}** (Clique no oceano para limpar)")
    if sel_categoria:
        df_filtrado = df_filtrado[df_filtrado["categoria"] == sel_categoria]
        st.info(f"Filtro ativo pelo gráfico: Categoria **{sel_categoria}** (Clique em uma área vazia para limpar)")

    # --- Indicadores gerais com Deltas ---
    total_atendimentos = int(df_filtrado["atendimentos"].sum())
    total_valor = float(df_filtrado["valor"].sum())
    qtde_estados = df_filtrado["estado"].nunique()
    qtde_categorias = df_filtrado["categoria"].nunique()

    atendimentos_formatado = f"{total_atendimentos:,}".replace(",", ".")
    valor_formatado = f"{total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    resumo_mensal = df_filtrado.groupby("data", as_index=False)[["atendimentos", "valor"]].sum().sort_values("data")
    delta_atendimentos, delta_valor = None, None

    if len(resumo_mensal) >= 2:
        atend_atual, atend_ant = resumo_mensal["atendimentos"].iloc[-1], resumo_mensal["atendimentos"].iloc[-2]
        valor_atual, valor_ant = resumo_mensal["valor"].iloc[-1], resumo_mensal["valor"].iloc[-2]
        
        if atend_ant > 0:
            variacao_atend = ((atend_atual - atend_ant) / atend_ant) * 100
            delta_atendimentos = f"{variacao_atend:.1f}% vs mês anterior".replace(".", ",")
        if valor_ant > 0:
            variacao_valor = ((valor_atual - valor_ant) / valor_ant) * 100
            delta_valor = f"{variacao_valor:.1f}% vs mês anterior".replace(".", ",")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Atendimentos", atendimentos_formatado, delta=delta_atendimentos)
    col2.metric("Valor total", f"R$ {valor_formatado}", delta=delta_valor)
    col3.metric("Estados", qtde_estados)
    col4.metric("Categorias", qtde_categorias)
    st.divider()

    # --- Visão temporal ---
    st.subheader("Visão geral temporal")
    serie_mensal = df_filtrado.groupby("data", as_index=False)["atendimentos"].sum().sort_values("data")

    fig_temporal = px.line(
        serie_mensal, x="data", y="atendimentos", markers=True,
        labels={"data": "Mês", "atendimentos": "Atendimentos"},
        color_discrete_sequence=[PALETA_ACESSIVEL[0]]
    )
    fig_temporal.update_traces(hovertemplate="<b>%{x|%B/%Y}</b><br>Atendimentos: %{y:,}<extra></extra>")
    fig_temporal.update_layout(
        height=340, margin=dict(l=40, r=20, t=30, b=40),
        hovermode="x unified", xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#E5E5E5"), plot_bgcolor="white"
    )

    st.plotly_chart(fig_temporal, key="grafico_temporal", on_select="rerun", selection_mode=["points"], use_container_width=True)

    # --- Layout Lado a Lado: Mapa e Barras ---
    col_mapa, col_barras = st.columns(2)

    with col_mapa:
        st.subheader("Distribuição espacial")
        mapa_dados = df_filtrado.groupby("estado", as_index=False)["atendimentos"].sum()
        fig_mapa = px.choropleth(
            mapa_dados, geojson=geojson_brasil, locations="estado",
            featureidkey="properties.sigla", color="atendimentos",
            color_continuous_scale="Blues", labels={"atendimentos": "Atendimentos"}
        )
        fig_mapa.update_traces(hovertemplate="<b>Estado:</b> %{location}<br><b>Atendimentos:</b> %{z:,}<extra></extra>")
        fig_mapa.update_geos(fitbounds="locations", visible=False)
        fig_mapa.update_layout(height=420, margin=dict(l=0, r=0, t=20, b=0), geo=dict(bgcolor="white"))
        
        st.plotly_chart(fig_mapa, key="grafico_mapa", on_select="rerun", selection_mode=["points"], use_container_width=True)

    with col_barras:
        st.subheader("Distribuição por categoria")
        barras_dados = df_filtrado.groupby("categoria", as_index=False)["atendimentos"].sum().sort_values("atendimentos", ascending=False)
        barras_dados["rotulo"] = barras_dados["atendimentos"].apply(lambda x: f"{x:,}".replace(",", "."))
        
        fig_barras = px.bar(
            barras_dados, x="categoria", y="atendimentos", text="rotulo",
            color="categoria", color_discrete_sequence=PALETA_ACESSIVEL,
            labels={"categoria": "Categoria", "atendimentos": "Atendimentos"}
        )
        fig_barras.update_traces(
            textposition="outside", textfont=dict(size=15, color="#333333"),
            hovertemplate="<b>%{x}</b><br>Atendimentos: %{y:,}<extra></extra>"
        )
        fig_barras.update_layout(
            height=420, showlegend=False, margin=dict(l=20, r=20, t=50, b=40),
            xaxis=dict(showgrid=False),
            yaxis=dict(showticklabels=False, showgrid=False, title="", zeroline=False),
            plot_bgcolor="white"
        )
        
        st.plotly_chart(fig_barras, key="grafico_barras", on_select="rerun", selection_mode=["points"], use_container_width=True)

    # --- Details on demand — tabela filtrada ---
    st.subheader("Detalhes sob demanda")

    colunas_detalhe = ["data", "estado", "categoria", "atendimentos", "valor"]
    tabela_detalhe = df_filtrado[colunas_detalhe].sort_values(["data", "estado", "categoria"]).copy()
    tabela_detalhe["data"] = tabela_detalhe["data"].dt.strftime("%d/%m/%Y")
    tabela_detalhe["valor"] = tabela_detalhe["valor"].map(lambda v: f"R$ {v:,.2f}")
    tabela_detalhe.columns = ["Data", "Estado", "Categoria", "Atendimentos", "Valor"]

    cor_cabecalho = PALETA_ACESSIVEL[0]
    cores_linhas = ["white" if i % 2 == 0 else "#F8F9FA" for i in range(len(tabela_detalhe))]

    fig_tabela = go.Figure(data=[go.Table(
        header=dict(
            values=["<b>" + col + "</b>" for col in tabela_detalhe.columns],
            fill_color=cor_cabecalho, align='center', font=dict(color='white', size=15), height=40
        ),
        cells=dict(
            values=[tabela_detalhe[col] for col in tabela_detalhe.columns],
            fill_color=[cores_linhas] * len(tabela_detalhe.columns),
            align='center', font=dict(color='#333333', size=13), height=35
        )
    )])
    fig_tabela.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=400)
    
    st.plotly_chart(fig_tabela, use_container_width=True, key="tabela_detalhes")

    st.download_button(
        label="Baixar dados filtrados em CSV",
        data=tabela_detalhe.to_csv(index=False).encode("utf-8-sig"),
        file_name="dados_filtrados.csv", mime="text/csv"
    )


# ==========================================
# PÁGINA 2: ARQUITETURA DE INTERAÇÃO
# ==========================================
elif pagina_selecionada == "🧩 Arquitetura de Interação":
    
    st.title("🧩 Arquitetura de Interação e Design")
    
    st.markdown("""
    Esta página documenta as bases conceptuais, as decisões de design e a arquitetura técnica aplicadas na construção deste painel analítico.
    
    ---
    
    ### 1. O Mantra de Visualização de Dados
    O layout foi rigorosamente estruturado seguindo o **Mantra da Busca de Informação Visual** proposto pelo investigador Ben Shneiderman (1996):
    
    * ***Overview First* (Visão Geral Primeiro):** A linha de tempo superior combinada com os KPIs funcionam como a porta de entrada da informação, oferecendo um diagnóstico macro imediato do desempenho global ao longo dos meses.
    * ***Zoom and Filter* (Zoom e Filtro):** Através da barra lateral e da interatividade direta nos componentes, o utilizador recorta a realidade institucional em secções menores (por ano, categoria ou área geográfica).
    * ***Details on Demand* (Detalhes sob Demanda):** A tabela zebrada no limite inferior do painel garante o acesso à granularidade máxima dos dados originais que formaram aquele contexto visual, permitindo inclusive a exportação (CSV) para auditoria.

    ### 2. Sincronização e *Brushing & Linking*
    A aplicação afasta-se de gráficos estáticos e isolados. Foi implementada uma arquitetura de **Estado Global** utilizando os recursos de sessão (`st.session_state`) do Streamlit integrados aos eventos nativos do Plotly (`on_select="rerun"`).
    
    Na prática, isto garante o efeito de *Brushing & Linking*: selecionar um ponto de dados num gráfico (ex: clicar no mapa) redimensiona e recalcula **instantaneamente** o contexto de todos os outros painéis e métricas (incluindo deltas de variação), refletindo uma perspetiva coesa.

    ### 3. Limpeza Visual (*Data-Ink Ratio*)
    Inspirados pela teoria de Edward Tufte, a interface foi otimizada para maximizar a proporção de "tinta de dados" (a percentagem de pixéis que efetivamente transmitem informação útil):
    * **Remoção de Redundâncias:** Ocultação do eixo vertical (Y) no gráfico de barras, uma vez que a rotulagem de dados exterior aos retângulos torna a grelha de fundo e a escala desnecessárias.
    * **Grelhas Minimalistas:** As grelhas horizontais foram substituídas por tons muito subtis e fundos puramente brancos para evitar a "poluição" cognitiva durante a leitura gerencial.
    * **Tabela Plotly Elegante:** Transição de uma grelha de dados em bruto para uma `go.Table` polida, com cabeçalhos destacados e efeito zebrado que reduz o esforço ocular na leitura horizontal de registos.

    ### 4. Acessibilidade Cognitiva e Visual
    A paleta de cores não foi escolhida ao acaso. As cores aplicadas (Azul, Laranja, Verde, Rosa e Azul Claro) obedecem a padrões de alto contraste e segurança cromática para deficiências visuais (Daltonismo), garantindo que categorias adjacentes não se fundem visualmente independentemente do utilizador.
    """)

# ==========================================
# PÁGINA 3: INFORMAÇÕES ACADÊMICAS
# ==========================================
elif pagina_selecionada == "🎓 Informações Acadêmicas":
    
    st.title("🎓 Créditos e Informações Acadêmicas")
    st.divider()
    
    st.markdown("""
    ### **UNIVERSIDADE FEDERAL DO PIAUÍ — UFPI**
    #### **CENTRO DE EDUCAÇÃO ABERTA E A DISTÂNCIA — CEAD**
    #### **CURSO TECNÓLOGO EM GESTÃO DE DADOS**
    
    ---
    
    * **Disciplina:** Introdução à Visualização da Informação (InfoVis)
    * **Módulo/Semestre:** 2026.2
    * **Professor:** Prof. MSc. Wesley Geraldo de Oliveira da Nóbrega
    * **Aluno:** Clériston de Castro Ramos
    * **Matrícula:** 20259048870
    
    ---
    
    *Este painel analítico foi desenvolvido como instrumento prático de avaliação técnica para a disciplina de Introdução à Visualização da Informação (InfoVis). O projeto materializa a aplicação de bibliotecas Python de alto desempenho (`Streamlit`, `Pandas`, `Plotly`) e a manipulação de dados geoespaciais (GeoJSON) na construção de interfaces gerenciais.* 
    
    *Destaca-se a implementação de uma arquitetura de estado global para permitir interações dinâmicas avançadas por meio de **Brushing & Linking**, onde a seleção em um gráfico cruza e filtra simultaneamente todo o contexto de dados do painel. Adicionalmente, o design foi rigorosamente pautado por diretrizes de **acessibilidade visual** — utilizando uma paleta de cores cromaticamente segura para daltônicos — e alinhado aos princípios de minimalismo analítico do **Data-Ink Ratio** de Edward Tufte, eliminando ruídos visuais para maximizar a eficiência e a precisão na comunicação da informação.*
    """)