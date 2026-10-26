import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

st.set_page_config(
    page_title="Dashboard Analítico Interativo",
    page_icon="📊",
    layout="wide",
)

# ==========================================
# CONSTANTES DE DESIGN
# ==========================================
# Paleta Okabe-Ito (segura para daltônicos). A ordem foi validada para que
# pares adjacentes mantenham separação perceptível (ΔE ≥ 8) sob deuteranopia,
# protanopia e tritanopia.
PALETA_ACESSIVEL = [
    "#0072B2",  # azul
    "#E69F00",  # laranja
    "#009E73",  # verde
    "#56B4E9",  # azul claro
    "#CC79A7",  # rosa
]
PRIMARIA = PALETA_ACESSIVEL[0]
VERMELHAO = "#D55E00"  # polo negativo da escala divergente (par azul × vermelhão)
CINZA = "#C5CDD6"  # elementos fora da seleção (contexto)
CINZA_ESCURO = "#7B8794"
TINTA = "#1F2933"
TINTA_SECUNDARIA = "#52606D"
GRADE = "#EEF1F4"
EIXO = "#CBD2D9"
ESCALA_SEQUENCIAL = [[0.0, "#CFE3F2"], [0.5, "#5AA6D6"], [1.0, "#0B4F7C"]]

URL_VIDEO = "https://www.youtube.com/watch?v=jbkSRLYSojo"
URL_PRODUCAO = "https://dashboard-infovis.streamlit.app/"

MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

REGIOES = {
    "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MT", "MS"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
}
REGIAO_POR_ESTADO = {uf: regiao for regiao, ufs in REGIOES.items() for uf in ufs}

# Dimensões que participam do Brushing & Linking: chave -> coluna do DataFrame
DIMENSOES = {"meses": "mes", "estados": "estado", "categorias": "categoria", "regioes": "regiao"}
ROTULO_DIMENSAO = {"meses": "Meses", "estados": "Estados", "categorias": "Categorias", "regioes": "Regiões"}

MEDIDAS = {"atendimentos": "Atendimentos", "valor": "Valor (R$)"}

CONFIG_PLOTLY = {
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "zoom2d", "pan2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d",
        "toImage", "zoomInGeo", "zoomOutGeo", "resetGeo", "hoverClosestGeo",
    ],
}

# Layout minimalista (Data-Ink Ratio de Tufte): fundo neutro, sem bordas,
# grade horizontal quase imperceptível e eixos recessivos.
LAYOUT_TUFTE = dict(
    font=dict(family="Source Sans Pro, Segoe UI, sans-serif", size=13, color=TINTA_SECUNDARIA),
    paper_bgcolor="white",
    plot_bgcolor="white",
    colorway=PALETA_ACESSIVEL,
    separators=",.",
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis=dict(showgrid=False, zeroline=False, showline=True, linecolor=EIXO,
               ticks="outside", tickcolor=EIXO, ticklen=4, automargin=True),
    yaxis=dict(showgrid=True, gridcolor=GRADE, zeroline=False, showline=False, automargin=True),
    hoverlabel=dict(bgcolor="white", bordercolor=EIXO, font=dict(color=TINTA, size=13)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None),
    barcornerradius=4,
)
pio.templates["tufte"] = go.layout.Template(layout=LAYOUT_TUFTE)
pio.templates.default = "tufte"


def estilo_tufte(fig):
    # O frontend do Streamlit reaplica o próprio tema sobre o template; por isso o
    # estilo base é gravado no layout da figura, preservando os ajustes específicos.
    especifico = fig.layout.to_plotly_json()
    especifico.pop("template", None)
    fig.layout = go.Layout(LAYOUT_TUFTE)
    fig.update_layout(especifico)
    return fig


# ==========================================
# DADOS
# ==========================================
@st.cache_data
def carregar_dados():
    df = pd.read_csv("data/vendas.csv", parse_dates=["data"])
    df["regiao"] = df["estado"].map(REGIAO_POR_ESTADO)
    return df


@st.cache_data
def carregar_geojson():
    # Cópia local e simplificada da malha estadual (codeforamerica/click_that_hood),
    # evita dependência de rede e reduz o payload enviado ao navegador.
    return json.loads(Path("data/brasil-estados.geojson").read_text(encoding="utf-8"))


df_original = carregar_dados()
geojson_brasil = carregar_geojson()
CATEGORIAS = sorted(df_original["categoria"].unique())
COR_CATEGORIA = dict(zip(CATEGORIAS, PALETA_ACESSIVEL))  # cor fixa por entidade, nunca por ranking


# ==========================================
# FORMATAÇÃO (padrão brasileiro)
# ==========================================
def fmt_num(v, casas=0):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_brl(v):
    return "R$ " + fmt_num(v, 2)


def fmt_compacto(v):
    for limite, sufixo in ((1e9, " bi"), (1e6, " mi"), (1e3, " mil")):
        if abs(v) >= limite:
            return fmt_num(v / limite, 1) + sufixo
    return fmt_num(v)


def fmt_medida(v, medida, compacto=True):
    if medida == "valor":
        return "R$ " + (fmt_compacto(v) if compacto else fmt_num(v, 2))
    return fmt_compacto(v) if compacto else fmt_num(v)


def rotulo_mes(chave_mes):
    ano, mes = chave_mes.split("-")
    return f"{MESES_PT[int(mes) - 1]}/{ano[2:]}"


def hover_medida(medida, campo="y"):
    return f"R$ %{{{campo}:,.2f}}" if medida == "valor" else f"%{{{campo}:,.0f}}"


# ==========================================
# ESTADO GLOBAL DE SELEÇÃO (Brushing & Linking)
# ==========================================
st.session_state.setdefault("sel", {dim: [] for dim in DIMENSOES})

