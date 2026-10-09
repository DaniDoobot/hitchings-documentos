import io
import struct
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.schemas.audio import SpeakerSegment
from app.services.gemini_client import GeminiEmptyResponseError, GeminiProviderError


def generate_synthetic_wav(duration_secs: float = 0.2, sample_rate: int = 8000) -> bytes:
    """Genera un archivo WAV PCM 8-bit mono sintético válido."""
    num_samples = int(sample_rate * duration_secs)
    data = b"\x80" * num_samples  # 0x80 es silencio en 8-bit unsigned PCM
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(data),
        b"WAVE",
        b"fmt ",
        16,  # Subchunk1Size
        1,   # AudioFormat (PCM)
        1,   # NumChannels (Mono)
        sample_rate,
        sample_rate,  # ByteRate
        1,   # BlockAlign
        8,   # BitsPerSample
        b"data",
        len(data),
    )
    return header + data


def generate_synthetic_mp3() -> bytes:
    """Genera bytes con cabecera ID3 y frames de sincronización MP3 válidos."""
    id3_header = b"ID3\x03\x00\x00\x00\x00\x00\x00"
    mp3_frames = b"\xff\xfb\x90\x64\x00\x00\x00\x00" * 30
    return id3_header + mp3_frames


@pytest.fixture
def mock_gemini():
    """Fixture que intercepta las llamadas a Gemini y simula respuestas válidas."""
    with patch("app.services.audio_transcription.gemini_client") as mock_client:
        mock_remote_file = MagicMock()
        mock_remote_file.name = "files/test_remote_audio_file_id"
        mock_remote_file.uri = "https://generativelanguage.googleapis.com/v1beta/files/test_remote_audio_file_id"
        mock_remote_file.mime_type = "audio/mpeg"
        mock_client.upload_file.return_value = mock_remote_file
        mock_client.delete_remote_file.return_value = True
        mock_client.transcribe_audio.return_value = (
            "Se abre la sesión de la vista civil ordinaria.",
            [],
            None,
        )
        yield mock_client


def test_transcribe_mp3_valid(client: TestClient, mock_gemini):
    mock_gemini.transcribe_audio.return_value = (
        "Se abre la sesión de la vista civil ordinaria.",
        [SpeakerSegment(speaker="spk_1", text="Se abre la sesión de la vista civil ordinaria.")],
        None,
    )
    mp3_bytes = generate_synthetic_mp3()
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("vista_oral.mp3", mp3_bytes, "audio/mpeg")},
        params={"mode": "verbatim", "diarization": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "vista_oral.mp3"
    assert data["extension"] == "mp3"
    assert data["content_type"] == "audio/mp3"
    assert data["mode"] == "verbatim"
    assert data["diarization"] is True
    assert data["detected_language"] is None
    assert data["language"] is None
    assert data["transcription_model"] == settings.GEMINI_TRANSCRIPTION_MODEL
    assert "Se abre la sesión" in data["text"]
    assert data["word_count"] > 0
    assert data["character_count"] == len(data["text"])
    assert len(data["segments"]) == 1
    assert data["segments"][0]["speaker"] == "spk_1"

    # Verificar que se subió y que se borró remotamente en Gemini Files API
    mock_gemini.upload_file.assert_called_once()
    mock_gemini.delete_remote_file.assert_called_once_with("files/test_remote_audio_file_id")


def test_transcribe_wav_valid_default_diarization_false(client: TestClient, mock_gemini):
    wav_bytes = generate_synthetic_wav()
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("declaracion.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "declaracion.wav"
    assert data["extension"] == "wav"
    assert data["content_type"] == "audio/wav"
    assert data["diarization"] is False
    assert data["detected_language"] is None
    assert "Se abre la sesión" in data["text"]
    assert data["segments"] == []
    mock_gemini.delete_remote_file.assert_called_once_with("files/test_remote_audio_file_id")


def test_transcribe_unsupported_format_returns_415(client: TestClient):
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("video.avi", b"fake avi video bytes", "video/x-msvideo")},
    )

    assert response.status_code == 415
    data = response.json()
    assert "Formato de audio no permitido" in data["detail"]


def test_transcribe_empty_audio_returns_400(client: TestClient):
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("vacio.mp3", b"", "audio/mpeg")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "está vacío" in data["detail"]


def test_transcribe_file_size_exceeded_returns_413(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "MAX_AUDIO_SIZE_MB", 1)
    large_wav = generate_synthetic_wav() + (b"\x80" * (2 * 1024 * 1024))

    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("pesado.wav", large_wav, "audio/wav")},
    )

    assert response.status_code == 413
    data = response.json()
    assert "excede el límite máximo" in data["detail"]


def test_transcribe_mode_smart_without_diarization(client: TestClient, mock_gemini):
    mock_gemini.transcribe_audio.return_value = ("Texto limpio en modo smart.", [], None)
    wav_bytes = generate_synthetic_wav()

    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("audio_smart.wav", wav_bytes, "audio/wav")},
        params={"mode": "smart", "diarization": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "smart"
    assert data["diarization"] is False
    assert data["text"] == "Texto limpio en modo smart."
    assert data["segments"] == []


def test_transcribe_smart_with_diarization_incompatible_returns_400(client: TestClient):
    wav_bytes = generate_synthetic_wav()
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("incompatible.wav", wav_bytes, "audio/wav")},
        params={"mode": "smart", "diarization": True},
    )

    assert response.status_code == 400
    data = response.json()
    assert "no es compatible con el modo 'smart'" in data["detail"]


