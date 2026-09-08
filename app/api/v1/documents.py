from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.documents import DocumentExtractResponse
from app.services.document_extractor import (
    EmptyFileError,
    ExtractionError,
    FileSizeExceededError,
    UnsupportedFormatError,
    document_extraction_service,
)

router = APIRouter(prefix="/documents", tags=["Documentos"])


@router.post(
    "/extract",
    response_model=DocumentExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="Extraer texto y metadatos de un documento",
    description="Recibe un archivo (PDF, DOCX o TXT), valida formato y tamaño, extrae y normaliza el texto, y devuelve métricas.",
)
async def extract_document(
    file: UploadFile = File(..., description="Archivo a procesar (PDF, DOCX, TXT)"),
) -> DocumentExtractResponse:
    try:
        file_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al leer el archivo enviado en la petición.",
        ) from exc
    finally:
        await file.close()

    try:
        return document_extraction_service.extract_document(
            file_bytes=file_bytes,
            raw_filename=file.filename,
            content_type_header=file.content_type,
        )
    except UnsupportedFormatError as err:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(err),
        ) from err
    except FileSizeExceededError as err:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(err),
        ) from err
    except EmptyFileError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except ExtractionError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
