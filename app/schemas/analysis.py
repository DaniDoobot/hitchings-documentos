from typing import List
from pydantic import BaseModel, Field

from app.schemas.prompts import AnalysisOptions


class AnalysisModelOutput(BaseModel):
    """
    Estructura esperada directamente del modelo de IA mediante Structured Outputs.
    """
    title: str = Field(..., description="Título breve y descriptivo del análisis efectuado")
    content: str = Field(..., description="Cuerpo completo del análisis formateado en Markdown")
    warnings: List[str] = Field(
        default_factory=list,
        description="Advertencias sobre datos faltantes, limitaciones o ambigüedades en el documento",
    )


class AnalysisUsage(BaseModel):
    """Métricas de consumo de tokens del proveedor Gemini."""
    input_tokens: int | None = Field(default=None, ge=0, description="Tokens consumidos en el prompt de entrada")
    output_tokens: int | None = Field(default=None, ge=0, description="Tokens consumidos en la respuesta generada")
    total_tokens: int | None = Field(default=None, ge=0, description="Total de tokens facturables de la interacción")


class AnalysisResponse(BaseModel):
    """Respuesta pública estructurada del endpoint de análisis."""
    prompt_id: str = Field(..., description="Identificador del prompt ejecutado")
    prompt_name: str = Field(..., description="Nombre del prompt ejecutado")
    model: str = Field(..., description="Modelo de IA utilizado")
    options: AnalysisOptions = Field(..., description="Opciones aplicadas durante el análisis")
    title: str = Field(..., description="Título del análisis")
    content: str = Field(..., description="Contenido completo del análisis en Markdown")
    warnings: List[str] = Field(default_factory=list, description="Lista de advertencias resultantes")
    usage: AnalysisUsage = Field(..., description="Desglose del consumo de tokens")
