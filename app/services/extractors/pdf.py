import io
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services.extractors.base import BaseExtractor, ExtractionError, ExtractionResult


class PdfExtractor(BaseExtractor):
    """Extractor de texto para archivos PDF."""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
        except (PdfReadError, Exception) as exc:
            raise ExtractionError(f"No se pudo leer el archivo PDF '{filename}'. El archivo puede estar dañado o tener un formato inválido.") from exc

        if reader.is_encrypted:
            # Intento de desencriptar si la contraseña es vacía
            try:
                decrypted = reader.decrypt("")
                if decrypted == 0:
                    raise ExtractionError(f"El archivo PDF '{filename}' está protegido por contraseña y no se puede procesar.")
            except Exception as exc:
                raise ExtractionError(f"El archivo PDF '{filename}' está protegido por contraseña y no se puede procesar.") from exc

        page_count = len(reader.pages)
        if page_count == 0:
            raise ExtractionError(f"El archivo PDF '{filename}' no contiene páginas válidas.")

        page_texts: list[str] = []
        empty_pages = 0

        for page_idx, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""

            cleaned = page_text.strip()
            if not cleaned:
                empty_pages += 1
            else:
                page_texts.append(page_text)

        full_text = "\n\n".join(page_texts)
        warnings: list[str] = []

        total_extracted_len = len(full_text.strip())

        if total_extracted_len == 0:
            warnings.append(
                "El documento no contiene texto extraíble o es un documento escaneado. "
                "Se requerirá OCR para procesar su contenido."
            )
        elif total_extracted_len / page_count < 20:
            warnings.append(
                "Se ha extraído muy poco texto del documento en relación al número de páginas. "
                "Es posible que contenga contenido escaneado o imágenes."
            )
        elif empty_pages > 0:
            warnings.append(
                f"{empty_pages} de las {page_count} páginas del documento no contienen texto extraíble."
            )

        return ExtractionResult(
            text=full_text,
            page_count=page_count,
            warnings=warnings,
        )
