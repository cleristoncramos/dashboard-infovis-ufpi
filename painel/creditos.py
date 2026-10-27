"""Informações acadêmicas e link de produção."""

import streamlit as st

from painel.base import URL_PRODUCAO


def render():
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

    *A base de dados (`data/vendas.csv`) é simulada pelo script `gerar_dados.py` e não representa estatísticas oficiais.*
    """)

    st.divider()
    st.subheader("Acesso ao Painel Publicado")
    st.info("O ambiente de produção deste painel está hospedado e disponível para acesso público no Streamlit Community Cloud.")
    st.link_button("Acessar o Painel Interativo Online", URL_PRODUCAO, type="primary", icon=":material/open_in_new:")
    st.caption(f"Link direto: {URL_PRODUCAO}")
