from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.prompts import Prompt, PromptListResponse
from app.services.prompt_service import PromptNotFoundError, prompt_service

router = APIRouter(prefix="/prompts", tags=["Prompts"])


@router.get(
    "",
    response_model=PromptListResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar catálogo de prompts disponibles",
    description=(
        "Obtiene los prompts configurados en el sistema. Por defecto retorna únicamente los activos. "
        "Permite el parámetro ?include_inactive=true para tareas administrativas o de auditoría."
    ),
)
@router.get(
    "/",
    response_model=PromptListResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_prompts(
    include_inactive: bool = Query(
        False,
        description="Si es True, incluye en el listado prompts inactivos.",
    ),
) -> PromptListResponse:
    prompts = prompt_service.get_all(include_inactive=include_inactive)
    return PromptListResponse(prompts=prompts, total=len(prompts))


@router.get(
    "/{prompt_id}",
    response_model=Prompt,
    status_code=status.HTTP_200_OK,
    summary="Obtener detalle de un prompt específico",
    description="Retorna la configuración completa de un prompt según su identificador único (ej. 'legal-analysis').",
)
async def get_prompt(prompt_id: str) -> Prompt:
    try:
        return prompt_service.get_by_id(prompt_id)
    except PromptNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
