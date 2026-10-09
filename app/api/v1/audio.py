import re
from typing import Literal
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.schemas.audio import AudioTranscribeResponse
from app.services.audio_transcription import (
    AudioFileSizeExceededError,
    CorruptedAudioFileError,
    EmptyAudioFileError,
    IncompatibleAudioParamsError,
    UnsupportedAudioFormatError,
    audio_transcription_service,
)
from app.services.gemini_client import (
    GeminiConfigurationError,
    GeminiEmptyResponseError,
    GeminiProviderError,
)
from app.services.media_service import (
    CorruptedMediaError,
    MediaDurationExceededError,
    MediaProcessingError,
    NoAudioTrackError,
)

router = APIRouter(prefix="/audio", tags=["Audio"])

BCP47_REGEX = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$")


@router.post(
    "/transcribe",
    response_model=AudioTranscribeResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribir archivo de audio o vídeo (MP4) con soporte de grabaciones largas",
    description=(
        "Recibe un archivo de audio o vídeo MP4 (mp3, wav, m4a, aac, ogg, flac, webm, mp4) de hasta 1 GB y 8 horas de duración. "
        "Valida formato y tamaño en streaming. Para grabaciones de larga duración realiza normalización a master FLAC y segmentación "
        "automática segura en llamadas continuas sin solapamiento, consolidando una única transcripción determinista."
    ),
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Archivo de audio o vídeo a transcribir (hasta 1 GB)"),
    mode: Literal["verbatim", "smart"] = Query(
        "verbatim",
        description="Modo de transcripción: 'verbatim' (literal) o 'smart' (limpieza gramatical y de muletillas).",
    ),
    diarization: bool = Query(
        False,
        description="Identificación de interlocutores por voz (solo compatible con modo 'verbatim'). Por defecto: False.",
    ),
    language: str | None = Query(
        None,
        description="Código de idioma BCP-47 opcional (ej. 'es', 'es-ES', 'en-US'). Si se omite, se aplica autodetección de idioma.",
    ),
) -> AudioTranscribeResponse:
    if language and not BCP47_REGEX.match(language):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de código de idioma inválido: '{language}'. Debe ser un código BCP-47 válido (ej. 'es', 'es-ES', 'en-US').",
        )

    try:
        return await audio_transcription_service.process_and_transcribe(
            file=file,
            mode=mode,
            diarization=diarization,
            language=language,
        )
    except UnsupportedAudioFormatError as err:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(err),
        ) from err
    except AudioFileSizeExceededError as err:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(err),
        ) from err
    except (
        EmptyAudioFileError,
        IncompatibleAudioParamsError,
        CorruptedAudioFileError,
        GeminiEmptyResponseError,
        NoAudioTrackError,
        CorruptedMediaError,
        MediaDurationExceededError,
    ) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except MediaProcessingError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(err),
        ) from err
    except GeminiProviderError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err),
        ) from err
    except GeminiConfigurationError as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(err),
        ) from err
