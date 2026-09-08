from fastapi import APIRouter
from app.api.v1.documents import router as documents_router
from app.schemas.health import HealthResponse

router = APIRouter()
router.include_router(documents_router, prefix="/api/v1")


@router.get("/", summary="Estado del servicio")
async def root():
    return {"message": "Servicio de análisis de documentos HITCHINGS activo"}


@router.get("/health", response_model=HealthResponse, summary="Healthcheck")
async def health():
    return HealthResponse(
        status="ok",
        service="hitchings-documentos",
    )
