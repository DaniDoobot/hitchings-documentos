from fastapi import APIRouter, Depends
from app.api.deps import get_current_user, verify_csrf
from app.api.v1.analysis import router as analysis_router
from app.api.v1.audio import router as audio_router
from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.export import router as export_router
from app.api.v1.prompts import router as prompts_router
from app.api.v1.text import router as text_router
from app.schemas.health import HealthResponse

router = APIRouter()

# Rutas de autenticación (login público, me y logout con su propia gestión interna)
router.include_router(auth_router, prefix="/api/v1")

# Rutas funcionales protegidas (requieren sesión activa y CSRF en mutaciones)
auth_dependencies = [Depends(get_current_user), Depends(verify_csrf)]

router.include_router(documents_router, prefix="/api/v1", dependencies=auth_dependencies)
router.include_router(audio_router, prefix="/api/v1", dependencies=auth_dependencies)
router.include_router(text_router, prefix="/api/v1", dependencies=auth_dependencies)
router.include_router(prompts_router, prefix="/api/v1", dependencies=auth_dependencies)
router.include_router(analysis_router, prefix="/api/v1", dependencies=auth_dependencies)
router.include_router(export_router, prefix="/api/v1", dependencies=auth_dependencies)


@router.get("/", summary="Estado del servicio")
async def root():
    return {"message": "Servicio de análisis de documentos HITCHINGS activo"}


@router.get("/health", response_model=HealthResponse, summary="Healthcheck")
async def health():
    return HealthResponse(
        status="ok",
        service="hitchings-documentos",
    )