# Mantém os filtros da barra lateral ao navegar entre páginas
for chave_filtro in ("f_ano", "f_regioes", "f_categorias", "f_estados", "f_medida"):
    if chave_filtro in st.session_state:
        st.session_state[chave_filtro] = st.session_state[chave_filtro]


def _chave_do_ponto(ponto):
    dado = ponto.get("customdata")
    return dado[0] if isinstance(dado, (list, tuple)) else dado


def registrar_selecao(chave_grafico, dimensao):
    """Converte o evento de seleção do Plotly em estado global persistente.

    Clique alterna o item (permite seleção múltipla), caixa/laço substitui a
    seleção e duplo clique em área vazia limpa a dimensão.
    """
    def _callback():
        evento = st.session_state.get(chave_grafico) or {}
        selecao = evento.get("selection", {}) or {}
        pontos = selecao.get("points", []) or []
        valores = {v for v in (_chave_do_ponto(p) for p in pontos) if v is not None}
        por_area = bool(selecao.get("box") or selecao.get("lasso"))

        atual = set(st.session_state.sel[dimensao])
        if not pontos and not por_area:
            atual = set()
        elif por_area:
            atual = valores
        else:
            atual ^= valores
        st.session_state.sel[dimensao] = sorted(atual)

    return _callback


def limpar_selecao(dimensao=None):
    for dim in ([dimensao] if dimensao else DIMENSOES):
        st.session_state.sel[dim] = []


def aplicar_selecoes(df, exceto=()):
    """Cross-filter: cada visão é filtrada pelas seleções das OUTRAS visões
    e apenas destaca a sua própria seleção."""
    for dim, coluna in DIMENSOES.items():
        valores = st.session_state.sel[dim]
        if dim not in exceto and valores:
            df = df[df[coluna].isin(valores)]
    return df


def destaque(chaves, dimensao, cor_base=PRIMARIA, cor_fora=CINZA):
    selecionados = set(st.session_state.sel[dimensao])
    if not selecionados:
        return [cor_base] * len(chaves)
    return [cor_base if c in selecionados else cor_fora for c in chaves]


def opacidades(chaves, dimensao, fora=0.28):
    selecionados = set(st.session_state.sel[dimensao])
    if not selecionados:
        return [1.0] * len(chaves)
    return [1.0 if c in selecionados else fora for c in chaves]


def grafico_interativo(fig, chave, dimensao, modos=("points", "box")):
    estilo_tufte(fig)
    # Sem textfont explícito o Plotly falha ao estilizar rótulos na seleção e o
    # evento não chega ao Streamlit.
    estilo_texto = dict(textfont=dict(color=TINTA_SECUNDARIA))
    fig.update_traces(selected=estilo_texto, unselected=estilo_texto,
                      selector=lambda t: t.type in ("bar", "scatter") and t.text is not None)
    st.plotly_chart(
        fig, key=chave, on_select=registrar_selecao(chave, dimensao),
        selection_mode=list(modos), config=CONFIG_PLOTLY, theme=None, width="stretch",
    )


def grafico_estatico(fig, chave):
    estilo_tufte(fig).update_layout(dragmode=False)
    st.plotly_chart(fig, key=chave, config=CONFIG_PLOTLY, theme=None, width="stretch")


def cabecalho(titulo, legenda=None):
    st.markdown(f"<div class='titulo-grafico'>{titulo}</div>", unsafe_allow_html=True)
    if legenda:
        st.caption(legenda)


