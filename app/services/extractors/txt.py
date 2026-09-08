from app.services.extractors.base import BaseExtractor, ExtractionError, ExtractionResult


class TxtExtractor(BaseExtractor):
    """Extractor de texto para archivos TXT con detección robusta de codificación y rechazo de binarios."""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:
        # 1. Detección de contenido binario mediante bytes nulos
        if b"\x00" in file_bytes:
            raise ExtractionError(
                "El archivo contiene caracteres binarios nulos y no es un documento de texto plano válido."
            )

        decoded_text: str | None = None

        # 2. Intentar codificaciones en orden de prioridad
        candidate_encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]

        for encoding in candidate_encodings:
            try:
                candidate = file_bytes.decode(encoding)
                # Si se utilizó un fallback permisivo como latin-1, verificar que no sea basura binaria
                if encoding in ("cp1252", "latin-1") and len(candidate) > 0:
                    # Contar caracteres de control no estándar (excepto \n, \r, \t)
                    control_chars = sum(1 for c in candidate[:1024] if ord(c) < 32 and c not in ("\n", "\r", "\t"))
                    if control_chars / min(len(candidate), 1024) > 0.15:
                        continue  # Demasiados caracteres de control, no es texto legible
                decoded_text = candidate
                break
            except UnicodeDecodeError:
                continue

        if decoded_text is None:
            raise ExtractionError(
                "No se pudo decodificar el archivo de texto. Codificación no compatible o contenido binario."
            )

        warnings: list[str] = []
        if not decoded_text.strip():
            warnings.append("El archivo de texto está vacío o contiene únicamente espacios en blanco.")

        return ExtractionResult(
            text=decoded_text,
            page_count=None,
            warnings=warnings,
        )