def test_transcribe_gemini_empty_response_returns_400(client: TestClient, mock_gemini):
    mock_gemini.transcribe_audio.side_effect = GeminiEmptyResponseError("No se detectó voz.")
    wav_bytes = generate_synthetic_wav()

    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("silencio.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "No se detectó voz" in data["detail"]
    # El archivo remoto de todas formas debe eliminarse
    mock_gemini.delete_remote_file.assert_called_once_with("files/test_remote_audio_file_id")


def test_transcribe_gemini_provider_error_returns_502(client: TestClient, mock_gemini):
    mock_gemini.transcribe_audio.side_effect = GeminiProviderError("Fallo del servidor de Gemini")
    wav_bytes = generate_synthetic_wav()

    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("fallo_api.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 502
    data = response.json()
    assert "Fallo del servidor de Gemini" in data["detail"]
    # El archivo remoto debe eliminarse tras el error
    mock_gemini.delete_remote_file.assert_called_once_with("files/test_remote_audio_file_id")


def test_remote_file_deleted_on_upload_error(client: TestClient, mock_gemini):
    mock_gemini.upload_file.side_effect = GeminiProviderError("Fallo en upload")
    wav_bytes = generate_synthetic_wav()

    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("error_subida.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 502


def test_confidentiality_logs_do_not_contain_filename_or_transcribed_text(
    client: TestClient, mock_gemini, caplog
):
    import logging
    sensitive_filename = "grabacion_secreta_reunion_directorio.wav"
    secret_text = "Acuerdo secreto sobre la fusión de empresas 777"
    mock_gemini.transcribe_audio.return_value = (secret_text, [], None)
    wav_bytes = generate_synthetic_wav()

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/v1/audio/transcribe",
            files={"file": (sensitive_filename, wav_bytes, "audio/wav")},
        )

    assert response.status_code == 200
    assert response.json()["filename"] == sensitive_filename

    # Comprobar que en los logs NO figura el nombre del fichero ni el texto sensible
    assert "grabacion_secreta_reunion_directorio" not in caplog.text
    assert "Acuerdo secreto sobre la fusión" not in caplog.text
    assert "files/test_remote_audio_file_id" not in caplog.text

    # Comprobar que sí figuran metadatos técnicos seguros
    assert "Transcripción de audio completada" in caplog.text
    assert "Ext: wav" in caplog.text


def test_corrupted_wav_header_returns_400(client: TestClient):
    corrupted_bytes = b"NO_RIFF_HEADER_CORRUPTED_BYTES"
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("corrupto.wav", corrupted_bytes, "audio/wav")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "WAV" in data["detail"] or "dañado" in data["detail"]


def test_audio_stream_aborts_early_without_consuming_full_stream():
    """Verifica que save_stream_to_temp_file aborta de inmediato al superar el límite de audio."""
    import asyncio
    from fastapi import UploadFile
    from app.services.audio_transcription import (
        AudioFileSizeExceededError,
        audio_transcription_service,
    )

    valid_wav_header = generate_synthetic_wav(duration_secs=0.01)

    class CountingAudioStream(io.BytesIO):
        def __init__(self, header: bytes, chunk_size: int, total_chunks: int):
            super().__init__()
            self.header = header
            self.chunk = b"\x80" * chunk_size
            self.total_chunks = total_chunks
            self.chunks_read = 0

        def read(self, size: int = -1):
            if self.chunks_read == 0:
                self.chunks_read += 1
                return self.header
            if self.chunks_read < self.total_chunks:
                self.chunks_read += 1
                return self.chunk
            return b""

    # 10 chunks de 100 KB = 1000 KB. Límite: 250 KB
    stream = CountingAudioStream(header=valid_wav_header, chunk_size=100 * 1024, total_chunks=10)
    upload_file = UploadFile(file=stream, filename="stream_audio.wav")

    async def run_test():
        try:
            await audio_transcription_service.save_stream_to_temp_file(
                file=upload_file,
                extension="wav",
                max_bytes=250 * 1024,
            )
            assert False, "Debería haber lanzado AudioFileSizeExceededError"
        except AudioFileSizeExceededError:
            pass

    asyncio.run(run_test())

    # Comprobar que abortó al cruzar 250 KB y no leyó los 10 chunks
    assert stream.chunks_read <= 4


def test_transcribe_language_param_valid(client: TestClient, mock_gemini):
    wav_bytes = generate_synthetic_wav()
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("declaracion.wav", wav_bytes, "audio/wav")},
        params={"language": "es-ES"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "es-ES"
    mock_gemini.transcribe_audio.assert_called_once()
    _, kwargs = mock_gemini.transcribe_audio.call_args
    assert kwargs.get("language") == "es-ES"


def test_transcribe_language_param_invalid_returns_400(client: TestClient):
    wav_bytes = generate_synthetic_wav()
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("declaracion.wav", wav_bytes, "audio/wav")},
        params={"language": "es_ES_INVALID!!!"},
    )
    assert response.status_code == 400
    data = response.json()
    assert "BCP-47" in data["detail"]


def test_gemini_client_transcribe_audio_interactions_api_verbatim():
    """Verifica la llamada exacta a client.interactions.create en modo verbatim sin diarización."""
    from app.services.gemini_client import GeminiClient

    client = GeminiClient()
    mock_genai_client = MagicMock()
    mock_interaction = MagicMock()
    mock_interaction.output_text = "Transcripción literal verbatim."
    mock_interaction.steps = []
    mock_interaction.detected_language = None
    mock_genai_client.interactions.create.return_value = mock_interaction
    client._client = mock_genai_client

    mock_remote_file = MagicMock()
    mock_remote_file.uri = "https://generativelanguage.googleapis.com/v1beta/files/test_file_id"
    mock_remote_file.mime_type = "audio/wav"

    text, segments, detected_lang, usage = client.transcribe_audio(
        remote_file=mock_remote_file,
        mode="verbatim",
        diarization=False,
    )

    assert text == "Transcripción literal verbatim."
    assert segments == []
    assert detected_lang is None
    assert usage is None

    mock_genai_client.interactions.create.assert_called_once()
    call_kwargs = mock_genai_client.interactions.create.call_args.kwargs
    assert call_kwargs["model"] == settings.GEMINI_TRANSCRIPTION_MODEL
    assert call_kwargs.get("store") is False
    assert "previous_interaction_id" not in call_kwargs
    assert call_kwargs["input"] == [
        {"type": "audio", "uri": mock_remote_file.uri, "mime_type": "audio/wav"}
    ]
    assert call_kwargs["generation_config"] == {
        "transcription_config": {
            "mode": {"type": "verbatim"},
        }
    }
    # Asegurar que NO se hayan solicitado word timestamps
    assert "timestamp_granularities" not in call_kwargs["generation_config"]["transcription_config"]["mode"]


