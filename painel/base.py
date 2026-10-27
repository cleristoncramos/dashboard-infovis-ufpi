"""Recursos compartilhados entre as páginas: dados, paleta, formatação,
estado de seleção (Brushing & Linking), estilo dos gráficos e exportação."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent

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
ESCALA_DIVERGENTE = [[0.0, VERMELHAO], [0.5, "#F2F2F2"], [1.0, PRIMARIA]]

URL_PRODUCAO = "https://dashboard-infovis.streamlit.app/"
ARQUIVO_VIDEO = RAIZ / "assets" / "video_ilustrativo.mp4"

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
ROTULO_DIMENSAO = {"meses": "Meses", "estados": "Estados", "categorias": "Áreas", "regioes": "Regiões"}

MEDIDAS = {"atendimentos": "Atendimentos", "valor": "Recursos (R$)"}

# Páginas registradas pelo app.py (permite navegar sem import circular)
PAGINAS = {}

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

# Barra de ferramentas sempre visível e enxuta: câmera (PNG), caixa e laço.
CONFIG_PLOTLY = {
    "displaylogo": False,
    "displayModeBar": True,
    "modeBarButtonsToRemove": [
        "zoom2d", "pan2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d",
        "zoomInGeo", "zoomOutGeo", "resetGeo", "hoverClosestGeo", "select2d", "lasso2d",
    ],
}


# ==========================================
# DADOS
# ==========================================
@st.cache_data
def carregar_dados():
    df = pd.read_csv(RAIZ / "data" / "vendas.csv", parse_dates=["data"])
    df["regiao"] = df["estado"].map(REGIAO_POR_ESTADO)
    return df


@st.cache_data
def carregar_geojson():
    # Cópia local e simplificada da malha estadual (codeforamerica/click_that_hood),
    # evita dependência de rede e reduz o payload enviado ao navegador.
    return json.loads((RAIZ / "data" / "brasil-estados.geojson").read_text(encoding="utf-8"))


df_original = carregar_dados()
geojson_brasil = carregar_geojson()
CATEGORIAS = sorted(df_original["categoria"].unique())
COR_CATEGORIA = dict(zip(CATEGORIAS, PALETA_ACESSIVEL))  # cor fixa por entidade, nunca por ranking
NOME_UF = {f["properties"]["sigla"]: f["properties"]["name"] for f in geojson_brasil["features"]}
ANOS = sorted(df_original["ano"].unique())


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


def fmt_pct(v, casas=1, sinal=False):
    return (f"{v:+.{casas}f}%" if sinal else f"{v:.{casas}f}%").replace(".", ",")


def rotulo_mes(chave_mes):
    ano, mes = chave_mes.split("-")
    return f"{MESES_PT[int(mes) - 1]}/{ano[2:]}"


def hover_medida(medida, campo="y"):
    return f"R$ %{{{campo}:,.2f}}" if medida == "valor" else f"%{{{campo}:,.0f}}"


def prefixo_eixo(medida):
    return "R$ " if medida == "valor" else ""


# ==========================================
# ESTADO GLOBAL DE SELEÇÃO (Brushing & Linking)
# ==========================================
def iniciar_estado():
    st.session_state.setdefault("sel", {dim: [] for dim in DIMENSOES})
    # Mantém os filtros da barra lateral ao navegar entre páginas
    for chave in ("f_ano", "f_regioes", "f_categorias", "f_estados", "f_medida", "f_uf"):
        if chave in st.session_state:
            st.session_state[chave] = st.session_state[chave]


def _chave_do_ponto(ponto):
    dado = ponto.get("customdata")
    return dado[0] if isinstance(dado, (list, tuple)) else dado


def valores_do_evento(chave_grafico):
    """Retorna (valores, por_area, vazio) a partir do evento de seleção do Plotly."""
    evento = st.session_state.get(chave_grafico) or {}
    selecao = evento.get("selection", {}) or {}
    pontos = selecao.get("points", []) or []
    valores = {v for v in (_chave_do_ponto(p) for p in pontos) if v is not None}
    por_area = bool(selecao.get("box") or selecao.get("lasso"))
    return valores, por_area, not pontos and not por_area


def registrar_selecao(chave_grafico, dimensao):
    """Converte o evento de seleção do Plotly em estado global persistente.

    Clique alterna o item (permite seleção múltipla), caixa/laço substitui a
    seleção e duplo clique em área vazia limpa a dimensão.
    """
    def _callback():
        valores, por_area, vazio = valores_do_evento(chave_grafico)
        atual = set(st.session_state.sel[dimensao])
        if vazio:
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


def aplicar_selecoes(df, exceto=(), somente=None):
    """Cross-filter: cada visão é filtrada pelas seleções das OUTRAS visões
    e apenas destaca a sua própria seleção."""
    for dim, coluna in DIMENSOES.items():
        if dim in exceto or (somente is not None and dim not in somente):
            continue
        valores = st.session_state.sel[dim]
        if valores:
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


def barra_de_selecoes(dimensoes=tuple(DIMENSOES)):
    sel = st.session_state.sel
    ativos = [dim for dim in dimensoes if sel[dim]]
    if not ativos:
        st.caption(
            ":material/touch_app: Clique nos gráficos para selecionar e cruzar as visões · "
            ":material/photo_camera: câmera = imagem PNG · :material/download: Dados = tabela CSV"
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


# ==========================================
# FILTROS GLOBAIS (barra lateral)
# ==========================================
def filtros_globais(regioes=True, estados=True, categorias=True):
    with st.sidebar:
        st.markdown("<div class='rotulo-lateral'>Filtros</div>", unsafe_allow_html=True)
        medida = st.segmented_control(
            "Medida", options=list(MEDIDAS), format_func=MEDIDAS.get,
            default="atendimentos", key="f_medida",
        ) or "atendimentos"
        ano = st.selectbox("Ano", options=["Todos"] + ANOS, key="f_ano")
        regioes_sel = st.pills("Regiões", options=list(REGIOES), selection_mode="multi",
                               key="f_regioes") if regioes else []
        categorias_sel = st.pills("Áreas", options=CATEGORIAS, selection_mode="multi",
                                  key="f_categorias") if categorias else []
        estados_sel = []
        if estados:
            opcoes = sorted(uf for uf in NOME_UF if not regioes_sel or REGIAO_POR_ESTADO[uf] in regioes_sel)
            estados_sel = st.multiselect("Estados", options=opcoes, key="f_estados",
                                         placeholder="Todos os estados")
        st.caption("Sem itens marcados, todos são considerados.")

    base = df_original
    if regioes_sel:
        base = base[base["regiao"].isin(regioes_sel)]
    if categorias_sel:
        base = base[base["categoria"].isin(categorias_sel)]
    if estados_sel:
        base = base[base["estado"].isin(estados_sel)]
    base_todos_anos = base
    if ano != "Todos":
        base = base[base["ano"] == ano]
    return medida, ano, base, base_todos_anos


# ==========================================
# GRÁFICOS: estilo, renderização e exportação
# ==========================================
def estilo_tufte(fig):
    # O frontend do Streamlit reaplica o próprio tema sobre o template; por isso o
    # estilo base é gravado no layout da figura, preservando os ajustes específicos.
    especifico = fig.layout.to_plotly_json()
    especifico.pop("template", None)
    fig.layout = go.Layout(LAYOUT_TUFTE)
    fig.update_layout(especifico)
    return fig


def _config(nome_arquivo, selecao=False):
    config = dict(CONFIG_PLOTLY)
    if selecao:
        config["modeBarButtonsToRemove"] = [b for b in CONFIG_PLOTLY["modeBarButtonsToRemove"]
                                            if b not in ("select2d", "lasso2d")]
    config["toImageButtonOptions"] = {"format": "png", "filename": nome_arquivo, "scale": 2}
    return config


def grafico_interativo(fig, chave, dimensao=None, modos=("points", "box"), nome_arquivo=None, callback=None):
    estilo_tufte(fig)
    # Sem textfont explícito o Plotly falha ao estilizar rótulos na seleção e o
    # evento não chega ao Streamlit.
    estilo_texto = dict(textfont=dict(color=TINTA_SECUNDARIA))
    fig.update_traces(selected=estilo_texto, unselected=estilo_texto,
                      selector=lambda t: t.type in ("bar", "scatter") and t.text is not None)
    st.plotly_chart(
        fig, key=chave, on_select=callback or registrar_selecao(chave, dimensao),
        selection_mode=list(modos), config=_config(nome_arquivo or chave, selecao=True),
        theme=None, width="stretch",
    )


def grafico_estatico(fig, chave, nome_arquivo=None):
    estilo_tufte(fig).update_layout(dragmode=False)
    st.plotly_chart(fig, key=chave, config=_config(nome_arquivo or chave), theme=None, width="stretch")


def csv_bytes(df):
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def exportar_csv(df, nome_arquivo, rotulo="Dados (CSV)"):
    st.download_button(
        rotulo, data=csv_bytes(df), file_name=f"{nome_arquivo}.csv", mime="text/csv",
        key=f"csv_{nome_arquivo}", type="tertiary", icon=":material/download:", on_click="ignore",
    )


def cabecalho(titulo, insight=None):
    st.markdown(f"<div class='titulo-grafico'>{titulo}</div>", unsafe_allow_html=True)
    if insight:
        st.markdown(f"<div class='insight'>{insight}</div>", unsafe_allow_html=True)


def secao(texto):
    st.markdown(f"<div class='secao'>{texto}</div>", unsafe_allow_html=True)


def sem_dados():
    st.info("Sem dados para o recorte atual.")


def colunas_mensais(serie_datas):
    """Valores e rótulos de eixo em português para séries mensais."""
    datas = list(serie_datas)
    passo = max(1, len(datas) // 8)
    return datas[::passo], [f"{MESES_PT[d.month - 1]}/{str(d.year)[2:]}" for d in datas[::passo]]


def np_coluna(*series):
    return np.column_stack(list(series))
