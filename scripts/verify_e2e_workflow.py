import io
import json
import os
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import httpx

SAMPLE_TEXT = (
    "El 3 de marzo de 2026, Empresa Alfa firmó un contrato de servicios por doce meses. "
    "Debe entregar un informe mensual antes del día 5. Existe una penalización de 500 euros "
    "por retrasos superiores a diez días."
)

BASE_URL = "http://localhost:8000"


def verify_e2e():
    print("=" * 65)
    print("=== VERIFICACIÓN E2E REAL: Flujo Completo Backend <-> Gemini ===")
    print("=" * 65)

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Health check
        print("\n[1] Verificando salud del backend...")
        health_resp = client.get("/health")
        if health_resp.status_code != 200:
            print(f"[ERROR] Backend health check falló: {health_resp.status_code}")
            sys.exit(1)
        print(f"[OK] Backend operativo: {health_resp.json()}")

        # 2. Catálogo de prompts
        print("\n[2] Consultando catálogo de prompts...")
        prompts_resp = client.get("/api/v1/prompts")
        if prompts_resp.status_code != 200:
            print(f"[ERROR] Error al consultar prompts: {prompts_resp.status_code}")
            sys.exit(1)
        prompts = prompts_resp.json()
        print(f"[OK] {len(prompts)} prompts disponibles en catálogo.")

        # 3. Document Extraction (TXT sintético muy pequeño)
        print("\n[3] Probando extracción documental (POST /api/v1/documents/extract)...")
        doc_content = b"Contrato sintetico de prueba para verificacion de extraccion."
        files = {"file": ("contrato_prueba.txt", doc_content, "text/plain")}
        doc_resp = client.post("/api/v1/documents/extract", files=files)
        if doc_resp.status_code != 200:
            print(f"[ERROR] Extracción de documento falló: {doc_resp.status_code} - {doc_resp.text}")
            sys.exit(1)
        doc_data = doc_resp.json()
        print(f"[OK] Documento extraído correctamente:")
        print(f"     Archivo: {doc_data.get('filename')}")
        print(f"     Caracteres: {doc_data.get('character_count')}, Palabras: {doc_data.get('word_count')}")
        print(f"     Texto: \"{doc_data.get('text')}\"")

        # 4. Text Preparation (POST /api/v1/text/prepare)
        print("\n[4] Probando preparación de texto (POST /api/v1/text/prepare)...")
        text_resp = client.post("/api/v1/text/prepare", json={"text": SAMPLE_TEXT})
        if text_resp.status_code != 200:
            print(f"[ERROR] Preparación de texto falló: {text_resp.status_code} - {text_resp.text}")
            sys.exit(1)
        text_data = text_resp.json()
        normalized_text = text_data["text"]
        print(f"[OK] Texto preparado y normalizado:")
        print(f"     Palabras: {text_data['word_count']}, Caracteres: {text_data['character_count']}")

        # 5. Real Analysis with Gemini 3.8 Flash (1 única llamada)
        prompt_id = "key-points"
        options = {
            "detail_level": "standard",
            "output_format": "sections",
        }
        print(f"\n[5] Ejecutando análisis REAL con Gemini 3.8 Flash (POST /api/v1/analysis)...")
        print(f"     Prompt ID: {prompt_id}")
        print(f"     Opciones: {options}")

        start_time = time.perf_counter()
        analysis_resp = client.post(
            "/api/v1/analysis",
            json={
                "text": normalized_text,
                "prompt_id": prompt_id,
                "options": options,
            },
        )
        elapsed = time.perf_counter() - start_time

        if analysis_resp.status_code != 200:
            print(f"[ERROR] Análisis falló con HTTP {analysis_resp.status_code}: {analysis_resp.text}")
            sys.exit(1)

        result = analysis_resp.json()
        print(f"[OK] Análisis completado con éxito en {elapsed:.2f} s")
        print("\n" + "=" * 65)
        print("=== RESULTADO DEL ANÁLISIS REAL ===")
        print("=" * 65)
        print(f"Título          : {result.get('title')}")
        print(f"Prompt          : {result.get('prompt_name')} ({result.get('prompt_id')})")
        print(f"Modelo          : {result.get('model')}")
        print(f"Advertencias    : {result.get('warnings')}")
        print(f"\nFragmento del contenido:")
        snippet = result.get('content', '')[:300]
        print(f"{snippet}...")
        print(f"\nMétricas de tokens:")
        usage = result.get('usage', {})
        print(f"  - Entrada : {usage.get('input_tokens')}")
        print(f"  - Salida  : {usage.get('output_tokens')}")
        print(f"  - Total   : {usage.get('total_tokens')}")
        print("=" * 65)
        print(">>> VERIFICACIÓN E2E COMPLETADA CON ÉXITO <<<")
        print("=" * 65)


if __name__ == "__main__":
    verify_e2e()
