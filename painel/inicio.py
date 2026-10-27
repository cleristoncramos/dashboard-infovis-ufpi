"""Página inicial: apresenta o que pode ser analisado e leva ao painel pelo botão Get started."""

import streamlit as st

from painel.base import ARQUIVO_VIDEO, CATEGORIAS, PAGINAS, df_original, fmt_compacto, fmt_num, secao


def render():
    total_atend = fmt_compacto(df_original["atendimentos"].sum())
    total_valor = fmt_compacto(df_original["valor"].sum())
    total_meses = df_original["mes"].nunique()

    barras_svg = "".join(
        f"<rect x='{i * 26}' y='{180 - h}' width='18' height='{h}' fill='white' fill-opacity='{0.25 + i * 0.07:.2f}'/>"
        for i, h in enumerate([60, 90, 75, 120, 105, 150, 135, 170])
    )
    st.markdown(f"""
    <div class="hero">
        <span class="rotulo">Painel analítico · 2024–2025</span>
        <h1>Atendimentos e recursos aplicados em serviços nas 27 unidades federativas</h1>
        <p>Descubra onde a demanda se concentra, quais áreas custam mais por atendimento, quais
        estados cresceram e em que meses a procura aumenta, em Educação, Infraestrutura, Saúde,
        Segurança e Tecnologia.</p>
        <div class="numeros">
            <div><b>{total_atend}</b><span>atendimentos</span></div>
            <div><b>R$ {total_valor}</b><span>em recursos aplicados</span></div>
            <div><b>27</b><span>unidades federativas</span></div>
            <div><b>{len(CATEGORIAS)}</b><span>áreas de serviço</span></div>
            <div><b>{total_meses}</b><span>meses de histórico</span></div>
        </div>
        <svg width="210" height="180" viewBox="0 0 210 180" aria-hidden="true">{barras_svg}</svg>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    if st.button("Get started", type="primary", icon=":material/arrow_forward:", key="btn_comecar"):
        st.switch_page(PAGINAS["panorama"])

    # --- Primeiros passos ---
    with secao("Primeiros passos"):
        st.subheader("Três perguntas, três páginas")
        passos = [
            ("1", "Panorama Nacional", "Qual o volume total, como ele evolui mês a mês e onde se concentra? "
                                       "Mapa, ranking de UFs, áreas, regiões e comparativo 2024 × 2025."),
            ("2", "Perfil por Estado", "Como uma UF se compara ao país? Posição no ranking, custo por "
                                       "atendimento, áreas de maior peso e crescimento anual."),
            ("3", "Áreas de Atendimento", "Qual área cresce mais, qual custa mais, em que meses a demanda sobe "
                                          "e qual a vocação de cada região?"),
            ("4", "Cruze e exporte", "Clique nos gráficos para cruzar as visões. Baixe qualquer gráfico em PNG "
                                     "(ícone de câmera) e seus dados em CSV."),
        ]
        colunas = st.columns(4)
        for coluna, (num, titulo, texto) in zip(colunas, passos):
            coluna.markdown(
                f"<div class='passo'><div class='num'>{num}</div><h4>{titulo}</h4><p>{texto}</p></div>",
                unsafe_allow_html=True,
            )

    # --- Vídeo ilustrativo gerado com os dados do próprio painel ---
    with secao("Vídeo ilustrativo"):
        col_video, col_texto = st.columns([3, 2], gap="large")
        with col_video:
            if ARQUIVO_VIDEO.exists():
                st.video(str(ARQUIVO_VIDEO))
            else:
                st.info("Vídeo não encontrado. Gere-o com `python gerar_video.py`.")
        with col_texto:
            st.subheader("Os dados em 40 segundos")
            st.markdown(
                "Animação produzida a partir da mesma base usada no painel. Em sequência, ela mostra:"
            )
            st.markdown("""
1. **A evolução mensal** dos atendimentos entre jan/2024 e dez/2025.
2. **A corrida entre as UFs**: o acumulado de atendimentos mês a mês.
3. **O peso de cada área** no total e o custo médio por atendimento.
4. **Quem cresceu e quem recuou** de 2024 para 2025.
        """)

    # --- O que pode ser analisado ---
    with secao("O que você pode analisar"):
        perguntas = [
            ("Volume e evolução", "Quantos atendimentos foram realizados, qual o mês de pico e se 2025 superou 2024."),
            ("Distribuição territorial", "Quais UFs e regiões concentram a demanda e quanto os 3 maiores estados representam."),
            ("Custo por atendimento", "Quanto se aplica, em média, por atendimento em cada área e em cada UF."),
            ("Crescimento", "Quais estados e áreas cresceram ou recuaram de um ano para o outro."),
            ("Sazonalidade", "Em quais meses a procura sobe ou cai, no total e em cada área."),
            ("Concentração e vocação", "Se a demanda está espalhada ou concentrada e em que área cada região se especializa."),
        ]
        c1, c2, c3 = st.columns(3)
        for i, (titulo, texto) in enumerate(perguntas):
            (c1, c2, c3)[i % 3].markdown(
                f"<div class='recurso'><h4>{titulo}</h4><p>{texto}</p></div>", unsafe_allow_html=True
            )

    st.divider()
    st.caption(f"Base com {fmt_num(len(df_original))} registros mensais (UF × área), simulada para fins "
               "acadêmicos · Clériston de Castro Ramos · Introdução à Visualização da Informação · UFPI / CEAD")
