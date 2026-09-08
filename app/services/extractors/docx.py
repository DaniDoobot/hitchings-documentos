import io
import zipfile
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.services.extractors.base import BaseExtractor, ExtractionError, ExtractionResult


class DocxExtractor(BaseExtractor):
    """Extractor de texto para archivos DOCX."""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:
        # 1. Validar que es un archivo ZIP válido
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                namelist = zf.namelist()
                # 2. Validar estructura OPC de documento Word (word/document.xml)
                if "word/document.xml" not in namelist:
                    raise ExtractionError(
                        "El archivo no es un documento DOCX válido (falta la estructura word/document.xml)."
                    )
        except zipfile.BadZipFile as exc:
            raise ExtractionError(
                "El archivo no es un documento DOCX válido o está dañado."
            ) from exc

        # 3. Cargar con python-docx
        try:
            doc = Document(io.BytesIO(file_bytes))
        except Exception as exc:
            raise ExtractionError(
                "No se pudo leer el archivo DOCX. El archivo puede estar dañado o tener un formato inválido."
            ) from exc

        content_parts: list[str] = []

        try:
            # iter_inner_content recorre párrafos, títulos, listas y tablas en el orden exacto del documento
            for item in doc.iter_inner_content():
                if isinstance(item, Paragraph):
                    p_text = item.text.strip()
                    if p_text:
                        content_parts.append(p_text)
                elif isinstance(item, Table):
                    table_rows: list[str] = []
                    for row in item.rows:
                        row_cells = [cell.text.strip() for cell in row.cells]
                        row_text = " | ".join(c for c in row_cells if c)
                        if row_text:
                            table_rows.append(row_text)
                    if table_rows:
                        content_parts.append("\n".join(table_rows))
        except Exception as exc:
            raise ExtractionError(
                "Error al extraer contenido del documento DOCX."
            ) from exc

        full_text = "\n\n".join(content_parts)
        warnings: list[str] = []

        if not full_text.strip():
            warnings.append("El documento DOCX no contiene texto extraíble.")

        return ExtractionResult(
            text=full_text,
            page_count=None,
            warnings=warnings,
        )