# ==========================================
# ESTILO GLOBAL
# ==========================================
st.markdown("""
<style>
:root {
    --tinta: #1F2933; --tinta-2: #52606D; --primaria: #0072B2;
    --linha: #E4E7EB; --superficie: #F5F7FA;
}
.block-container { padding-top: 2.2rem; max-width: 1400px; }
h1, h2, h3 { color: var(--tinta); letter-spacing: -0.01em; }

div[data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid var(--linha); border-radius: 12px;
    padding: 14px 18px; min-height: 150px;
}
div[data-testid="stMetricValue"] { font-size: 1.6rem; }
div[data-testid="stMetricValue"] > div, div[data-testid="stMetricLabel"] p { white-space: normal; overflow: visible; }
div[data-testid="stMetricLabel"] p { font-size: 0.85rem; color: var(--tinta-2); text-transform: uppercase; letter-spacing: .04em; }

.titulo-grafico { font-size: 1.05rem; font-weight: 600; color: var(--tinta); margin-bottom: -0.3rem; }
.secao { font-size: 0.78rem; font-weight: 700; color: var(--primaria); text-transform: uppercase;
         letter-spacing: .08em; margin: 1.4rem 0 0.2rem; }

/* ---------- Página inicial ---------- */
.hero {
    position: relative; overflow: hidden; border-radius: 18px; padding: 56px 48px 48px;
    background: linear-gradient(120deg, #0B3C5D 0%, #0072B2 55%, #3E9BD3 100%); color: #fff;
}
.hero h1 { color: #fff; font-size: 2.7rem; line-height: 1.1; margin: 0 0 14px; max-width: 720px; }
.hero p { font-size: 1.15rem; opacity: .92; max-width: 640px; margin: 0; }
.hero .rotulo { display: inline-block; font-size: .78rem; font-weight: 700; letter-spacing: .1em;
                text-transform: uppercase; background: rgba(255,255,255,.16); padding: 5px 12px;
                border-radius: 999px; margin-bottom: 18px; }
.hero .numeros { display: flex; gap: 36px; margin-top: 30px; flex-wrap: wrap; }
.hero .numeros b { display: block; font-size: 1.7rem; }
.hero .numeros span { font-size: .85rem; opacity: .8; }
.hero svg { position: absolute; right: 40px; bottom: 0; opacity: .9; }
@media (max-width: 900px) { .hero svg { display: none; } .hero { padding: 36px 24px; } .hero h1 { font-size: 2rem; } }

.passo { border: 1px solid var(--linha); border-radius: 14px; padding: 22px; background: #fff; height: 100%; }
.passo .num { width: 34px; height: 34px; border-radius: 50%; background: var(--primaria); color: #fff;
              display: flex; align-items: center; justify-content: center; font-weight: 700; margin-bottom: 12px; }
.passo h4 { margin: 0 0 6px; font-size: 1.05rem; color: var(--tinta); }
.passo p { margin: 0; color: var(--tinta-2); font-size: .95rem; }

.recurso { border-left: 3px solid var(--primaria); padding: 4px 0 4px 16px; margin-bottom: 18px; }
.recurso h4 { margin: 0 0 4px; font-size: 1rem; color: var(--tinta); }
.recurso p { margin: 0; color: var(--tinta-2); font-size: .93rem; }

.amostra { display: inline-flex; align-items: center; gap: 8px; margin: 0 18px 8px 0; font-size: .92rem; }
.amostra i { width: 18px; height: 18px; border-radius: 4px; display: inline-block; }

.st-key-btn_comecar button { padding: 0.75rem 2rem; font-size: 1.1rem; font-weight: 600; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# PÁGINA: INÍCIO
# ==========================================
def pagina_inicio():
    total_registros = fmt_num(len(df_original))
    total_estados = df_original["estado"].nunique()
    total_meses = df_original["mes"].nunique()

    barras_svg = "".join(
        f"<rect x='{i * 26}' y='{180 - h}' width='18' height='{h}' rx='4' fill='white' fill-opacity='{0.25 + i * 0.07:.2f}'/>"
        for i, h in enumerate([60, 90, 75, 120, 105, 150, 135, 170])
    )
    st.markdown(f"""
    <div class="hero">
        <span class="rotulo">InfoVis · UFPI 2026.2</span>
        <h1>Explore atendimentos e valores do Brasil em um painel que responde a cada clique.</h1>
        <p>Selecione meses, estados, regiões e categorias diretamente nos gráficos: todas as
        visões se filtram e se destacam em conjunto, com cores seguras para daltônicos e
        um visual enxuto que prioriza os dados.</p>
        <div class="numeros">
            <div><b>{total_registros}</b><span>registros</span></div>
            <div><b>{total_estados}</b><span>unidades federativas</span></div>
            <div><b>{len(CATEGORIAS)}</b><span>categorias</span></div>
            <div><b>{total_meses}</b><span>meses de histórico</span></div>
        </div>
        <svg width="210" height="180" viewBox="0 0 210 180" aria-hidden="true">{barras_svg}</svg>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    with st.container(horizontal=True, gap="small"):
        if st.button("Get started", type="primary", icon=":material/arrow_forward:", key="btn_comecar"):
            st.switch_page(PAGINA_DASHBOARD)
        if st.button("Como foi construído", icon=":material/account_tree:", key="btn_arquitetura"):
            st.switch_page(PAGINA_ARQUITETURA)

    # --- Primeiros passos ---
    st.markdown("<div class='secao'>Primeiros passos</div>", unsafe_allow_html=True)
    st.subheader("Do panorama ao detalhe em quatro passos")
    passos = [
        ("1", "Comece pelo panorama", "Os indicadores e a linha do tempo mostram o comportamento geral antes de qualquer recorte."),
        ("2", "Recorte com os filtros", "Na barra lateral, escolha ano, regiões, categorias e a medida (atendimentos ou valor)."),
        ("3", "Selecione nos gráficos", "Clique em barras, estados ou pontos, ou use caixa e laço. Tudo se atualiza junto."),
        ("4", "Vá aos detalhes", "A tabela final mostra os registros do contexto escolhido e permite exportar em CSV."),
    ]
    colunas = st.columns(4)
    for coluna, (num, titulo, texto) in zip(colunas, passos):
        coluna.markdown(
            f"<div class='passo'><div class='num'>{num}</div><h4>{titulo}</h4><p>{texto}</p></div>",
            unsafe_allow_html=True,
        )

    with st.expander("Gestos de interação (Brushing & Linking)", icon=":material/touch_app:"):
        st.markdown("""
| Gesto | Efeito |
|---|---|
| **Clique** em um elemento | Adiciona ou remove o item da seleção (permite selecionar vários) |
| **Caixa** (ícone na barra do gráfico) | Arraste para selecionar todos os itens dentro da área |
| **Laço** (ícone na barra do gráfico) | Desenhe uma área livre, ideal no gráfico de dispersão |
| **Duplo clique** em área vazia | Limpa a seleção daquele gráfico |
| Botões **✕** no topo do painel | Removem seleções individuais ou todas de uma vez |
        """)

    # --- Vídeo ilustrativo ---
    st.markdown("<div class='secao'>Vídeo ilustrativo</div>", unsafe_allow_html=True)
    col_video, col_texto = st.columns([3, 2], gap="large")
    with col_video:
        st.video(URL_VIDEO)
    with col_texto:
        st.subheader("Por que visualizar dados?")
        st.markdown(
            "No clássico *200 países, 200 anos, 4 minutos*, Hans Rosling mostra como uma "
            "visualização bem desenhada transforma milhares de números em uma história "
            "compreensível em segundos. Os mesmos princípios guiam este painel:"
        )
        st.markdown("""
- **Visão geral primeiro**, depois zoom, filtro e detalhes sob demanda (Shneiderman).
- **Codificação visual clara:** posição e comprimento para magnitude, cor para identidade.
- **Interação direta:** o usuário pergunta ao dado clicando no próprio gráfico.
        """)

    # --- O que há no painel ---
    st.markdown("<div class='secao'>O que você vai encontrar</div>", unsafe_allow_html=True)
    recursos = [
        ("Evolução e sazonalidade", "Série mensal, mapa de calor mês × categoria e comparativo 2024 × 2025."),
        ("Geografia", "Mapa coroplético, ranking de estados, totais por região e variação anual por UF."),
        ("Categorias e eficiência", "Volume por categoria, ticket médio e dispersão volume × ticket por estado."),
        ("Brushing & Linking", "Seleções cruzadas entre todos os gráficos, KPIs e tabela, com seleção múltipla."),
        ("Acessibilidade", "Paleta Okabe-Ito validada para daltonismo, rótulos diretos e tabela de dados."),
        ("Data-Ink Ratio", "Sem molduras, fundos ou eixos redundantes: a tinta está nos dados."),
    ]
    c1, c2, c3 = st.columns(3)
    for i, (titulo, texto) in enumerate(recursos):
        (c1, c2, c3)[i % 3].markdown(
            f"<div class='recurso'><h4>{titulo}</h4><p>{texto}</p></div>", unsafe_allow_html=True
        )

    st.divider()
    st.caption("Clériston de Castro Ramos · Introdução à Visualização da Informação · UFPI / CEAD")


# ==========================================
# PÁGINA: DASHBOARD
# ==========================================
def barra_de_selecoes():
    sel = st.session_state.sel
    ativos = [dim for dim in DIMENSOES if sel[dim]]
    if not ativos:
        st.caption(
            ":material/touch_app: Clique nos gráficos para selecionar (caixa e laço ficam na barra de cada gráfico). "
            "As demais visões serão filtradas e o gráfico de origem destacará a seleção."
        )
        return
    with st.container(horizontal=True, gap="small", vertical_alignment="center"):
        st.markdown("**Seleções ativas:**")
        for dim in ativos:
            valores = [rotulo_mes(v) for v in sel[dim]] if dim == "meses" else sel[dim]
            resumo = ", ".join(valores[:4]) + (f" +{len(valores) - 4}" if len(valores) > 4 else "")
            st.button(f"{ROTULO_DIMENSAO[dim]}: {resumo}", icon=":material/close:",
                      key=f"limpar_{dim}", on_click=limpar_selecao, args=(dim,))
        st.button("Limpar todas", icon=":material/filter_alt_off:", type="tertiary",
                  key="limpar_todas", on_click=limpar_selecao)


def filtros_globais():
    with st.sidebar:
        st.header("Filtros globais")
        medida = st.segmented_control(
            "Medida", options=list(MEDIDAS), format_func=MEDIDAS.get,
            default="atendimentos", key="f_medida",
        ) or "atendimentos"
        anos = sorted(df_original["ano"].unique())
        ano = st.selectbox("Ano", options=["Todos"] + anos, key="f_ano")
        regioes = st.pills("Regiões", options=list(REGIOES), selection_mode="multi", key="f_regioes")
        categorias = st.pills("Categorias", options=CATEGORIAS, selection_mode="multi", key="f_categorias")
        estados_opcoes = sorted(
            uf for uf in df_original["estado"].unique() if not regioes or REGIAO_POR_ESTADO[uf] in regioes
        )
        estados = st.multiselect("Estados", options=estados_opcoes, key="f_estados",
                                 placeholder="Todos os estados")
        st.caption("Sem itens marcados, todos são considerados.")

    base = df_original
    if regioes:
        base = base[base["regiao"].isin(regioes)]
    if categorias:
        base = base[base["categoria"].isin(categorias)]
    if estados:
        base = base[base["estado"].isin(estados)]
    base_todos_anos = base
    if ano != "Todos":
        base = base[base["ano"] == ano]
    return medida, ano, base, base_todos_anos


def indicadores(df, medida):
    mensal = df.groupby("data")[["atendimentos", "valor"]].sum().sort_index()

    def delta(serie):
        if len(serie) < 2 or serie.iloc[-2] == 0:
            return None
        return f"{(serie.iloc[-1] / serie.iloc[-2] - 1) * 100:+.1f}%".replace(".", ",")

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
    c1.metric("Atendimentos", fmt_num(total_atend), delta=delta(mensal["atendimentos"]),
              delta_description=descricao, chart_data=mensal["atendimentos"].tolist(), chart_type="area")
    c2.metric("Valor total", "R$ " + fmt_compacto(total_valor), delta=delta(mensal["valor"]),
              delta_description=descricao, chart_data=mensal["valor"].tolist(), chart_type="area",
              help=fmt_brl(total_valor))
    c3.metric("Ticket médio", fmt_brl(ticket), delta=delta(ticket_mensal),
              delta_description=descricao, chart_data=ticket_mensal.round(2).tolist(), chart_type="line",
              help="Valor total ÷ atendimentos")
    c4.metric("Mês de pico", pico_txt, delta=pico_valor, delta_color="off", delta_arrow="off",
              help=f"Mês com maior {MEDIDAS[medida].lower()} no contexto atual")
    c5.metric("Cobertura", f"{df['estado'].nunique()} UFs",
              delta=f"{df['categoria'].nunique()} categorias", delta_color="off", delta_arrow="off")


def grafico_temporal(base, medida):
    dados = aplicar_selecoes(base, exceto={"meses"})
    serie = dados.groupby(["data", "mes"], as_index=False)[medida].sum().sort_values("data")
    if serie.empty:
        st.info("Sem dados para o recorte atual.")
        return
    selecionados = set(st.session_state.sel["meses"])
    rotulos = [rotulo_mes(m) for m in serie["mes"]]

    fig = go.Figure(go.Scatter(
        x=serie["data"], y=serie[medida], mode="lines+markers",
        line=dict(color=CINZA_ESCURO if selecionados else PRIMARIA, width=2),
        marker=dict(
            color=destaque(serie["mes"], "meses"),
            size=[12 if m in selecionados else 8 for m in serie["mes"]],
            line=dict(color="white", width=2),
        ),
        customdata=np.column_stack([serie["mes"], rotulos]),
        hovertemplate=f"<b>%{{customdata[1]}}</b><br>{MEDIDAS[medida]}: {hover_medida(medida)}<extra></extra>",
    ))
    pico = serie.loc[serie[medida].idxmax()]
    fig.add_annotation(
        x=pico["data"], y=pico[medida], text=f"pico {fmt_medida(pico[medida], medida)}",
        showarrow=False, yshift=16, font=dict(size=12, color=TINTA),
    )
    passo = max(1, len(serie) // 8)
    fig.update_layout(
        height=300, showlegend=False,
        xaxis=dict(tickvals=serie["data"][::passo], ticktext=rotulos[::passo]),
        yaxis=dict(rangemode="tozero", tickformat="~s" if medida == "atendimentos" else "~s",
                   tickprefix="R$ " if medida == "valor" else ""),
    )
    grafico_interativo(fig, "g_temporal", "meses")


def grafico_mapa(base, medida):
    dados = aplicar_selecoes(base, exceto={"estados"})
    mapa = dados.groupby("estado", as_index=False)[medida].sum()
    if mapa.empty:
        st.info("Sem dados para o recorte atual.")
        return
    mapa["participacao"] = mapa[medida] / mapa[medida].sum() * 100
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
            customdata=np.column_stack([camada["estado"], camada["participacao"]]),
            hovertemplate=(f"<b>%{{location}}</b><br>{MEDIDAS[medida]}: {hover_medida(medida, 'z')}"
                           "<br>Participação: %{customdata[1]:.1f}%<extra></extra>"),
            colorbar=dict(thickness=10, len=0.55, x=0.98, outlinewidth=0, tickformat="~s",
                          title=dict(text=MEDIDAS[medida], side="right", font=dict(size=12))),
        ))
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)", projection_type="mercator")
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0))
    grafico_interativo(fig, "g_mapa", "estados")


