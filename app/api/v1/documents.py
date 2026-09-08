from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas.documents import DocumentExtractResponse
from app.services.document_extractor import (
    EmptyFileError,
    ExtractionError,
    FileSizeExceededError,
    UnsupportedFormatError,
    document_extraction_service,
)

router = APIRouter(prefix="/documents", tags=["Documentos"])

CHUNK_SIZE = 64 * 1024  # 64 KB por fragmento


async def read_upload_file_chunked(file: UploadFile, max_bytes: int) -> bytes:
    """
    Lee un UploadFile en fragmentos (chunks) y se detiene inmediatamente
    en cuanto el total acumulado supera max_bytes, evitando cargar archivos gigantes en RAM.
    """
    buffer = bytearray()
    total_read = 0

    try:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            total_read += len(chunk)
            if total_read > max_bytes:
                # Se aborta la lectura de forma inmediata sin seguir consumiendo el stream
                raise FileSizeExceededError(total_read, max_bytes)
            buffer.extend(chunk)
        return bytes(buffer)
    finally:
        await file.close()


@router.post(
    "/extract",
    response_model=DocumentExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="Extraer texto y metadatos de un documento",
    description="Recibe un archivo (PDF, DOCX o TXT), valida formato y tamaño de forma incremental, extrae y normaliza el texto, y devuelve métricas.",
)
async def extract_document(
    file: UploadFile = File(..., description="Archivo a procesar (PDF, DOCX, TXT)"),
) -> DocumentExtractResponse:
    # 1. Lectura incremental con aborto temprano si supera el límite de tamaño
    try:
        file_bytes = await read_upload_file_chunked(file, settings.max_document_size_bytes)
    except FileSizeExceededError as err:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(err),
        ) from err
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al leer el archivo enviado en la petición.",
        ) from exc

    # 2. Validación y extracción
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