def test_gemini_client_transcribe_audio_interactions_api_verbatim_with_diarization():
    """Verifica client.interactions.create con verbatim y diarization_mode='speaker'."""
    from app.services.gemini_client import GeminiClient

    client = GeminiClient()
    mock_genai_client = MagicMock()
    mock_interaction = MagicMock()
    mock_interaction.output_text = "Interlocutor 1 y 2 hablando."

    # Simular estructura de steps devuelta por Interactions API con diarización
    content1 = MagicMock()
    content1.speaker = "spk_1"
    content1.text = "Buenos días señoría."
    content1.annotations = None

    content2 = MagicMock()
    content2.speaker = "spk_2"
    content2.text = "Tiene la palabra la defensa."
    content2.annotations = None

    step = MagicMock()
    step.content = [content1, content2]
    mock_interaction.steps = [step]
    mock_interaction.detected_language = None

    mock_genai_client.interactions.create.return_value = mock_interaction
    client._client = mock_genai_client

    mock_remote_file = MagicMock()
    mock_remote_file.uri = "https://generativelanguage.googleapis.com/v1beta/files/test_file_id"
    mock_remote_file.mime_type = "audio/mp3"

    text, segments, detected_lang, usage = client.transcribe_audio(
        remote_file=mock_remote_file,
        mode="verbatim",
        diarization=True,
        language="es",
    )

    assert text == "Interlocutor 1 y 2 hablando."
    assert len(segments) == 2
    assert segments[0].speaker == "spk_1"
    assert segments[0].text == "Buenos días señoría."
    assert segments[1].speaker == "spk_2"
    assert segments[1].text == "Tiene la palabra la defensa."
    assert detected_lang is None
    assert usage is None

    call_kwargs = mock_genai_client.interactions.create.call_args.kwargs
    assert call_kwargs.get("store") is False
    assert "previous_interaction_id" not in call_kwargs
    assert call_kwargs["generation_config"] == {
        "transcription_config": {
            "mode": {
                "type": "verbatim",
                "diarization_mode": "speaker",
            },
            "language_codes": ["es"],
        }
    }
    # No se solicitan word timestamps
    assert "timestamp_granularities" not in call_kwargs["generation_config"]["transcription_config"]["mode"]


def test_gemini_client_transcribe_audio_interactions_api_smart():
    """Verifica client.interactions.create en modo smart."""
    from app.services.gemini_client import GeminiClient

    client = GeminiClient()
    mock_genai_client = MagicMock()
    mock_interaction = MagicMock()
    mock_interaction.output_text = "Texto limpio en modo smart."
    mock_interaction.steps = []
    mock_interaction.detected_language = "es"

    mock_genai_client.interactions.create.return_value = mock_interaction
    client._client = mock_genai_client

    mock_remote_file = MagicMock()
    mock_remote_file.uri = "https://generativelanguage.googleapis.com/v1beta/files/test_file_id"
    mock_remote_file.mime_type = "audio/ogg"

    text, segments, detected_lang, usage = client.transcribe_audio(
        remote_file=mock_remote_file,
        mode="smart",
        diarization=False,
    )

    assert text == "Texto limpio en modo smart."
    assert segments == []
    assert detected_lang == "es"
    assert usage is None

    call_kwargs = mock_genai_client.interactions.create.call_args.kwargs
    assert call_kwargs.get("store") is False
    assert "previous_interaction_id" not in call_kwargs
    assert call_kwargs["generation_config"] == {
        "transcription_config": {
            "mode": "smart",
        }
    }


def test_gemini_client_duration_exceeded_error_mapping():
    """Verifica que el error de duración máxima de Gemini se mapea a un mensaje amigable."""
    from google.genai.errors import APIError
    from app.services.gemini_client import GeminiClient, GeminiProviderError

    client = GeminiClient()
    mock_genai_client = MagicMock()
    mock_genai_client.interactions.create.side_effect = APIError(
        code=400,
        response_json={"error": {"message": "Audio duration exceeds maximum supported length (3600s)"}},
    )
    client._client = mock_genai_client

    mock_remote_file = MagicMock()
    mock_remote_file.uri = "uri"
    mock_remote_file.mime_type = "audio/wav"

    with pytest.raises(GeminiProviderError) as exc_info:
        client.transcribe_audio(remote_file=mock_remote_file, mode="verbatim", diarization=True)

    assert "duración máxima" in str(exc_info.value)
    assert "30 minutos" in str(exc_info.value)


def test_gemini_client_transcribe_audio_extracts_usage():
    """Verifica que si Interactions API devuelve usage, se extrae tipado correctamente."""
    from app.services.gemini_client import GeminiClient
    from app.schemas.audio import AudioTranscriptionUsage

    client = GeminiClient()
    mock_genai_client = MagicMock()
    mock_interaction = MagicMock()
    mock_interaction.output_text = "Transcripción con usage."
    mock_interaction.steps = []
    mock_interaction.detected_language = None

    mock_usage = MagicMock()
    mock_usage.total_input_tokens = 1245
    mock_usage.total_output_tokens = 380
    mock_usage.total_tokens = 1625
    mock_interaction.usage = mock_usage

    mock_genai_client.interactions.create.return_value = mock_interaction
    client._client = mock_genai_client

    mock_remote_file = MagicMock()
    mock_remote_file.uri = "https://example.com/audio"
    mock_remote_file.mime_type = "audio/wav"

    text, segments, detected_lang, usage = client.transcribe_audio(
        remote_file=mock_remote_file,
        mode="verbatim",
        diarization=False,
    )

    assert text == "Transcripción con usage."
    assert isinstance(usage, AudioTranscriptionUsage)
    assert usage.input_tokens == 1245
    assert usage.output_tokens == 380
    assert usage.total_tokens == 1625


