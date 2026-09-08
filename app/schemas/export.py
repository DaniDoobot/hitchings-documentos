from pydantic import BaseModel, Field


class WordExportMetadata(BaseModel):
    """Metadatos opcionales asociados al análisis para exportación."""

    prompt_name: str | None = Field(
        default=None,
        description="Nombre descriptivo del prompt de análisis utilizado",
    )
    model: str | None = Field(
        default=None,
        description="Identificador del modelo de IA (metadato técnico preserved)",
    )


class WordExportRequest(BaseModel):
    """Esquema de solicitud para exportación de resultado de análisis a documento Word."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Título principal del análisis para encabezar el documento Word",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Contenido completo del análisis en formato Markdown",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Lista opcional de advertencias u omisiones detectadas durante el análisis",
    )
    metadata: WordExportMetadata | None = Field(
        default=None,
        description="Metadatos contextuales opcionales del análisis",
    )
