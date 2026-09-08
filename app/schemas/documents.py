from typing import Optional
from pydantic import BaseModel, Field


class DocumentExtractResponse(BaseModel):
    filename: str = Field(..., description="Nombre del archivo original sanitizado")
    extension: str = Field(..., description="Extensión del documento (pdf, docx, txt)")
    content_type: str = Field(..., description="MIME type del documento")
    size_bytes: int = Field(..., ge=0, description="Tamaño del archivo en bytes")
    page_count: Optional[int] = Field(
        default=None,
        description="Número real de páginas en PDF. null para DOCX y TXT",
    )
    word_count: int = Field(..., ge=0, description="Conteo de palabras del texto extraído")
    character_count: int = Field(..., ge=0, description="Conteo de caracteres del texto extraído")
    text: str = Field(..., description="Contenido textual normalizado extraído del documento")
    warnings: list[str] = Field(
        default_factory=list,
        description="Lista de advertencias sobre la extracción (p. ej. texto escaso, escaneado)",
    )
