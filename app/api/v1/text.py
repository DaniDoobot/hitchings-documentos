from fastapi import APIRouter, HTTPException, status

from app.schemas.text import TextPrepareRequest, TextPrepareResponse
from app.services.text_service import (
    EmptyTextError,
    TextSizeExceededError,
    text_preparation_service,
)

router = APIRouter(prefix="/text", tags=["Text"])


@router.post(
    "/prepare",
    response_model=TextPrepareResponse,
    status_code=status.HTTP_200_OK,
    summary="Preparar y normalizar texto pegado directamente",
    description=(
        "Recibe un payload JSON con texto pegado por el usuario, valida tamaño y contenido, "
        "aplica normalización conservadora de caracteres y saltos de línea, y calcula conteos de palabras y caracteres."
    ),
)
async def prepare_text(payload: TextPrepareRequest) -> TextPrepareResponse:
    try:
        return text_preparation_service.prepare_text(payload.text)
    except EmptyTextError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except TextSizeExceededError as err:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(err),
        ) from err
