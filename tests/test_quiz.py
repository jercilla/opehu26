import subprocess
import sys
import time
import urllib.request
from playwright.sync_api import sync_playwright

REPO_ROOT = "/home/jercilla/OPs/2026/ehu"
PORT = 8765
BASE_URL = f"http://localhost:{PORT}/quiz/index.html"


def wait_for_server(url, timeout=10):
    for _ in range(timeout * 10):
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.1)
    return False


def run_test():
    # Start static file server from repo root
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT)],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        if not wait_for_server(BASE_URL):
            raise RuntimeError("Server did not start")

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 800})

            # --- Test 1: modo Empezar debe actualizar estadísticas ---
            page.goto(BASE_URL, wait_until="networkidle")
            page.evaluate("localStorage.clear()")
            page.reload(wait_until="networkidle")

            # Expandir primer card y entrar (por defecto todos expandidos)
            page.locator(".btn-open-session").first.click()
            page.wait_for_selector("#screen-session", state="visible")

            page.locator("#btn-start-session").click()
            page.wait_for_selector("#screen-quiz", state="visible")

            # Responder primera opción y validar
            page.locator("#options-list .option").first.click()
            page.locator("#btn-validate").click()
            page.wait_for_selector("#btn-next", state="visible")

            # Volver al menú
            page.locator("#btn-quit-quiz").click()
            page.wait_for_selector("#screen-menu", state="visible")

            # Leer estadísticas del primer quiz
            respondidas = page.locator(".quiz-card").first.locator(".stat-value").nth(0).inner_text()
            assert respondidas == "1", f"Esperaba 1 respondida tras 'Empezar', pero fue {respondidas}"
            print("[PASS] Modo 'Empezar' actualiza estadísticas correctamente")

            # --- Test 2: modo Probar NO debe actualizar estadísticas ---
            page.evaluate("localStorage.clear()")
            page.reload(wait_until="networkidle")

            page.locator(".btn-open-session").first.click()
            page.wait_for_selector("#screen-session", state="visible")

            page.locator("#btn-practice-session").click()
            page.wait_for_selector("#screen-quiz", state="visible")

            # Verificar que el título muestra (Prueba)
            label = page.locator("#quiz-label").inner_text()
            assert "(Prueba)" in label, f"Esperaba indicador de prueba en el título, pero fue: {label}"

            # Responder primera opción y validar
            page.locator("#options-list .option").first.click()
            page.locator("#btn-validate").click()
            page.wait_for_selector("#btn-next", state="visible")

            # Volver al menú
            page.locator("#btn-quit-quiz").click()
            page.wait_for_selector("#screen-menu", state="visible")

            # Leer estadísticas del primer quiz
            respondidas = page.locator(".quiz-card").first.locator(".stat-value").nth(0).inner_text()
            assert respondidas == "0", f"Esperaba 0 respondidas tras 'Probar', pero fue {respondidas}"
            print("[PASS] Modo 'Probar' NO actualiza estadísticas")

            browser.close()
            print("\nTodos los tests pasaron.")
    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    run_test()
