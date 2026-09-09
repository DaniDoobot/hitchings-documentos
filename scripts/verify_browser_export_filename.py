"""
Script de validación para la captura del filename real en exportación Word desde navegador (Bloque 6C corrección).
Garantiza:
1. Cero llamadas a Gemini (análisis interceptado con fixture local idéntica a la respuesta real).
2. Servidor backend real FastAPI (8000) y frontend Vite (5173).
3. Verificación de que Access-Control-Expose-Headers: Content-Disposition permite al frontend leer el nombre de archivo real.
4. Verificación de que el navegador descarga 'analisis-de-puntos-clave-contrato-de-servicios-de-empresa-al.docx' y NO el fallback 'hitchings-analisis.docx'.
"""

import io
import json
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

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

FIXTURE_RESPONSE = {
    "prompt_id": "key-points",
    "prompt_name": "Puntos clave",
    "model": "gemini-3.8-flash",
    "options": {
        "detail_level": "standard",
        "output_format": "sections",
    },
    "title": "Análisis de Puntos Clave: Contrato de Servicios de Empresa Alfa",
    "content": (
        "## 1. Listado Priorizado por Relevancia\n"
        "- Firma y duración contractual: Formalización de un contrato de servicios por un período de doce meses.\n"
        "- Obligación periódica de entrega: Compromiso de remitir un informe mensual antes del día 5.\n"
        "- Régimen sancionador: Penalización económica de 500 euros por retrasos superiores a diez días.\n"
    ),
    "warnings": [
        "No se menciona la identidad de la otra parte contratante.",
    ],
    "usage": {
        "input_tokens": 790,
        "output_tokens": 669,
        "total_tokens": 1846,
    },
}


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


def run_filename_verification():
    print("=" * 70)
    print("=== VERIFICACIÓN DE FILENAME REAL EN NAVEGADOR (CERO GEMINI) ===")
    print("=" * 70)

    backend_proc = None
    frontend_proc = None

    if not check_service(f"{BACKEND_URL}/health"):
        print("[1/5] Iniciando Backend FastAPI...")
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
        print("[1/5] Backend FastAPI ya se encuentra activo.")

    if not check_service(FRONTEND_URL):
        print("[2/5] Iniciando Frontend Vite...")
        frontend_proc = subprocess.Popen(
            "npm run dev -- --host 0.0.0.0 --port 5173",
            shell=True,
            cwd=str(ROOT_DIR / "frontend"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    else:
        print("[2/5] Frontend Vite ya se encuentra activo.")

    if not wait_for_services(30):
        print("[ERROR] No se pudo conectar a los servicios.")
        sys.exit(1)

    download_dir = ROOT_DIR / "scripts" / "tmp_dl"
    download_dir.mkdir(exist_ok=True)
    temp_docx = download_dir / "downloaded.docx"
    if temp_docx.exists():
        temp_docx.unlink()

    try:
        with sync_playwright() as p:
            print("[3/5] Lanzando navegador Chrome...")
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            # Interceptar llamada /api/v1/analysis para NO llamar a Gemini
            def handle_analysis_route(route):
                print("      [Interceptado POST /api/v1/analysis] Devolviendo fixture local (0 llamadas Gemini)")
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(FIXTURE_RESPONSE),
                )

            page.route("**/api/v1/analysis", handle_analysis_route)

            print("[4/5] Navegando a la aplicación e inyectando análisis...")
            page.goto(FRONTEND_URL, wait_until="networkidle")

            page.wait_for_selector(".brand-title", timeout=5000)
            page.wait_for_selector("#prompt-select option", state="attached", timeout=10000)

            page.locator('button[role="tab"]:has-text("Pegar texto")').click()
            textarea = page.locator('textarea[aria-label="Contenido documental en texto"]')
            textarea.fill("Texto de prueba para verificar filename de exportación.")

            page.locator('button:has-text("Analizar texto")').click()

            page.wait_for_selector('[data-testid="analysis-result"]', timeout=10000)
            print("      Resultado de análisis renderizado correctamente en pantalla.")

            # 5. Exportar a Word (Llamada REAL a /api/v1/export/word)
            print("[5/5] Pulsando 'Exportar a Word' y capturando descarga del navegador...")
            export_btn = page.locator('button:has-text("Exportar a Word")')

            with page.expect_download(timeout=15000) as download_info:
                export_btn.click()

            download = download_info.value
            actual_filename = download.suggested_filename
            print("\n" + "=" * 60)
            print(f">>> FILENAME REAL OBTENIDO POR EL NAVEGADOR: '{actual_filename}' <<<")
            print("=" * 60)

            download.save_as(str(temp_docx))
            assert temp_docx.exists(), "El archivo descargado no existe"
            file_size = temp_docx.stat().st_size
            print(f"Tamaño del archivo descargado: {file_size} bytes")

            # Verificaciones
            assert actual_filename != "hitchings-analisis.docx", (
                "FALLO: El navegador continuó usando el fallback 'hitchings-analisis.docx'. "
                "CORS Access-Control-Expose-Headers no funcionó."
            )
            assert actual_filename.endswith(".docx"), "El archivo no tiene extensión .docx"
            assert "analisis" in actual_filename.lower(), "El nombre no contiene 'analisis'"
            assert "puntos-clave" in actual_filename.lower(), "El nombre no contiene 'puntos-clave'"

            # Inspección rápida con python-docx
            doc = docx.Document(str(temp_docx))
            print(f"Párrafos en el documento: {len(doc.paragraphs)}")
            all_text = " ".join(p.text for p in doc.paragraphs)
            assert "Análisis de Puntos Clave" in all_text, "Título no encontrado en DOCX"
            assert "gemini-3.8-flash" not in all_text, "El modelo interno NO debe aparecer en el cuerpo del Word"

            print("\n" + "=" * 70)
            print(">>> VALIDACIÓN DE FILENAME REAL EXITOSA (0 LLAMADAS GEMINI) <<<")
            print(f"Filename exacto recibido: {actual_filename}")
            print(f"Fallback evitado: Sí ('hitchings-analisis.docx' no fue usado)")
            print(f"Expose-Headers operativo: Sí (Content-Disposition leído por JS)")
            print(f"Modelo IA en cuerpo del DOCX: No presente (correcto)")
            print("=" * 70)

            browser.close()

    finally:
        if temp_docx.exists():
            try:
                temp_docx.unlink()
            except Exception:
                pass
        if download_dir.exists():
            try:
                download_dir.rmdir()
            except Exception:
                pass

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
    run_filename_verification()
