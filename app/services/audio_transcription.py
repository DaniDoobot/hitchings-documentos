import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Tuple

from fastapi import UploadFile

from app.core.config import settings
from app.core.logging import logger
from app.schemas.audio import AudioTranscribeResponse, SpeakerSegment
from app.services.gemini_client import (
    GeminiClient,
    GeminiEmptyResponseError,
    GeminiProviderError,
    gemini_client,
)
from app.utils.text import calculate_text_metrics, normalize_text

CHUNK_SIZE = 64 * 1024  # 64 KB por fragmento


class UnsupportedAudioFormatError(Exception):
    """Excepción para formatos de audio no permitidos (HTTP 415)."""

    def __init__(self, extension: str):
        self.extension = extension
        super().__init__(
            f"Formato de audio no permitido: '.{extension}'. Formatos soportados: mp3, wav, m4a, aac, ogg, flac, webm."
        )


class AudioFileSizeExceededError(Exception):
    """Excepción cuando el audio excede el límite máximo permitido (HTTP 413)."""

    def __init__(self, size_bytes: int, max_bytes: int):
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
        max_mb = max_bytes / (1024 * 1024)
        super().__init__(
            f"El archivo de audio excede el límite máximo permitido de {max_mb:.0f} MB."
        )


class EmptyAudioFileError(Exception):
    """Excepción cuando el archivo de audio está vacío (HTTP 400)."""

    def __init__(self):
        super().__init__("El archivo de audio enviado está vacío (0 bytes).")


class IncompatibleAudioParamsError(Exception):
    """Excepción para combinaciones incompatibles de parámetros (HTTP 400)."""

    def __init__(self, message: str):
        super().__init__(message)


class CorruptedAudioFileError(Exception):
    """Excepción para archivos de audio dañados o sin cabecera válida (HTTP 400)."""

    def __init__(self, message: str = "El archivo de audio está dañado o no tiene una estructura válida."):
        super().__init__(message)


