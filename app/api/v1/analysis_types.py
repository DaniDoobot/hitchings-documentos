from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.analysis_types import (
    AnalysisTypeCreateRequest,
    AnalysisTypeListResponse,
    AnalysisTypeResponse,
    AnalysisTypeUpdateRequest,
)
from app.services.analysis_type_service import analysis_type_service

router = APIRouter(prefix="/analysis-types", tags=["Tipos de Análisis"])


@router.get(
    "",
    response_model=AnalysisTypeListResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar tipos de análisis documental",
    description="Retorna los tipos de análisis disponibles compartidos por el despacho. Permite filtrar inactivos con ?include_inactive=false.",
)
@router.get(
    "/",
    response_model=AnalysisTypeListResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_analysis_types(
    include_inactive: bool = Query(
        True,
        description="Si es True, incluye tipos activos e inactivos en el listado.",
    ),
    db: Session = Depends(get_db),
) -> AnalysisTypeListResponse:
    types = analysis_type_service.list_analysis_types(db, include_inactive=include_inactive)
    items = [AnalysisTypeResponse.model_validate(t) for t in types]
    return AnalysisTypeListResponse(items=items, total=len(items))


@router.get(
    "/{type_id}",
    response_model=AnalysisTypeResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener detalle de un tipo de análisis",
    description="Retorna la configuración detallada de un tipo de análisis por su identificador UUID.",
)
async def get_analysis_type(
    type_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> AnalysisTypeResponse:
    item = analysis_type_service.get_by_id(db, type_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el tipo de análisis con ID '{type_id}'.",
        )
    return AnalysisTypeResponse.model_validate(item)


@router.post(
    "",
    response_model=AnalysisTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo tipo de análisis",
    description="Crea un nuevo tipo de análisis documental compartido para todo el despacho. Accesible para cualquier usuario autenticado.",
)
@router.post(
    "/",
    response_model=AnalysisTypeResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_analysis_type(
    data: AnalysisTypeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalysisTypeResponse:
    created = analysis_type_service.create(db, data, user_id=current_user.id)
    return AnalysisTypeResponse.model_validate(created)


@router.patch(
    "/{type_id}",
    response_model=AnalysisTypeResponse,
    status_code=status.HTTP_200_OK,
    summary="Modificar un tipo de análisis",
    description="Permite actualizar nombre, descripción, instrucciones o activar/desactivar un tipo de análisis. El código permanece inmutable.",
)
async def update_analysis_type(
    type_id: uuid.UUID,
    data: AnalysisTypeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalysisTypeResponse:
    item = analysis_type_service.get_by_id(db, type_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el tipo de análisis con ID '{type_id}'.",
        )
    updated = analysis_type_service.update(db, item, data, user_id=current_user.id)
    return AnalysisTypeResponse.model_validate(updated)
