"""Gera o vídeo ilustrativo da página inicial a partir de data/vendas.csv.

Uso:  python gerar_video.py
Requer as dependências de requirements-dev.txt (matplotlib e imageio-ffmpeg).
Saída: assets/video_ilustrativo.mp4 (1280×720, H.264, 24 fps).
"""

from pathlib import Path

import imageio_ffmpeg
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.animation import FFMpegWriter  # noqa: E402

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "assets" / "video_ilustrativo.mp4"
FPS = 24

# Mesma paleta acessível do painel (Okabe-Ito, ordem validada)
PALETA = ["#0072B2", "#E69F00", "#009E73", "#56B4E9", "#CC79A7"]
PRIMARIA, VERMELHAO = "#0072B2", "#D55E00"
TINTA, TINTA_2, GRADE, CINZA = "#1F2933", "#52606D", "#EEF1F4", "#C5CDD6"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 15, "text.color": TINTA,
    "axes.edgecolor": CINZA, "axes.labelcolor": TINTA_2,
    "xtick.color": TINTA_2, "ytick.color": TINTA_2,
    "animation.ffmpeg_path": imageio_ffmpeg.get_ffmpeg_exe(),
})


def fmt_num(v, casas=0):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_compacto(v):
    for limite, sufixo in ((1e9, " bi"), (1e6, " mi"), (1e3, " mil")):
        if abs(v) >= limite:
            return fmt_num(v / limite, 1) + sufixo
    return fmt_num(v)


