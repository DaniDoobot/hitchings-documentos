from typing import List, Tuple
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import settings
from app.core.logging import logger
from app.schemas.audio import AudioTranscriptionUsage, SpeakerSegment


class GeminiConfigurationError(Exception):
    """Excepción cuando la configuración o la clave de API de Gemini no está disponible."""
    pass


class GeminiProviderError(Exception):
    """Excepción cuando el proveedor Gemini falla o devuelve un error controlado (HTTP 502/503)."""
    pass


class GeminiEmptyResponseError(Exception):
    """Excepción cuando Gemini no genera transcripción válida para el audio (HTTP 400)."""
    pass


class GeminiClient:
    """Cliente para la interacción con Google Gemini Developer API vía google-genai."""

    def __init__(self):
        self._client: genai.Client | None = None

    def get_client(self) -> genai.Client:
        """Inicializa u obtiene el cliente de Google GenAI de forma perezosa."""
        if self._client is not None:
            return self._client
        if not settings.GEMINI_API_KEY:
            raise GeminiConfigurationError(
                "La clave GEMINI_API_KEY no está configurada en las variables de entorno."
            )
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def upload_file(self, file_path: str, mime_type: str) -> types.File:
        """Sube un archivo a Gemini Files API."""
        client = self.get_client()
        try:
            upload_config = types.UploadFileConfig(mime_type=mime_type)
            remote_file = client.files.upload(file=file_path, config=upload_config)
            return remote_file
        except APIError as exc:
            logger.error("Error al subir archivo a Gemini Files API: %s", exc)
            raise GeminiProviderError("Error de comunicación al transferir el audio al proveedor de transcripción.") from exc
        except Exception as exc:
            logger.error("Error inesperado en upload a Gemini Files API: %s", exc, exc_info=True)
            raise GeminiProviderError("Error interno al preparar el archivo de audio para transcripción.") from exc

    def delete_remote_file(self, remote_file_name: str) -> bool:
        """
        Elimina un archivo de Gemini Files API.
        Retorna True si fue eliminado con éxito, False si falló.
        No propaga excepciones para no invalidar una transcripción exitosa en bloques finally.
        """
        if not remote_file_name:
            return False

        try:
            client = self.get_client()
            client.files.delete(name=remote_file_name)
            logger.info("Archivo remoto eliminado con éxito de Gemini Files API")
            return True
        except Exception as exc:
            # Nunca registrar la URI completa, filenames ni datos sensibles en el log de error
            logger.error("Fallo al eliminar archivo remoto de Gemini Files API: %s", exc)
            return False

    def transcribe_audio(
        self,
        remote_file: types.File,
        mode: str = "verbatim",
        diarization: bool = False,
        language: str | None = None,
    ) -> Tuple[str, List[SpeakerSegment], str | None]:
        """
        Invoca el modelo de transcripción de Gemini mediante la Interactions API oficial actual.
        Retorna (texto_completo, lista_segmentos_hablantes, detected_language).
        """
        client = self.get_client()

        # Construir configuración de transcripción según la API actual
        transcription_config: dict = {}
        if mode == "verbatim":
            if diarization:
                transcription_config["mode"] = {
                    "type": "verbatim",
                    "diarization_mode": "speaker",
                }
            else:
                transcription_config["mode"] = {
                    "type": "verbatim",
                }
        elif mode == "smart":
            transcription_config["mode"] = "smart"

        if language:
            transcription_config["language_codes"] = [language]

        generation_config = {
            "transcription_config": transcription_config,
        }

        # Preparar payload de entrada conforme al estándar de Interactions API
        file_uri = getattr(remote_file, "uri", None)
        file_mime = getattr(remote_file, "mime_type", None) or "audio/mpeg"

        input_payload = [
            {
                "type": "audio",
                "uri": file_uri,
                "mime_type": file_mime,
            }
        ]

        try:
            interaction = client.interactions.create(
                model=settings.GEMINI_TRANSCRIPTION_MODEL,
                input=input_payload,
                store=False,
                generation_config=generation_config,
            )
        except APIError as exc:
            logger.error("Error retornado por Gemini durante la transcripción: %s", exc)
            exc_msg = str(exc).lower()
            if "duration" in exc_msg or "too long" in exc_msg or "exceeds maximum" in exc_msg:
                max_duration = "30 minutos (con diarización)" if diarization else "1 hora"
                raise GeminiProviderError(
                    f"El audio excede la duración máxima permitida por Gemini para el modo seleccionado ({max_duration})."
                ) from exc
            raise GeminiProviderError("El proveedor de transcripción devolvió un error al procesar el audio.") from exc
        except Exception as exc:
            logger.error("Fallo de comunicación con Gemini: %s", exc, exc_info=True)
            raise GeminiProviderError("No se pudo completar la transcripción con el proveedor de IA.") from exc

        # Extraer texto de la respuesta
        full_text = getattr(interaction, "output_text", None)
        if not full_text and hasattr(interaction, "steps") and interaction.steps:
            # Fallback en caso de que output_text esté vacío pero haya texto en steps
            text_parts: List[str] = []
            for step in interaction.steps:
                contents = getattr(step, "content", []) or []
                for content in contents:
                    txt = getattr(content, "text", None)
                    if txt:
                        text_parts.append(txt)
            if text_parts:
                full_text = " ".join(text_parts)

        if not full_text or not full_text.strip():
            logger.warning("Gemini no devolvió texto de transcripción.")
            raise GeminiEmptyResponseError(
                "El modelo de IA procesó el audio pero no detectó contenido hablado transcribible."
            )

        full_text = full_text.strip()
        segments: List[SpeakerSegment] = []

        # Extraer diarización real si se solicitó
        if diarization and hasattr(interaction, "steps") and interaction.steps:
            for step in interaction.steps:
                contents = getattr(step, "content", []) or []
                for content in contents:
                    speaker_id = getattr(content, "speaker", None)
                    content_text = getattr(content, "text", None)

                    # Inspeccionar también annotations si speaker no vino como atributo directo
                    if not speaker_id and hasattr(content, "annotations") and content.annotations:
                        for ann in content.annotations:
                            raw = getattr(ann, "raw", None)
                            if isinstance(raw, dict) and "speaker" in raw:
                                speaker_id = raw.get("speaker")
                                break
                            elif hasattr(ann, "speaker"):
                                speaker_id = getattr(ann, "speaker")
                                break

                    if speaker_id and content_text:
                        segments.append(
                            SpeakerSegment(
                                speaker=str(speaker_id),
                                text=str(content_text).strip(),
                            )
                        )

        # Extraer detected_language explícito únicamente si el proveedor lo suministra como string real
        detected_language = None
        raw_lang = getattr(interaction, "detected_language", None)
        if isinstance(raw_lang, str) and raw_lang.strip():
            detected_language = raw_lang.strip()
        else:
            usage_meta = getattr(interaction, "usage_metadata", None)
            if usage_meta is not None and not isinstance(usage_meta, str):
                meta_lang = getattr(usage_meta, "detected_language", None)
                if isinstance(meta_lang, str) and meta_lang.strip():
                    detected_language = meta_lang.strip()

        # Extraer usage de la interacción si el proveedor lo suministra oficialmente
        usage = None
        usage_data = getattr(interaction, "usage", None)
        if usage_data is not None:
            if isinstance(usage_data, dict):
                in_tok = usage_data.get("total_input_tokens", usage_data.get("input_tokens"))
                out_tok = usage_data.get("total_output_tokens", usage_data.get("output_tokens"))
                tot_tok = usage_data.get("total_tokens")
            else:
                in_tok = getattr(usage_data, "total_input_tokens", None)
                if in_tok is None:
                    in_tok = getattr(usage_data, "input_tokens", None)
                out_tok = getattr(usage_data, "total_output_tokens", None)
                if out_tok is None:
                    out_tok = getattr(usage_data, "output_tokens", None)
                tot_tok = getattr(usage_data, "total_tokens", None)

            # Validar que los valores sean enteros reales (evita auto-atributos de MagicMock)
            in_int = in_tok if isinstance(in_tok, int) and not isinstance(in_tok, bool) else None
            out_int = out_tok if isinstance(out_tok, int) and not isinstance(out_tok, bool) else None
            tot_int = tot_tok if isinstance(tot_tok, int) and not isinstance(tot_tok, bool) else None

            if in_int is not None or out_int is not None or tot_int is not None:
                usage = AudioTranscriptionUsage(
                    input_tokens=in_int,
                    output_tokens=out_int,
                    total_tokens=tot_int,
                )

        return full_text, segments, detected_language, usage


gemini_client = GeminiClient()
