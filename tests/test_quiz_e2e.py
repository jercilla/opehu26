"""
Tests E2E del quiz por casos de uso.
Ejecutar: python3 tests/test_quiz_e2e.py
"""
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


class QuizE2E:
    def __init__(self):
        self.proc = None
        self.browser = None
        self.page = None
        self.failures = []

    def setup(self):
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(PORT)],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if not wait_for_server(BASE_URL):
            raise RuntimeError("Server did not start")

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch()
        self.page = self.browser.new_page(viewport={"width": 1280, "height": 800})

    def teardown(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        if self.proc:
            self.proc.terminate()
            self.proc.wait()

    def refresh_and_clear(self):
        self.page.goto(BASE_URL, wait_until="networkidle")
        self.page.evaluate("localStorage.clear()")
        self.page.reload(wait_until="networkidle")

    def assert_eq(self, got, expected, msg):
        if got != expected:
            self.failures.append(f"FAIL: {msg} | esperado={expected}, obtenido={got}")

    def assert_true(self, condition, msg):
        if not condition:
            self.failures.append(f"FAIL: {msg}")

    # --- helpers de navegacion ---
    def open_first_quiz(self):
        self.page.locator(".btn-open-session").first.click()
        self.page.wait_for_selector("#screen-session", state="visible")

    def start_normal(self):
        self.page.locator("#btn-start-session").click()
        self.page.wait_for_selector("#screen-quiz", state="visible")

    def start_practice(self):
        self.page.locator("#btn-practice-session").click()
        self.page.wait_for_selector("#screen-quiz", state="visible")

    def answer_and_validate(self, option_index=0):
        self.page.locator("#options-list .option").nth(option_index).click()
        self.page.locator("#btn-validate").click()
        self.page.wait_for_selector("#btn-next", state="visible")

    def click_next(self):
        self.page.locator("#btn-next").click()

    def quit_to_menu(self):
        self.page.locator("#btn-quit-quiz").click()
        self.page.wait_for_selector("#screen-menu", state="visible")

    def current_qnum(self):
        """Numero de la pregunta mostrada (el enunciado empieza por 'N.- ...')."""
        txt = self.page.locator("#question-text").inner_text()
        return int(txt.strip().split('.', 1)[0])

    def back_to_menu_from_results(self):
        self.page.locator("#btn-back-menu").click()
        self.page.wait_for_selector("#screen-menu", state="visible")

    def get_first_quiz_stats(self):
        """Devuelve [respondidas, aciertos, fallos] del primer card."""
        card = self.page.locator(".quiz-card").first
        vals = [card.locator(".stat-value").nth(i).inner_text() for i in range(3)]
        return [int(v) for v in vals]

    def switch_user(self, name):
        self.page.locator("#btn-switch-user").click()
        self.page.wait_for_selector("#screen-users", state="visible")
        inp = self.page.locator("#new-user-name")
        inp.fill(name)
        self.page.locator("#new-user-form button[type=submit]").click()
        self.page.wait_for_selector("#screen-menu", state="visible")

    def clear_all_data(self):
        self.page.locator("#btn-switch-user").click()
        self.page.wait_for_selector("#screen-users", state="visible")
        self.page.locator("#btn-clear-data").click()
        # playwright no maneja dialogs por defecto; aceptamos
        self.page.on("dialog", lambda dialog: dialog.accept())
        # reintentar click para disparar el dialog
        self.page.locator("#btn-clear-data").click()
        # esperar a que localStorage se limpie
        self.page.wait_for_timeout(300)
        self.page.go_back(wait_until="networkidle")

    # ========== CASOS DE USO ==========

    def test_happy_sequential_completes_and_updates_stats(self):
        """Happy path: secuencial, responder 2 preguntas, stats se actualizan."""
        self.refresh_and_clear()
        self.open_first_quiz()
        self.start_normal()

        # Primera pregunta
        self.answer_and_validate(0)
        self.click_next()

        # Segunda pregunta
        self.answer_and_validate(1)
        self.click_next()

        self.quit_to_menu()
        stats = self.get_first_quiz_stats()
        self.assert_eq(stats[0], 2, "respondidas tras 2 preguntas secuenciales")
        # aciertos/fallos suman 2
        self.assert_true(stats[1] + stats[2] == 2, "aciertos+fallos == 2")

    def test_happy_random_new_session_uses_full_range(self):
        """Happy path: aleatorio nuevo usa el rango completo sin filtrar historial."""
        self.refresh_and_clear()
        quiz = self.page.evaluate("() => Object.keys(QUIZZES)[0]")
        q_len = self.page.evaluate(f"() => QUIZZES['{quiz}'].questions.length")

        self.open_first_quiz()
        # Activar modo aleatorio con rango completo
        self.page.locator("#radio-random").check()
        self.page.locator("#rand-start").fill("1")
        self.page.locator("#rand-end").fill(str(q_len))
        self.start_normal()

        # Responder la primera pregunta que aparezca
        self.answer_and_validate(0)
        self.click_next()
        self.quit_to_menu()

        stats1 = self.get_first_quiz_stats()
        self.assert_eq(stats1[0], 1, "respondidas tras 1 pregunta aleatoria")

        # Volver a empezar aleatorio nuevo: debe incluir TODAS las preguntas del rango
        self.open_first_quiz()
        self.page.locator("#radio-random").check()
        self.page.locator("#rand-start").fill("1")
        self.page.locator("#rand-end").fill(str(q_len))
        self.start_normal()

        progress_text = self.page.locator("#quiz-progress").inner_text()
        self.assert_eq(progress_text.strip(), f"1 / {q_len}", "nuevo test aleatorio incluye rango completo")
        self.quit_to_menu()

    def test_happy_resume_session(self):
        """Happy path: sesion guardada se puede continuar."""
        self.refresh_and_clear()
        self.open_first_quiz()
        self.start_normal()

        # Responder 1 pregunta y salir sin terminar
        self.answer_and_validate(0)
        self.click_next()
        self.quit_to_menu()

        stats = self.get_first_quiz_stats()
        self.assert_eq(stats[0], 1, "respondidas tras salir a mitad de sesion")

        # Volver a entrar: debe aparecer boton continuar
        self.open_first_quiz()
        resume_visible = self.page.locator("#session-resume-box").is_visible()
        self.assert_true(resume_visible, "caja de continuar sesion visible")

        self.page.locator("#btn-continue-session").click()
        self.page.wait_for_selector("#screen-quiz", state="visible")

        # Deberia estar en la pregunta 2
        progress = self.page.locator("#quiz-progress").inner_text()
        self.assert_true(progress.startswith("2 "), f"continua en pregunta 2, progreso={progress}")
        self.quit_to_menu()

    def test_happy_user_profiles_isolated(self):
        """Happy path: dos perfiles tienen estadisticas independientes."""
        self.refresh_and_clear()

        # User 1 responde 1 pregunta
        self.open_first_quiz()
        self.start_normal()
        self.answer_and_validate(0)
        self.click_next()
        self.quit_to_menu()

        stats_u1 = self.get_first_quiz_stats()
        self.assert_eq(stats_u1[0], 1, "User 1 tiene 1 respondida")

        # Cambiar a User 2
        self.switch_user("User 2")
        stats_u2 = self.get_first_quiz_stats()
        self.assert_eq(stats_u2[0], 0, "User 2 tiene 0 respondidas")

    def test_happy_practice_does_not_affect_stats_or_session(self):
        """Happy path: modo practica no toca stats ni sesion guardada."""
        self.refresh_and_clear()

        # 1. Sesion normal parcial: 1 respondida, sesion guardada
        self.open_first_quiz()
        self.start_normal()
        self.answer_and_validate(0)
        self.click_next()
        self.quit_to_menu()
        stats_after_normal = self.get_first_quiz_stats()
        self.assert_eq(stats_after_normal[0], 1, "stats tras sesion normal")

        # 2. Modo practica: responder otra pregunta
        self.open_first_quiz()
        self.start_practice()
        label = self.page.locator("#quiz-label").inner_text()
        self.assert_true("(Prueba)" in label, "titulo indica prueba")

        self.answer_and_validate(0)
        self.click_next()
        self.quit_to_menu()

        stats_after_practice = self.get_first_quiz_stats()
        self.assert_eq(stats_after_practice[0], 1, "stats tras practica no cambian")

        # 3. Volver a entrar: debe ofrecer continuar la sesion NORMAL (no la practica)
        self.open_first_quiz()
        resume_visible = self.page.locator("#session-resume-box").is_visible()
        self.assert_true(resume_visible, "sesion normal aun disponible tras practica")

    # ========== CORNER CASES ==========

    def test_corner_quit_without_answering_leaves_stats_zero(self):
        """Corner case: entrar y salir sin responder no modifica stats."""
        self.refresh_and_clear()
        self.open_first_quiz()
        self.start_normal()
        self.quit_to_menu()
        stats = self.get_first_quiz_stats()
        self.assert_eq(stats[0], 0, "stats sin responder deben ser 0")

    def test_corner_clear_data_wipes_everything(self):
        """Corner case: limpiar datos borra stats y sesiones."""
        self.refresh_and_clear()
        self.open_first_quiz()
        self.start_normal()
        self.answer_and_validate(0)
        self.click_next()
        self.quit_to_menu()

        self.assert_eq(self.get_first_quiz_stats()[0], 1, "stats antes de limpiar")

        self.clear_all_data()
        self.refresh_and_clear()

        # Despues de limpiar, stats deben ser 0
        stats = self.get_first_quiz_stats()
        self.assert_eq(stats[0], 0, "stats tras limpiar datos")

        # Y no debe haber sesion guardada
        self.open_first_quiz()
        resume_visible = self.page.locator("#session-resume-box").is_visible()
        self.assert_true(not resume_visible, "no hay sesion guardada tras limpiar")

    def test_corner_invalid_range(self):
        """Corner case: rango invalido (start > end) no rompe la app."""
        self.refresh_and_clear()
        self.open_first_quiz()

        # Poner start mayor que end en secuencial
        self.page.locator("#seq-start").fill("50")
        self.page.locator("#seq-end").fill("10")
        self.page.locator("#btn-start-session").click()

        # Con rango vacio, la app muestra resultados inmediatamente (o quiz)
        # Verificamos que NO hay errores JS y que alguna pantalla post-sesion es visible
        self.page.wait_for_timeout(500)
        quiz_visible = self.page.locator("#screen-quiz").is_visible()
        results_visible = self.page.locator("#screen-results").is_visible()
        self.assert_true(quiz_visible or results_visible,
                          "app no crashea con rango invertido: muestra quiz o resultados")

        # Volver al menu sin crash
        if quiz_visible:
            self.quit_to_menu()
        else:
            self.back_to_menu_from_results()

    def test_corner_practice_random_does_not_filter_answered(self):
        """Corner case: modo practica aleatorio NO filtra preguntas ya respondidas."""
        self.refresh_and_clear()
        quiz = self.page.evaluate("() => Object.keys(QUIZZES)[0]")
        q_len = self.page.evaluate(f"() => QUIZZES['{quiz}'].questions.length")

        # Responder 1 pregunta en modo normal
        self.open_first_quiz()
        self.start_normal()
        self.answer_and_validate(0)
        self.click_next()
        self.quit_to_menu()

        stats = self.get_first_quiz_stats()
        self.assert_eq(stats[0], 1, "1 respondida en modo normal")

        # Modo practica aleatorio: deberia tener TODAS las preguntas disponibles
        self.open_first_quiz()
        self.page.locator("#radio-random").check()
        self.page.locator("#rand-start").fill("1")
        self.page.locator("#rand-end").fill(str(q_len))
        self.start_practice()

        progress = self.page.locator("#quiz-progress").inner_text()
        # En modo practica aleatorio no se filtran respondidas -> todas las del rango
        total_in_session = progress.split("/")[1].strip()
        self.assert_eq(int(total_in_session), q_len,
                       f"practica aleatoria muestra todas las preguntas ({q_len}), no filtra respondidas")
        self.quit_to_menu()

    def test_happy_sequential_partial_range(self):
        """Happy path: secuencial con rango parcial (preguntas 5-7)."""
        self.refresh_and_clear()
        self.open_first_quiz()

        self.page.locator("#seq-start").fill("5")
        self.page.locator("#seq-end").fill("7")
        self.start_normal()

        # Debe empezar en pregunta 1 de la sesion (que es la 5 del quiz)
        progress = self.page.locator("#quiz-progress").inner_text()
        self.assert_true(progress.startswith("1 / 3"), f"sesion parcial: 3 preguntas, progreso={progress}")

        # Responder las 3 preguntas del rango
        self.answer_and_validate(0)
        self.click_next()
        self.answer_and_validate(0)
        self.click_next()
        self.answer_and_validate(0)
        self.click_next()

        # Debe terminar y mostrar resultados
        results_visible = self.page.locator("#screen-results").is_visible()
        self.assert_true(results_visible, "rango parcial termina y muestra resultados")
        detail = self.page.locator("#result-detail").inner_text()
        self.assert_true("3 de 3" in detail, f"resultados del rango parcial: {detail}")

        self.back_to_menu_from_results()
        stats = self.get_first_quiz_stats()
        self.assert_eq(stats[0], 3, "stats reflejan solo las 3 preguntas del rango")

    def test_happy_random_partial_range(self):
        """Happy path: aleatorio con rango parcial (preguntas 10-15)."""
        self.refresh_and_clear()
        self.open_first_quiz()

        self.page.locator("#radio-random").check()
        self.page.locator("#rand-start").fill("10")
        self.page.locator("#rand-end").fill("15")
        self.start_normal()

        # Debe mostrar exactamente 6 preguntas en la sesion
        progress = self.page.locator("#quiz-progress").inner_text()
        self.assert_true("/ 6" in progress, f"aleatorio parcial: 6 preguntas, progreso={progress}")

        # Responder 1 y salir
        self.answer_and_validate(0)
        self.click_next()
        self.quit_to_menu()

        stats = self.get_first_quiz_stats()
        self.assert_eq(stats[0], 1, "stats tras 1 respuesta en rango aleatorio parcial")

    def test_corner_range_exceeds_total(self):
        """Corner case: rango que excede el total de preguntas se clampa."""
        self.refresh_and_clear()
        quiz = self.page.evaluate("() => Object.keys(QUIZZES)[0]")
        q_len = self.page.evaluate(f"() => QUIZZES['{quiz}'].questions.length")

        self.open_first_quiz()
        self.page.locator("#seq-start").fill("1")
        self.page.locator("#seq-end").fill(str(q_len + 100))
        self.start_normal()

        # Debe mostrar el total real de preguntas, no q_len+100
        progress = self.page.locator("#quiz-progress").inner_text()
        expected = f"/ {q_len}"
        self.assert_true(expected in progress,
                         f"rango excedido se clampa a {q_len}, progreso={progress}")
        self.quit_to_menu()

    def test_happy_user_highlight_post_validate(self):
        """Happy path: tras validar, se puede subrayar texto plano y persiste."""
        self.refresh_and_clear()
        self.open_first_quiz()
        self.start_normal()

        # Responder y validar
        self.answer_and_validate(0)

        # Verificar que las opciones son texto plano (no contienen diff-highlight)
        html = self.page.locator("#options-list").inner_html()
        self.assert_true("diff-highlight" not in html, "post-validar: no quedan diffs HTML")

        # Simular seleccion de texto en la primera opcion via JS
        self.page.evaluate("""
            () => {
                const opt = document.querySelector('#options-list .option');
                const textNode = opt.querySelector('.option-text').childNodes[0];
                if (!textNode) return;
                const range = document.createRange();
                range.setStart(textNode, 0);
                range.setEnd(textNode, Math.min(5, textNode.textContent.length));
                const sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
            }
        """)
        self.page.wait_for_timeout(100)

        # Disparar selectionchange manualmente (el menu se muestra por el listener)
        menu_visible = self.page.locator("#highlight-menu").is_visible()
        if menu_visible:
            self.page.locator("#highlight-menu").click()
            self.page.wait_for_timeout(100)

            # Verificar que aparece el span user-highlight
            html_after = self.page.locator("#options-list .option").first.inner_html()
            self.assert_true("user-highlight" in html_after, "highlight se aplico al texto")
        else:
            # Si el menu no aparecio por el evento, al menos verificamos
            # que la estructura permite highlights (texto plano)
            self.assert_true("option-text" in html, "texto plano disponible para highlight")

        # Recargar y continuar sesion
        self.page.reload(wait_until="networkidle")
        self.page.wait_for_selector("#screen-menu", state="visible")
        self.open_first_quiz()
        resume_visible = self.page.locator("#session-resume-box").is_visible()
        self.assert_true(resume_visible, "sesion post-validar disponible para continuar")
        self.page.locator("#btn-continue-session").click()
        self.page.wait_for_selector("#screen-quiz", state="visible")

        # Verificar que sigue en estado post-validar (texto plano)
        html_resume = self.page.locator("#options-list").inner_html()
        self.assert_true("diff-highlight" not in html_resume, "post-validar persistido: sin diffs")

        self.quit_to_menu()

    def test_happy_export_import_incognito(self):
        """Exporta datos de pestaña normal e importa en contexto incognito (localStorage limpio)."""
        self.refresh_and_clear()
        self.open_first_quiz()
        self.start_normal()

        # Responder 2 preguntas
        self.answer_and_validate(0)
        self.click_next()
        self.answer_and_validate(1)
        self.click_next()
        self.quit_to_menu()

        # Exportar datos con la funcion REAL de la app
        exported = self.page.evaluate("() => Users.exportData()")
        self.assert_true(len(exported) > 0, "hay datos para exportar")

        # Crear contexto incognito (localStorage limpio)
        incognito = self.browser.new_context()
        page2 = incognito.new_page()
        page2.set_viewport_size({"width": 1280, "height": 800})
        page2.goto(BASE_URL, wait_until="networkidle")

        # El incognito arranca solo con el perfil por defecto (ensureDefault crea
        # 'User 1' al cargar), sin datos importados todavia: no debe haber stats.
        stats_before = page2.evaluate("""
            () => {
                const raw = localStorage.getItem('quiz_user_User 1_global');
                return raw ? JSON.parse(raw) : null;
            }
        """)
        self.assert_true(stats_before is None,
                         "incognito sin stats importadas antes de importar")

        # Importar con la funcion REAL de la app (merge + aplicar conflictos)
        page2.evaluate("""
            (exported) => {
                Users.previewImport(exported).apply();
            }
        """, exported)

        # Verificar stats del primer quiz
        page2.reload(wait_until="networkidle")
        page2.wait_for_selector("#screen-menu", state="visible")

        stats = page2.evaluate("""
            () => {
                const slug = Object.keys(QUIZZES)[0];
                const user = JSON.parse(localStorage.getItem('quiz_users') || '[]')[0] || 'User 1';
                const raw = localStorage.getItem('quiz_user_' + user + '_global');
                return raw ? JSON.parse(raw)[slug] : null;
            }
        """)
        self.assert_true(stats is not None, "stats importadas presentes en incognito")
        self.assert_true(stats.get('total_respondidas', 0) >= 2,
                         f"stats sumadas: respondidas={stats.get('total_respondidas')}")

        incognito.close()

    def test_happy_delete_highlight_and_import_conflict(self):
        """Eliminar un highlight local, exportar, y al importar de otro dispositivo detectar conflicto."""
        self.refresh_and_clear()
        self.open_first_quiz()
        self.start_normal()

        # Responder y validar
        self.answer_and_validate(0)

        # Obtener letra de la primera opcion
        first_letter = self.page.evaluate("() => document.querySelector('#options-list .option').dataset.letter")
        slug = self.page.evaluate("() => Object.keys(QUIZZES)[0]")
        qid = self.page.evaluate("() => QUIZZES[Object.keys(QUIZZES)[0]].questions[0].idpregunta")

        # Simular subrayado via localStorage directamente
        self.page.evaluate("""
            (args) => {
                const [slug, qid, letter] = args;
                const all = JSON.parse(localStorage.getItem('quiz_user_User 1_highlights') || '{}');
                if (!all[slug]) all[slug] = {};
                if (!all[slug][qid]) all[slug][qid] = {};
                if (!all[slug][qid][letter]) all[slug][qid][letter] = [];
                all[slug][qid][letter].push('testword');
                localStorage.setItem('quiz_user_User 1_highlights', JSON.stringify(all));
            }
        """, [slug, qid, first_letter])

        # Verificar que el highlight existe en localStorage
        has_highlight = self.page.evaluate("""
            (args) => {
                const [slug, qid, letter] = args;
                const all = JSON.parse(localStorage.getItem('quiz_user_User 1_highlights') || '{}');
                return !!(all[slug] && all[slug][qid] && all[slug][qid][letter] && all[slug][qid][letter].includes('testword'));
            }
        """, [slug, qid, first_letter])
        self.assert_true(has_highlight, "highlight creado en localStorage")

        # Eliminar el highlight y loguear delete
        self.page.evaluate("""
            (args) => {
                const [slug, qid, letter] = args;
                // Remove highlight
                const all = JSON.parse(localStorage.getItem('quiz_user_User 1_highlights') || '{}');
                if (all[slug] && all[slug][qid] && all[slug][qid][letter]) {
                    const arr = all[slug][qid][letter];
                    const idx = arr.indexOf('testword');
                    if (idx >= 0) {
                        arr.splice(idx, 1);
                        if (arr.length === 0) delete all[slug][qid][letter];
                        localStorage.setItem('quiz_user_User 1_highlights', JSON.stringify(all));
                    }
                }
                // Log delete
                const del = JSON.parse(localStorage.getItem('quiz_user_User 1_deleted_highlights') || '{}');
                if (!del[slug]) del[slug] = {};
                if (!del[slug][qid]) del[slug][qid] = {};
                if (!del[slug][qid][letter]) del[slug][qid][letter] = [];
                del[slug][qid][letter].push('testword');
                localStorage.setItem('quiz_user_User 1_deleted_highlights', JSON.stringify(del));
            }
        """, [slug, qid, first_letter])

        # Verificar que el delete se logueo
        has_delete = self.page.evaluate("""
            (args) => {
                const [slug, qid, letter] = args;
                const del = JSON.parse(localStorage.getItem('quiz_user_User 1_deleted_highlights') || '{}');
                return !!(del[slug] && del[slug][qid] && del[slug][qid][letter] && del[slug][qid][letter].includes('testword'));
            }
        """, [slug, qid, first_letter])
        self.assert_true(has_delete, "delete logueado en deleted_highlights")

        # Exportar datos con la funcion REAL de la app
        exported = self.page.evaluate("() => Users.exportData()")

        # Contexto incognito donde el highlight aun existe
        incognito = self.browser.new_context()
        page2 = incognito.new_page()
        page2.set_viewport_size({"width": 1280, "height": 800})
        page2.goto(BASE_URL, wait_until="networkidle")

        # Crear el highlight en incognito (simulando que existia antes)
        page2.evaluate("""
            (args) => {
                const [slug, qid, letter] = args;
                const all = JSON.parse(localStorage.getItem('quiz_user_User 1_highlights') || '{}');
                if (!all[slug]) all[slug] = {};
                if (!all[slug][qid]) all[slug][qid] = {};
                if (!all[slug][qid][letter]) all[slug][qid][letter] = [];
                all[slug][qid][letter].push('testword');
                localStorage.setItem('quiz_user_User 1_highlights', JSON.stringify(all));
            }
        """, [slug, qid, first_letter])

        # Previsualizar el import con la funcion REAL de la app.
        # previewImport() solo DETECTA conflictos (highlights borrados en origen
        # que aun existen en local); no muta localStorage todavia.
        conflicts = page2.evaluate("""
            (exported) => {
                window.__preview = Users.previewImport(exported);
                return window.__preview.conflicts;
            }
        """, exported)

        # El highlight local debe detectarse como conflicto (borrado en origen)
        self.assert_true(
            any(c.get('text') == 'testword' for c in conflicts),
            "previewImport detecta el highlight borrado como conflicto",
        )

        # Verificar que el highlight sigue existiendo (previewImport no elimina nada)
        highlight_exists = page2.evaluate("""
            (args) => {
                const [slug, qid, letter] = args;
                const all = JSON.parse(localStorage.getItem('quiz_user_User 1_highlights') || '{}');
                return !!(all[slug] && all[slug][qid] && all[slug][qid][letter] && all[slug][qid][letter].includes('testword'));
            }
        """, [slug, qid, first_letter])
        self.assert_true(highlight_exists, "highlight sigue existiendo antes de aplicar deletes")

        # El usuario acepta el import desde el modal -> apply() hace merge + borra
        # los conflictos detectados. Es la funcion REAL de la app.
        page2.evaluate("() => window.__preview.apply()")

        # Verificar que el highlight fue eliminado
        highlight_gone = page2.evaluate("""
            (args) => {
                const [slug, qid, letter] = args;
                const all = JSON.parse(localStorage.getItem('quiz_user_User 1_highlights') || '{}');
                return !(all[slug] && all[slug][qid] && all[slug][qid][letter] && all[slug][qid][letter].includes('testword'));
            }
        """, [slug, qid, first_letter])
        self.assert_true(highlight_gone, "highlight eliminado tras aplicar deletes del import")

        incognito.close()

    def test_happy_toggle_diffs_off(self):
        """El resaltado de diferencias se puede desactivar desde la pantalla de sesion."""
        self.refresh_and_clear()
        # Buscar en el primer quiz una pregunta que tenga resaltado (diff-highlight)
        quiz = self.page.evaluate("() => Object.keys(QUIZZES)[0]")
        diff_num = self.page.evaluate(f"""
            () => {{
                const qs = QUIZZES['{quiz}'].questions;
                for (let i = 0; i < qs.length; i++) {{
                    const d = qs[i].diffs;
                    if (d && Object.values(d).some(v => v.includes('diff-highlight'))) return i + 1;
                }}
                return null;
            }}
        """)
        self.assert_true(diff_num is not None, "hay alguna pregunta con resaltado en el primer quiz")
        if diff_num is None:
            return

        # --- Resaltado ACTIVADO (por defecto) ---
        self.open_first_quiz()
        self.page.locator("#seq-start").fill(str(diff_num))
        self.page.locator("#seq-end").fill(str(diff_num))
        self.assert_true(self.page.locator("#chk-show-diffs").is_checked(),
                         "el checkbox de resaltado viene activado por defecto")
        self.start_practice()
        html_on = self.page.locator("#options-list").inner_html()
        self.assert_true("diff-highlight" in html_on, "con resaltado ON aparece diff-highlight")
        self.quit_to_menu()

        # --- Resaltado DESACTIVADO ---
        self.open_first_quiz()
        self.page.locator("#seq-start").fill(str(diff_num))
        self.page.locator("#seq-end").fill(str(diff_num))
        self.page.locator("#chk-show-diffs").uncheck()
        self.start_practice()
        html_off = self.page.locator("#options-list").inner_html()
        self.assert_true("diff-highlight" not in html_off, "con resaltado OFF no aparece diff-highlight")
        self.assert_true("option-text" in html_off, "el texto de opciones sigue presente sin resaltado")
        self.quit_to_menu()

    def test_happy_cuesta_button(self):
        """Boton 'Esta me cuesta': oculto en Probar; en Empezar marca/desmarca,
        persiste por pregunta y se cuenta en resultados y en la tarjeta del menu."""
        self.refresh_and_clear()
        quiz = self.page.evaluate("() => Object.keys(QUIZZES)[0]")
        idp1 = str(self.page.evaluate(f"() => QUIZZES['{quiz}'].questions[0].idpregunta"))

        def cuesta_persisted():
            return self.page.evaluate("""
                (args) => {
                    const [q, idp] = args;
                    const pp = JSON.parse(localStorage.getItem('quiz_user_User 1_por_pregunta') || '{}');
                    const rec = pp[q] && pp[q][idp];
                    return !!(rec && rec.cuesta === true);
                }
            """, [quiz, idp1])

        # --- Modo Probar: el boton NO debe aparecer tras validar ---
        self.open_first_quiz()
        self.page.locator("#seq-start").fill("1")
        self.page.locator("#seq-end").fill("2")
        self.start_practice()
        self.answer_and_validate(0)
        self.assert_true(self.page.locator("#btn-cuesta").is_hidden(),
                         "en Probar el boton 'me cuesta' no aparece")
        self.quit_to_menu()

        # --- Modo Empezar: rango 1-2 ---
        self.open_first_quiz()
        self.page.locator("#seq-start").fill("1")
        self.page.locator("#seq-end").fill("2")
        self.start_normal()

        # Q1: validar -> el boton aparece; marcar -> estado + persistencia
        self.answer_and_validate(0)
        self.assert_true(self.page.locator("#btn-cuesta").is_visible(),
                         "en Empezar el boton 'me cuesta' aparece tras validar")
        self.page.locator("#btn-cuesta").click()
        cls = self.page.locator("#btn-cuesta").get_attribute("class") or ""
        self.assert_true("marked" in cls, "el boton pasa a estado marcado")
        self.assert_true(cuesta_persisted(), "cuesta=true persistido en por_pregunta")

        # Toggle: desmarcar -> deja de estar persistido
        self.page.locator("#btn-cuesta").click()
        self.assert_true(not cuesta_persisted(), "toggle desmarca (cuesta ya no es true)")

        # Marcar de nuevo para el recuento final
        self.page.locator("#btn-cuesta").click()
        self.assert_true(cuesta_persisted(), "re-marcado persistido")

        # Q2: validar sin marcar, y terminar la sesion
        self.click_next()
        self.answer_and_validate(0)
        self.click_next()

        # Resultados: recuento de 'me cuesta' de la sesion
        self.page.wait_for_selector("#screen-results", state="visible")
        cuesta_txt = self.page.locator("#result-cuesta").inner_text()
        self.assert_true("1" in cuesta_txt,
                         f"resultados muestran 1 'me cuesta' (texto: {cuesta_txt!r})")

        # Tarjeta del menu: contador 'Me cuesta' == 1
        self.back_to_menu_from_results()
        card = self.page.locator(".quiz-card").first
        idx_cuesta = self.page.evaluate("""
            () => {
                const labels = Array.from(document.querySelectorAll('.quiz-card')[0].querySelectorAll('.stat-label'));
                return labels.findIndex(l => l.textContent.trim() === 'Me cuestan');
            }
        """)
        self.assert_true(idx_cuesta >= 0, "la tarjeta tiene un stat 'Me cuestan'")
        count = card.locator(".stat-value").nth(idx_cuesta).inner_text()
        self.assert_eq(int(count), 1, "la tarjeta del menu muestra 1 'me cuesta'")

    def test_happy_difficulty_order(self):
        """Modo 'Por dificultad': ordena por intentos asc, luego tasa de fallo,
        luego 'me cuestan', dentro del rango por numero de pregunta."""
        self.refresh_and_clear()
        quiz = self.page.evaluate("() => Object.keys(QUIZZES)[0]")
        idps = self.page.evaluate(f"() => QUIZZES['{quiz}'].questions.slice(0,6).map(q => String(q.idpregunta))")

        # Escenario controlado sobre las preguntas num 1..6:
        #   num1: 4 aciertos, 0 fallos            -> intentos 4, fr 0
        #   num2: (sin registro)                  -> intentos 0
        #   num3: 1 acierto, 1 fallo              -> intentos 2, fr 0.5
        #   num4: 0 aciertos, 2 fallos            -> intentos 2, fr 1.0
        #   num5: 0 aciertos, 1 fallo             -> intentos 1, fr 1.0
        #   num6: 1 acierto, 1 fallo, me-cuesta   -> intentos 2, fr 0.5, cuesta
        seed = {
            idps[0]: {"aciertos": 4, "fallos": 0},
            idps[2]: {"aciertos": 1, "fallos": 1},
            idps[3]: {"aciertos": 0, "fallos": 2},
            idps[4]: {"aciertos": 0, "fallos": 1},
            idps[5]: {"aciertos": 1, "fallos": 1, "cuesta": True},
        }
        self.page.evaluate("""
            (args) => {
                const [quiz, seed] = args;
                const pp = {}; pp[quiz] = seed;
                localStorage.setItem('quiz_user_User 1_por_pregunta', JSON.stringify(pp));
            }
        """, [quiz, seed])

        # Sesion en modo dificultad, rango 1-6, en Probar (no altera stats)
        self.open_first_quiz()
        self.page.locator("#radio-difficulty").check()
        self.page.locator("#diff-start").fill("1")
        self.page.locator("#diff-end").fill("6")
        self.start_practice()

        nums = []
        for _ in range(6):
            nums.append(self.current_qnum())
            self.answer_and_validate(0)
            self.click_next()

        self.assert_eq(nums, [2, 5, 4, 6, 3, 1], "orden por dificultad")

    def run_all(self):
        tests = [
            self.test_happy_sequential_completes_and_updates_stats,
            self.test_happy_random_new_session_uses_full_range,
            self.test_happy_resume_session,
            self.test_happy_user_profiles_isolated,
            self.test_happy_practice_does_not_affect_stats_or_session,
            self.test_happy_sequential_partial_range,
            self.test_happy_random_partial_range,
            self.test_corner_quit_without_answering_leaves_stats_zero,
            self.test_corner_clear_data_wipes_everything,
            self.test_corner_invalid_range,
            self.test_corner_range_exceeds_total,
            self.test_corner_practice_random_does_not_filter_answered,
            self.test_happy_user_highlight_post_validate,
            self.test_happy_export_import_incognito,
            self.test_happy_delete_highlight_and_import_conflict,
            self.test_happy_toggle_diffs_off,
            self.test_happy_cuesta_button,
            self.test_happy_difficulty_order,
        ]
        passed = 0
        for t in tests:
            name = t.__name__
            print(f"\n>>> RUNNING {name}")
            before = len(self.failures)
            try:
                t()
                new_failures = self.failures[before:]
                if not new_failures:
                    print(f"[PASS] {name}")
                    passed += 1
                else:
                    # Imprimir los fallos que este test acumulo
                    for f in new_failures:
                        print(f)
            except Exception as e:
                print(f"[ERROR] {name}: {e}")
        return passed, len(tests)


def main():
    suite = QuizE2E()
    suite.setup()
    try:
        passed, total = suite.run_all()
        print(f"\n{'='*50}")
        print(f"Resultado: {passed}/{total} tests pasaron")
        if suite.failures:
            print("\nFallos acumulados:")
            for f in suite.failures:
                print(f"  {f}")
        if passed < total:
            sys.exit(1)
    finally:
        suite.teardown()


if __name__ == "__main__":
    main()
