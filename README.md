# HITCHINGS - Análisis de Documentos (Parte 2)

Servicio backend en Python + FastAPI dedicado al procesamiento, análisis e interpretación de documentos para el sistema HITCHINGS.

Este servicio es totalmente independiente de la Parte 1 de HITCHINGS y está preparado para ser desplegado en Dokploy e interactuar con la API de Google Gemini (mediante API Key).

---

## Estructura del Proyecto

```text
hitchings-documentos/
├── app/
│   ├── api/          # Rutas y controladores HTTP
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── documents.py
│   ├── core/         # Configuración central (Pydantic Settings) y logging
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── logging.py
│   ├── models/       # Modelos de dominio y persistencia
│   │   └── __init__.py
│   ├── schemas/      # Esquemas de validación Pydantic
│   │   ├── __init__.py
│   │   ├── documents.py
│   │   └── health.py
│   ├── services/     # Lógica de negocio y orquestación
│   │   ├── __init__.py
│   │   ├── document_extractor.py
│   │   └── extractors/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── docx.py
│   │       ├── pdf.py
│   │       └── txt.py
│   ├── utils/        # Utilidades y funciones auxiliares
│   │   ├── __init__.py
│   │   └── text.py
│   ├── __init__.py
│   └── main.py       # Entrada FastAPI, ciclo de vida y handlers de error
├── tests/            # Tests automatizados (pytest)
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_documents.py
│   └── test_health.py
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## Requisitos Previos

- Python 3.12 (versión de referencia) o superior
- Git
- Docker (para despliegue en contenedor / Dokploy)

---

## Variables de Entorno

Crea tu archivo `.env` local copiando la plantilla:

```bash
cp .env.example .env
```

En Windows PowerShell:
```powershell
Copy-Item .env.example .env
```

Variables disponibles:

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `APP_ENV` | Entorno de ejecución (`development`, `staging`, `production`) | `development` |
| `APP_HOST` | Host de escucha del servidor | `0.0.0.0` |
| `APP_PORT` | Puerto de escucha del servidor | `8000` |
| `LOG_LEVEL` | Nivel de logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `GEMINI_API_KEY` | Clave de API de Google Gemini (Direct API Key, sin Vertex AI) | *(vacío)* |
| `MAX_DOCUMENT_SIZE_MB` | Límite técnico inicial por archivo (HTTP 413 si se excede) | `25` |

> **Nota de seguridad:** Nunca subas el archivo `.env` con claves reales al control de versiones. Ya se encuentra excluido en `.gitignore`.

---

## Ingesta y Extracción de Documentos

### Formatos Soportados
- **PDF** (`.pdf`): Extracción por páginas, cálculo real de `page_count`.
- **DOCX** (`.docx`): Extracción de párrafos, títulos, listas y tablas respetando el orden del documento (`page_count: null`).
- **TXT** (`.txt`): Soporte UTF-8 con/sin BOM y fallback de codificación (`page_count: null`).

Cualquier otro formato no soportado (imágenes, Excel, .doc antiguo, etc.) devolverá un error HTTP 415.

### Límite de Tamaño
El tamaño máximo permitido por petición está determinado por `MAX_DOCUMENT_SIZE_MB` (25 MB por defecto). Si se excede, el servidor retorna inmediatamente un error **HTTP 413**.

### Documentos Escaneados y OCR
Si un documento PDF contiene páginas escaneadas o no contiene texto extraíble digital:
- No se inventa contenido.
- **OCR todavía no está implementado en este bloque**.
- El servicio extrae cualquier texto parcial que exista e incluye advertencias explícitas en el campo `warnings` (por ejemplo: `"El documento no contiene texto extraíble o es un documento escaneado. Se requerirá OCR para procesar su contenido."`).

---

## Endpoints Disponibles

### 1. `POST /api/v1/documents/extract`
Extrae el contenido textual y metadatos de un archivo enviado mediante `multipart/form-data`.

**Ejemplo de llamada con cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/documents/extract \
  -F "file=@sentencia.pdf"
```

**Ejemplo de respuesta (JSON):**
```json
{
  "filename": "sentencia.pdf",
  "extension": "pdf",
  "content_type": "application/pdf",
  "size_bytes": 123456,
  "page_count": 25,
  "word_count": 18432,
  "character_count": 112345,
  "text": "Contenido completo extraído y normalizado...",
  "warnings": []
}
```

### 2. Otros Endpoints:
- **`GET /`**: Comprueba que el servicio está activo.
- **`GET /health`**: Healthcheck JSON estructurado (`{"status": "ok", "service": "hitchings-documentos"}`).
- **`GET /docs`**: Documentación interactiva OpenAPI (Swagger UI).
- **`GET /redoc`**: Documentación interactiva ReDoc.

---

## Instalación y Ejecución Local

1. **Crear y activar el entorno virtual**:
   ```bash
   # En Windows PowerShell
   python -m venv .venv
   .venv\Scripts\Activate.ps1

   # En Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Instalar dependencias**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Ejecutar el servidor**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## Ejecución de Tests

Con el entorno virtual activado:

```bash
pytest -v
```

---

## Ejecución con Docker (Dokploy)

1. **Construir la imagen**:
   ```bash
   docker build -t hitchings-documentos .
   ```

2. **Ejecutar el contenedor**:
   ```bash
   docker run -d -p 8000:8000 --env-file .env --name hitchings-documentos-svc hitchings-documentos
   ```

3. **Verificar estado**:
   ```bash
   curl http://localhost:8000/health
   ```
