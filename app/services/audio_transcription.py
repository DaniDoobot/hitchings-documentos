import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple

from fastapi import UploadFile

from app.core.config import settings
from app.core.logging import logger
from app.schemas.audio import (
    AudioTranscribeResponse,
    AudioTranscriptionUsage,
    SpeakerSegment,
)
from app.services.gemini_client import (
    GeminiClient,
    GeminiEmptyResponseError,
    GeminiProviderError,
    gemini_client,
)
from app.services.media_service import MediaSegment, media_service
from app.utils.text import calculate_text_metrics, normalize_text

CHUNK_SIZE = 64 * 1024  # 64 KB por fragmento de streaming


class UnsupportedAudioFormatError(Exception):
    """Excepción para formatos de audio no permitidos (HTTP 415)."""

    def __init__(self, extension: str):
        self.extension = extension
        super().__init__(
            f"Formato de audio no permitido: '.{extension}'. Formatos soportados: mp3, wav, m4a, aac, ogg, flac, webm, mp4."
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
    """Servicio de validación, ingesta en streaming, segmentación automática y transcripción con Gemini."""

    ALLOWED_AUDIO_EXTENSIONS: set[str] = {
        "mp3",
        "wav",
        "m4a",
        "aac",
        "ogg",
        "flac",
        "webm",
        "mp4",
    }

    AUDIO_MIME_MAPPING: Dict[str, str] = {
        "mp3": "audio/mp3",
        "wav": "audio/wav",
        "m4a": "audio/m4a",
        "aac": "audio/aac",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
        "webm": "audio/webm",
        "mp4": "video/mp4",
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
        """Comprobación básica de firmas de cabecera de audio/vídeo para evitar archivos falsos."""
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
        elif extension in ("m4a", "mp4") and b"ftyp" not in initial_bytes[:16]:
            raise CorruptedAudioFileError(f"El archivo no es un documento {extension.upper()} válido (firma ftyp no encontrada).")

    async def save_stream_to_temp_file(
        self, file: UploadFile, extension: str, max_bytes: int
    ) -> Tuple[str, int]:
        """
        Lee el UploadFile en bloques y lo escribe directamente a un fichero
        temporal anónimo en disco, abortando inmediatamente si supera max_bytes.
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

    def _aggregate_usage(self, usages: List[AudioTranscriptionUsage | None]) -> AudioTranscriptionUsage | None:
        """
        Suma estrictamente los tokens enteros reales devueltos por cada llamada a Gemini.
        Si ningún fragmento devolvió métricas de tokens, retorna None.
        """
        total_in = 0
        total_out = 0
        total_all = 0
        has_in = False
        has_out = False
        has_all = False

        for u in usages:
            if u is None:
                continue
            if isinstance(u.input_tokens, int):
                total_in += u.input_tokens
                has_in = True
            if isinstance(u.output_tokens, int):
                total_out += u.output_tokens
                has_out = True
            if isinstance(u.total_tokens, int):
                total_all += u.total_tokens
                has_all = True

        if not (has_in or has_out or has_all):
            return None

        return AudioTranscriptionUsage(
            input_tokens=total_in if has_in else None,
            output_tokens=total_out if has_out else None,
            total_tokens=total_all if has_all else None,
        )

    async def process_and_transcribe(
        self,
        file: UploadFile,
        mode: str = "verbatim",
        diarization: bool = False,
        language: str | None = None,
    ) -> AudioTranscribeResponse:
        """
        Orquesta la validación, almacenamiento temporal seguro, inspección de duración,
        segmentación automática cuando exceda los límites single-pass, transcripción
        secuencial y borrado exhaustivo de recursos locales y remotos.
        """
        start_time = time.perf_counter()
        raw_filename = file.filename
        filename = self.sanitize_filename(raw_filename)
        extension = self.get_extension(filename)

        # 1. Validar extensión permitida
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

        # 3. Guardado en fichero temporal seguro con corte por tamaño (1 GB)
        temp_path, size_bytes = await self.save_stream_to_temp_file(
            file=file,
            extension=extension,
            max_bytes=settings.max_audio_size_bytes,
        )

        extracted_audio_path: str | None = None
        master_flac_path: str | None = None
        chunks_to_cleanup: List[str] = []
        remote_files_to_cleanup: List[str] = []
        warnings: List[str] = []

        try:
            # 4. Inspección multimedia con ffprobe (para todos los formatos: MP4 y audio)
            media_info = media_service.inspect_media(temp_path)

            # 5. Validación del límite máximo total de duración (8 horas)
            media_service.validate_total_duration(media_info.duration_seconds)

            # 6. Comprobar si requiere segmentación automática
            needs_segmentation = media_service.needs_segmentation(
                media_info.duration_seconds, diarization=diarization
            )

            if not needs_segmentation:
                # -------------------------------------------------------------
                # FLUJO CORTO (SINGLE-PASS): 1 sola llamada sin segmentación
                # -------------------------------------------------------------
                if extension == "mp4":
                    flac_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".flac")
                    flac_temp.close()
                    extracted_audio_path = flac_temp.name
                    media_service.extract_audio(temp_path, extracted_audio_path)
                    upload_path = extracted_audio_path
                    upload_mime = "audio/flac"
                else:
                    upload_path = temp_path
                    upload_mime = mime_type

                remote_file = self.client.upload_file(upload_path, mime_type=upload_mime)
                remote_name = getattr(remote_file, "name", None)
                if remote_name:
                    remote_files_to_cleanup.append(remote_name)

                transcribe_result = self.client.transcribe_audio(
                    remote_file=remote_file,
                    mode=mode,
                    diarization=diarization,
                    language=language,
                )

                if len(transcribe_result) >= 4:
                    raw_text, segments, detected_language, usage = transcribe_result[:4]
                else:
                    raw_text, segments, detected_language = transcribe_result
                    usage = None

                normalized_text = normalize_text(raw_text)
                word_count, character_count = calculate_text_metrics(normalized_text)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                logger.info(
                    "Transcripción de audio completada | Ext: %s | Tamaño: %d B | Modo: %s | Diarización: %s | Duración: %s s | Tiempo: %.2f ms",
                    extension,
                    size_bytes,
                    mode,
                    str(diarization),
                    str(media_info.duration_seconds),
                    elapsed_ms,
                )

                return AudioTranscribeResponse(
                    filename=filename,
                    extension=extension,
                    content_type=mime_type,
                    size_bytes=size_bytes,
                    transcription_model=settings.GEMINI_TRANSCRIPTION_MODEL,
                    mode=mode,
                    diarization=diarization,
                    language=language,
                    detected_language=detected_language,
                    text=normalized_text,
                    word_count=word_count,
                    character_count=character_count,
                    segments=segments,
                    warnings=warnings,
                    usage=usage,
                    was_segmented=False,
                    segment_count=1,
                    duration_seconds=media_info.duration_seconds,
                )

            # -----------------------------------------------------------------
            # FLUJO LARGO (SEGMENTADO): División y llamadas secuenciales
            # -----------------------------------------------------------------
            logger.info(
                "Grabación de larga duración detectada (%s s) | Iniciando procesamiento segmentado",
                str(media_info.duration_seconds),
            )

            # Paso 1: Generar master FLAC homogéneo mono 16 kHz (una sola vez)
            master_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".flac")
            master_temp.close()
            master_flac_path = master_temp.name

            if extension == "mp4":
                media_service.extract_audio(temp_path, master_flac_path)
            else:
                media_service.convert_to_master_flac(temp_path, master_flac_path)

            # Paso 2: Detección oportunista de silencios (best-effort)
            detected_silences = media_service.detect_silences(master_flac_path)

            # Paso 3: Planificar segmentos continuos sin huecos ni solapamientos
            total_dur = media_info.duration_seconds or 0.0
            planned_segments = media_service.plan_segments(
                total_duration=total_dur,
                diarization=diarization,
                detected_silences=detected_silences,
            )

            chunk_texts: List[str] = []
            all_speaker_segments: List[SpeakerSegment] = []
            all_usages: List[AudioTranscriptionUsage | None] = []
            detected_lang_final: str | None = None

            # Paso 4: Transcripción secuencial de cada fragmento
            for seg in planned_segments:
                seg_chunk_file = tempfile.NamedTemporaryFile(delete=False, suffix=".flac")
                seg_chunk_file.close()
                seg_chunk_path = seg_chunk_file.name
                chunks_to_cleanup.append(seg_chunk_path)

                # Extraer fragmento FLAC del master
                media_service.create_segment_chunk(
                    master_flac_path=master_flac_path,
                    start_seconds=seg.start_seconds,
                    duration_seconds=seg.duration_seconds,
                    output_chunk_path=seg_chunk_path,
                )

                chunk_remote_name: str | None = None
                try:
                    # Subir SOLO el fragmento a Gemini Files API
                    chunk_remote_file = self.client.upload_file(seg_chunk_path, mime_type="audio/flac")
                    chunk_remote_name = getattr(chunk_remote_file, "name", None)
                    if chunk_remote_name:
                        remote_files_to_cleanup.append(chunk_remote_name)

                    # Transcribir fragmento
                    transcribe_chunk_res = self.client.transcribe_audio(
                        remote_file=chunk_remote_file,
                        mode=mode,
                        diarization=diarization,
                        language=language,
                    )

                    if len(transcribe_chunk_res) >= 4:
                        c_text, c_segments, c_lang, c_usage = transcribe_chunk_res[:4]
                    else:
                        c_text, c_segments, c_lang = transcribe_chunk_res
                        c_usage = None

                    if not detected_lang_final and c_lang:
                        detected_lang_final = c_lang

                    all_usages.append(c_usage)

                    # Formatear el contenido del segmento
                    if diarization:
                        seg_header = f"[Segmento {seg.index}]"
                        chunk_texts.append(f"{seg_header}\n{c_text.strip()}")
                        # Prefijar speaker de cada segmento para trazabilidad limpia
                        for spk in c_segments:
                            all_speaker_segments.append(
                                SpeakerSegment(
                                    speaker=f"Seg{seg.index}-{spk.speaker}",
                                    text=spk.text,
                                )
                            )
                    else:
                        chunk_texts.append(c_text.strip())

                except Exception as err:
                    logger.error(
                        "Error durante la transcripción del segmento %d/%d: %s",
                        seg.index,
                        len(planned_segments),
                        type(err).__name__,
                    )
                    # En caso de fallo en cualquier segmento, abortar sin devolver transcripciones incompletas
                    raise GeminiProviderError(
                        "No se ha podido completar la transcripción de la grabación. Puedes volver a intentarlo."
                    ) from err
                finally:
                    # Borrado inmediato del archivo remoto de Gemini del fragmento procesado
                    if chunk_remote_name:
                        self.client.delete_remote_file(chunk_remote_name)
                        if chunk_remote_name in remote_files_to_cleanup:
                            remote_files_to_cleanup.remove(chunk_remote_name)

                    # Borrado local inmediato del fragmento procesado
                    Path(seg_chunk_path).unlink(missing_ok=True)
                    if seg_chunk_path in chunks_to_cleanup:
                        chunks_to_cleanup.remove(seg_chunk_path)

            # Paso 5: Consolidación determinista (Stitching sin IA)
            consolidated_raw = "\n\n".join(t for t in chunk_texts if t.strip())
            if not consolidated_raw.strip():
                raise GeminiEmptyResponseError(
                    "El modelo de IA procesó la grabación pero no detectó contenido hablado transcribible."
                )

            normalized_text = normalize_text(consolidated_raw)
            word_count, character_count = calculate_text_metrics(normalized_text)

            # Paso 6: Advertencias contextuales
            if diarization:
                warnings.append(
                    "En grabaciones largas procesadas por segmentos, la numeración de los interlocutores puede reiniciarse entre segmentos."
                )

            # Paso 7: Agregación de métricas de tokens
            aggregated_usage = self._aggregate_usage(all_usages)

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "Transcripción segmentada completada con éxito | Ext: %s | Tamaño: %d B | Segmentos: %d | Palabras: %d | Tiempo: %.2f ms",
                extension,
                size_bytes,
                len(planned_segments),
                word_count,
                elapsed_ms,
            )

            return AudioTranscribeResponse(
                filename=filename,
                extension=extension,
                content_type=mime_type,
                size_bytes=size_bytes,
                transcription_model=settings.GEMINI_TRANSCRIPTION_MODEL,
                mode=mode,
                diarization=diarization,
                language=language,
                detected_language=detected_lang_final,
                text=normalized_text,
                word_count=word_count,
                character_count=character_count,
                segments=all_speaker_segments,
                warnings=warnings,
                usage=aggregated_usage,
                was_segmented=True,
                segment_count=len(planned_segments),
                duration_seconds=media_info.duration_seconds,
            )

        finally:
            # Borrado exhaustivo y garantizado de todos los recursos (happy path o error)
            for remote_name in remote_files_to_cleanup:
                self.client.delete_remote_file(remote_name)

            for chunk_path in chunks_to_cleanup:
                Path(chunk_path).unlink(missing_ok=True)

            if master_flac_path:
                Path(master_flac_path).unlink(missing_ok=True)

            if extracted_audio_path:
                Path(extracted_audio_path).unlink(missing_ok=True)

            if temp_path:
                Path(temp_path).unlink(missing_ok=True)


audio_transcription_service = AudioTranscriptionService()