def grafico_barras_horizontais(dados, chave_col, valor_col, medida, chave, dimensao, altura):
    dados = dados.sort_values(valor_col)
    fig = go.Figure(go.Bar(
        x=dados[valor_col], y=dados[chave_col], orientation="h",
        marker=dict(color=destaque(dados[chave_col], dimensao)),
        text=[fmt_medida(v, medida) for v in dados[valor_col]], textposition="outside",
        textfont=dict(color=TINTA_SECUNDARIA, size=12), cliponaxis=False,
        customdata=np.column_stack([dados[chave_col]]),
        hovertemplate=f"<b>%{{y}}</b><br>{MEDIDAS[medida]}: {hover_medida(medida, 'x')}<extra></extra>",
    ))
    fig.update_layout(
        height=altura, bargap=0.25, margin=dict(l=10, r=60, t=10, b=10),
        xaxis=dict(visible=False), yaxis=dict(showgrid=False, ticks="", tickfont=dict(color=TINTA)),
    )
    grafico_interativo(fig, chave, dimensao)


def grafico_ranking_estados(base, medida):
    dados = aplicar_selecoes(base, exceto={"estados"}).groupby("estado", as_index=False)[medida].sum()
    if dados.empty:
        st.info("Sem dados para o recorte atual.")
        return
    grafico_barras_horizontais(dados, "estado", medida, medida, "g_ranking", "estados",
                               altura=max(220, 19 * len(dados) + 40))