class AudioTranscriptionService:
    """Servicio de validación, ingesta en streaming y transcripción de audio con Gemini."""

    ALLOWED_AUDIO_EXTENSIONS: set[str] = {
        "mp3",
        "wav",
        "m4a",
        "aac",
        "ogg",
        "flac",
        "webm",
    }

    AUDIO_MIME_MAPPING: Dict[str, str] = {
        "mp3": "audio/mp3",
        "wav": "audio/wav",
        "m4a": "audio/m4a",
        "aac": "audio/aac",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
        "webm": "audio/webm",
    }

    def __init__(self, client: GeminiClient | None = None):
        self._client = client

    @property
    def client(self) -> GeminiClient:
        return self._client if self._client is not None else gemini_client

    def sanitize_filename(self, filename: str | None) -> str:
        """Sanitiza el nombre del archivo eliminando directorios."""
        if not filename:
            return "audio_sin_nombre"
        return Path(filename).name

    def get_extension(self, filename: str) -> str:
        """Obtiene la extensión en minúsculas."""
        parts = filename.rsplit(".", 1)
        if len(parts) > 1:
            return parts[1].lower()
        return ""

    def validate_audio_header(self, initial_bytes: bytes, extension: str) -> None:
        """Comprobación básica de firmas de cabecera de audio para evitar archivos falsos."""
        if len(initial_bytes) < 4:
            raise CorruptedAudioFileError("El archivo de audio es demasiado pequeño o está corrupto.")

        if extension == "wav" and not (initial_bytes.startswith(b"RIFF") and b"WAVE" in initial_bytes[:16]):
            raise CorruptedAudioFileError("El archivo no es un documento WAV válido (firma RIFF/WAVE no encontrada).")
        elif extension == "flac" and not initial_bytes.startswith(b"fLaC"):
            raise CorruptedAudioFileError("El archivo no es un documento FLAC válido (firma fLaC no encontrada).")
        elif extension == "ogg" and not initial_bytes.startswith(b"OggS"):
            raise CorruptedAudioFileError("El archivo no es un documento OGG válido (firma OggS no encontrada).")
        elif extension == "webm" and not initial_bytes.startswith(b"\x1a\x45\xdf\xa3"):
            raise CorruptedAudioFileError("El archivo no es un documento WebM válido (firma EBML no encontrada).")
        elif extension == "m4a" and b"ftyp" not in initial_bytes[:16]:
            raise CorruptedAudioFileError("El archivo no es un documento M4A válido (firma ftyp no encontrada).")

    async def save_stream_to_temp_file(
        self, file: UploadFile, extension: str, max_bytes: int
    ) -> Tuple[str, int]:
        """
        Lee el UploadFile de audio en bloques y lo escribe directamente a un fichero
        temporal anónimo en el sistema, abortando inmediatamente si supera max_bytes.
        """
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}")
        temp_path = temp_file.name
        total_size = 0
        first_chunk = True

        try:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > max_bytes:
                    temp_file.close()
                    Path(temp_path).unlink(missing_ok=True)
                    raise AudioFileSizeExceededError(total_size, max_bytes)

                if first_chunk:
                    self.validate_audio_header(chunk, extension)
                    first_chunk = False

                temp_file.write(chunk)

            temp_file.close()

            if total_size == 0:
                Path(temp_path).unlink(missing_ok=True)
                raise EmptyAudioFileError()

            return temp_path, total_size
        except Exception:
            temp_file.close()
            Path(temp_path).unlink(missing_ok=True)
            raise
        finally:
            await file.close()

    async def process_and_transcribe(
        self,
        file: UploadFile,
        mode: str = "verbatim",
        diarization: bool = True,
    ) -> AudioTranscribeResponse:
        """
        Orquesta la validación, almacenamiento temporal seguro, subida a Gemini Files API,
        transcripción y posterior borrado obligatorio remoto y local.
        """
        start_time = time.perf_counter()
        raw_filename = file.filename
        filename = self.sanitize_filename(raw_filename)
        extension = self.get_extension(filename)

        # 1. Validar extensión
        if extension not in self.ALLOWED_AUDIO_EXTENSIONS:
            logger.warning("Intento de subida de audio con formato no permitido | Ext: '%s'", extension)
            raise UnsupportedAudioFormatError(extension)

        # 2. Validar combinación de parámetros
        if mode == "smart" and diarization:
            raise IncompatibleAudioParamsError(
                "La diarización de interlocutores no es compatible con el modo 'smart'. "
                "Utilice el modo 'verbatim' para diarización o establezca diarization=false."
            )

        mime_type = self.AUDIO_MIME_MAPPING.get(extension, file.content_type or "audio/mpeg")

        # 3. Guardado en fichero temporal seguro con corte por tamaño
        temp_path, size_bytes = await self.save_stream_to_temp_file(
            file=file,
            extension=extension,
            max_bytes=settings.max_audio_size_bytes,
        )

        remote_file = None
        remote_file_name = None
        warnings: list[str] = []

        try:
            # 4. Subida a Gemini Files API
            remote_file = self.client.upload_file(temp_path, mime_type=mime_type)
            remote_file_name = getattr(remote_file, "name", None)

            # 5. Transcripción con Gemini
            raw_text, segments = self.client.transcribe_audio(
                remote_file=remote_file,
                mode=mode,
                diarization=diarization,
            )

            # 6. Normalización conservadora de texto (respetando verbatim)
            normalized_text = normalize_text(raw_text)
            word_count, character_count = calculate_text_metrics(normalized_text)

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # 7. Log técnico seguro (cero nombres de archivo, cero texto, cero PII)
            logger.info(
                "Transcripción de audio completada | Ext: %s | Tamaño: %d B | Modo: %s | Diarización: %s | Palabras: %d | Tiempo: %.2f ms | Segmentos: %d",
                extension,
                size_bytes,
                mode,
                str(diarization),
                word_count,
                elapsed_ms,
                len(segments),
            )

            return AudioTranscribeResponse(
                filename=filename,
                extension=extension,
                content_type=mime_type,
                size_bytes=size_bytes,
                transcription_model=settings.GEMINI_TRANSCRIPTION_MODEL,
                mode=mode,
                diarization=diarization,
                text=normalized_text,
                word_count=word_count,
                character_count=character_count,
                segments=segments,
                warnings=warnings,
            )
        finally:
            # 8. Borrado remoto OBLIGATORIO de Gemini Files API (éxito o error)
            if remote_file_name:
                self.client.delete_remote_file(remote_file_name)

            # 9. Borrado local OBLIGATORIO del archivo temporal
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)


audio_transcription_service = AudioTranscriptionService()
