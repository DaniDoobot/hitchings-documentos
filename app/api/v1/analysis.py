from fastapi import APIRouter, HTTPException, status

from app.schemas.analysis import AnalysisResponse
from app.schemas.prompts import AnalysisRequest
from app.services.analysis_service import (
    AnalysisStructuredOutputError,
    InactivePromptError,
    TokenLimitExceededError,
    analysis_service,
)
from app.services.gemini_client import (
    GeminiConfigurationError,
    GeminiProviderError,
)
from app.services.prompt_service import PromptNotFoundError
from app.services.text_service import EmptyTextError, TextSizeExceededError

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analizar contenido documental con Gemini 3.8 Flash",
    description=(
        "Recibe contenido textual normalizado (procedente de documento, audio o texto pegado), "
        "valida límites de caracteres y tokens, aplica el prompt seleccionado y sus opciones, "
        "e invoca la Gemini Interactions API con Structured Output y separación robusta de instrucciones."
    ),
)
async def analyze_document(request: AnalysisRequest) -> AnalysisResponse:
    try:
        return analysis_service.analyze_document(request)
    except PromptNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except (EmptyTextError, InactivePromptError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except (TextSizeExceededError, TokenLimitExceededError) as err:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(err),
        ) from err
    except AnalysisStructuredOutputError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err),
        ) from err
    except GeminiProviderError as err:
        err_msg = str(err).lower()
        if "tiempo de espera" in err_msg or "timeout" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=str(err),
            ) from err
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err),
        ) from err
    except GeminiConfigurationError as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(err),
        ) from err
