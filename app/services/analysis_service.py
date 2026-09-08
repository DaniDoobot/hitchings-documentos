import json
import time
from typing import Any

from google.genai.errors import APIError
from pydantic import ValidationError

from app.core.config import settings
from app.core.logging import logger
from app.schemas.analysis import AnalysisModelOutput, AnalysisResponse, AnalysisUsage
from app.schemas.prompts import AnalysisRequest, Prompt
from app.services.analysis_prompt_builder import analysis_prompt_builder
from app.services.gemini_client import (
    GeminiClient,
    GeminiConfigurationError,
    GeminiProviderError,
    gemini_client,
)
from app.services.prompt_service import PromptNotFoundError, prompt_service
from app.services.text_service import EmptyTextError, TextSizeExceededError


class InactivePromptError(Exception):
    """Excepción cuando el prompt solicitado está desactivado (HTTP 400)."""

    def __init__(self, prompt_id: str):
        super().__init__(f"El prompt '{prompt_id}' no está activo actualmente.")


class TokenLimitExceededError(Exception):
    """Excepción cuando el contenido excede el límite operativo de tokens de entrada (HTTP 413)."""

    def __init__(self, token_count: int, max_tokens: int):
        self.token_count = token_count
        self.max_tokens = max_tokens
        super().__init__(
            f"El contenido excede el límite operativo de tokens de entrada ({token_count:,} tokens > máximo {max_tokens:,}). "
            "Reduzca el texto para permitir el análisis en una única interacción."
        )


class AnalysisStructuredOutputError(Exception):
    """Excepción cuando Gemini no devuelve una respuesta JSON conforme al esquema (HTTP 502)."""

    def __init__(self, message: str = "El modelo devolvió una respuesta que no cumple con el esquema estructurado esperado."):
        super().__init__(message)


