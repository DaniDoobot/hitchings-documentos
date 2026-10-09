import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.core.logging import logger

# Límites de un solo pase (single-pass)
SINGLE_PASS_STANDARD_MAX_SECONDS = 3600.0  # 1 hora
SINGLE_PASS_DIARIZATION_MAX_SECONDS = 1800.0  # 30 minutos

# Parámetros para segmentación (chunking)
STANDARD_CHUNK_TARGET_SECONDS = 2700.0  # 45 minutos objetivo
STANDARD_CHUNK_MAX_SECONDS = 3540.0  # 59 minutos margen de seguridad (< 1 hora)
DIARIZATION_CHUNK_TARGET_SECONDS = 1500.0  # 25 minutos objetivo
DIARIZATION_CHUNK_MAX_SECONDS = 1740.0  # 29 minutos margen de seguridad (< 30 minutos)


class MediaProcessingError(Exception):
    """Error al procesar el archivo multimedia mediante FFmpeg/ffprobe."""

    def __init__(self, message: str = "No se pudo procesar la grabación multimedia."):
        super().__init__(message)


class NoAudioTrackError(Exception):
    """Excepción cuando el contenedor multimedia no contiene ninguna pista de audio."""

    def __init__(self, message: str = "El archivo multimedia no contiene una pista de audio que pueda transcribirse."):
        super().__init__(message)


class CorruptedMediaError(Exception):
    """Excepción cuando el archivo multimedia está dañado o no puede ser leído por ffprobe."""

    def __init__(self, message: str = "El archivo multimedia no ha podido procesarse."):
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


@dataclass
class MediaSegment:
    """Definición matemática y temporal de un fragmento de audio para procesamiento seguro."""

    index: int
    start_seconds: float
    end_seconds: float
    duration_seconds: float


