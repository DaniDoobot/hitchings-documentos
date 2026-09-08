import io
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from docx import Document

from app.core.config import settings


def generate_pdf_bytes(text: str, num_pages: int = 1) -> bytes:
    """Genera un archivo PDF válido en memoria con texto sintético."""
    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + i * 3} 0 R" for i in range(num_pages))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {num_pages} >>".encode())

    for i in range(num_pages):
        page_id = 3 + i * 3
        content_id = page_id + 1
        font_id = page_id + 2
        page_text = f"{text} Pagina {i+1}"
        stream_bytes = f"BT /F1 12 Tf 50 700 Td ({page_text}) Tj ET".encode("latin-1")

        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {content_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode()
        )
        objects.append(
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode() + stream_bytes + b"\nendstream"
        )
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")

    xref_offset = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return out.getvalue()


def generate_blank_pdf_bytes() -> bytes:
    """Genera un PDF válido de 1 página sin texto alguno (simula escaneo sin OCR)."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    bio = io.BytesIO()
    writer.write(bio)
    return bio.getvalue()


def generate_docx_bytes(paragraphs: list[str], table_rows: list[list[str]] | None = None) -> bytes:
    """Genera un archivo DOCX válido en memoria."""
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    if table_rows:
        table = doc.add_table(rows=len(table_rows), cols=len(table_rows[0]))
        for r_idx, row in enumerate(table_rows):
            for c_idx, val in enumerate(row):
                table.cell(r_idx, c_idx).text = val
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


def test_extract_pdf_valid(client: TestClient):
    pdf_bytes = generate_pdf_bytes("Resolucion judicial de prueba", num_pages=2)
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("sentencia_prueba.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "sentencia_prueba.pdf"
    assert data["extension"] == "pdf"
    assert data["content_type"] == "application/pdf"
    assert data["page_count"] == 2
    assert "Resolucion judicial de prueba Pagina 1" in data["text"]
    assert "Resolucion judicial de prueba Pagina 2" in data["text"]
    assert data["word_count"] > 0
    assert data["character_count"] == len(data["text"])
    assert data["size_bytes"] == len(pdf_bytes)
    assert isinstance(data["warnings"], list)


def test_extract_docx_valid(client: TestClient):
    docx_bytes = generate_docx_bytes(
        paragraphs=["Demanda mercantil", "Hechos probados en la causa."],
        table_rows=[["Clausula", "Estado"], ["Primera", "Aceptada"]],
    )
    response = client.post(
        "/api/v1/documents/extract",
        files={
            "file": (
                "demanda.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "demanda.docx"
    assert data["extension"] == "docx"
    assert data["page_count"] is None
    assert "Demanda mercantil" in data["text"]
    assert "Hechos probados en la causa." in data["text"]
    assert "Clausula | Estado" in data["text"]
    assert data["word_count"] > 0
    assert data["character_count"] == len(data["text"])


def test_extract_txt_valid_utf8(client: TestClient):
    content = "Contrato de confidencialidad\n\nCláusula primera: el presente acuerdo regula..."
    txt_bytes = content.encode("utf-8")
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("contrato.txt", txt_bytes, "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "contrato.txt"
    assert data["extension"] == "txt"
    assert data["page_count"] is None
    assert "Contrato de confidencialidad" in data["text"]
    assert data["word_count"] == len(data["text"].split())
    assert data["character_count"] == len(data["text"])


def test_extract_txt_with_bom(client: TestClient):
    content = "Texto jurídico con BOM utf-8-sig."
    txt_bytes = content.encode("utf-8-sig")
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("informe_bom.txt", txt_bytes, "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "Texto jurídico con BOM" in data["text"]
    assert not data["text"].startswith("\ufeff")


def test_extract_unsupported_format_returns_415(client: TestClient):
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("documento.xlsx", b"fake-excel-data", "application/vnd.ms-excel")},
    )

    assert response.status_code == 415
    data = response.json()
    assert "Formato no permitido" in data["detail"]


def test_extract_empty_file_returns_400(client: TestClient):
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("vacio.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "está vacío" in data["detail"]


def test_extract_file_size_exceeded_returns_413(client: TestClient, monkeypatch):
    # Simular límite de 1 KB para probar 413 sin asignar 25 MB en memoria
    monkeypatch.setattr(settings, "MAX_DOCUMENT_SIZE_MB", 1)
    # 2 MB de bytes
    large_bytes = b"A" * (2 * 1024 * 1024)

    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("muy_grande.txt", large_bytes, "text/plain")},
    )

    assert response.status_code == 413
    data = response.json()
    assert "excede el límite máximo" in data["detail"]


def test_extract_scanned_pdf_warning(client: TestClient):
    blank_pdf = generate_blank_pdf_bytes()
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("escaneado.pdf", blank_pdf, "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["page_count"] == 1
    assert data["text"] == ""
    assert data["word_count"] == 0
    assert len(data["warnings"]) > 0
    assert any("OCR" in w or "escaneado" in w for w in data["warnings"])


def test_extract_corrupted_pdf_returns_400(client: TestClient):
    corrupted_bytes = b"%PDF-1.4 corrupt content invalid header and trailer"
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("corrupto.pdf", corrupted_bytes, "application/pdf")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "dañado" in data["detail"] or "formato inválido" in data["detail"]


def test_extract_corrupted_docx_returns_400(client: TestClient):
    corrupted_bytes = b"not a zip file or docx archive"
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("corrupto.docx", corrupted_bytes, "application/vnd.openxmlformats")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "dañado" in data["detail"] or "formato inválido" in data["detail"]


def test_health_and_root_still_work(client: TestClient):
    res_root = client.get("/")
    assert res_root.status_code == 200

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json() == {"status": "ok", "service": "hitchings-documentos"}


def test_confidentiality_logs_do_not_contain_filename_or_text(client: TestClient, caplog):
    """Verifica que NUNCA se registre el filename ni el texto del documento en los logs."""
    import logging
    pdf_bytes = generate_pdf_bytes("Contenido Secreto y Confidencial de Juicio 888", num_pages=1)
    sensitive_filename = "expediente_secreto_garcia_perez.pdf"

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/v1/documents/extract",
            files={"file": (sensitive_filename, pdf_bytes, "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json()["filename"] == sensitive_filename

    # Validar que los logs NO contienen el nombre ni el texto sensible
    assert "expediente_secreto_garcia_perez" not in caplog.text
    assert "Contenido Secreto y Confidencial" not in caplog.text

    # Validar que los logs SÍ contienen la metadata técnica permitida
    assert "Extracción completada" in caplog.text
    assert "Ext: pdf" in caplog.text


def test_extract_non_docx_zip_returns_400(client: TestClient):
    """Verifica que un archivo ZIP genérico que no sea DOCX sea rechazado con HTTP 400."""
    import zipfile
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        zf.writestr("sheet1.xml", "<worksheet>fake excel data</worksheet>")
    fake_zip_bytes = bio.getvalue()

    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("falso.docx", fake_zip_bytes, "application/vnd.openxmlformats")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "no es un documento DOCX válido" in data["detail"]


def test_extract_binary_file_disguised_as_txt_returns_400(client: TestClient):
    """Verifica que un archivo binario (con bytes nulos) con extensión .txt sea rechazado con HTTP 400."""
    binary_bytes = b"CABECERA\x00\x01\x02\x03DATOS_BINARIOS\x00"
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("programa.txt", binary_bytes, "text/plain")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "binarios" in data["detail"] or "no es un documento de texto plano válido" in data["detail"]


def test_chunked_reader_aborts_early():
    """Verifica que read_upload_file_chunked aborta inmediatamente al superar el límite sin leer todo el stream."""
    import asyncio
    from fastapi import UploadFile
    from app.api.v1.documents import read_upload_file_chunked
    from app.services.document_extractor import FileSizeExceededError

    class CountingStream(io.BytesIO):
        def __init__(self, chunk_size: int, total_chunks: int):
            super().__init__()
            self.chunk = b"X" * chunk_size
            self.total_chunks = total_chunks
            self.chunks_read = 0

        def read(self, size: int = -1):
            if self.chunks_read < self.total_chunks:
                self.chunks_read += 1
                return self.chunk
            return b""

    # 10 chunks de 100 KB = 1000 KB. Límite: 250 KB
    stream = CountingStream(chunk_size=100 * 1024, total_chunks=10)
    upload_file = UploadFile(file=stream, filename="stream_test.pdf")

    async def run_test():
        try:
            await read_upload_file_chunked(upload_file, max_bytes=250 * 1024)
            assert False, "Debería haber lanzado FileSizeExceededError"
        except FileSizeExceededError:
            pass

    asyncio.run(run_test())

    # Comprobar que abortó tras leer 3 chunks (300 KB > 250 KB) y no continuó leyendo los 10 chunks
    assert stream.chunks_read == 3