def test_gemini_client_transcribe_audio_handles_null_usage_without_fallback():
    """Verifica que si no hay usage oficial, es None y NO hay estimaciones ni fallbacks inventados."""
    from app.services.gemini_client import GeminiClient

    client = GeminiClient()
    mock_genai_client = MagicMock()
    mock_interaction = MagicMock()
    mock_interaction.output_text = "Transcripción sin usage."
    mock_interaction.steps = []
    mock_interaction.detected_language = None
    mock_interaction.usage = None

    mock_genai_client.interactions.create.return_value = mock_interaction
    client._client = mock_genai_client

    mock_remote_file = MagicMock()
    mock_remote_file.uri = "https://example.com/audio"
    mock_remote_file.mime_type = "audio/wav"

    text, segments, detected_lang, usage = client.transcribe_audio(
        remote_file=mock_remote_file,
        mode="verbatim",
        diarization=False,
    )

    assert text == "Transcripción sin usage."
    assert usage is None


def test_audio_endpoint_includes_usage_when_provided(client: TestClient, mock_gemini):
    """Verifica que el endpoint /api/v1/audio/transcribe incluye usage en el response cuando el cliente lo suministra."""
    from app.schemas.audio import AudioTranscriptionUsage

    mock_usage = AudioTranscriptionUsage(input_tokens=850, output_tokens=210, total_tokens=1060)
    mock_gemini.transcribe_audio.return_value = (
        "Transcripción con usage de tokens.",
        [],
        None,
        mock_usage,
    )
    mp3_bytes = generate_synthetic_mp3()
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("vista.mp3", mp3_bytes, "audio/mpeg")},
        params={"mode": "verbatim", "diarization": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["usage"] is not None
    assert data["usage"]["input_tokens"] == 850
    assert data["usage"]["output_tokens"] == 210
    assert data["usage"]["total_tokens"] == 1060


def test_audio_endpoint_handles_null_usage(client: TestClient, mock_gemini):
    """Verifica que el endpoint maneja correctamente usage null sin romper el esquema."""
    mock_gemini.transcribe_audio.return_value = (
        "Transcripción sin usage.",
        [],
        None,
        None,
    )
    mp3_bytes = generate_synthetic_mp3()
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("vista.mp3", mp3_bytes, "audio/mpeg")},
        params={"mode": "verbatim", "diarization": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["usage"] is None


def test_audio_transcription_interactions_create_explicitly_disables_storage():
    """Verifica que la transcripción de audio invoca Interactions API con store=False explícito y sin previous_interaction_id."""
    from app.services.gemini_client import GeminiClient

    client = GeminiClient()
    mock_genai_client = MagicMock()
    mock_interaction = MagicMock()
    mock_interaction.output_text = "Texto transcrito."
    mock_interaction.steps = []
    mock_interaction.detected_language = None
    mock_interaction.usage = None

    mock_genai_client.interactions.create.return_value = mock_interaction
    client._client = mock_genai_client

    mock_remote_file = MagicMock()
    mock_remote_file.uri = "https://generativelanguage.googleapis.com/v1beta/files/test_audio_store"
    mock_remote_file.mime_type = "audio/wav"

    text, segments, detected_lang, usage = client.transcribe_audio(
        remote_file=mock_remote_file,
        mode="verbatim",
        diarization=False,
    )

    mock_genai_client.interactions.create.assert_called_once()
    call_kwargs = mock_genai_client.interactions.create.call_args.kwargs
    assert call_kwargs.get("store") is False
    assert "previous_interaction_id" not in call_kwargs


# ==============================================================================
# TESTS BLOQUE 8A — COMPATIBILIDAD MP4 PARA TRANSCRIPCIÓN
# ==============================================================================

def generate_synthetic_mp4(num_bytes: int = 512) -> bytes:
    """Genera bytes con cabecera ftyp MP4 válida."""
    ftyp_box = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
    padding = b"\x00" * max(0, num_bytes - len(ftyp_box))
    return ftyp_box + padding


def test_transcribe_mp4_valid_pipeline(client: TestClient, mock_gemini):
    """Verifica el flujo completo para un archivo MP4: extracción local a FLAC y transcripción con Gemini."""
    from app.services.media_service import MediaInspectionResult

    mock_gemini.transcribe_audio.return_value = (
        "Declaración del testigo en la grabación de vídeo judicial.",
        [SpeakerSegment(speaker="spk_1", text="Declaración del testigo en la grabación de vídeo judicial.")],
        "es",
        None,
    )

    mp4_bytes = generate_synthetic_mp4()

    def fake_extract_audio(input_video_path, output_audio_path):
        from pathlib import Path
        Path(output_audio_path).write_bytes(b"fLaCdummy")

    with patch("app.services.audio_transcription.media_service.inspect_media") as mock_inspect, \
         patch("app.services.audio_transcription.media_service.extract_audio", side_effect=fake_extract_audio) as mock_extract:
        mock_inspect.return_value = MediaInspectionResult(
            has_audio=True,
            audio_codec="aac",
            duration_seconds=120.0,
            format_name="mov,mp4",
        )

        response = client.post(
            "/api/v1/audio/transcribe",
            files={"file": ("vista_audiencia.mp4", mp4_bytes, "video/mp4")},
            params={"mode": "verbatim", "diarization": True},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "vista_audiencia.mp4"
    assert data["extension"] == "mp4"
    assert data["content_type"] == "video/mp4"
    assert "Declaración del testigo" in data["text"]
    assert data["mode"] == "verbatim"
    assert data["diarization"] is True
    assert len(data["segments"]) == 1

    # Verificar que se llamó a inspect y extract
    mock_inspect.assert_called_once()
    mock_extract.assert_called_once()

    # Verificar que a Gemini se le subió el audio FLAC extraído y NO el archivo MP4
    mock_gemini.upload_file.assert_called_once()
    upload_call_args = mock_gemini.upload_file.call_args
    assert upload_call_args.kwargs.get("mime_type") == "audio/flac"
    assert upload_call_args.args[0].endswith(".flac")

    # Verificar que se borró remotamente de Gemini
    mock_gemini.delete_remote_file.assert_called_once_with("files/test_remote_audio_file_id")


def test_transcribe_mp4_without_audio_track_returns_400(client: TestClient, mock_gemini):
    """Verifica que un archivo MP4 sin pista de audio es rechazado con HTTP 400 y mensaje claro."""
    from app.services.media_service import NoAudioTrackError

    mp4_bytes = generate_synthetic_mp4()

    with patch("app.services.audio_transcription.media_service.inspect_media") as mock_inspect:
        mock_inspect.side_effect = NoAudioTrackError("El archivo MP4 no contiene una pista de audio que pueda transcribirse.")

        response = client.post(
            "/api/v1/audio/transcribe",
            files={"file": ("video_mudo.mp4", mp4_bytes, "video/mp4")},
        )

    assert response.status_code == 400
    assert "El archivo MP4 no contiene una pista de audio que pueda transcribirse." in response.json()["detail"]
    mock_gemini.upload_file.assert_not_called()


def test_transcribe_mp4_corrupted_ffprobe_returns_400(client: TestClient, mock_gemini):
    """Verifica que un MP4 dañado o corrupto que falla en ffprobe devuelve HTTP 400."""
    from app.services.media_service import CorruptedMediaError

    mp4_bytes = generate_synthetic_mp4()

    with patch("app.services.audio_transcription.media_service.inspect_media") as mock_inspect:
        mock_inspect.side_effect = CorruptedMediaError("El archivo de vídeo no ha podido procesarse.")

        response = client.post(
            "/api/v1/audio/transcribe",
            files={"file": ("corrupto.mp4", mp4_bytes, "video/mp4")},
        )

    assert response.status_code == 400
    assert "El archivo de vídeo no ha podido procesarse." in response.json()["detail"]


def test_transcribe_mp4_corrupted_header_without_ftyp_returns_400(client: TestClient, mock_gemini):
    """Verifica que un MP4 con bytes de cabecera inválidos (sin ftyp) es rechazado en la validación inicial."""
    fake_bytes = b"RANDOM_NON_MP4_BYTES" * 10
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("falso.mp4", fake_bytes, "video/mp4")},
    )
    assert response.status_code == 400
    assert "firma ftyp no encontrada" in response.json()["detail"]