class MediaService:
    """
    Servicio de inspección, normalización y segmentación de medios (audio y vídeo)
    utilizando herramientas del sistema (ffprobe y ffmpeg) mediante llamadas seguras por lista de argumentos.
    """

    def inspect_media(self, file_path: str) -> MediaInspectionResult:
        """
        Inspecciona el archivo multimedia (vídeo o audio) con ffprobe para verificar
        integridad, existencia de pista de audio y duración del archivo.
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
        except FileNotFoundError:
            logger.warning("ffprobe no se encuentra disponible en el sistema anfitrión. Continuando sin metadatos de duración.")
            return MediaInspectionResult(
                has_audio=True,
                audio_codec=None,
                duration_seconds=None,
                format_name=None,
            )
        except subprocess.TimeoutExpired as err:
            logger.error("Tiempo de espera agotado al inspeccionar archivo multimedia con ffprobe.")
            raise MediaProcessingError("Tiempo de espera agotado al inspeccionar la grabación.") from err
        except Exception as err:
            logger.error("Error inesperado al ejecutar ffprobe: %s", type(err).__name__)
            raise MediaProcessingError("Error al analizar la estructura del archivo multimedia.") from err

        if result.returncode != 0:
            logger.warning("ffprobe devolvió código de error %d", result.returncode)
            raise CorruptedMediaError("El archivo multimedia no ha podido procesarse.")

        try:
            data = json.loads(result.stdout)
        except Exception as err:
            logger.warning("Error al decodificar salida JSON de ffprobe: %s", err)
            raise CorruptedMediaError("El archivo multimedia no ha podido procesarse.")

        streams = data.get("streams", [])
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if not audio_stream:
            logger.info("El contenedor no contiene ninguna pista de audio.")
            raise NoAudioTrackError("El archivo multimedia no contiene una pista de audio que pueda transcribirse.")

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

    def validate_total_duration(self, duration_seconds: float | None) -> None:
        """
        Verifica que la duración de la grabación no sobrepase el límite operativo total de la aplicación (8 horas por defecto).
        """
        if duration_seconds is None:
            return

        max_allowed = settings.max_media_duration_seconds
        if duration_seconds > max_allowed:
            hours = int(settings.MAX_MEDIA_DURATION_HOURS)
            raise MediaDurationExceededError(
                f"La grabación supera la duración máxima admitida actualmente de {hours} horas."
            )

    def validate_duration(self, duration_seconds: float | None, diarization: bool = False) -> None:
        """
        Método de compatibilidad con 8A. En 8B valida que no se supere el límite total operativo de 8 horas.
        """
        self.validate_total_duration(duration_seconds)

    def needs_segmentation(self, duration_seconds: float | None, diarization: bool = False) -> bool:
        """
        Determina si un archivo requiere división en fragmentos por superar el umbral de una única llamada a Gemini.
        """
        if duration_seconds is None:
            return False

        single_pass_max = SINGLE_PASS_DIARIZATION_MAX_SECONDS if diarization else SINGLE_PASS_STANDARD_MAX_SECONDS
        return duration_seconds > single_pass_max

    def detect_silences(
        self,
        file_path: str,
        min_duration: float = 0.5,
        noise_threshold: str = "-30dB",
    ) -> list[tuple[float, float]]:
        """
        Detecta silencios en el archivo de audio con FFmpeg silencedetect.
        Es una optimización best-effort: si falla o agota el tiempo de espera, retorna una lista vacía
        sin interrumpir el pipeline de transcripción.
        """
        cmd = [
            "ffmpeg",
            "-nostdin",
            "-v", "info",
            "-i", file_path,
            "-af", f"silencedetect=noise={noise_threshold}:d={min_duration}",
            "-f", "null",
            "-",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except Exception as err:
            logger.warning("Fallo no bloqueante al detectar silencios con FFmpeg: %s", err)
            return []

        silences: list[tuple[float, float]] = []
        current_start: float | None = None

        # FFmpeg silencedetect emite logs en stderr
        for line in result.stderr.splitlines():
            start_match = re.search(r"silence_start:\s*([\d\.]+)", line)
            if start_match:
                try:
                    current_start = float(start_match.group(1))
                except ValueError:
                    current_start = None
                continue

            end_match = re.search(r"silence_end:\s*([\d\.]+)", line)
            if end_match and current_start is not None:
                try:
                    end_val = float(end_match.group(1))
                    silences.append((current_start, end_val))
                except ValueError:
                    pass
                current_start = None

        return silences

    def plan_segments(
        self,
        total_duration: float,
        diarization: bool = False,
        detected_silences: list[tuple[float, float]] | None = None,
    ) -> list[MediaSegment]:
        """
        Calcula una partición temporal determinista y ordenada del archivo.
        Garantiza:
        - Cobertura exacta de 0 a total_duration sin huecos ni solapamientos.
        - Cada segmento respeta el límite máximo seguro por llamada.
        - Si existen silencios detectados, realiza cortes óptimos de forma oportunista.
        """
        single_pass_max = SINGLE_PASS_DIARIZATION_MAX_SECONDS if diarization else SINGLE_PASS_STANDARD_MAX_SECONDS

        if total_duration <= single_pass_max:
            return [
                MediaSegment(
                    index=1,
                    start_seconds=0.0,
                    end_seconds=round(total_duration, 3),
                    duration_seconds=round(total_duration, 3),
                )
            ]

        target_duration = DIARIZATION_CHUNK_TARGET_SECONDS if diarization else STANDARD_CHUNK_TARGET_SECONDS
        max_duration = DIARIZATION_CHUNK_MAX_SECONDS if diarization else STANDARD_CHUNK_MAX_SECONDS

        segments: list[MediaSegment] = []
        current_start = 0.0
        seg_index = 1
        silences = detected_silences or []

        while current_start < total_duration:
            remaining = total_duration - current_start
            # Si lo que resta cabe de forma segura en un último segmento dentro de max_duration:
            if remaining <= max_duration:
                segments.append(
                    MediaSegment(
                        index=seg_index,
                        start_seconds=round(current_start, 3),
                        end_seconds=round(total_duration, 3),
                        duration_seconds=round(remaining, 3),
                    )
                )
                break

            target_end = current_start + target_duration
            chosen_end = target_end

            # Buscar un silencio cercano en una ventana de tolerancia razonable
            # tal que el corte no exceda max_duration y no sea excesivamente corto
            best_silence: float | None = None
            best_distance = float("inf")

            for s_start, s_end in silences:
                s_mid = (s_start + s_end) / 2.0
                if (current_start + 60.0) < s_mid <= (current_start + max_duration):
                    distance = abs(s_mid - target_end)
                    if distance <= 180.0 and distance < best_distance:
                        best_distance = distance
                        best_silence = s_mid

            if best_silence is not None:
                chosen_end = best_silence

            # Garantizar que jamás se supere max_duration
            if chosen_end > (current_start + max_duration):
                chosen_end = current_start + max_duration

            # Garantizar que no sobrepase total_duration
            if chosen_end >= total_duration:
                chosen_end = total_duration

            duration = chosen_end - current_start
            segments.append(
                MediaSegment(
                    index=seg_index,
                    start_seconds=round(current_start, 3),
                    end_seconds=round(chosen_end, 3),
                    duration_seconds=round(duration, 3),
                )
            )
            current_start = chosen_end
            seg_index += 1

        return segments

    def extract_audio(self, input_video_path: str, output_audio_path: str) -> None:
        """
        Extrae la pista de audio de un archivo de vídeo MP4 y la normaliza a FLAC mono 16 kHz.
        FLAC es lossless, ligero y nativamente compatible con el transcriptor de Gemini.
        """
        cmd = [
            "ffmpeg",
            "-nostdin",
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
                timeout=300,
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

    def convert_to_master_flac(self, input_audio_path: str, output_flac_path: str) -> None:
        """
        Normaliza cualquier archivo de audio de entrada a FLAC mono 16 kHz cuando requiere segmentación.
        Permite que todos los chunks subsiguientes se extraigan del mismo audio master homogéneo.
        """
        cmd = [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-v", "error",
            "-i", input_audio_path,
            "-vn",
            "-c:a", "flac",
            "-ar", "16000",
            "-ac", "1",
            output_flac_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
        except FileNotFoundError as err:
            logger.error("ffmpeg no se encuentra disponible en el sistema.")
            raise MediaProcessingError("El motor de conversión de audio (ffmpeg) no está disponible en el servidor.") from err
        except subprocess.TimeoutExpired as err:
            logger.error("Tiempo de espera agotado al normalizar audio a master FLAC.")
            raise MediaProcessingError("Tiempo de espera agotado al normalizar el audio de la grabación.") from err
        except Exception as err:
            logger.error("Error inesperado al ejecutar ffmpeg: %s", type(err).__name__)
            raise MediaProcessingError("Error al normalizar el archivo de audio para su segmentación.") from err

        if result.returncode != 0:
            logger.warning("ffmpeg devolvió código de error %d al crear master FLAC", result.returncode)
            raise MediaProcessingError("No se pudo normalizar el archivo de audio para su segmentación.")

        if not Path(output_flac_path).is_file() or Path(output_flac_path).stat().st_size == 0:
            logger.warning("El master FLAC no existe o tiene 0 bytes.")
            raise MediaProcessingError("La normalización de audio no generó contenido utilizable.")

    def create_segment_chunk(
        self,
        master_flac_path: str,
        start_seconds: float,
        duration_seconds: float,
        output_chunk_path: str,
    ) -> None:
        """
        Extrae un fragmento de audio FLAC a partir del master FLAC mediante corte por tiempo exacto.
        """
        cmd = [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-v", "error",
            "-ss", str(start_seconds),
            "-t", str(duration_seconds),
            "-i", master_flac_path,
            "-c:a", "flac",
            "-ar", "16000",
            "-ac", "1",
            output_chunk_path,
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
            raise MediaProcessingError("El motor de segmentación de audio (ffmpeg) no está disponible en el servidor.") from err
        except subprocess.TimeoutExpired as err:
            logger.error("Tiempo de espera agotado al generar fragmento de audio con ffmpeg.")
            raise MediaProcessingError("Tiempo de espera agotado al segmentar la grabación de audio.") from err
        except Exception as err:
            logger.error("Error inesperado al ejecutar ffmpeg: %s", type(err).__name__)
            raise MediaProcessingError("Error al segmentar el archivo de audio.") from err

        if result.returncode != 0:
            logger.warning("ffmpeg devolvió código de error %d al crear fragmento", result.returncode)
            raise MediaProcessingError("No se pudo generar un fragmento de la grabación para su transcripción.")

        if not Path(output_chunk_path).is_file() or Path(output_chunk_path).stat().st_size == 0:
            logger.warning("El fragmento FLAC no existe o tiene 0 bytes.")
            raise MediaProcessingError("La creación del fragmento de audio no generó contenido utilizable.")


media_service = MediaService()
