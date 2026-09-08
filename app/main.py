from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.core.logging import logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(
        "Iniciando servicio hitchings-documentos (ENV=%s, PORT=%s)",
        settings.APP_ENV,
        settings.APP_PORT,
    )
    yield
    logger.info("Deteniendo servicio hitchings-documentos")


app = FastAPI(
    title="HITCHINGS - Análisis de Documentos",
    description="Backend para el procesamiento y análisis de documentos de HITCHINGS.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Error no controlado procesando %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor"},
    )


app.include_router(router)