def grafico_regioes(base, medida):
    dados = aplicar_selecoes(base, exceto={"regioes"}).groupby("regiao", as_index=False)[medida].sum()
    if dados.empty:
        st.info("Sem dados para o recorte atual.")
        return
    grafico_barras_horizontais(dados, "regiao", medida, medida, "g_regioes", "regioes", altura=300)


def grafico_categorias(base, medida):
    dados = (aplicar_selecoes(base, exceto={"categorias"})
             .groupby("categoria", as_index=False)[medida].sum()
             .sort_values(medida, ascending=False))
    if dados.empty:
        st.info("Sem dados para o recorte atual.")
        return
    fig = go.Figure(go.Bar(
        x=dados["categoria"], y=dados[medida],
        marker=dict(color=[COR_CATEGORIA[c] for c in dados["categoria"]],
                    opacity=opacidades(dados["categoria"], "categorias")),
        text=[fmt_medida(v, medida) for v in dados[medida]], textposition="outside",
        textfont=dict(color=TINTA_SECUNDARIA, size=12), cliponaxis=False,
        customdata=np.column_stack([dados["categoria"]]),
        hovertemplate=f"<b>%{{x}}</b><br>{MEDIDAS[medida]}: {hover_medida(medida)}<extra></extra>",
    ))
    fig.update_layout(
        height=300, bargap=0.35, margin=dict(l=10, r=10, t=24, b=10),
        yaxis=dict(visible=False), xaxis=dict(showline=False, ticks="", tickfont=dict(color=TINTA)),
    )
    grafico_interativo(fig, "g_categorias", "categorias")


