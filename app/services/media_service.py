import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.logging import logger

MAX_AUDIO_DURATION_SECONDS = 3600.0  # 1 hora
MAX_DIARIZATION_DURATION_SECONDS = 1800.0  # 30 minutos


class MediaProcessingError(Exception):
    """Error al procesar el archivo multimedia mediante FFmpeg/ffprobe."""

    def __init__(self, message: str = "No se pudo procesar la grabación multimedia."):
        super().__init__(message)


class NoAudioTrackError(Exception):
    """Excepción cuando el contenedor multimedia no contiene ninguna pista de audio."""

    def __init__(self, message: str = "El archivo MP4 no contiene una pista de audio que pueda transcribirse."):
        super().__init__(message)


class CorruptedMediaError(Exception):
    """Excepción cuando el archivo multimedia está dañado o no puede ser leído por ffprobe."""

    def __init__(self, message: str = "El archivo de vídeo no ha podido procesarse."):
        super().__init__(message)


class MediaDurationExceededError(Exception):
    """Excepción cuando la duración de la grabación excede el límite soportado por el pipeline."""

    def __init__(self, message: str):
        super().__init__(message)


@dataclass
class MediaInspectionResult:
    """Metadatos extraídos de la inspección del contenedor multimedia con ffprobe."""
    has_audio: bool
    audio_codec: str | None = None
    duration_seconds: float | None = None
    format_name: str | None = None


class MediaService:
    """
    Servicio de inspección y extracción de pistas de audio para archivos de vídeo (MP4)
    utilizando herramientas del sistema (ffprobe y ffmpeg) mediante llamadas seguras por lista de argumentos.
    """

    def inspect_media(self, file_path: str) -> MediaInspectionResult:
        """
        Inspecciona el archivo multimedia con ffprobe para verificar integridad,
        existencia de pista de audio y duración del archivo.
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration,format_name:stream=codec_type,codec_name",
            "-of", "json",
            file_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except FileNotFoundError as err:
            logger.error("ffprobe no se encuentra disponible en el sistema.")
            raise MediaProcessingError("El motor de análisis multimedia (ffprobe) no está disponible en el servidor.") from err
        except subprocess.TimeoutExpired as err:
            logger.error("Tiempo de espera agotado al inspeccionar archivo multimedia con ffprobe.")
            raise MediaProcessingError("Tiempo de espera agotado al inspeccionar la grabación de vídeo.") from err
        except Exception as err:
            logger.error("Error inesperado al ejecutar ffprobe: %s", type(err).__name__)
            raise MediaProcessingError("Error al analizar la estructura del archivo de vídeo.") from err

        if result.returncode != 0:
            logger.warning("ffprobe devolvió código de error %d", result.returncode)
            raise CorruptedMediaError("El archivo de vídeo no ha podido procesarse.")

        try:
            data = json.loads(result.stdout)
        except Exception as err:
            logger.warning("Error al decodificar salida JSON de ffprobe: %s", err)
            raise CorruptedMediaError("El archivo de vídeo no ha podido procesarse.")

        streams = data.get("streams", [])
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if not audio_stream:
            logger.info("El contenedor de vídeo no contiene ninguna pista de audio.")
            raise NoAudioTrackError("El archivo MP4 no contiene una pista de audio que pueda transcribirse.")

        audio_codec = audio_stream.get("codec_name")

        duration_seconds = None
        format_info = data.get("format", {})
        raw_duration = format_info.get("duration")
        if raw_duration:
            try:
                duration_seconds = float(raw_duration)
            except (ValueError, TypeError):
                duration_seconds = None

        return MediaInspectionResult(
            has_audio=True,
            audio_codec=audio_codec,
            duration_seconds=duration_seconds,
            format_name=format_info.get("format_name"),
        )

    def validate_duration(self, duration_seconds: float | None, diarization: bool = False) -> None:
        """
        Verifica que la duración de la grabación no sobrepase los límites operativos vigentes.
        """
        if duration_seconds is None:
            return

        if diarization and duration_seconds > MAX_DIARIZATION_DURATION_SECONDS:
            raise MediaDurationExceededError(
                "La grabación supera la duración máxima admitida para diarización (30 minutos). "
                "Desactive la diarización para grabaciones de hasta 1 hora o procese un archivo de menor duración."
            )

        if duration_seconds > MAX_AUDIO_DURATION_SECONDS:
            raise MediaDurationExceededError(
                "La grabación supera la duración admitida actualmente. "
                "El soporte automático para grabaciones largas se incorporará mediante procesamiento por segmentos."
            )

    def extract_audio(self, input_video_path: str, output_audio_path: str) -> None:
        """
        Extrae la pista de audio de un archivo de vídeo y la normaliza a FLAC mono 16 kHz.
        FLAC es lossless, ligero y nativamente compatible con el transcriptor de Gemini.
        """
        cmd = [
            "ffmpeg",
            "-y",
            "-v", "error",
            "-i", input_video_path,
            "-vn",
            "-c:a", "flac",
            "-ar", "16000",
            "-ac", "1",
            output_audio_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        except FileNotFoundError as err:
            logger.error("ffmpeg no se encuentra disponible en el sistema.")
            raise MediaProcessingError("El motor de extracción de audio (ffmpeg) no está disponible en el servidor.") from err
        except subprocess.TimeoutExpired as err:
            logger.error("Tiempo de espera agotado al extraer audio con ffmpeg.")
            raise MediaProcessingError("Tiempo de espera agotado al extraer la pista de audio del vídeo.") from err
        except Exception as err:
            logger.error("Error inesperado al ejecutar ffmpeg: %s", type(err).__name__)
            raise MediaProcessingError("Error al extraer la pista de audio del vídeo.") from err

        if result.returncode != 0:
            logger.warning("ffmpeg devolvió código de error %d durante la extracción", result.returncode)
            raise MediaProcessingError("No se pudo extraer la pista de audio de la grabación de vídeo.")

        if not Path(output_audio_path).is_file() or Path(output_audio_path).stat().st_size == 0:
            logger.warning("El archivo de audio extraído no existe o tiene 0 bytes.")
            raise MediaProcessingError("La extracción de audio no generó contenido utilizable.")


media_service = MediaService()