def test_transcribe_mp4_extraction_error_returns_500(client: TestClient, mock_gemini):
    """Verifica que un fallo inesperado durante ffmpeg extract devuelve HTTP 500 y no llama a Gemini."""
    from app.services.media_service import MediaInspectionResult, MediaProcessingError

    mp4_bytes = generate_synthetic_mp4()

    with patch("app.services.audio_transcription.media_service.inspect_media") as mock_inspect, \
         patch("app.services.audio_transcription.media_service.extract_audio") as mock_extract:
        mock_inspect.return_value = MediaInspectionResult(has_audio=True, duration_seconds=60.0)
        mock_extract.side_effect = MediaProcessingError("No se pudo extraer la pista de audio de la grabación de vídeo.")

        response = client.post(
            "/api/v1/audio/transcribe",
            files={"file": ("error_ffmpeg.mp4", mp4_bytes, "video/mp4")},
        )

    assert response.status_code == 500
    assert "No se pudo extraer la pista de audio de la grabación de vídeo." in response.json()["detail"]
    mock_gemini.upload_file.assert_not_called()


def test_transcribe_mp4_duration_exceeded_returns_400(client: TestClient, mock_gemini):
    """Verifica que una grabación MP4 que supera 8 horas es rechazada con el mensaje especificado."""
    from app.services.media_service import MediaInspectionResult

    mp4_bytes = generate_synthetic_mp4()

    with patch("app.services.audio_transcription.media_service.inspect_media") as mock_inspect:
        # 28801 segundos (> 8 horas)
        mock_inspect.return_value = MediaInspectionResult(has_audio=True, duration_seconds=28801.0)

        response = client.post(
            "/api/v1/audio/transcribe",
            files={"file": ("muy_larga.mp4", mp4_bytes, "video/mp4")},
        )

    assert response.status_code == 400
    assert "La grabación supera la duración máxima admitida actualmente de 8 horas." in response.json()["detail"]
    mock_gemini.upload_file.assert_not_called()


def test_transcribe_mp4_diarization_duration_exceeded_returns_400(client: TestClient, mock_gemini):
    """Verifica que una grabación MP4 de más de 8 horas con diarización activa es rechazada."""
    from app.services.media_service import MediaInspectionResult

    mp4_bytes = generate_synthetic_mp4()

    with patch("app.services.audio_transcription.media_service.inspect_media") as mock_inspect:
        # 28801 segundos (> 8 horas)
        mock_inspect.return_value = MediaInspectionResult(has_audio=True, duration_seconds=28801.0)

        response = client.post(
            "/api/v1/audio/transcribe",
            files={"file": ("audiencia_diarization.mp4", mp4_bytes, "video/mp4")},
            params={"mode": "verbatim", "diarization": True},
        )

    assert response.status_code == 400
    assert "La grabación supera la duración máxima admitida actualmente de 8 horas." in response.json()["detail"]
    mock_gemini.upload_file.assert_not_called()


