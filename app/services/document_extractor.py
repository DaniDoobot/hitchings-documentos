import os
import time
from pathlib import Path
from typing import Dict, Type

from app.core.config import settings
from app.core.logging import logger
from app.schemas.documents import DocumentExtractResponse
from app.services.extractors.base import BaseExtractor, ExtractionError, ExtractionResult
from app.services.extractors.docx import DocxExtractor
from app.services.extractors.pdf import PdfExtractor
from app.services.extractors.txt import TxtExtractor
from app.utils.text import calculate_text_metrics, normalize_text


class UnsupportedFormatError(Exception):
    """Excepción para formatos de archivo no permitidos (HTTP 415)."""

    def __init__(self, extension: str):
        self.extension = extension
        super().__init__(
            f"Formato no permitido: '.{extension}'. Formatos soportados: pdf, docx, txt."
        )


class FileSizeExceededError(Exception):
    """Excepción cuando el archivo excede el tamaño máximo permitido (HTTP 413)."""

    def __init__(self, size_bytes: int, max_bytes: int):
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
        max_mb = max_bytes / (1024 * 1024)
        super().__init__(
            f"El archivo excede el límite máximo permitido de {max_mb:.0f} MB."
        )


class EmptyFileError(Exception):
    """Excepción cuando el archivo recibido está vacío (HTTP 400)."""

    def __init__(self, filename: str):
        super().__init__(f"El archivo '{filename}' está vacío (0 bytes).")


class DocumentExtractionService:
    """Servicio de validación, orquestación y extracción de texto de documentos."""

    ALLOWED_EXTENSIONS: set[str] = {"pdf", "docx", "txt"}

    CONTENT_TYPE_MAPPING: Dict[str, str] = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
    }

    _EXTRACTORS: Dict[str, Type[BaseExtractor]] = {
        "pdf": PdfExtractor,
        "docx": DocxExtractor,
        "txt": TxtExtractor,
    }

    def sanitize_filename(self, filename: str | None) -> str:
        """Sanitiza el nombre del archivo eliminando rutas de directorios."""
        if not filename:
            return "documento_sin_nombre"
        return Path(filename).name

    def get_extension(self, filename: str) -> str:
        """Obtiene la extensión en minúsculas sin el punto."""
        parts = filename.rsplit(".", 1)
        if len(parts) > 1:
            return parts[1].lower()
        return ""

    def extract_document(
        self,
        file_bytes: bytes,
        raw_filename: str | None,
        content_type_header: str | None = None,
    ) -> DocumentExtractResponse:
        """
        Valida, extrae y normaliza el contenido de un documento en memoria.
        """
        start_time = time.perf_counter()
        filename = self.sanitize_filename(raw_filename)
        extension = self.get_extension(filename)
        size_bytes = len(file_bytes)

        # 1. Validar extensión permitida
        if extension not in self.ALLOWED_EXTENSIONS:
            logger.warning(
                "Intento de subida con formato no permitido. Extension: '%s', Size: %d bytes",
                extension,
                size_bytes,
            )
            raise UnsupportedFormatError(extension)

        # 2. Validar archivo no vacío
        if size_bytes == 0:
            logger.warning("Intento de subida de archivo vacío: '%s'", filename)
            raise EmptyFileError(filename)

        # 3. Validar límite técnico de tamaño
        if size_bytes > settings.max_document_size_bytes:
            logger.warning(
                "Archivo excede el límite de tamaño. Archivo: '%s', Size: %d, Max: %d",
                filename,
                size_bytes,
                settings.max_document_size_bytes,
            )
            raise FileSizeExceededError(size_bytes, settings.max_document_size_bytes)

        # 4. Determinar content_type
        content_type = self.CONTENT_TYPE_MAPPING.get(extension, content_type_header or "application/octet-stream")

        # 5. Instanciar extractor y extraer
        extractor_cls = self._EXTRACTORS[extension]
        extractor = extractor_cls()

        try:
            extraction_result: ExtractionResult = extractor.extract(file_bytes, filename)
        except ExtractionError:
            raise
        except Exception as exc:
            logger.error("Error no esperado en extractor %s para '%s': %s", extension, filename, exc, exc_info=True)
            raise ExtractionError(f"Error interno procesando el archivo '{filename}'.") from exc

        # 6. Normalización conservadora del texto
        normalized_text = normalize_text(extraction_result.text)

        # 7. Cálculo de métricas
        word_count, character_count = calculate_text_metrics(normalized_text)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # 8. Log técnico de operación (sin registrar contenido textual ni PII)
        logger.info(
            "Extracción completada: '%s' | Ext: %s | Tamaño: %d B | Páginas: %s | Palabras: %d | Tiempo: %.2f ms | Warnings: %d",
            filename,
            extension,
            size_bytes,
            str(extraction_result.page_count) if extraction_result.page_count is not None else "null",
            word_count,
            elapsed_ms,
            len(extraction_result.warnings),
        )

        return DocumentExtractResponse(
            filename=filename,
            extension=extension,
            content_type=content_type,
            size_bytes=size_bytes,
            page_count=extraction_result.page_count,
            word_count=word_count,
            character_count=character_count,
            text=normalized_text,
            warnings=extraction_result.warnings,
        )


document_extraction_service = DocumentExtractionService()
