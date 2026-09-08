"""
Script de smoke test puntual y seguro para validar la integración REAL con Google Gemini Interactions API.

REQUISITOS PREVIOS:
1. Configurar la clave GEMINI_API_KEY en el entorno o en un archivo .env:
   GEMINI_API_KEY=AIzaSy...

INSTRUCCIONES DE USO:
  python scripts/smoke_test_gemini_audio.py

GARANTÍAS DE SEGURIDAD:
- NO se ejecuta automáticamente en suites de test de CI o pytest.
- Utiliza un audio PCM WAV sintético muy corto generado en memoria (no confidencial, sin costes apreciables).
- Sube el audio a la Files API, ejecuta la transcripción con Interactions API y elimina de forma garantizada el archivo remoto en finally.
- No deja archivos temporales residuales en disco local.
- No imprime la clave de API ni datos confidenciales en consola o logs.
"""

import math
import os
import struct
import sys
import tempfile
from pathlib import Path

# Añadir raíz del proyecto al path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings
from app.services.gemini_client import gemini_client


def generate_short_synthetic_wav(duration_secs: float = 1.0, sample_rate: int = 8000) -> bytes:
    """Genera un archivo WAV PCM 8-bit mono sintético."""
    num_samples = int(sample_rate * duration_secs)
    samples = bytearray()
    for i in range(num_samples):
        val = int(128 + 100 * math.sin(2 * math.pi * 440 * (i / sample_rate)))
        samples.append(max(0, min(255, val)))

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(samples),
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        1,  # Mono
        sample_rate,
        sample_rate,
        1,
        8,
        b"data",
        len(samples),
    )
    return header + bytes(samples)


def run_smoke_test():
    print("=== SMOKE TEST: Gemini Interactions API Audio Transcription ===")

    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[AVISO] GEMINI_API_KEY no está definida en el entorno ni en .env.")
        print("Para realizar la prueba real:")
        print("  1. Defina GEMINI_API_KEY en su archivo .env o en el entorno del sistema.")
        print("  2. Ejecute de nuevo: python scripts/smoke_test_gemini_audio.py")
        sys.exit(0)

    print("[1/4] Generando audio sintético efímero (sin datos confidenciales)...")
    wav_data = generate_short_synthetic_wav(duration_secs=1.5)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_data)
        temp_path = tmp.name

    remote_file_name = None
    try:
        print("[2/4] Subiendo archivo temporal a Gemini Files API...")
        remote_file = gemini_client.upload_file(temp_path, mime_type="audio/wav")
        remote_file_name = getattr(remote_file, "name", None)
        print("      Subida exitosa (ID remoto asignado)")

        print("[3/4] Invocando client.interactions.create con gemini-3.5-transcribe...")
        text, segments, detected_lang = gemini_client.transcribe_audio(
            remote_file=remote_file,
            mode="verbatim",
            diarization=False,
        )
        print("      Respuesta recibida:")
        print(f"      - Caracteres devueltos: {len(text)}")
        print(f"      - Idioma detectado: {detected_lang}")
        print(f"      - Segmentos: {len(segments)}")
        print("[OK] Transcripción completada con éxito.")
    except Exception as exc:
        print(f"[ERROR] Falló la interacción con Gemini: {exc}")
        sys.exit(1)
    finally:
        print("[4/4] Limpieza obligatoria de recursos...")
        if remote_file_name:
            deleted = gemini_client.delete_remote_file(remote_file_name)
            print(f"      Borrado remoto en Gemini Files API: {'OK' if deleted else 'FALLO'}")
        if os.path.exists(temp_path):
            os.unlink(temp_path)
            print("      Borrado de archivo temporal local: OK")

    print("=== SMOKE TEST FINALIZADO CON ÉXITO ===")


if __name__ == "__main__":
    run_smoke_test()
