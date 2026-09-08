from typing import List, Literal
from pydantic import BaseModel, Field


class Prompt(BaseModel):
    """Configuración reutilizable de análisis documental."""
    id: str = Field(..., description="Identificador único y estable del prompt (ej. 'legal-analysis')")
    name: str = Field(..., description="Nombre visible del prompt")
    description: str = Field(..., description="Descripción detallada de la finalidad del análisis")
    instructions: str = Field(..., description="Instrucciones del sistema y de análisis que se enviarán al modelo")
    is_active: bool = Field(default=True, description="Indica si el prompt está activo y disponible")
    is_system: bool = Field(default=True, description="Indica si es un prompt predefinido del sistema")
    created_at: str = Field(..., description="Fecha y hora de creación en formato ISO 8601")
    updated_at: str = Field(..., description="Fecha y hora de última actualización en formato ISO 8601")


class PromptListResponse(BaseModel):
    """Listado estructurado de prompts disponibles."""
    prompts: List[Prompt] = Field(..., description="Colección de prompts disponibles")
    total: int = Field(..., ge=0, description="Total de prompts retornados en la consulta")


class AnalysisOptions(BaseModel):
    """Parámetros ajustables para el análisis documental."""
    detail_level: Literal["brief", "standard", "detailed"] = Field(
        default="standard",
        description="Nivel de detalle del análisis: 'brief' (resumido), 'standard' (estándar), 'detailed' (exhaustivo).",
    )
    output_format: Literal["prose", "sections", "bullet_points"] = Field(
        default="sections",
        description="Formato de salida deseado: 'prose' (párrafos continuos), 'sections' (apartados temáticos), 'bullet_points' (listas viñetadas).",
    )
    additional_instructions: str | None = Field(
        default=None,
        max_length=10000,
        description="Instrucciones adicionales o preguntas específicas del usuario para guiar el análisis (máximo 10.000 caracteres).",
    )


class AnalysisRequest(BaseModel):
    """Esquema para una futura solicitud de análisis documental con Gemini (Bloque 4B)."""
    text: str = Field(
        ...,
        description="Contenido textual normalizado que será analizado como datos puros por el modelo",
    )
    prompt_id: str = Field(
        ...,
        description="Identificador del prompt configurado a aplicar (ej. 'legal-analysis')",
    )
    options: AnalysisOptions = Field(
        default_factory=AnalysisOptions,
        description="Opciones y parámetros configurables de salida y enfoque",
    )
