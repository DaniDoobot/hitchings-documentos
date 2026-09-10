from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class AnalysisTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str
    instructions: str
    is_active: bool
    created_by_user_id: Optional[uuid.UUID] = None
    updated_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class AnalysisTypeListResponse(BaseModel):
    items: List[AnalysisTypeResponse]
    total: int


class AnalysisTypeCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Nombre del tipo de análisis")
    description: str = Field(default="", max_length=1000, description="Descripción de la finalidad")
    instructions: str = Field(..., min_length=10, max_length=15000, description="Instrucciones especializadas")
    is_active: bool = Field(default=True, description="Estado activo o inactivo")


class AnalysisTypeUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150, description="Nombre del tipo de análisis")
    description: Optional[str] = Field(default=None, max_length=1000, description="Descripción de la finalidad")
    instructions: Optional[str] = Field(default=None, min_length=10, max_length=15000, description="Instrucciones especializadas")
    is_active: Optional[bool] = Field(default=None, description="Estado activo o inactivo")
