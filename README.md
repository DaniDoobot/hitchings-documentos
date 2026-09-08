# HITCHINGS - Análisis de Documentos y Audio (Parte 2)

Servicio backend en Python + FastAPI dedicado al procesamiento, extracción de texto y transcripción de documentos y grabaciones de audio para el sistema HITCHINGS.

Este servicio es totalmente independiente de la Parte 1 de HITCHINGS, está preparado para ser desplegado en Dokploy e interactúa con la API de Google Gemini (mediante API Key directa, sin Vertex AI).

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
│   │       ├── audio.py      # Endpoint de transcripción de audio
│   │       └── documents.py  # Endpoint de extracción de documentos
│   ├── core/         # Configuración central (Pydantic Settings) y logging
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── logging.py
│   ├── models/       # Modelos de dominio y persistencia
│   │   └── __init__.py
│   ├── schemas/      # Esquemas de validación Pydantic
│   │   ├── __init__.py
│   │   ├── audio.py      # Schemas para transcripción y segmentos
│   │   ├── documents.py  # Schemas para extracción documental
│   │   └── health.py     # Schema para healthcheck
│   ├── services/     # Lógica de negocio y orquestación
│   │   ├── __init__.py
│   │   ├── audio_transcription.py # Orquestación de audio y ciclo Files API
│   │   ├── document_extractor.py  # Orquestación de extracción documental
│   │   ├── gemini_client.py       # Wrapper oficial SDK google-genai
│   │   └── extractors/            # Extractores por formato
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── docx.py
│   │       ├── pdf.py
│   │       └── txt.py
│   ├── utils/        # Utilidades y funciones auxiliares
│   │   ├── __init__.py
│   │   └── text.py   # Normalización conservadora y métricas
│   ├── __init__.py
│   └── main.py       # Entrada FastAPI, ciclo de vida y handlers de error
├── tests/            # Tests automatizados (pytest)
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_audio.py     # Tests de transcripción (mocks de Gemini)
│   ├── test_documents.py # Tests de extracción documental
│   └── test_health.py    # Tests de salud y root
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

- Python 3.12 (versión de referencia oficial)
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
| `GEMINI_API_KEY` | Clave de API de Google Gemini (Developer API Key, sin Vertex AI) | *(vacío)* |
| `GEMINI_TRANSCRIPTION_MODEL` | Modelo de Gemini utilizado para la transcripción | `gemini-3.5-transcribe` |
| `GEMINI_TIMEOUT_SECONDS` | Tiempo límite en segundos para llamadas a Gemini | `300` |
| `GEMINI_MAX_RETRIES` | Número de reintentos para fallos transitorios | `2` |
| `MAX_DOCUMENT_SIZE_MB` | Límite técnico por archivo documental (HTTP 413 si se supera) | `25` |
| `MAX_AUDIO_SIZE_MB` | Límite técnico por archivo de audio (HTTP 413 si se supera) | `200` |

> **Nota de seguridad:** Nunca subas el archivo `.env` con claves reales al control de versiones. Ya se encuentra excluido en `.gitignore`.

---

## Endpoints Disponibles

### 1. Transcripción de Audio (`POST /api/v1/audio/transcribe`)

Recibe un archivo de audio mediante `multipart/form-data`, valida su formato y tamaño en streaming, procesa el audio con Gemini Files API y devuelve la transcripción y los segmentos de hablantes.

* **Formatos soportados**: `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.webm`.
* **Parámetros opcionales (query params)**:
  * `mode`: `verbatim` (por defecto, máxima fidelidad textual con lo hablado) o `smart` (limpieza de muletillas y formato ligero).
  * `diarization`: booleano (`true` por defecto). Identificación y etiquetado de interlocutores. *Nota: La diarización solo es compatible con el modo `verbatim`; si se solicita `smart` con `diarization=true` se devolverá HTTP 400.*
* **Límite de tamaño**: Configurado con `MAX_AUDIO_SIZE_MB` (200 MB por defecto). Si se excede, el servidor aborta inmediatamente la recepción con **HTTP 413**.

#### Flujo Técnico de Privacidad y Eliminación de Audios
```text
Usuario → Backend HITCHINGS → Gemini Files API → Transcripción → Eliminación Remota Inmediata
```
* **Sin almacenamiento permanente**: HITCHINGS no almacena de forma persistente los archivos de audio.
* **Archivos temporales locales**: Si se genera un archivo temporal local en el disco del servidor para la transferencia, se elimina siempre en un bloque `finally`, tanto si la llamada concluye con éxito como si se produce un error.
* **Eliminación remota garantizada**: El archivo subido a Gemini Files API se elimina de forma explícita e inmediata tras la transcripción mediante `client.files.delete()`. Si el borrado remoto fallara, se registra una advertencia técnica en los logs sin exponer datos confidenciales.

**Ejemplo de llamada con cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/audio/transcribe?mode=verbatim&diarization=true" \
  -F "file=@grabacion_vista.mp3"
```

**Ejemplo de respuesta (JSON):**
```json
{
  "filename": "grabacion_vista.mp3",
  "extension": "mp3",
  "content_type": "audio/mp3",
  "size_bytes": 38492013,
  "transcription_model": "gemini-3.5-transcribe",
  "mode": "verbatim",
  "diarization": true,
  "text": "Se abre la sesión de la vista civil ordinaria...",
  "word_count": 8432,
  "character_count": 51678,
  "segments": [
    {
      "speaker": "spk_1",
      "text": "Se abre la sesión de la vista civil ordinaria."
    }
  ],
  "warnings": []
}
```

---

### 2. Ingesta y Extracción Documental (`POST /api/v1/documents/extract`)

Extrae el contenido textual y metadatos de documentos jurídicos y corporativos en memoria.

* **Formatos soportados**: `.pdf` (con `page_count` real y detección de escaneados), `.docx` (párrafos y tablas en orden, `page_count: null`), `.txt` (UTF-8 con/sin BOM, `page_count: null`).
* **Límite de tamaño**: 25 MB por defecto (HTTP 413).
* **PDFs escaneados sin OCR**: Si el PDF no contiene texto digital, no se inventa contenido y se devuelven advertencias en `warnings`. *(OCR se implementará en un bloque posterior).*

**Ejemplo de llamada con cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/documents/extract \
  -F "file=@sentencia.pdf"
```

---

### 3. Endpoints de Diagnóstico
- **`GET /`**: Estado general del servicio activo.
- **`GET /health`**: Healthcheck JSON (`{"status": "ok", "service": "hitchings-documentos"}`).
- **`GET /docs`**: Documentación interactiva Swagger UI.
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