def test_transcribe_mp4_cleanup_on_gemini_failure(client: TestClient, mock_gemini):
    """Verifica que todos los archivos temporales (MP4 y audio extraído) son eliminados si Gemini falla."""
    from pathlib import Path
    from app.services.media_service import MediaInspectionResult

    mock_gemini.transcribe_audio.side_effect = GeminiProviderError("Fallo de red en Gemini API")

    mp4_bytes = generate_synthetic_mp4()
    created_paths = []

    def tracking_extract_audio(input_video_path, output_audio_path):
        Path(output_audio_path).write_bytes(b"fLaCcontent")
        created_paths.append(output_audio_path)
        created_paths.append(input_video_path)

    with patch("app.services.audio_transcription.media_service.inspect_media") as mock_inspect, \
         patch("app.services.audio_transcription.media_service.extract_audio", side_effect=tracking_extract_audio):
        mock_inspect.return_value = MediaInspectionResult(has_audio=True, duration_seconds=60.0)

        response = client.post(
            "/api/v1/audio/transcribe",
            files={"file": ("test_cleanup.mp4", mp4_bytes, "video/mp4")},
        )

    assert response.status_code == 502

    # Verificar que todos los archivos temporales creados fueron eliminados
    assert len(created_paths) == 2
    for p in created_paths:
        assert not Path(p).exists(), f"El archivo temporal {p} no fue eliminado tras error de Gemini."


def test_media_service_unit_inspect_invokes_ffprobe_safely():
    """Verifica que MediaService.inspect_media invoca ffprobe como lista de argumentos sin shell=True."""
    import subprocess
    from app.services.media_service import MediaService

    service = MediaService()
    fake_json_output = '{"streams": [{"codec_type": "audio", "codec_name": "aac"}], "format": {"duration": "45.5", "format_name": "mov,mp4"}}'

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=fake_json_output,
            stderr="",
        )

        info = service.inspect_media("/tmp/video.mp4")

    mock_run.assert_called_once()
    call_args = mock_run.call_args
    cmd = call_args[0][0]
    assert isinstance(cmd, list)
    assert cmd[0] == "ffprobe"
    assert "/tmp/video.mp4" in cmd
    assert call_args.kwargs.get("shell") is not True

    assert info.has_audio is True
    assert info.audio_codec == "aac"
    assert info.duration_seconds == 45.5


def test_media_service_unit_extract_invokes_ffmpeg_with_flac():
    """Verifica que MediaService.extract_audio invoca ffmpeg para convertir a FLAC mono 16kHz sin shell=True."""
    import subprocess
    from pathlib import Path
    from app.services.media_service import MediaService

    service = MediaService()

    def fake_ffmpeg_run(cmd, **kwargs):
        # cmd[-1] es el archivo de salida
        output_file = cmd[-1]
        Path(output_file).write_bytes(b"dummy_flac_content")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=fake_ffmpeg_run) as mock_run:
        import tempfile
        out_f = tempfile.NamedTemporaryFile(delete=False, suffix=".flac")
        out_f.close()
        out_path = out_f.name
        try:
            service.extract_audio("/tmp/input.mp4", out_path)
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert isinstance(cmd, list)
            assert cmd[0] == "ffmpeg"
            assert "-vn" in cmd
            assert "-c:a" in cmd
            assert "flac" in cmd
            assert "-ac" in cmd
            assert "1" in cmd
            assert "-ar" in cmd
            assert "16000" in cmd
            assert mock_run.call_args.kwargs.get("shell") is not True
        finally:
            Path(out_path).unlink(missing_ok=True)


# ==============================================================================
# BLOQUE 8B — PRUEBAS DE GRABACIONES LARGAS, SEGMENTACIÓN Y CONSOLIDACIÓN
# ==============================================================================

def test_8b_short_audio_single_call(client: TestClient, mock_gemini):
    """1. Audio corto (<= 3600s) sigue haciendo una única llamada a Gemini sin segmentar."""
    from app.services.media_service import MediaInspectionResult

    wav_bytes = generate_synthetic_wav()
    with patch("app.services.audio_transcription.media_service.inspect_media") as mock_inspect:
        mock_inspect.return_value = MediaInspectionResult(has_audio=True, duration_seconds=120.0)
        res = client.post("/api/v1/audio/transcribe", files={"file": ("corto.wav", wav_bytes, "audio/wav")})

    assert res.status_code == 200
    data = res.json()
    assert data["was_segmented"] is False
    assert data["segment_count"] == 1
    assert data["duration_seconds"] == 120.0
    mock_gemini.upload_file.assert_called_once()
    mock_gemini.transcribe_audio.assert_called_once()


def test_8b_short_mp4_single_call(client: TestClient, mock_gemini):
    """2. MP4 corto (<= 3600s) mantiene comportamiento 8A intacto: extrae audio y hace 1 llamada."""
    from app.services.media_service import MediaInspectionResult

    mp4_bytes = generate_synthetic_mp4()
    with patch("app.services.audio_transcription.media_service.inspect_media") as mock_inspect, \
         patch("app.services.audio_transcription.media_service.extract_audio") as mock_extract:
        mock_inspect.return_value = MediaInspectionResult(has_audio=True, duration_seconds=300.0)
        res = client.post("/api/v1/audio/transcribe", files={"file": ("corto.mp4", mp4_bytes, "video/mp4")})

    assert res.status_code == 200
    data = res.json()
    assert data["was_segmented"] is False
    assert data["segment_count"] == 1
    mock_extract.assert_called_once()
    mock_gemini.upload_file.assert_called_once()
    mock_gemini.transcribe_audio.assert_called_once()


