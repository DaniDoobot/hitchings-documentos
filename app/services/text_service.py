from app.core.config import settings
from app.core.logging import logger
from app.schemas.text import TextPrepareResponse
from app.utils.text import calculate_text_metrics, normalize_text


class EmptyTextError(Exception):
    """Excepción cuando el texto está vacío o compuesto exclusivamente de espacios en blanco (HTTP 400)."""

    def __init__(self, message: str = "El texto proporcionado está vacío o solo contiene espacios en blanco."):
        super().__init__(message)


class TextSizeExceededError(Exception):
    """Excepción cuando el texto supera el límite técnico permitido de caracteres (HTTP 413)."""

    def __init__(self, character_count: int, max_characters: int):
        self.character_count = character_count
        self.max_characters = max_characters
        super().__init__(
            f"El texto excede el límite máximo permitido de {max_characters:,} caracteres (recibidos: {character_count:,})."
        )


class TextPreparationService:
    """Servicio para validar, limpiar y normalizar texto pegado por el usuario."""

    def prepare_text(self, raw_text: str) -> TextPrepareResponse:
        """
        Valida que exista texto, verifica el límite de caracteres,
        aplica normalización conservadora y retorna las métricas.
        """
        if not raw_text or not raw_text.strip():
            logger.warning("Rechazada petición de texto: entrada vacía o solo espacios")
            raise EmptyTextError()

        char_len = len(raw_text)
        max_chars = settings.MAX_TEXT_CHARACTERS

        if char_len > max_chars:
            logger.warning(
                "Rechazada petición de texto por tamaño: %d caracteres (máximo: %d)",
                char_len,
                max_chars,
            )
            raise TextSizeExceededError(character_count=char_len, max_characters=max_chars)

        # Normalización conservadora estandarizada
        normalized = normalize_text(raw_text)

        if not normalized:
            logger.warning("Rechazada petición de texto: normalización resultó en texto vacío")
            raise EmptyTextError()

        word_count, character_count = calculate_text_metrics(normalized)

        # Log confidencial: cero contenido del texto, solo métricas
        logger.info(
            "Texto preparado con éxito | Caracteres recibidos: %d | Caracteres norm.: %d | Palabras: %d",
            char_len,
            character_count,
            word_count,
        )

        return TextPrepareResponse(
            text=normalized,
            word_count=word_count,
            character_count=character_count,
        )


text_preparation_service = TextPreparationService()