def grafico_ticket_categoria(base):
    dados = (aplicar_selecoes(base, exceto={"categorias"})
             .groupby("categoria", as_index=False)[["valor", "atendimentos"]].sum())
    if dados.empty:
        st.info("Sem dados para o recorte atual.")
        return
    dados["ticket"] = dados["valor"] / dados["atendimentos"]
    dados = dados.sort_values("ticket")
    media = dados["valor"].sum() / dados["atendimentos"].sum()

    fig = go.Figure(go.Scatter(
        x=dados["ticket"], y=dados["categoria"], mode="markers+text",
        marker=dict(size=14, color=[COR_CATEGORIA[c] for c in dados["categoria"]],
                    opacity=opacidades(dados["categoria"], "categorias"), line=dict(color="white", width=2)),
        text=[fmt_brl(v) for v in dados["ticket"]], textposition="middle right",
        textfont=dict(color=TINTA_SECUNDARIA, size=12), cliponaxis=False,
        customdata=np.column_stack([dados["categoria"]]),
        hovertemplate="<b>%{y}</b><br>Ticket médio: R$ %{x:,.2f}<extra></extra>",
    ))
    fig.add_vline(x=media, line=dict(color=CINZA_ESCURO, width=1, dash="dot"),
                  annotation=dict(text=f"média {fmt_brl(media)}", font=dict(size=11, color=TINTA_SECUNDARIA)),
                  annotation_position="top")
    amplitude = dados["ticket"].max() - dados["ticket"].min() or 1
    fig.update_layout(
        height=300, showlegend=False, margin=dict(l=10, r=30, t=30, b=10),
        # Eixo X oculto: os rótulos diretos já informam o valor de cada ponto
        xaxis=dict(visible=False,
                   range=[dados["ticket"].min() - amplitude * 0.3, dados["ticket"].max() + amplitude * 0.9]),
        yaxis=dict(showgrid=False, tickfont=dict(color=TINTA)),
    )
    grafico_interativo(fig, "g_ticket", "categorias")


def grafico_dispersao_estados(base):
    dados = (aplicar_selecoes(base, exceto={"estados"})
             .groupby("estado", as_index=False)[["atendimentos", "valor"]].sum())
    if dados.empty:
        st.info("Sem dados para o recorte atual.")
        return
    dados["ticket"] = dados["valor"] / dados["atendimentos"]
    selecionados = set(st.session_state.sel["estados"])

    fig = go.Figure(go.Scatter(
        x=dados["atendimentos"], y=dados["ticket"], mode="markers+text",
        text=dados["estado"], textposition="top center",
        textfont=dict(size=11, color=[TINTA if (not selecionados or e in selecionados) else CINZA
                                      for e in dados["estado"]]),
        marker=dict(size=11, color=destaque(dados["estado"], "estados"), line=dict(color="white", width=2)),
        customdata=np.column_stack([dados["estado"], dados["valor"]]),
        hovertemplate=("<b>%{customdata[0]}</b><br>Atendimentos: %{x:,.0f}"
                       "<br>Ticket médio: R$ %{y:,.2f}<extra></extra>"),
    ))
    for linha in ("x", "y"):
        mediana = dados["atendimentos" if linha == "x" else "ticket"].median()
        (fig.add_vline if linha == "x" else fig.add_hline)(
            mediana, line=dict(color=EIXO, width=1, dash="dot"))
    fig.update_layout(
        height=420, showlegend=False,
        xaxis=dict(title=dict(text="Atendimentos", font=dict(size=12)), tickformat="~s"),
        yaxis=dict(title=dict(text="Ticket médio (R$)", font=dict(size=12)), tickprefix="R$ ", tickformat=",.0f"),
    )
    grafico_interativo(fig, "g_dispersao", "estados", modos=("points", "box", "lasso"))


def grafico_calor(base, medida):
    dados = aplicar_selecoes(base, exceto={"meses", "categorias"})
    tabela = dados.pivot_table(index="categoria", columns="mes", values=medida, aggfunc="sum").sort_index(ascending=False)
    if tabela.empty:
        st.info("Sem dados para o recorte atual.")
        return
    meses = list(tabela.columns)
    rotulos = [rotulo_mes(m) for m in meses]
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
    grafico_estatico(fig, "g_calor")


def grafico_comparativo_anual(base_todos_anos, medida):
    dados = aplicar_selecoes(base_todos_anos, exceto={"meses"})
    serie = dados.groupby(["ano", dados["data"].dt.month])[medida].sum().reset_index()
    serie.columns = ["ano", "mes_num", medida]
    if serie.empty:
        st.info("Sem dados para o recorte atual.")
        return
    anos = sorted(serie["ano"].unique())
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
        yaxis=dict(tickformat="~s", tickprefix="R$ " if medida == "valor" else ""),
    )
    grafico_estatico(fig, "g_anual")


