from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, verify_csrf
from app.db.session import get_db
from app.models.user import User
from app.schemas.prompts import AnalysisOptions
from app.schemas.prompt_settings import (
    EffectiveInstructionsRequest,
    EffectiveInstructionsResponse,
    PromptOptionsGuidelines,
    PromptSettingPublic,
    PromptSettingUpdate,
)
from app.services.analysis_prompt_builder import (
    DETAIL_LEVEL_GUIDELINES,
    OUTPUT_FORMAT_GUIDELINES,
    analysis_prompt_builder,
)
from app.services.prompt_service import PromptNotFoundError, prompt_service
from app.services.prompt_setting_service import (
    BasePromptNotFoundError,
    prompt_setting_service,
)

router = APIRouter(prefix="/prompt-settings", tags=["Prompt Settings"])


@router.get(
    "/base",
    response_model=PromptSettingPublic,
    status_code=status.HTTP_200_OK,
    summary="Obtener el Prompt Base global de análisis",
    description="Disponible para todos los usuarios autenticados (admin y user). Retorna el prompt base vigente y metadatos de autoría.",
)
async def get_base_prompt(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PromptSettingPublic:
    try:
        return prompt_setting_service.get_base_prompt_public(db)
    except BasePromptNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.patch(
    "/base",
    response_model=PromptSettingPublic,
    status_code=status.HTTP_200_OK,
    summary="Actualizar el Prompt Base global de análisis",
    description=(
        "Permite a cualquier usuario autenticado (admin o user) modificar sustantivamente el Prompt Base. "
        "Exige token CSRF válido y actualiza la fuente de verdad en PostgreSQL sin requerir despliegue."
    ),
)
async def update_base_prompt(
    update_data: PromptSettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    csrf: None = Depends(verify_csrf),
) -> PromptSettingPublic:
    try:
        return prompt_setting_service.update_base_prompt(
            db=db,
            content=update_data.content,
            user=current_user,
        )
    except BasePromptNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/guidelines",
    response_model=PromptOptionsGuidelines,
    status_code=status.HTTP_200_OK,
    summary="Obtener directivas transparentes de modificadores de salida",
    description="Retorna las directivas exactas asociadas a nivel de profundidad y estructura de formato.",
)
async def get_options_guidelines(
    current_user: User = Depends(get_current_user),
) -> PromptOptionsGuidelines:
    return PromptOptionsGuidelines(
        detail_levels=DETAIL_LEVEL_GUIDELINES,
        output_formats=OUTPUT_FORMAT_GUIDELINES,
    )


@router.post(
    "/preview-instructions",
    response_model=EffectiveInstructionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Generar vista previa transparente de instrucciones efectivas",
    description="Permite inspeccionar exactamente la composición de instrucciones (base + tipo + opciones + adicionales).",
)
async def preview_effective_instructions(
    request: EffectiveInstructionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EffectiveInstructionsResponse:
    try:
        base_prompt = prompt_setting_service.get_base_prompt_content(db)
    except BasePromptNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    try:
        prompt_item = prompt_service.get_by_id(request.prompt_id, db=db)
    except PromptNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    options = AnalysisOptions(
        detail_level=request.detail_level,
        output_format=request.output_format,
        additional_instructions=request.additional_instructions,
    )

    data = analysis_prompt_builder.build_effective_instructions(
        base_prompt=base_prompt,
        type_name=prompt_item.name,
        type_instructions=prompt_item.instructions,
        options=options,
    )

    return EffectiveInstructionsResponse(**data)
