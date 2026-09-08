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

router = APIRouter(prefix="/audio", tags=["Audio"])


@router.post(
    "/transcribe",
    response_model=AudioTranscribeResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribir archivo de audio mediante Gemini",
    description="Recibe un archivo de audio (mp3, wav, m4a, aac, ogg, flac, webm), valida formato y tamaño en streaming, procesa mediante Gemini Files API y devuelve texto y segmentos.",
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Archivo de audio a transcribir"),
    mode: Literal["verbatim", "smart"] = Query(
        "verbatim",
        description="Modo de transcripción: 'verbatim' (fiel y literal) o 'smart' (limpieza gramatical y de muletillas).",
    ),
    diarization: bool = Query(
        True,
        description="Identificación y separación de hablantes (solo compatible con modo 'verbatim').",
    ),
) -> AudioTranscribeResponse:
    try:
        return await audio_transcription_service.process_and_transcribe(
            file=file,
            mode=mode,
            diarization=diarization,
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
    except (EmptyAudioFileError, IncompatibleAudioParamsError, CorruptedAudioFileError, GeminiEmptyResponseError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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
