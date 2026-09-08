"""
Script de smoke test puntual para validar la integración REAL con Google Gemini Interactions API en análisis documental.

REQUISITOS PREVIOS:
1. Configurar GEMINI_API_KEY en el entorno o en un archivo .env:
   GEMINI_API_KEY=AIzaSy...

INSTRUCCIONES DE USO:
  python scripts/smoke_test_gemini_analysis.py

GARANTÍAS DE SEGURIDAD:
- NO se ejecuta en pytest ni en CI automatizado.
- Utiliza un texto sintético mínimo, controlado y NO confidencial.
- Realiza EXACTAMENTE UNA llamada real para evitar costes innecesarios.
- NO imprime la clave de API.
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Añadir raíz del proyecto al path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings
from app.schemas.prompts import AnalysisOptions, AnalysisRequest
from app.services.analysis_service import analysis_service

DEFAULT_SAMPLE_TEXT = (
    "El 3 de marzo de 2026, Empresa Alfa y Empresa Beta firmaron un contrato de prestación "
    "de servicios por doce meses. Empresa Alfa se comprometió a entregar un informe mensual "
    "antes del día 5. El contrato establece una penalización de 500 euros por cada entrega "
    "realizada con más de diez días de retraso."
)


def run_smoke_test(prompt_id: str = "key-points", custom_text: str | None = None):
    print("=================================================================")
    print("=== SMOKE TEST REAL: Google Gemini 3.8 Flash Document Analysis ==")
    print("=================================================================")

    # 1. Comprobación de GEMINI_API_KEY
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY no está configurada en .env ni en variables de entorno.")
        sys.exit(1)

    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    print(f"[OK] GEMINI_API_KEY detectada (longitud: {len(api_key)}, formato: {masked_key})")
    print(f"[OK] Modelo de análisis configurado: {settings.GEMINI_ANALYSIS_MODEL}")
    print(f"[OK] Thinking level configurado: {settings.GEMINI_ANALYSIS_THINKING_LEVEL}")
    print(f"[OK] Límite operativo tokens entrada: {settings.MAX_ANALYSIS_INPUT_TOKENS:,}")

    sample_text = custom_text or DEFAULT_SAMPLE_TEXT
    print(f"\n[INFO] Texto de prueba (NO confidencial):")
    print(f"       \"{sample_text}\"")
    print(f"       Caracteres: {len(sample_text)}")

    request = AnalysisRequest(
        text=sample_text,
        prompt_id=prompt_id,
        options=AnalysisOptions(
            detail_level="standard",
            output_format="sections",
        ),
    )

    # 2. Ejecutar el pipeline completo
    print(f"\n[INFO] Ejecutando análisis real con prompt_id='{prompt_id}'...")
    start_time = time.perf_counter()
    try:
        response = analysis_service.analyze_document(request)
        elapsed_secs = time.perf_counter() - start_time
    except Exception as exc:
        print(f"\n[FALLO] Error durante el análisis real con Gemini:")
        print(f"        Tipo de excepción: {type(exc).__name__}")
        print(f"        Mensaje: {exc}")
        sys.exit(1)

    print(f"[OK] Llamada a Gemini Interactions API completada en {elapsed_secs:.2f} s")

    # 3. Resultados obtenidos
    print("\n=================================================================")
    print("=== RESULTADO DEL ANÁLISIS ESTRUCTURADO (Structured Output) =====")
    print("=================================================================")
    print(f"Prompt aplicado : {response.prompt_name} ({response.prompt_id})")
    print(f"Modelo real     : {response.model}")
    print(f"Título          : {response.title}")
    print(f"Advertencias    : {response.warnings if response.warnings else 'Ninguna'}")
    print("\n--- CONTENIDO GENERADO (Markdown) ---")
    print(response.content)
    print("-------------------------------------")

    print("\n=== USO DE TOKENS (Gemini interaction.usage) ===")
    print(f"Tokens de entrada : {response.usage.input_tokens}")
    print(f"Tokens de salida  : {response.usage.output_tokens}")
    print(f"Tokens totales    : {response.usage.total_tokens}")

    # Validaciones de aceptación
    assert response.title, "El título generado no puede estar vacío"
    assert response.content, "El contenido generado no puede estar vacío"
    assert response.model == settings.GEMINI_ANALYSIS_MODEL
    assert response.usage.input_tokens is not None and response.usage.input_tokens > 0

    print("\n=================================================================")
    print(">>> SMOKE TEST REAL: PASS <<<")
    print("=================================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke test real para análisis con Gemini 3.8 Flash")
    parser.add_argument(
        "--prompt",
        default="key-points",
        choices=["executive-summary", "legal-analysis", "key-points", "timeline", "custom-analysis"],
        help="ID del prompt a ejecutar (por defecto: key-points)",
    )
    parser.add_argument(
        "--text",
        default=None,
        help="Texto alternativo no confidencial para análisis",
    )
    args = parser.parse_args()
    run_smoke_test(prompt_id=args.prompt, custom_text=args.text)
