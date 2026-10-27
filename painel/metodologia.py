"""Metodologia: dados, indicadores e decisões de design e interação."""

import streamlit as st

from painel.base import CATEGORIAS, CINZA, COR_CATEGORIA, VERMELHAO


def render():
    st.title("Metodologia e Design")
    st.markdown(
        "Como os dados são organizados, como cada indicador é calculado e quais princípios de "
        "visualização orientam o painel."
    )

    st.header("1. Dados e indicadores", divider="gray")
    st.markdown("""
A base reúne **registros mensais por UF e área de serviço** (jan/2024 a dez/2025) com duas medidas:
**atendimentos** realizados e **recursos aplicados** (R$). A partir delas o painel deriva:

| Indicador | Cálculo | O que revela |
|---|---|---|
| Custo por atendimento | recursos ÷ atendimentos | eficiência relativa de áreas e UFs |
| Participação | valor do item ÷ total do recorte | peso de uma UF, região ou área |
| Variação anual | último ano ÷ ano anterior − 1 | crescimento ou retração |
| Tendência mensal | inclinação da reta de regressão ÷ média | ritmo de crescimento de cada área |
| Índice sazonal | média do mês ÷ média geral × 100 | meses de demanda acima/abaixo do típico |
| Curva de concentração | participação acumulada das UFs ordenadas | quão espalhada é a demanda |
| Quociente locacional | peso da área na região ÷ peso no Brasil | vocação (especialização) regional |

Os textos sob cada título são **calculados a partir do recorte atual** e mudam com filtros e seleções.
    """)

    st.header("2. Organização das páginas", divider="gray")
    st.markdown("""
O layout segue o **Mantra da Busca de Informação Visual** de Ben Shneiderman (1996):

* **Panorama Nacional** — *overview first*: KPIs, evolução, mapa, áreas, regiões e comparativo anual.
* **Perfil por Estado** — *zoom and filter*: uma UF frente à média nacional.
* **Áreas de Atendimento** — análise por tema: tendência, custo, sazonalidade, concentração e vocação.
* Tabelas ao final de cada página — *details on demand*, com exportação em CSV.
    """)

    st.header("3. Brushing & Linking com estado global", divider="gray")
    st.markdown("""
Cada gráfico interativo publica a sua seleção em um **estado global** (`st.session_state.sel`), organizado
em quatro dimensões: **meses, estados, áreas e regiões**. A partir dele aplica-se o padrão de *cross-filtering*:

* **Filtrar:** cada visão é recalculada com as seleções feitas nas *outras* visões.
* **Destacar:** a visão de origem mantém seus itens e realça os selecionados (os demais ficam em cinza ou
  translúcidos). Gráficos que compartilham a mesma dimensão destacam a mesma seleção ao mesmo tempo.
* **Seleção múltipla:** clique alterna itens, caixa/laço substitui a seleção e duplo clique limpa a dimensão.
* No **Perfil por Estado**, clicar em outra UF do ranking troca a UF analisada; clicar numa área filtra o perfil.
* Nas **Áreas de Atendimento**, clicar numa área dos pequenos múltiplos realça-a em todos os gráficos da página.
    """)
    st.graphviz_chart("""
digraph {
  rankdir=LR; bgcolor="transparent";
  node [shape=box, style="rounded,filled", fillcolor="#F5F7FA", color="#CBD2D9", fontname="Helvetica", fontsize=11];
  edge [color="#7B8794", fontname="Helvetica", fontsize=9];
  csv [label="vendas.csv"]; filtros [label="Filtros\\n(medida, ano, regiões,\\náreas, UFs)"];
  estado [label="Estado global\\nsel = {meses, estados,\\náreas, regiões}", fillcolor="#DCEBF5", color="#0072B2"];
  graficos [label="Gráficos\\n(filtrados pelas outras\\ndimensões + destaque)"];
  kpis [label="KPIs, insights\\ne tabelas"];
  exp [label="Exportação\\nPNG e CSV"];
  csv -> filtros -> graficos; filtros -> kpis;
  graficos -> estado [label="clique / caixa / laço"];
  estado -> graficos [label="cross-filter"]; estado -> kpis;
  graficos -> exp; kpis -> exp;
}
    """)

    st.header("4. Exportação", divider="gray")
    st.markdown("""
* **PNG:** o ícone de câmera na barra de cada gráfico baixa a imagem em alta resolução (escala 2×).
* **CSV:** o botão *Dados (CSV)* sob cada gráfico baixa exatamente os números exibidos; as tabelas finais
  exportam os registros do recorte. Os arquivos usam `;` como separador e `,` decimal (padrão do Excel em português).
    """)

    st.header("5. Limpeza visual (Data-Ink Ratio)", divider="gray")
    st.markdown("""
Inspirado em Edward Tufte, um layout Plotly próprio maximiza a proporção de tinta dedicada aos dados:
* **Sem fundos, molduras ou legendas redundantes:** rótulos diretos substituem eixos nos gráficos de barras.
* **Grade recessiva:** apenas linhas horizontais muito claras onde a leitura de magnitude depende delas.
* **Anotações seletivas:** pico, médias, medianas e o último valor; nunca um número em cada ponto.
* **Pequenos múltiplos** com eixo compartilhado em vez de cinco linhas sobrepostas.
* **Separação entre marcas** (espaços de 2px nos mapas de calor e entre barras) em vez de bordas pesadas.
    """)

    st.header("6. Acessibilidade visual", divider="gray")
    st.markdown("""
A paleta categórica é a **Okabe-Ito**, projetada para deficiências de visão de cores. A ordem dos tons foi
validada computacionalmente: todos os pares adjacentes mantêm diferença perceptual (ΔE OKLab) ≥ 8 sob
deuteranopia, protanopia e tritanopia. Além disso:
* **Cor segue a entidade:** cada área mantém sempre a mesma cor, em todas as páginas e no vídeo.
* **Magnitude usa uma única matiz** (azul, do claro ao escuro) e a **polaridade usa um par divergente**
  azul × vermelhão com meio neutro, distinguível por qualquer tipo de daltonismo.
* **Identidade nunca depende só da cor:** rótulos diretos, posição ordenada, contorno nas seleções e tabelas.
    """)
    amostras = "".join(
        f"<span class='amostra'><i style='background:{COR_CATEGORIA[c]}'></i>{c} <code>{COR_CATEGORIA[c]}</code></span>"
        for c in CATEGORIAS
    )
    amostras += (f"<span class='amostra'><i style='background:{VERMELHAO}'></i>Queda <code>{VERMELHAO}</code></span>"
                 f"<span class='amostra'><i style='background:{CINZA}'></i>Fora da seleção <code>{CINZA}</code></span>")
    st.markdown(amostras, unsafe_allow_html=True)
