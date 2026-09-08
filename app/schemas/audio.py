from typing import List
from pydantic import BaseModel, Field


class SpeakerSegment(BaseModel):
    """Segmento de transcripción asociado a un interlocutor identificado."""
    speaker: str = Field(..., description="Identificador del hablante (ej. 'spk_1', 'spk_2')")
    text: str = Field(..., description="Texto emitido por el hablante en este segmento")


class AudioTranscribeResponse(BaseModel):
    """Respuesta estructurada para la transcripción de audio."""
    filename: str = Field(..., description="Nombre del archivo original sanitizado")
    extension: str = Field(..., description="Extensión del archivo de audio")
    content_type: str = Field(..., description="MIME type del audio")
    size_bytes: int = Field(..., ge=0, description="Tamaño del archivo en bytes")
    transcription_model: str = Field(..., description="Modelo utilizado para la transcripción")
    mode: str = Field(..., description="Modo de transcripción utilizado ('verbatim' o 'smart')")
    diarization: bool = Field(..., description="Indica si se solicitó diarización de hablantes")
    text: str = Field(..., description="Transcripción completa normalizada")
    word_count: int = Field(..., ge=0, description="Conteo total de palabras del texto transcrito")
    character_count: int = Field(..., ge=0, description="Conteo total de caracteres del texto transcrito")
    segments: List[SpeakerSegment] = Field(
        default_factory=list,
        description="Lista de segmentos por hablante si hubo diarización disponible",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Lista de advertencias sobre el proceso de transcripción",
    )
