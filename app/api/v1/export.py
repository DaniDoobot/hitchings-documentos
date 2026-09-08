import time
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.logging import logger
from app.schemas.export import WordExportRequest
from app.services.word_export_service import (
    WordExportEmptyContentError,
    WordExportError,
    WordExportSizeExceededError,
    word_export_service,
)

router = APIRouter(prefix="/export", tags=["Export"])

DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.post(
    "/word",
    summary="Exportar resultado de análisis a documento Microsoft Word (.docx)",
    description=(
        "Recibe un resultado de análisis estructurado (título, contenido Markdown, advertencias opcionales y metadatos) "
        "y genera un archivo .docx descargable 100% en memoria con estilos limpios y profesionales."
    ),
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Documento Word (.docx) generado exitosamente para descarga",
            "content": {DOCX_MIME_TYPE: {}},
        },
        400: {"description": "Título o contenido vacío"},
        413: {"description": "El contenido supera el límite máximo de caracteres permitido"},
        422: {"description": "Error de validación del payload"},
        500: {"description": "Error inesperado durante la generación del documento"},
    },
)
async def export_to_word(request: WordExportRequest) -> StreamingResponse:
    start_time = time.perf_counter()
    try:
        docx_buffer = word_export_service.generate_docx(request)
        filename = word_export_service.sanitize_filename(request.title)
        docx_bytes = docx_buffer.getbuffer().nbytes
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Logging técnico estricto de confidencialidad (cero texto de documento o título)
        logger.info(
            "Exportación a Word completada | Caracteres: %d | Warnings: %d | Tamaño DOCX: %d bytes | Duración: %.2f ms",
            len(request.content),
            len(request.warnings),
            docx_bytes,
            elapsed_ms,
        )

        return StreamingResponse(
            docx_buffer,
            media_type=DOCX_MIME_TYPE,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(docx_bytes),
            },
        )
    except WordExportEmptyContentError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except WordExportSizeExceededError as err:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(err),
        ) from err
    except WordExportError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except Exception as err:
        logger.error("Error inesperado al exportar a Word: %s", err, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error inesperado durante la generación del archivo Word.",
        ) from err
