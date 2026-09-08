from app.services.extractors.base import BaseExtractor, ExtractionError, ExtractionResult


class TxtExtractor(BaseExtractor):
    """Extractor de texto para archivos TXT con detección robusta de codificación."""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:
        decoded_text: str | None = None

        # Intentar codificaciones en orden de prioridad: UTF-8 con/sin BOM, luego cp1252/latin-1
        candidate_encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]

        for encoding in candidate_encodings:
            try:
                decoded_text = file_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if decoded_text is None:
            raise ExtractionError(
                f"No se pudo decodificar el archivo de texto '{filename}'. Codificación no compatible."
            )

        warnings: list[str] = []
        if not decoded_text.strip():
            warnings.append("El archivo de texto está vacío o contiene únicamente espacios en blanco.")

        return ExtractionResult(
            text=decoded_text,
            page_count=None,
            warnings=warnings,
        )
