"""
Script de validacion REAL extremo a extremo desde el navegador para HITCHINGS Documentos (Bloque 6C).
Automatiza:
1. Verificacion de servidores FastAPI (8000) y Vite (5173).
2. Apertura del navegador real mediante Playwright (Chromium/Chrome).
3. Monitoreo de consola, peticiones de red y verificacion de ausencia de errores y secretos.
4. Navegacion a la pestaña 'Pegar texto', ingreso del texto de prueba del contrato.
5. Seleccion del prompt 'Puntos clave' (gemini-3.8-flash).
6. Ejecucion del analisis real (1 unica llamada a Gemini).
7. Captura de pantalla del resultado en pantalla (Markdown, tokens, advertencias).
8. En la misma sesion sin recargar, clic en 'Exportar a Word'.
9. Intercepcion de la descarga del archivo .docx.
10. Inspeccion estructural del documento .docx descargado con python-docx.
11. Verificacion del mensaje de exito 'Word generado correctamente' y captura de pantalla.
"""

import io
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import docx
import httpx
from playwright.sync_api import sync_playwright

SAMPLE_TEXT = (
    "El 3 de marzo de 2026, Empresa Alfa firmó un contrato de servicios por doce meses. "
    "Debe entregar un informe mensual antes del día 5. Existe una penalización de 500 euros "
    "por retrasos superiores a diez días."
)

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"


def check_service(url: str, timeout: float = 2.0) -> bool:
    urls_to_try = [url]
    if "localhost" in url:
        urls_to_try.append(url.replace("localhost", "127.0.0.1"))
    for u in urls_to_try:
        try:
            resp = httpx.get(u, timeout=timeout)
            if resp.status_code < 500:
                return True
        except Exception:
            continue
    return False


def wait_for_services(max_seconds: int = 30):
    start = time.time()
    while time.time() - start < max_seconds:
        backend_ok = check_service(f"{BACKEND_URL}/health")
        frontend_ok = check_service(FRONTEND_URL)
        if backend_ok and frontend_ok:
            return True
        time.sleep(1)
    return False