def grafico_variacao_estados(base_todos_anos, medida):
    dados = aplicar_selecoes(base_todos_anos, exceto={"estados"})
    tabela = dados.pivot_table(index="estado", columns="ano", values=medida, aggfunc="sum")
    anos = sorted(tabela.columns)
    if len(anos) < 2:
        st.info("São necessários dois anos para calcular a variação.")
        return
    a0, a1 = anos[-2], anos[-1]
    var = ((tabela[a1] / tabela[a0] - 1) * 100).dropna().sort_values().reset_index()
    var.columns = ["estado", "variacao"]
    cor_base = [PRIMARIA if v >= 0 else VERMELHAO for v in var["variacao"]]

    fig = go.Figure(go.Bar(
        x=var["variacao"], y=var["estado"], orientation="h",
        marker=dict(color=cor_base, opacity=opacidades(var["estado"], "estados")),
        text=[f"{v:+.1f}%".replace(".", ",") for v in var["variacao"]], textposition="outside",
        textfont=dict(size=11, color=TINTA_SECUNDARIA), cliponaxis=False,
        customdata=np.column_stack([var["estado"]]),
        hovertemplate=f"<b>%{{y}}</b><br>Variação {a1} vs {a0}: %{{x:+.1f}}%<extra></extra>",
    ))
    fig.update_layout(
        height=max(240, 19 * len(var) + 40), bargap=0.25, margin=dict(l=10, r=50, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        shapes=[dict(type="line", x0=0, x1=0, y0=-0.5, y1=len(var) - 0.5, line=dict(color=TINTA_SECUNDARIA, width=1))],
    )
    # Siglas do lado oposto à barra, junto à linha de base, para não colidir com os valores
    for estado, v in zip(var["estado"], var["variacao"]):
        fig.add_annotation(x=0, y=estado, text=estado, showarrow=False,
                           xanchor="left" if v < 0 else "right", xshift=5 if v < 0 else -5,
                           font=dict(size=11, color=TINTA))
    grafico_interativo(fig, "g_variacao", "estados")


def tabela_detalhes(df):
    detalhe = (df[["data", "regiao", "estado", "categoria", "atendimentos", "valor"]]
               .sort_values(["data", "estado", "categoria"]).copy())
    detalhe["ticket"] = detalhe["valor"] / detalhe["atendimentos"]
    st.caption(f"{fmt_num(len(detalhe))} registros no contexto atual.")
    st.dataframe(
        detalhe, hide_index=True, height=380, width="stretch",
        column_config={
            "data": st.column_config.DateColumn("Mês", format="MM/YYYY"),
            "regiao": "Região", "estado": "UF", "categoria": "Categoria",
            "atendimentos": st.column_config.NumberColumn("Atendimentos", format="localized"),
            "valor": st.column_config.NumberColumn("Valor (R$)", format="localized"),
            "ticket": st.column_config.NumberColumn("Ticket médio (R$)", format="localized"),
        },
    )
    exportar = detalhe.assign(data=detalhe["data"].dt.strftime("%m/%Y")).round(2)
    st.download_button(
        "Baixar dados filtrados (CSV)", icon=":material/download:",
        data=exportar.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name="dados_filtrados.csv", mime="text/csv",
    )


def pagina_dashboard():
    medida, ano, base, base_todos_anos = filtros_globais()

    st.title("Dashboard Analítico Interativo")
    st.caption("Visão gerencial de atendimentos e valores por estado, região, categoria e período.")
    barra_de_selecoes()

    df_contexto = aplicar_selecoes(base)
    if df_contexto.empty:
        st.warning("Nenhum registro corresponde à combinação de filtros e seleções. Limpe alguma seleção.")

    # ---------- Visão geral ----------
    indicadores(df_contexto, medida)

    st.markdown("<div class='secao'>Visão geral</div>", unsafe_allow_html=True)
    cabecalho(f"{MEDIDAS[medida]} por mês", "Clique nos pontos para selecionar meses (ou use a caixa na barra do gráfico).")
    grafico_temporal(base, medida)

    # ---------- Geografia ----------
    st.markdown("<div class='secao'>Geografia</div>", unsafe_allow_html=True)
    col_mapa, col_rank = st.columns([3, 2], gap="large")
    with col_mapa:
        cabecalho("Distribuição espacial", "Clique nos estados para selecioná-los; clique de novo para remover.")
        grafico_mapa(base, medida)
    with col_rank:
        cabecalho("Ranking de estados", "Mesma seleção do mapa: os dois gráficos compartilham a dimensão estado.")
        grafico_ranking_estados(base, medida)

    # ---------- Categorias e regiões ----------
    st.markdown("<div class='secao'>Categorias e regiões</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        cabecalho("Por categoria")
        grafico_categorias(base, medida)
    with c2:
        cabecalho("Ticket médio por categoria", "Valor ÷ atendimentos; linha pontilhada = média do contexto.")
        grafico_ticket_categoria(base)
    with c3:
        cabecalho("Por região")
        grafico_regioes(base, medida)

    # ---------- Relações e padrões ----------
    st.markdown("<div class='secao'>Relações e padrões</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        cabecalho("Volume × ticket médio por estado",
                  "Use o laço (barra do gráfico) para selecionar grupos de estados; linhas pontilhadas = medianas.")
        grafico_dispersao_estados(base)
    with c2:
        cabecalho("Sazonalidade: mês × categoria",
                  "Intensidade da cor = magnitude. Contornos marcam meses e categorias selecionados.")
        grafico_calor(base, medida)

    # ---------- Comparativo anual ----------
    st.markdown("<div class='secao'>Comparativo anual</div>", unsafe_allow_html=True)
    nota_ano = " Ignora o filtro de ano para permitir a comparação." if ano != "Todos" else ""
    c1, c2 = st.columns(2, gap="large")
    with c1:
        cabecalho("Ano contra ano", "Linha tracejada = ano anterior." + nota_ano)
        grafico_comparativo_anual(base_todos_anos, medida)
    with c2:
        cabecalho("Variação anual por estado",
                  "Azul = crescimento, vermelhão = queda (escala divergente segura para daltônicos)." + nota_ano)
        grafico_variacao_estados(base_todos_anos, medida)

    # ---------- Detalhes ----------
    st.markdown("<div class='secao'>Detalhes sob demanda</div>", unsafe_allow_html=True)
    tabela_detalhes(df_contexto)


# ==========================================
# PÁGINA: ARQUITETURA DE INTERAÇÃO
# ==========================================
def pagina_arquitetura():
    st.title("Arquitetura de Interação e Design")
    st.markdown(
        "Esta página documenta as bases conceituais, as decisões de design e a arquitetura "
        "técnica aplicadas na construção deste painel analítico."
    )

    st.header("1. O Mantra de Visualização de Dados", divider="gray")
    st.markdown("""
O layout segue o **Mantra da Busca de Informação Visual** de Ben Shneiderman (1996):

* ***Overview first* (visão geral primeiro):** KPIs com minigráficos de tendência e a série mensal oferecem o diagnóstico macro.
* ***Zoom and filter* (zoom e filtro):** filtros globais na barra lateral e seleção direta em qualquer gráfico recortam o contexto.
* ***Details on demand* (detalhes sob demanda):** a tabela final expõe os registros do contexto e permite exportá-los em CSV.
    """)

    st.header("2. Brushing & Linking com estado global", divider="gray")
    st.markdown("""
Cada gráfico interativo publica a sua seleção em um **estado global** (`st.session_state.sel`), organizado
em quatro dimensões: **meses, estados, categorias e regiões**. A partir dele aplica-se o padrão de
*cross-filtering*:

* **Filtrar:** cada visão é recalculada com as seleções feitas nas *outras* visões.
* **Destacar:** a visão de origem mantém todos os seus itens e realça os selecionados (os demais ficam em cinza ou translúcidos),
  preservando o contexto. Gráficos que compartilham a mesma dimensão, como mapa, ranking, dispersão e variação anual
  para *estados*, destacam a mesma seleção ao mesmo tempo.
* **Seleção múltipla:** clique alterna itens, caixa/laço substitui a seleção e duplo clique limpa a dimensão.
* KPIs e tabela refletem a interseção de **todas** as seleções.
    """)
    st.graphviz_chart("""
digraph {
  rankdir=LR; bgcolor="transparent";
  node [shape=box, style="rounded,filled", fillcolor="#F5F7FA", color="#CBD2D9", fontname="Helvetica", fontsize=11];
  edge [color="#7B8794", fontname="Helvetica", fontsize=9];
  csv [label="vendas.csv"]; filtros [label="Filtros globais\\n(ano, regiões,\\ncategorias, UFs)"];
  estado [label="Estado global\\nsel = {meses, estados,\\ncategorias, regiões}", fillcolor="#DCEBF5", color="#0072B2"];
  graficos [label="Gráficos\\n(filtrados pelas outras\\ndimensões + destaque)"];
  kpis [label="KPIs e tabela\\n(todas as seleções)"];
  csv -> filtros -> graficos; filtros -> kpis;
  graficos -> estado [label="clique / caixa / laço"];
  estado -> graficos [label="cross-filter"]; estado -> kpis;
}
    """)

    st.header("3. Limpeza visual (Data-Ink Ratio)", divider="gray")
    st.markdown("""
Inspirado em Edward Tufte, um *template* Plotly próprio (`tufte`) maximiza a proporção de tinta dedicada aos dados:
* **Sem fundos, molduras ou legendas redundantes:** rótulos diretos substituem eixos nos gráficos de barras.
* **Grade recessiva:** apenas linhas horizontais muito claras onde a leitura de magnitude depende delas.
* **Anotações seletivas:** só o pico da série, médias e medianas são anotados, nunca todos os pontos.
* **Separação entre marcas** (espaços de 2px no mapa de calor e entre barras) em vez de bordas pesadas.
    """)

    st.header("4. Acessibilidade visual", divider="gray")
    st.markdown("""
A paleta categórica é a **Okabe-Ito**, projetada para deficiências de visão de cores. A ordem dos tons foi
validada computacionalmente: todos os pares adjacentes mantêm diferença perceptual (ΔE OKLab) ≥ 8 sob
deuteranopia, protanopia e tritanopia. Além disso:
* **Cor segue a entidade:** cada categoria mantém sempre a mesma cor, independentemente de filtros ou ranking.
* **Magnitude usa uma única matiz** (azul, do claro ao escuro) e a **polaridade usa um par divergente**
  azul × vermelhão, distinguível por qualquer tipo de daltonismo.
* **Identidade nunca depende só da cor:** rótulos diretos, posição ordenada, contorno nas seleções e tabela de dados.
    """)
    amostras = "".join(
        f"<span class='amostra'><i style='background:{COR_CATEGORIA[c]}'></i>{c} <code>{COR_CATEGORIA[c]}</code></span>"
        for c in CATEGORIAS
    )
    amostras += (f"<span class='amostra'><i style='background:{VERMELHAO}'></i>Queda <code>{VERMELHAO}</code></span>"
                 f"<span class='amostra'><i style='background:{CINZA}'></i>Fora da seleção <code>{CINZA}</code></span>")
    st.markdown(amostras, unsafe_allow_html=True)


# ==========================================
# PÁGINA: INFORMAÇÕES ACADÊMICAS
# ==========================================
def pagina_creditos():
    st.title("Créditos e Informações Acadêmicas")
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

    st.divider()
    st.subheader("Acesso ao Painel Publicado")
    st.info("O ambiente de produção deste painel está hospedado e disponível para acesso público no Streamlit Community Cloud.")
    st.link_button("Acessar o Painel Interativo Online", URL_PRODUCAO, type="primary", icon=":material/open_in_new:")
    st.caption(f"Link direto: {URL_PRODUCAO}")


# ==========================================
# NAVEGAÇÃO (a casa leva de volta à página inicial)
# ==========================================
PAGINA_INICIO = st.Page(pagina_inicio, title="Início", icon=":material/home:", url_path="inicio", default=True)
PAGINA_DASHBOARD = st.Page(pagina_dashboard, title="Dashboard Analítico", icon=":material/monitoring:", url_path="dashboard")
PAGINA_ARQUITETURA = st.Page(pagina_arquitetura, title="Arquitetura de Interação", icon=":material/account_tree:", url_path="arquitetura")
PAGINA_CREDITOS = st.Page(pagina_creditos, title="Informações Acadêmicas", icon=":material/school:", url_path="creditos")

navegacao = st.navigation([PAGINA_INICIO, PAGINA_DASHBOARD, PAGINA_ARQUITETURA, PAGINA_CREDITOS])
navegacao.run()
