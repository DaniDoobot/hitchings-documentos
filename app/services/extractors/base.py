from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


class ExtractionError(Exception):
    """Excepción para errores al procesar o extraer contenido de un documento (formato inválido, corrupto, etc.)."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass
class ExtractionResult:
    text: str
    page_count: Optional[int] = None
    warnings: list[str] = field(default_factory=list)


class BaseExtractor(ABC):
    """Interfaz base para extractores de documentos."""

    @abstractmethod
    def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:
        """Extrae el contenido textual y metadatos del documento en memoria."""
        pass
