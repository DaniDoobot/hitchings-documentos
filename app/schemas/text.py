from pydantic import BaseModel, Field


class TextPrepareRequest(BaseModel):
    """Solicitud de preparación de texto pegado directamente por el usuario."""
    text: str = Field(
        ...,
        description="Contenido textual pegado por el usuario para su preparación previa al análisis",
    )


class TextPrepareResponse(BaseModel):
    """Respuesta con el texto normalizado conservadoramente y sus métricas."""
    text: str = Field(
        ...,
        description="Contenido textual normalizado y listo para el análisis",
    )
    word_count: int = Field(
        ...,
        ge=0,
        description="Conteo total de palabras del texto normalizado",
    )
    character_count: int = Field(
        ...,
        ge=0,
        description="Conteo total de caracteres del texto normalizado",
    )