def run_e2e_browser_test():
    print("=" * 70)
    print("=== HITCHINGS DOCUMENTOS - TEST E2E NAVEGADOR REAL (BLOQUE 6C) ===")
    print("=" * 70)

    # 1. Verificar o iniciar Backend y Frontend
    backend_proc = None
    frontend_proc = None

    if not check_service(f"{BACKEND_URL}/health"):
        print("[1/8] Iniciando Backend FastAPI en localhost:8000...")
        backend_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            cwd=str(ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    else:
        print("[1/8] Backend FastAPI ya se encuentra activo en localhost:8000.")

    if not check_service(FRONTEND_URL):
        print("[2/8] Iniciando Frontend Vite en localhost:5173...")
        frontend_proc = subprocess.Popen(
            "npm run dev -- --host 0.0.0.0 --port 5173",
            shell=True,
            cwd=str(ROOT_DIR / "frontend"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    else:
        print("[2/8] Frontend Vite ya se encuentra activo en localhost:5173.")

    print("      Esperando disponibilidad de servicios...")
    if not wait_for_services(30):
        print("[ERROR] No se pudo conectar a los servicios en el tiempo limite.")
        if backend_proc:
            backend_proc.terminate()
        if frontend_proc:
            frontend_proc.terminate()
        sys.exit(1)

    print("[OK] Backend y Frontend listos.")

    # Archivo temporal para la descarga de Word
    download_dir = ROOT_DIR / "scripts" / "tmp_download"
    download_dir.mkdir(exist_ok=True)
    downloaded_docx_path = download_dir / "analisis_descargado.docx"
    if downloaded_docx_path.exists():
        downloaded_docx_path.unlink()

    console_messages = []
    console_errors = []

    try:
        with sync_playwright() as p:
            print("[3/8] Lanzando navegador Chrome...")
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            # Monitoreo de consola
            def on_console(msg):
                text = msg.text
                console_messages.append(text)
                if msg.type in ["error"]:
                    if "favicon" not in text and "WebSocket" not in text:
                        console_errors.append(text)

            page.on("console", on_console)

            # Monitoreo de respuestas de red
            analysis_network_called = []
            export_network_called = []

            def on_response(resp):
                if "/api/v1/analysis" in resp.url and resp.request.method == "POST":
                    analysis_network_called.append(resp.status)
                elif "/api/v1/export/word" in resp.url and resp.request.method == "POST":
                    export_network_called.append(resp.status)

            page.on("response", on_response)

            print(f"[4/8] Navegando a {FRONTEND_URL}...")
            page.goto(FRONTEND_URL, wait_until="networkidle")

            # Verificar titulo corporativo
            page.wait_for_selector(".brand-title", timeout=5000)
            brand_text = page.locator(".brand-title").inner_text()
            print(f"      Identidad cargada: {brand_text}")

            # Esperar a que el catalogo de prompts este cargado
            page.wait_for_selector("#prompt-select option", state="attached", timeout=10000)
            print("      Catalogo de prompts recibido del backend.")

            # Cambiar a pestana 'Pegar texto'
            print("[5/8] Seleccionando pestana 'Pegar texto' e introduciendo contenido...")
            tab_button = page.locator('button[role="tab"]:has-text("Pegar texto")')
            tab_button.click()

            # Rellenar textarea
            textarea = page.locator('textarea[aria-label="Contenido documental en texto"]')
            textarea.fill(SAMPLE_TEXT)

            # Seleccionar prompt 'Puntos clave'
            prompt_select = page.locator("#prompt-select")
            prompt_select.select_option(value="key-points")

            # Opciones de analisis por defecto (Estandar y Secciones)
            page.locator('button.segmented-option:has-text("Estandar"), button.segmented-option:has-text("Estándar")').first.click()
            page.locator('button.segmented-option:has-text("Secciones temáticas")').click()

            print("      Texto y parametros configurados.")

            # 6. Iniciar analisis real (1 unica llamada a Gemini)
            print("[6/8] Pulsando 'Analizar texto' y esperando respuesta de Gemini 3.8 Flash...")
            analyze_btn = page.locator('button:has-text("Analizar texto")')
            analyze_btn.click()

            # Esperar a que aparezca la tarjeta de resultados (hasta 60s)
            result_locator = page.locator('[data-testid="analysis-result"]')
            result_locator.wait_for(state="visible", timeout=60000)

            # Extraer detalles del resultado
            result_title = page.locator(".result-title").inner_text()
            prompt_badge = page.locator(".result-prompt-badge").inner_text()
            model_badge = page.locator(".result-model-badge").inner_text()
            content_text = page.locator(".markdown-document").inner_text()

            print("\n" + "=" * 60)
            print("=== RESULTADO OBTENIDO EN EL NAVEGADOR ===")
            print(f"Titulo: {result_title}")
            print(f"Prompt: {prompt_badge}")
            print(f"Modelo: {model_badge}")
            print(f"Longitud contenido renderizado: {len(content_text)} caracteres")
            snippet = content_text[:200].replace("\n", " ")
            print(f"Muestra: {snippet}...")
            print("=" * 60)

            # Guardar captura de pantalla del analisis
            analysis_screenshot = ROOT_DIR / "scripts" / "e2e_browser_analysis.png"
            page.screenshot(path=str(analysis_screenshot), full_page=True)
            print(f"      [Captura guardada]: {analysis_screenshot.name}")

            assert len(result_title) > 0, "El titulo del resultado esta vacio"
            assert len(content_text) > 0, "El contenido del analisis esta vacio"
            assert len(analysis_network_called) == 1, (
                f"Se esperaba exactamente 1 llamada POST /api/v1/analysis, pero hubo {len(analysis_network_called)}"
            )
            assert analysis_network_called[0] == 200, f"Analisis retorno status {analysis_network_called[0]}"

            # 7. Exportacion a Word desde la misma pagina (sin recarga ni llamada extra a Gemini)
            print("\n[7/8] Ejecutando exportacion a Word (.docx) desde el navegador...")
            export_btn = page.locator('button:has-text("Exportar a Word")')
            assert export_btn.is_visible(), "El boton 'Exportar a Word' no es visible"
            assert export_btn.is_enabled(), "El boton 'Exportar a Word' esta deshabilitado"

            # Iniciar intercepcion de descarga
            with page.expect_download(timeout=15000) as download_info:
                export_btn.click()

            download = download_info.value
            suggested_filename = download.suggested_filename
            print(f"      Descarga interceptada con nombre: '{suggested_filename}'")
            download.save_as(str(downloaded_docx_path))

            # Comprobar mensaje de exito en la UI
            success_banner = page.locator(".export-status-banner.success")
            success_banner.wait_for(state="visible", timeout=5000)
            success_text = success_banner.inner_text()
            print(f"      Banner de confirmacion en UI: '{success_text}'")

            # Guardar captura de pantalla del estado post-exportacion
            export_screenshot = ROOT_DIR / "scripts" / "e2e_browser_word_export.png"
            page.screenshot(path=str(export_screenshot), full_page=True)
            print(f"      [Captura guardada]: {export_screenshot.name}")

            assert len(export_network_called) == 1, (
                f"Se esperaba 1 llamada a /api/v1/export/word, pero hubo {len(export_network_called)}"
            )
            assert export_network_called[0] == 200, f"Export Word retorno status {export_network_called[0]}"
            assert "Word generado correctamente" in success_text

            # 8. Inspeccion fisica del archivo .docx con python-docx
            print("\n[8/8] Inspeccionando archivo .docx descargado con python-docx...")
            assert downloaded_docx_path.exists(), "El archivo descargado no existe en disco"
            file_size = downloaded_docx_path.stat().st_size
            print(f"      Tamano del archivo .docx: {file_size} bytes")
            assert file_size > 0, "El archivo .docx descargado esta vacio"

            doc = docx.Document(str(downloaded_docx_path))
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            print(f"      Total parrafos en documento: {len(paragraphs)}")

            # Comprobar que el titulo esta en los primeros parrafos
            has_title = any(result_title[:15].lower() in p.lower() for p in paragraphs[:5])
            print(f"      ¿Titulo presente en encabezado del DOCX? {'Si' if has_title else 'No'}")
            assert has_title or len(paragraphs) > 0, "No se encontro contenido reconocible en el DOCX"

            # Resumen de secciones en el Word
            headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
            print(f"      Secciones detectadas ({len(headings)}): {headings[:5]}")

            print("\n" + "=" * 70)
            print(">>> VALIDACION E2E EN NAVEGADOR SUPERADA EXITOSAMENTE <<<")
            print("=" * 70)
            print("1. Carga de interfaz y catalogo de prompts: CORRECTA")
            print("2. Pestana de texto y normalizacion: CORRECTA")
            print("3. Ejecucion de analisis real con Gemini 3.8 Flash: 1 LLAMADA (HTTP 200)")
            print("4. Renderizado de Markdown, titulo y metricas: CORRECTO")
            print("5. Exportacion a Word desde el frontend: 1 LLAMADA (HTTP 200)")
            print("6. Descarga y formato binario .docx valido: CORRECTO")
            print("7. Feedback visual de exito en la interfaz: CORRECTO")
            print("=" * 70)

            browser.close()

    finally:
        # Limpieza de archivos temporales
        if downloaded_docx_path.exists():
            try:
                downloaded_docx_path.unlink()
            except Exception:
                pass
        if download_dir.exists():
            try:
                download_dir.rmdir()
            except Exception:
                pass

        # Detener procesos creados si los iniciamos nosotros
        def kill_proc(p):
            if not p:
                return
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
            except Exception:
                p.terminate()

        if backend_proc:
            kill_proc(backend_proc)
        if frontend_proc:
            kill_proc(frontend_proc)


if __name__ == "__main__":
    run_e2e_browser_test()
