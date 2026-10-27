import streamlit as st

st.set_page_config(
    page_title="Atendimentos e Recursos por UF",
    page_icon="📊",
    layout="wide",
)

from painel import areas, creditos, estados, inicio, metodologia, panorama  # noqa: E402
from painel.base import PAGINAS, iniciar_estado  # noqa: E402

iniciar_estado()

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

.titulo-grafico { font-size: 1.08rem; font-weight: 600; color: var(--tinta); margin-bottom: 0.15rem; }
.insight { font-size: 0.92rem; color: var(--tinta-2); line-height: 1.45; margin-bottom: 0.3rem; }
.insight b { color: var(--tinta); }
.resumo { background: var(--superficie); border-left: 3px solid var(--primaria); border-radius: 6px;
          padding: 12px 16px; color: var(--tinta-2); margin: 0.6rem 0 0.4rem; }
.resumo b { color: var(--tinta); }
.secao { font-size: 0.78rem; font-weight: 700; color: var(--primaria); text-transform: uppercase;
         letter-spacing: .08em; margin: 1.6rem 0 0.4rem; border-top: 1px solid var(--linha); padding-top: 1rem; }
.rotulo-lateral { font-size: 0.72rem; font-weight: 700; color: var(--tinta-2); text-transform: uppercase;
                  letter-spacing: .08em; margin: 0.4rem 0 0.2rem; }

/* Ícone de casa no canto superior do sidebar, na mesma linha do botão de recolher */
.st-key-btn_home { margin-top: -3.6rem; margin-bottom: 1.2rem; }
.st-key-btn_home button { border: none; background: transparent; padding: 4px 6px; min-height: 0; }
.st-key-btn_home button span[data-testid="stIconMaterial"] { font-size: 1.6rem; color: var(--primaria); }
.st-key-btn_home button:hover { background: var(--superficie); }

/* ---------- Página inicial ---------- */
.hero {
    position: relative; overflow: hidden; border-radius: 18px; padding: 56px 48px 48px;
    background: linear-gradient(120deg, #0B3C5D 0%, #0072B2 55%, #3E9BD3 100%); color: #fff;
}
.hero h1 { color: #fff; font-size: 2.6rem; line-height: 1.12; margin: 0 0 14px; max-width: 760px; }
.hero p { font-size: 1.12rem; opacity: .92; max-width: 680px; margin: 0; }
.hero .rotulo { display: inline-block; font-size: .78rem; font-weight: 700; letter-spacing: .1em;
                text-transform: uppercase; background: rgba(255,255,255,.16); padding: 5px 12px;
                border-radius: 999px; margin-bottom: 18px; }
.hero .numeros { display: flex; gap: 36px; margin-top: 30px; flex-wrap: wrap; }
.hero .numeros b { display: block; font-size: 1.6rem; }
.hero .numeros span { font-size: .85rem; opacity: .8; }
.hero svg { position: absolute; right: 40px; bottom: 0; opacity: .9; }
@media (max-width: 1100px) { .hero svg { display: none; } }
@media (max-width: 900px) { .hero { padding: 36px 24px; } .hero h1 { font-size: 1.9rem; } }

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

.st-key-btn_comecar button { padding: 0.75rem 2.2rem; font-size: 1.15rem; font-weight: 600; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# NAVEGAÇÃO
# ==========================================
# O menu padrão fica oculto: a página inicial não exibe barra lateral e só leva ao
# painel pelo botão "Get started"; nas demais páginas, o ícone de casa volta ao início.
PAGINAS.update({
    "inicio": st.Page(inicio.render, title="Início", icon=":material/home:", url_path="inicio", default=True),
    "panorama": st.Page(panorama.render, title="Panorama Nacional", icon=":material/public:", url_path="panorama"),
    "estados": st.Page(estados.render, title="Perfil por Estado", icon=":material/location_on:", url_path="estados"),
    "areas": st.Page(areas.render, title="Áreas de Atendimento", icon=":material/category:", url_path="areas"),
    "metodologia": st.Page(metodologia.render, title="Metodologia e Design", icon=":material/menu_book:",
                           url_path="metodologia"),
    "creditos": st.Page(creditos.render, title="Informações Acadêmicas", icon=":material/school:",
                        url_path="creditos"),
})

pagina_atual = st.navigation(list(PAGINAS.values()), position="hidden")

if pagina_atual.url_path != PAGINAS["inicio"].url_path:
    with st.sidebar:
        if st.button("", icon=":material/home:", key="btn_home", help="Voltar à página inicial"):
            st.switch_page(PAGINAS["inicio"])
        st.markdown("<div class='rotulo-lateral'>Análises</div>", unsafe_allow_html=True)
        for chave in ("panorama", "estados", "areas"):
            st.page_link(PAGINAS[chave])
        st.markdown("<div class='rotulo-lateral'>Sobre</div>", unsafe_allow_html=True)
        for chave in ("metodologia", "creditos"):
            st.page_link(PAGINAS[chave])
        st.divider()

pagina_atual.run()