class DocumentAnalysisService:
    """Servicio para orquestar el análisis documental con Google Gemini Interactions API."""

    def __init__(self, client: GeminiClient | None = None):
        self._client = client

    @property
    def client(self) -> GeminiClient:
        return self._client if self._client is not None else gemini_client

    def validate_request(self, request: AnalysisRequest) -> Prompt:
        """
        Valida que el texto no esté vacío ni exceda el límite de caracteres,
        y que el prompt exista y esté activo.
        """
        raw_text = request.text
        if not raw_text or not raw_text.strip():
            raise EmptyTextError()

        char_len = len(raw_text)
        if char_len > settings.MAX_TEXT_CHARACTERS:
            raise TextSizeExceededError(char_len, settings.MAX_TEXT_CHARACTERS)

        prompt = prompt_service.get_by_id(request.prompt_id)
        if not prompt.is_active:
            raise InactivePromptError(request.prompt_id)

        return prompt

    def count_input_tokens(self, system_instruction: str, user_input: str) -> int:
        """
        Calcula con precisión oficial los tokens totales de entrada
        (system instruction + prompt template + opciones + documento).
        Si el conteo oficial falla, no se aplica estimación aproximada y
        se eleva un error controlado de proveedor.
        """
        genai_client = self.client.get_client()
        try:
            response = genai_client.models.count_tokens(
                model=settings.GEMINI_ANALYSIS_MODEL,
                contents=[
                    f"System: {system_instruction}",
                    f"User: {user_input}",
                ],
            )
            return response.total_tokens or 0
        except APIError as exc:
            logger.error("Error de proveedor Gemini durante token preflight: %s", exc)
            raise GeminiProviderError(
                "No se pudo verificar el número de tokens con el proveedor de IA."
            ) from exc
        except Exception as exc:
            logger.error("Fallo inesperado al contar tokens con Gemini: %s", exc, exc_info=True)
            raise GeminiProviderError(
                "No se pudo verificar el número de tokens con el proveedor de IA."
            ) from exc

    def analyze_document(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        Ejecuta el pipeline de análisis documental:
        1. Validaciones previas
        2. Construcción desacoplada de System Instruction e Input
        3. Token preflight (rechazo HTTP 413 si supera MAX_ANALYSIS_INPUT_TOKENS)
        4. Invocación a client.interactions.create con Structured Output y Thinking Level
        5. Validación estricta con Pydantic del JSON estructurado
        6. Métricas y logging de confidencialidad
        """
        start_time = time.perf_counter()

        # 1. Validaciones
        prompt = self.validate_request(request)

        # 2. Construcción desacoplada de System Instruction e Input
        system_instruction = analysis_prompt_builder.get_system_instruction()
        user_input = analysis_prompt_builder.build_user_input(
            prompt=prompt,
            options=request.options,
            document_text=request.text,
        )

        # 3. Token preflight
        input_tokens_preflight = self.count_input_tokens(system_instruction, user_input)
        if input_tokens_preflight > settings.MAX_ANALYSIS_INPUT_TOKENS:
            logger.warning(
                "Petición de análisis rechazada por tokens: %d tokens (límite: %d)",
                input_tokens_preflight,
                settings.MAX_ANALYSIS_INPUT_TOKENS,
            )
            raise TokenLimitExceededError(input_tokens_preflight, settings.MAX_ANALYSIS_INPUT_TOKENS)

        # 4. Configuración de llamada a Interactions API
        genai_client = self.client.get_client()

        generation_config: dict[str, Any] = {
            "thinking_level": settings.GEMINI_ANALYSIS_THINKING_LEVEL,
        }

        response_format: dict[str, Any] = {
            "type": "text",
            "mime_type": "application/json",
            "schema": AnalysisModelOutput.model_json_schema(),
        }

        try:
            interaction = genai_client.interactions.create(
                model=settings.GEMINI_ANALYSIS_MODEL,
                system_instruction=system_instruction,
                input=user_input,
                generation_config=generation_config,
                response_format=response_format,
            )
        except APIError as exc:
            logger.error("Error de proveedor Gemini durante el análisis: %s", exc)
            exc_msg = str(exc).lower()
            if "deadline" in exc_msg or "timeout" in exc_msg or "timed out" in exc_msg:
                raise GeminiProviderError("Tiempo de espera agotado al comunicarse con el proveedor de IA.") from exc
            raise GeminiProviderError("El proveedor de IA devolvió un error al analizar el documento.") from exc
        except Exception as exc:
            logger.error("Fallo de comunicación con Gemini en análisis: %s", exc, exc_info=True)
            raise GeminiProviderError("No se pudo completar el análisis con el proveedor de IA.") from exc

        # 5. Extracción y parseo seguro con Pydantic
        raw_output_text = getattr(interaction, "output_text", None)
        if not raw_output_text or not raw_output_text.strip():
            logger.warning("Gemini devolvió output_text vacío durante el análisis")
            raise AnalysisStructuredOutputError("El modelo de IA devolvió una respuesta vacía.")

        try:
            data = json.loads(raw_output_text.strip())
            structured_output = AnalysisModelOutput.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as err:
            logger.error("Fallo al validar JSON estructurado de Gemini: %s", err)
            raise AnalysisStructuredOutputError(
                "La respuesta del modelo no cumple con la estructura JSON requerida."
            ) from err

        # 6. Extracción de Usage de tokens
        usage_data = getattr(interaction, "usage", None)
        input_tokens = getattr(usage_data, "total_input_tokens", None) if usage_data else input_tokens_preflight
        output_tokens = getattr(usage_data, "total_output_tokens", None) if usage_data else None
        total_tokens = getattr(usage_data, "total_tokens", None) if usage_data else None

        usage = AnalysisUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # 7. Logging técnico seguro (CONFIDENCIALIDAD TOTAL: cero texto de documento, cero respuesta, cero PII)
        logger.info(
            "Análisis documental completado con éxito | Prompt: %s | Modelo: %s | Nivel Detalle: %s | Formato: %s | Tokens in: %s | Tokens out: %s | Tokens total: %s | Duración: %.2f ms",
            prompt.id,
            settings.GEMINI_ANALYSIS_MODEL,
            request.options.detail_level,
            request.options.output_format,
            str(input_tokens),
            str(output_tokens),
            str(total_tokens),
            elapsed_ms,
        )

        return AnalysisResponse(
            prompt_id=prompt.id,
            prompt_name=prompt.name,
            model=settings.GEMINI_ANALYSIS_MODEL,
            options=request.options,
            title=structured_output.title,
            content=structured_output.content,
            warnings=structured_output.warnings,
            usage=usage,
        )


analysis_service = DocumentAnalysisService()
