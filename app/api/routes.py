from fastapi import APIRouter
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/", summary="Estado del servicio")
async def root():
    return {"message": "Servicio de análisis de documentos HITCHINGS activo"}


@router.get("/health", response_model=HealthResponse, summary="Healthcheck")
async def health():
    return HealthResponse(
        status="ok",
        service="hitchings-documentos",
    )