def suave(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def eixo_limpo(ax, grade_y=True):
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(length=0)
    if grade_y:
        ax.grid(axis="y", color=GRADE, linewidth=1)
        ax.set_axisbelow(True)


def titulo(fig, texto, subtitulo=None):
    fig.text(0.06, 0.90, texto, fontsize=28, fontweight="bold", color=TINTA)
    if subtitulo:
        fig.text(0.06, 0.845, subtitulo, fontsize=16, color=TINTA_2)


def rodape(fig):
    fig.text(0.06, 0.04, "Painel Analítico · Atendimentos e recursos por UF · 2024–2025",
             fontsize=12, color=TINTA_2)


# ==========================================
# DADOS
# ==========================================
df = pd.read_csv(RAIZ / "data" / "vendas.csv", parse_dates=["data"])
mensal = df.groupby("data")["atendimentos"].sum().sort_index()
acumulado_uf = df.pivot_table(index="data", columns="estado", values="atendimentos", aggfunc="sum").sort_index().cumsum()
por_area = df.groupby("categoria")[["atendimentos", "valor"]].sum()
por_area["participacao"] = por_area["atendimentos"] / por_area["atendimentos"].sum() * 100
por_area["custo"] = por_area["valor"] / por_area["atendimentos"]
por_area = por_area.sort_values("atendimentos")
COR_AREA = dict(zip(sorted(por_area.index), PALETA))
anos = sorted(df["ano"].unique())
tab_ano = df.pivot_table(index="estado", columns="ano", values="atendimentos", aggfunc="sum")
variacao = ((tab_ano[anos[-1]] / tab_ano[anos[-2]] - 1) * 100).sort_values()


# ==========================================
# CENAS (cada uma desenha um quadro a partir do progresso t ∈ [0, 1])
# ==========================================
def cena_abertura(fig, t):
    a = suave(t * 2)
    fig.text(0.06, 0.62, "Atendimentos e recursos aplicados", fontsize=40, fontweight="bold",
             color=TINTA, alpha=a)
    fig.text(0.06, 0.55, "Educação · Infraestrutura · Saúde · Segurança · Tecnologia", fontsize=20,
             color=TINTA_2, alpha=a)
    numeros = [(fmt_compacto(df["atendimentos"].sum()), "atendimentos"),
               ("R$ " + fmt_compacto(df["valor"].sum()), "em recursos"),
               ("27", "unidades federativas"), (str(df["mes"].nunique()), "meses")]
    for i, ((valor, rotulo), x) in enumerate(zip(numeros, (0.06, 0.26, 0.52, 0.74))):
        b = suave(t * 2.5 - 0.3 - i * 0.15)
        fig.text(x, 0.36, valor, fontsize=32, fontweight="bold", color=PRIMARIA, alpha=b)
        fig.text(x, 0.31, rotulo, fontsize=15, color=TINTA_2, alpha=b)
    rodape(fig)


def cena_evolucao(fig, t):
    titulo(fig, "Como a demanda evoluiu mês a mês", "Total de atendimentos por mês, jan/2024 a dez/2025")
    ax = fig.add_axes([0.08, 0.14, 0.86, 0.64])
    eixo_limpo(ax)
    n = len(mensal)
    visiveis = max(1, int(round(suave(t / 0.8) * n)))
    x = list(range(n))
    ax.plot(x[:visiveis], mensal.values[:visiveis], color=PRIMARIA, linewidth=3, marker="o",
            markersize=6, markeredgecolor="white")
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(0, mensal.max() * 1.18)
    ax.set_xticks(x[::3])
    ax.set_xticklabels([f"{MESES[d.month - 1]}/{str(d.year)[2:]}" for d in mensal.index[::3]])
    ax.yaxis.set_major_formatter(lambda v, _: fmt_compacto(v))
    ultimo = mensal.index[visiveis - 1]
    ax.text(visiveis - 1, mensal.values[visiveis - 1] * 1.05, fmt_compacto(mensal.values[visiveis - 1]),
            ha="center", fontsize=14, color=TINTA, fontweight="bold")
    fig.text(0.94, 0.80, f"{MESES[ultimo.month - 1]}/{ultimo.year}", ha="right", fontsize=22, color=CINZA,
             fontweight="bold")
    if visiveis == n:
        pico = mensal.idxmax()
        i = list(mensal.index).index(pico)
        a = suave((t - 0.8) / 0.15)
        ax.annotate(f"pico: {MESES[pico.month - 1]}/{pico.year}", (i, mensal.max()), xytext=(i, mensal.max() * 1.12),
                    ha="center", fontsize=14, color=TINTA_2, alpha=a,
                    arrowprops=dict(arrowstyle="-", color=TINTA_2, alpha=a))
    rodape(fig)


def cena_corrida(fig, t):
    titulo(fig, "A corrida entre as UFs", "Atendimentos acumulados mês a mês: as 12 maiores")
    ax = fig.add_axes([0.08, 0.10, 0.84, 0.70])
    eixo_limpo(ax, grade_y=False)
    pos = suave(t / 0.9) * (len(acumulado_uf) - 1)
    i0 = int(pos)
    i1 = min(i0 + 1, len(acumulado_uf) - 1)
    frac = pos - i0
    valores = acumulado_uf.iloc[i0] * (1 - frac) + acumulado_uf.iloc[i1] * frac
    top = valores.sort_values(ascending=False).head(12)[::-1]
    ax.barh(range(len(top)), top.values, color=PRIMARIA, height=0.72)
    for j, (uf, v) in enumerate(top.items()):
        ax.text(v, j, f"  {fmt_compacto(v)}", va="center", fontsize=13, color=TINTA_2)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top.index, fontsize=15, color=TINTA)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    ax.set_xlim(0, acumulado_uf.iloc[-1].max() * 1.12)
    data = acumulado_uf.index[i1 if frac > 0.5 else i0]
    fig.text(0.94, 0.90, f"{MESES[data.month - 1]}/{data.year}", ha="right", fontsize=34,
             color=CINZA, fontweight="bold")
    rodape(fig)


