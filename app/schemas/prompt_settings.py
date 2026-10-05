from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, Field, field_validator


class PromptSettingPublic(BaseModel):
    id: uuid.UUID
    key: str
    content: str
    created_at: datetime
    updated_at: datetime
    updated_by_user_id: Optional[uuid.UUID] = None
    updated_by_email: Optional[str] = None

    model_config = {"from_attributes": True}


class PromptSettingUpdate(BaseModel):
    content: str = Field(
        ...,
        min_length=10,
        max_length=30000,
        description="Contenido del prompt base global (mínimo 10 caracteres, máximo 30.000)",
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 10:
            raise ValueError("El contenido del Prompt base debe tener al menos 10 caracteres.")
        return cleaned


class PromptOptionsGuidelines(BaseModel):
    detail_levels: dict[str, str]
    output_formats: dict[str, str]


class EffectiveInstructionsRequest(BaseModel):
    prompt_id: str
    detail_level: str = "standard"
    output_format: str = "sections"
    additional_instructions: Optional[str] = None


class EffectiveInstructionsResponse(BaseModel):
    base_prompt: str
    type_name: str
    type_instructions: str
    detail_level: str
    detail_modifier: str
    output_format: str
    format_modifier: str
    additional_instructions: Optional[str] = None
    effective_full_prompt: str
