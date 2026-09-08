"""
Script de smoke test puntual y seguro para validar la integración REAL con Google Gemini Interactions API.

REQUISITOS PREVIOS:
1. Configurar la clave GEMINI_API_KEY en el entorno o en un archivo .env:
   GEMINI_API_KEY=AIzaSy...

2. Grabar un audio corto, limpio y no confidencial (WAV o MP3) diciendo por ejemplo:
   "Hola, esto es una prueba de transcripción del proyecto Hitchings."

INSTRUCCIONES DE USO:
  python scripts/smoke_test_gemini_audio.py --audio ruta/al/audio.wav

GARANTÍAS DE SEGURIDAD:
- NO se ejecuta automáticamente en suites de test de CI o pytest.
- Utiliza el audio proporcionado por el usuario (no se commitean binarios de audio al repo).
- Valida formato y cabecera del archivo reutilizando las validaciones del servicio.
- Sube el audio a Gemini Files API, ejecuta la transcripción con Interactions API y elimina de forma garantizada el archivo remoto en finally.
- No deja archivos temporales residuales en disco local.
- No imprime la clave de API, tokens ni URLs remotas completas.
"""

import argparse
import os
import sys
from pathlib import Path

# Añadir raíz del proyecto al path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings
from app.services.audio_transcription import audio_transcription_service
from app.services.gemini_client import gemini_client


def run_smoke_test(audio_path_str: str | None = None):
    print("=== SMOKE TEST: Gemini Interactions API Audio Transcription ===")

    # 1. Comprobación de GEMINI_API_KEY
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[AVISO] GEMINI_API_KEY no está definida en el entorno ni en .env.")
        print("Para realizar la prueba real:")
        print("  1. Defina GEMINI_API_KEY en su archivo .env o en el entorno del sistema.")
        print("  2. Grabe un audio de prueba diciendo:")
        print("     'Hola, esto es una prueba de transcripción del proyecto Hitchings.'")
        print("  3. Ejecute de nuevo:")
        print("     python scripts/smoke_test_gemini_audio.py --audio ruta/a/tu_audio.wav")
        sys.exit(0)

    # 2. Comprobación de argumento de audio
    if not audio_path_str:
        print("[ERROR] Debe proporcionar la ruta a un archivo de audio real mediante el argumento --audio.")
        print("Ejemplo de uso:")
        print("  python scripts/smoke_test_gemini_audio.py --audio smoke_audio.wav")
        sys.exit(1)

    audio_path = Path(audio_path_str).resolve()
    if not audio_path.exists() or not audio_path.is_file():
        print(f"[ERROR] El archivo de audio indicado no existe: {audio_path_str}")
        sys.exit(1)

    # 3. Validación de formato y extensión
    extension = audio_transcription_service.get_extension(audio_path.name)
    if extension not in audio_transcription_service.ALLOWED_AUDIO_EXTENSIONS:
        print(f"[ERROR] Extensión de audio no soportada: '.{extension}'. Formatos válidos: mp3, wav, m4a, aac, ogg, flac, webm")
        sys.exit(1)

    file_size_bytes = audio_path.stat().st_size
    if file_size_bytes == 0:
        print("[ERROR] El archivo de audio está vacío (0 bytes).")
        sys.exit(1)

    # Validación de cabecera binaria básica
    with open(audio_path, "rb") as f:
        header_bytes = f.read(32)
    try:
        audio_transcription_service.validate_audio_header(header_bytes, extension)
    except Exception as exc:
        print(f"[ADVERTENCIA] Cabecera no estándar detectada: {exc}")

    mime_type = audio_transcription_service.AUDIO_MIME_MAPPING.get(extension, "audio/mpeg")
    print(f"[1/4] Audio cargado: extensión={extension}, tamaño={file_size_bytes} bytes, MIME={mime_type}")

    remote_file_name = None
    try:
        # 4. Subida mediante Gemini Files API
        print("[2/4] Subiendo archivo a Gemini Files API...")
        remote_file = gemini_client.upload_file(str(audio_path), mime_type=mime_type)
        remote_file_name = getattr(remote_file, "name", None)
        print("      Subida completada con éxito.")

        # 5. Invocación a Interactions API
        print("[3/4] Invocando client.interactions.create con modelo oficial...")
        text, segments, detected_lang = gemini_client.transcribe_audio(
            remote_file=remote_file,
            mode="verbatim",
            diarization=False,
        )

        print("\n--- RESULTADO DE LA TRANSCRIPCIÓN ---")
        print(f"Texto obtenido:\n\"{text}\"\n")
        print(f"Métricas técnicas:")
        print(f"- Total caracteres: {len(text)}")
        print(f"- Total palabras: {len(text.split())}")
        print(f"- Idioma detectado: {detected_lang or 'auto'}")
        print(f"- Segmentos de interlocutores: {len(segments)}")

        # 6. Comprobaciones de calidad y habla reconocida
        if not text or not text.strip():
            print("[FALLO] La respuesta de Gemini no contiene texto transcrito.")
            sys.exit(1)

        # Comprobación tolerante de palabras clave de la frase recomendada
        expected_keywords = ["prueba", "transcripción", "hitchings"]
        text_lower = text.lower()
        matched_keywords = [kw for kw in expected_keywords if kw in text_lower]
        if matched_keywords:
            print(f"[OK] Coincidencia tolerante de palabras clave: {matched_keywords}")
        else:
            print(f"[INFO] Palabras clave sugeridas no detectadas textualmente. Transcripción recibida correctamente.")

        print("[OK] Transcripción completada con éxito.")

    except Exception as exc:
        print(f"[ERROR] Falló la interacción con Gemini: {exc}")
        sys.exit(1)
    finally:
        # 7. Borrado remoto OBLIGATORIO en Gemini Files API
        print("\n[4/4] Limpieza obligatoria de recursos remotos...")
        if remote_file_name:
            deleted = gemini_client.delete_remote_file(remote_file_name)
            if deleted:
                print("      Borrado remoto en Gemini Files API: OK (archivo destruido)")
            else:
                print("      [ADVERTENCIA] No se pudo confirmar la eliminación remota.")
        print("=== SMOKE TEST FINALIZADO ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Smoke test de verificación de transcripción de audio con Gemini Interactions API."
    )
    parser.add_argument(
        "--audio",
        "-a",
        type=str,
        default=None,
        help="Ruta al archivo de audio real con voz (WAV o MP3) para la prueba.",
    )
    args = parser.parse_args()
    run_smoke_test(args.audio)

