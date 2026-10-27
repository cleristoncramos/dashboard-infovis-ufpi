"""Mantém o painel publicado no Streamlit Community Cloud acordado.

O Community Cloud hiberna apps sem visitas por algumas horas, e uma requisição
HTTP simples não conta como visita: o app só é carregado por um navegador real.
Este script abre o painel num Chromium headless, clica em "Yes, get this app
back up!" caso ele esteja hibernando e espera o conteúdo aparecer.

Uso:  python scripts/keep_alive.py            (APP_URL opcional no ambiente)
Requer:  pip install playwright && playwright install chromium
"""

import os
import re
import sys
import time

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("APP_URL", "https://dashboard-infovis.streamlit.app/")
TEXTO_ESPERADO = "Atendimentos e recursos aplicados"  # título da página inicial
TEMPO_MAXIMO = 240  # segundos para o app acordar e renderizar


def conteudo_visivel(pagina):
    # O Community Cloud exibe o app dentro de um iframe; procura em todos os frames
    for frame in pagina.frames:
        try:
            if frame.get_by_text(TEXTO_ESPERADO).count() > 0:
                return True
        except Exception:
            continue
    return False


def acordar_se_necessario(pagina):
    botao = pagina.get_by_role("button", name=re.compile("get this app back up", re.I))
    if botao.count() > 0 and botao.first.is_visible():
        print("App hibernando: solicitando que volte ao ar.")
        botao.first.click()
        return True
    return False


def main():
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page()
        print(f"Abrindo {APP_URL}")
        pagina.goto(APP_URL, wait_until="domcontentloaded", timeout=90_000)

        inicio = time.time()
        while time.time() - inicio < TEMPO_MAXIMO:
            if conteudo_visivel(pagina):
                print(f"App no ar ({time.time() - inicio:.0f}s).")
                navegador.close()
                return 0
            try:
                acordar_se_necessario(pagina)
            except PlaywrightTimeout:
                pass
            pagina.wait_for_timeout(5_000)

        pagina.screenshot(path="keep_alive_falha.png", full_page=True)
        print("O app não carregou dentro do tempo limite.", file=sys.stderr)
        navegador.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