def cena_areas(fig, t):
    titulo(fig, "O peso de cada área", "Participação nos atendimentos e custo médio por atendimento")
    ax = fig.add_axes([0.20, 0.12, 0.56, 0.66])
    eixo_limpo(ax, grade_y=False)
    a = suave(t / 0.6)
    cores = [COR_AREA[c] for c in por_area.index]
    ax.barh(range(len(por_area)), por_area["participacao"] * a, color=cores, height=0.62)
    for j, (cat, linha) in enumerate(por_area.iterrows()):
        ax.text(linha["participacao"] * a, j, f"  {fmt_num(linha['participacao'] * a, 1)}%",
                va="center", fontsize=15, color=TINTA_2)
        b = suave((t - 0.5) / 0.3)
        fig.text(0.83, 0.12 + (j + 0.5) * 0.66 / len(por_area) - 0.012,
                 f"R$ {fmt_num(linha['custo'], 2)}", fontsize=15, color=TINTA, alpha=b)
    fig.text(0.83, 0.80, "custo por atendimento", fontsize=13, color=TINTA_2, alpha=suave((t - 0.5) / 0.3))
    ax.set_yticks(range(len(por_area)))
    ax.set_yticklabels(por_area.index, fontsize=16, color=TINTA)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    ax.set_xlim(0, por_area["participacao"].max() * 1.3)
    ax.set_ylim(-0.5, len(por_area) - 0.5)
    rodape(fig)


def cena_variacao(fig, t):
    cresceram = int((variacao > 0).sum())
    titulo(fig, f"Quem cresceu de {anos[-2]} para {anos[-1]}",
           f"{cresceram} de {len(variacao)} UFs ampliaram os atendimentos · azul = alta, vermelhão = queda")
    ax = fig.add_axes([0.06, 0.10, 0.88, 0.68])
    eixo_limpo(ax, grade_y=False)
    a = suave(t / 0.6)
    cores = [PRIMARIA if v >= 0 else VERMELHAO for v in variacao.values]
    ax.bar(range(len(variacao)), variacao.values * a, color=cores, width=0.72)
    ax.axhline(0, color=TINTA_2, linewidth=1)
    for j, (uf, v) in enumerate(variacao.items()):
        ax.text(j, -0.8 if v >= 0 else 0.8, uf, ha="center", va="top" if v >= 0 else "bottom",
                fontsize=11, color=TINTA)
    for j in (0, len(variacao) - 1):
        v = variacao.values[j]
        ax.text(j, v * a + (0.8 if v >= 0 else -0.8), f"{v:+.1f}%".replace(".", ","), ha="center",
                va="bottom" if v >= 0 else "top", fontsize=13, fontweight="bold",
                color=TINTA, alpha=suave((t - 0.6) / 0.2))
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines["bottom"].set_visible(False)
    limite = max(abs(variacao.min()), abs(variacao.max())) * 1.25
    ax.set_ylim(-limite, limite)
    rodape(fig)


def cena_encerramento(fig, t):
    a = suave(t * 2)
    fig.text(0.5, 0.58, "Explore os dados no painel", ha="center", fontsize=40, fontweight="bold",
             color=TINTA, alpha=a)
    fig.text(0.5, 0.49, "Panorama Nacional  ·  Perfil por Estado  ·  Áreas de Atendimento", ha="center",
             fontsize=20, color=TINTA_2, alpha=a)
    fig.text(0.5, 0.36, "Clique em  Get started  →", ha="center", fontsize=24, color="white", alpha=a,
             bbox=dict(boxstyle="round,pad=0.7", facecolor=PRIMARIA, edgecolor="none", alpha=a))
    rodape(fig)


CENAS = [  # (função, segundos)
    (cena_abertura, 4),
    (cena_evolucao, 8),
    (cena_corrida, 12),
    (cena_areas, 6),
    (cena_variacao, 7),
    (cena_encerramento, 3),
]


def main():
    SAIDA.parent.mkdir(exist_ok=True)
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor="white")
    escritor = FFMpegWriter(fps=FPS, codec="libx264",
                            extra_args=["-pix_fmt", "yuv420p", "-crf", "23", "-movflags", "+faststart"])
    with escritor.saving(fig, str(SAIDA), dpi=100):
        for cena, segundos in CENAS:
            quadros = int(segundos * FPS)
            for q in range(quadros):
                fig.clf()
                cena(fig, q / (quadros - 1))
                escritor.grab_frame(facecolor="white")
    plt.close(fig)
    print(f"Vídeo gerado: {SAIDA} ({SAIDA.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