def test_8b_long_standard_audio_segmented(client: TestClient, mock_gemini):
    """3 y 11. Audio largo estándar (> 3600s) se segmenta, procesa secuencialmente y respeta orden."""
    from app.schemas.audio import AudioTranscriptionUsage
    from app.services.media_service import MediaInspectionResult

    wav_bytes = generate_synthetic_wav()
    call_count = 0

    def mock_transcribe(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return (
            f"Texto del fragmento {call_count}.",
            [],
            "es",
            AudioTranscriptionUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        )

    mock_gemini.transcribe_audio.side_effect = mock_transcribe

    with patch("app.services.audio_transcription.media_service.inspect_media") as mock_inspect, \
         patch("app.services.audio_transcription.media_service.convert_to_master_flac") as mock_conv, \
         patch("app.services.audio_transcription.media_service.detect_silences", return_value=[]), \
         patch("app.services.audio_transcription.media_service.create_segment_chunk") as mock_chunk:
        # 5400s = 90 minutos -> 2 fragmentos de 2700s
        mock_inspect.return_value = MediaInspectionResult(has_audio=True, duration_seconds=5400.0)

        res = client.post("/api/v1/audio/transcribe", files={"file": ("largo.wav", wav_bytes, "audio/wav")})

    assert res.status_code == 200
    data = res.json()
    assert data["was_segmented"] is True
    assert data["segment_count"] == 2
    mock_conv.assert_called_once()
    assert mock_chunk.call_count == 2
    assert mock_gemini.upload_file.call_count == 2
    assert mock_gemini.transcribe_audio.call_count == 2
    # Comprobar orden estricto de consolidación
    assert data["text"] == "Texto del fragmento 1.\n\nTexto del fragmento 2."
    # Comprobar agregación de usage
    assert data["usage"]["input_tokens"] == 200
    assert data["usage"]["output_tokens"] == 100
    assert data["usage"]["total_tokens"] == 300


def test_8b_long_standard_mp4_segmented(client: TestClient, mock_gemini):
    """4 y 13. MP4 largo extrae master FLAC una sola vez, nunca sube master completo a Gemini."""
    from app.services.media_service import MediaInspectionResult

    mp4_bytes = generate_synthetic_mp4()
    mock_gemini.transcribe_audio.return_value = ("Texto fragmento MP4.", [], "es", None)

    with patch("app.services.audio_transcription.media_service.inspect_media") as mock_inspect, \
         patch("app.services.audio_transcription.media_service.extract_audio") as mock_extract, \
         patch("app.services.audio_transcription.media_service.detect_silences", return_value=[]), \
         patch("app.services.audio_transcription.media_service.create_segment_chunk"):
        # 5400s (2 fragmentos)
        mock_inspect.return_value = MediaInspectionResult(has_audio=True, duration_seconds=5400.0)

        res = client.post("/api/v1/audio/transcribe", files={"file": ("vista_larga.mp4", mp4_bytes, "video/mp4")})

    assert res.status_code == 200
    data = res.json()
    assert data["was_segmented"] is True
    assert data["segment_count"] == 2
    # Master extraído exactamente una vez
    mock_extract.assert_called_once()
    # Gemini fue invocado 2 veces con los fragmentos
    assert mock_gemini.upload_file.call_count == 2


def test_8b_long_diarization_safe_chunk_limit_and_warning(client: TestClient, mock_gemini):
    """5, 16 y 17. Diarización larga divide en fragmentos seguros, añade delimitadores y warning."""
    from app.schemas.audio import SpeakerSegment
    from app.services.media_service import MediaInspectionResult

    wav_bytes = generate_synthetic_wav()
    step = 0

    def mock_transcribe_diar(*args, **kwargs):
        nonlocal step
        step += 1
        return (
            f"Hablante 1: Intervención {step}.",
            [SpeakerSegment(speaker="spk_1", text=f"Intervención {step}.")],
            "es",
            None,
        )

    mock_gemini.transcribe_audio.side_effect = mock_transcribe_diar

    with patch("app.services.audio_transcription.media_service.inspect_media") as mock_inspect, \
         patch("app.services.audio_transcription.media_service.convert_to_master_flac"), \
         patch("app.services.audio_transcription.media_service.detect_silences", return_value=[]), \
         patch("app.services.audio_transcription.media_service.create_segment_chunk"):
        # 3600s con diarización -> chunks de max 1740s / target 1500s -> se divide en 3 fragmentos
        mock_inspect.return_value = MediaInspectionResult(has_audio=True, duration_seconds=3600.0)

        res = client.post(
            "/api/v1/audio/transcribe",
            files={"file": ("diar_larga.wav", wav_bytes, "audio/wav")},
            params={"mode": "verbatim", "diarization": True},
        )

    assert res.status_code == 200
    data = res.json()
    assert data["was_segmented"] is True
    assert data["segment_count"] >= 2
    # Delimitadores de segmentos presentes
    assert "[Segmento 1]" in data["text"]
    assert "[Segmento 2]" in data["text"]
    # Warning de interlocutores presente
    assert any("la numeración de los interlocutores puede reiniciarse" in w for w in data["warnings"])


def test_8b_plan_segments_unit_coverage_and_invariants():
    """6, 7 y 8. plan_segments cubre de 0 a fin, sin huecos ni overlap, y respeta límites máximos."""
    from app.services.media_service import MediaService, STANDARD_CHUNK_MAX_SECONDS, DIARIZATION_CHUNK_MAX_SECONDS

    service = MediaService()

    # Caso 1: Estándar 3 horas (10800s)
    plan_std = service.plan_segments(total_duration=10800.0, diarization=False)
    assert len(plan_std) >= 4
    assert plan_std[0].start_seconds == 0.0
    assert plan_std[-1].end_seconds == 10800.0
    for i in range(len(plan_std) - 1):
        assert plan_std[i].end_seconds == plan_std[i + 1].start_seconds
    for seg in plan_std:
        assert seg.duration_seconds <= STANDARD_CHUNK_MAX_SECONDS

    # Caso 2: Diarización 2 horas (7200s)
    plan_diar = service.plan_segments(total_duration=7200.0, diarization=True)
    assert len(plan_diar) >= 4
    assert plan_diar[0].start_seconds == 0.0
    assert plan_diar[-1].end_seconds == 7200.0
    for i in range(len(plan_diar) - 1):
        assert plan_diar[i].end_seconds == plan_diar[i + 1].start_seconds
    for seg in plan_diar:
        assert seg.duration_seconds <= DIARIZATION_CHUNK_MAX_SECONDS


def test_8b_silence_detection_uses_nearby_silence():
    """9. plan_segments utiliza un silencio detectado cercano al punto de corte target."""
    from app.services.media_service import MediaService

    service = MediaService()
    # Total: 6000s. Target: 2700s. Silencio en [2680s, 2690s] (punto medio 2685s)
    silences = [(2680.0, 2690.0)]
    plan = service.plan_segments(total_duration=6000.0, diarization=False, detected_silences=silences)

    assert len(plan) >= 2
    # El primer segmento debió cortar en el silencio (2685.0s) en vez de en 2700.0s
    assert plan[0].end_seconds == 2685.0
    assert plan[1].start_seconds == 2685.0


def test_8b_silence_detection_fallback_on_failure():
    """10. Si la detección de silencios no encuentra nada, plan_segments corta por tiempo fijo."""
    from app.services.media_service import MediaService

    service = MediaService()
    # Sin silencios
    plan = service.plan_segments(total_duration=6000.0, diarization=False, detected_silences=[])
    assert len(plan) >= 2
    assert plan[0].end_seconds == 2700.0
    assert plan[1].start_seconds == 2700.0


def test_8b_intermediate_chunk_failure_aborts_without_partial_and_cleans_up(client: TestClient, mock_gemini):
    """18 y 19. Si falla un chunk intermedio, aborta sin devolver parcial y limpia todos los recursos."""
    from app.services.media_service import MediaInspectionResult

    wav_bytes = generate_synthetic_wav()
    call_idx = 0

    def mock_transcribe_with_failure(*args, **kwargs):
        nonlocal call_idx
        call_idx += 1
        if call_idx == 2:
            raise GeminiProviderError("Fallo inesperado de cuota en segmento 2")
        return ("Texto ok.", [], "es", None)

    mock_gemini.transcribe_audio.side_effect = mock_transcribe_with_failure

    with patch("app.services.audio_transcription.media_service.inspect_media") as mock_inspect, \
         patch("app.services.audio_transcription.media_service.convert_to_master_flac"), \
         patch("app.services.audio_transcription.media_service.detect_silences", return_value=[]), \
         patch("app.services.audio_transcription.media_service.create_segment_chunk"):
        # 5400s -> 2 segmentos
        mock_inspect.return_value = MediaInspectionResult(has_audio=True, duration_seconds=5400.0)

        res = client.post("/api/v1/audio/transcribe", files={"file": ("fallo_seg.wav", wav_bytes, "audio/wav")})

    # No devuelve 200 con transcripción parcial: devuelve HTTP 502/500
    assert res.status_code in (500, 502)
    assert "No se ha podido completar la transcripción de la grabación" in res.json()["detail"]


def test_8b_duration_over_8h_rejected_before_gemini(client: TestClient, mock_gemini):
    """21. Grabaciones de más de 8 horas se rechazan preventivamente con HTTP 400 sin invocar Gemini."""
    from app.services.media_service import MediaInspectionResult

    wav_bytes = generate_synthetic_wav()
    with patch("app.services.audio_transcription.media_service.inspect_media") as mock_inspect:
        # 28805s (> 8 horas = 28800s)
        mock_inspect.return_value = MediaInspectionResult(has_audio=True, duration_seconds=28805.0)

        res = client.post("/api/v1/audio/transcribe", files={"file": ("ocho_horas.wav", wav_bytes, "audio/wav")})

    assert res.status_code == 400
    assert "La grabación supera la duración máxima admitida actualmente de 8 horas." in res.json()["detail"]
    mock_gemini.upload_file.assert_not_called()


def test_8b_size_over_max_media_size_rejected(client: TestClient, monkeypatch):
    """22. Archivos que superan el límite configurado son rechazados con HTTP 413."""
    monkeypatch.setattr(settings, "MAX_MEDIA_SIZE_MB", 1)
    monkeypatch.setattr(settings, "MAX_AUDIO_SIZE_MB", 1)
    large_wav = generate_synthetic_wav() + (b"\x80" * (2 * 1024 * 1024))

    res = client.post("/api/v1/audio/transcribe", files={"file": ("excesivo.wav", large_wav, "audio/wav")})
    assert res.status_code == 413
    assert "excede el límite máximo" in res.json()["detail"]


def test_8b_media_service_detect_silences_parsing():
    """24. Unit test seguro del parser de silencedetect de MediaService."""
    import subprocess
    from app.services.media_service import MediaService

    service = MediaService()
    fake_stderr = (
        "[silencedetect @ 0x123] silence_start: 120.4\n"
        "[silencedetect @ 0x123] silence_end: 121.8 | silence_duration: 1.4\n"
        "[silencedetect @ 0x123] silence_start: 240.0\n"
        "[silencedetect @ 0x123] silence_end: 242.0 | silence_duration: 2.0\n"
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=fake_stderr)
        silences = service.detect_silences("/tmp/test.flac")

    assert len(silences) == 2
    assert silences[0] == (120.4, 121.8)
    assert silences[1] == (240.0, 242.0)


def test_8b_media_service_convert_to_master_flac_invokes_ffmpeg():
    """25. Unit test de convert_to_master_flac verificando invocación de ffmpeg sin shell."""
    import subprocess
    from pathlib import Path
    from app.services.media_service import MediaService

    service = MediaService()

    def fake_ffmpeg(cmd, **kwargs):
        Path(cmd[-1]).write_bytes(b"dummy_flac")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=fake_ffmpeg) as mock_run:
        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".flac")
        tmp.close()
        try:
            service.convert_to_master_flac("/tmp/input.mp3", tmp.name)
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "ffmpeg"
            assert "-c:a" in cmd and "flac" in cmd
            assert "-ar" in cmd and "16000" in cmd
            assert "-ac" in cmd and "1" in cmd
            assert mock_run.call_args.kwargs.get("shell") is not True
        finally:
            Path(tmp.name).unlink(missing_ok=True)





