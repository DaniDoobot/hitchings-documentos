from typing import List, Tuple
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import settings
from app.core.logging import logger
from app.schemas.audio import SpeakerSegment


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
        if not settings.GEMINI_API_KEY:
            raise GeminiConfigurationError(
                "La clave GEMINI_API_KEY no está configurada en las variables de entorno."
            )
        if self._client is None:
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
        diarization: bool = True,
    ) -> Tuple[str, List[SpeakerSegment]]:
        """
        Invoca el modelo de transcripción de Gemini.
        Retorna (texto_completo, lista_segmentos_hablantes).
        """
        client = self.get_client()

        # Determinar modo oficial
        mode_enum = (
            types.AudioTranscriptionConfigMode.VERBATIM
            if mode == "verbatim"
            else types.AudioTranscriptionConfigMode.SMART
        )

        # Diarización solo es compatible con VERBATIM
        use_diarization = diarization if mode == "verbatim" else False

        transcription_config = types.AudioTranscriptionConfig(
            mode=mode_enum,
            diarization=use_diarization,
        )

        generate_config = types.GenerateContentConfig(
            audio_transcription_config=transcription_config,
        )

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_TRANSCRIPTION_MODEL,
                contents=[remote_file],
                config=generate_config,
            )
        except APIError as exc:
            logger.error("Error retornado por Gemini durante la transcripción: %s", exc)
            raise GeminiProviderError("El proveedor de transcripción devolvió un error al procesar el audio.") from exc
        except Exception as exc:
            logger.error("Fallo de comunicación con Gemini: %s", exc, exc_info=True)
            raise GeminiProviderError("No se pudo completar la transcripción con el proveedor de IA.") from exc

        if not response or not response.text:
            logger.warning("Gemini no devolvió texto de transcripción.")
            raise GeminiEmptyResponseError(
                "El modelo de IA procesó el audio pero no detectó contenido hablado transcribible."
            )

        full_text = response.text.strip()
        segments: List[SpeakerSegment] = []

        # Extraer información de hablantes si se devolvió en la estructura de candidatos
        if use_diarization and response.candidates:
            for candidate in response.candidates:
                if not candidate.content or not candidate.content.parts:
                    continue
                for part in candidate.content.parts:
                    at = getattr(part, "audio_transcription", None)
                    if at:
                        speaker = getattr(at, "speaker_label", None)
                        seg_text = getattr(at, "text", None)
                        if speaker and seg_text:
                            segments.append(
                                SpeakerSegment(
                                    speaker=str(speaker),
                                    text=str(seg_text).strip(),
                                )
                            )

        return full_text, segments


gemini_client = GeminiClient()
