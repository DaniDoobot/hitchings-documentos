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
| `GEMINI_TRANSCRIPTION_MODEL` | Modelo de Gemini utilizado para la transcripción de audio | `gemini-3.5-transcribe` |
| `GEMINI_ANALYSIS_MODEL` | Modelo de Gemini previsto para el análisis documental (Bloque 4B) | `gemini-3.8-flash` |
| `GEMINI_TIMEOUT_SECONDS` | Tiempo límite en segundos para llamadas a Gemini | `300` |
| `GEMINI_MAX_RETRIES` | Número de reintentos para fallos transitorios | `2` |
| `MAX_DOCUMENT_SIZE_MB` | Límite técnico por archivo documental (HTTP 413 si se supera) | `25` |
| `MAX_AUDIO_SIZE_MB` | Límite técnico por archivo de audio (HTTP 413 si se supera) | `200` |
| `MAX_TEXT_CHARACTERS` | Límite técnico por texto pegado en caracteres (HTTP 413 si se supera) | `5000000` |

> **Nota de seguridad:** Nunca subas el archivo `.env` con claves reales al control de versiones. Ya se encuentra excluido en `.gitignore`.

---

## Endpoints Disponibles

### 1. Transcripción de Audio (`POST /api/v1/audio/transcribe`)

Recibe un archivo de audio mediante `multipart/form-data`, valida su formato y tamaño en streaming, procesa el audio con la **Gemini Interactions API** oficial (`gemini-3.5-transcribe`) y devuelve la transcripción literal o refinada, junto con metadatos y segmentos de interlocutores.

* **Formatos soportados**: `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.webm`.
* **Parámetros opcionales (query params)**:
  * `mode`: `verbatim` (por defecto, máxima fidelidad textual con lo hablado) o `smart` (limpieza de muletillas, disfluencias y formato refinado).
  * `diarization`: booleano (**`false` por defecto**). Identificación y separación de interlocutores (`diarization_mode: "speaker"`).
    * *Decisión de arquitectura*: Se mantiene en `false` por defecto debido a las limitaciones de duración del proveedor:
      * **Transcripción estándar sin diarización**: Hasta **1 hora** de audio por petición.
      * **Transcripción con diarización**: Máximo **30 minutos** de audio por petición.
      * Dado que HITCHINGS procesa grabaciones extensas de vistas orales y declaraciones judiciales, se prioriza por defecto la ventana de 1 hora.
    * *Compatibilidad*: La diarización solo es compatible con el modo `verbatim`. Si se solicita `mode="smart"` con `diarization=true`, la API devuelve inmediatamente **HTTP 400 Bad Request**.
  * `language`: string opcional con código de idioma BCP-47 (ej. `"es"`, `"es-ES"`, `"en-US"`). Si se omite, Gemini aplica autodetección de idioma de forma automática.
* **Límites de tamaño vs. límites de duración**:
  * `MAX_AUDIO_SIZE_MB` (200 MB por defecto) es un límite técnico de transporte para proteger la memoria RAM del backend mediante streaming y corte anticipado (**HTTP 413**).
  * No garantiza por sí solo que Gemini acepte el audio si este supera la duración máxima admitida (1 hora en estándar, 30 minutos con diarización).
  * Si Gemini rechaza el audio por superar la duración, el error es capturado y mapeado a un mensaje de error claro sin exponer trazas internas.
* **Timestamps**: No se solicitan marcas temporales palabra por palabra (`timestamp_granularities`) para optimizar rendimiento y tiempo de respuesta. La diarización devuelve de forma limpia y fiable el identificador del interlocutor (`spk_1`, `spk_2`, etc.) y el contenido asociado.

#### Flujo Técnico de Privacidad y Eliminación de Audios
```text
Usuario → Backend HITCHINGS → Gemini Files API → Interactions API → Eliminación Remota Inmediata
```
* **Sin almacenamiento permanente**: HITCHINGS no almacena de forma persistente los archivos de audio.
* **Archivos temporales locales**: Se escriben en streaming seguro y se eliminan siempre en un bloque `finally`, tanto si la llamada concluye con éxito como ante cualquier excepción.
* **Eliminación remota garantizada**: El archivo subido a Gemini Files API se elimina de forma explícita e inmediata tras la interacción mediante `client.files.delete(name)`.
* **Confidencialidad absoluta en logs**: No se registran nombres originales de archivos, ni palabras transcritas, ni datos personales. Solo métricas numéricas técnicas (bytes, duración en ms, recuento de palabras).

**Ejemplo de llamada con cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/audio/transcribe?mode=verbatim&diarization=false&language=es-ES" \
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
  "diarization": false,
  "language": "es-ES",
  "detected_language": null,
  "text": "Se abre la sesión de la vista civil ordinaria...",
  "word_count": 8432,
  "character_count": 51678,
  "segments": [],
  "warnings": []
}
```

#### Smoke Test de Verificación Real
Para ejecutar una prueba manual real contra Gemini (cuando se disponga de `GEMINI_API_KEY`):
1. Graba un archivo de audio corto y claro (WAV o MP3) diciendo por ejemplo:
   > *"Hola, esto es una prueba de transcripción del proyecto Hitchings."*
2. Ejecuta el smoke test pasando la ruta del archivo:
   ```bash
   python scripts/smoke_test_gemini_audio.py --audio ruta/al/audio.wav
   ```
Este script carga el audio real con voz, lo valida, lo sube a la Files API de Gemini, invoca la Interactions API oficial, comprueba que se recibe una transcripción no vacía, realiza un matching tolerante de palabras clave (`prueba`, `transcripción`, `Hitchings`) y destruye de forma garantizada el recurso remoto en Gemini (`finally`). Los archivos de prueba (`smoke_audio.*`, `tmp/`, audios) están ignorados en `.gitignore` para no contaminar el repositorio.

---

### 2. Preparación de Texto Pegado (`POST /api/v1/text/prepare`)

Tercera vía de entrada de contenido. Permite recibir texto pegado directamente por el usuario en formato JSON, validando su tamaño y contenido, y aplicando normalización conservadora antes del análisis.

* **Payload de entrada (JSON)**:
  ```json
  {
    "text": "Contenido pegado directamente por el usuario..."
  }
  ```
* **Límite técnico**: Configurado con `MAX_TEXT_CHARACTERS` (5.000.000 de caracteres por defecto). Si se supera, se devuelve **HTTP 413**.
* **Validación**: Rechaza con **HTTP 400** entradas vacías o compuestas únicamente por espacios en blanco.
* **Respuesta (JSON)**:
  ```json
  {
    "text": "Contenido normalizado...",
    "word_count": 120,
    "character_count": 750
  }
  ```

---

### 3. Catálogo de Prompts (`GET /api/v1/prompts`)

Permite al frontend consultar los prompts predefinidos y configuraciones de análisis disponibles en HITCHINGS.

* **Listar prompts activos**: `GET /api/v1/prompts`
  * Parámetro opcional: `?include_inactive=true` (para uso administrativo futuro).
* **Consultar un prompt específico**: `GET /api/v1/prompts/{prompt_id}`
  * Devuelve la configuración completa o **HTTP 404** si no existe.
* **Prompts predefinidos iniciales (IDs estables)**:
  * `executive-summary`: Resumen ejecutivo orientado a síntesis de propósito, hechos y conclusiones.
  * `legal-analysis`: Análisis jurídico estructurado (partes, pretensiones, antecedentes, fundamentos, normativa, fallo, contingencias).
  * `key-points`: Puntos clave priorizados (cifras, fechas, decisiones, obligaciones, riesgos).
  * `timeline`: Cronología estricta y ordenada de acontecimientos y fechas detectadas.
  * `custom-analysis`: Plantilla base flexible para análisis guiado por instrucciones personalizadas del usuario.

#### Arquitectura Conceptual del Pipeline de Análisis (Hacia el Bloque 4B)
```text
┌─────────────────┐
│ 1. Documento    ├─┐
├─────────────────┤ │   ┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│ 2. Audio        ├─┼──>│ Contenido Textual    │ ──> │ Prompt Elegido       │ ──> │ Gemini Analysis      │ ──> Resultado
├─────────────────┤ │   │ Normalizado          │     │ + Opciones de Salida │     │ (gemini-3.8-flash)   │
│ 3. Texto Pegado ├─┘   └──────────────────────┘     └──────────────────────┘     └──────────────────────┘
└─────────────────┘
```

#### Prevención de Prompt Injection Documental
En el pipeline de análisis con LLM, el contenido textual del documento debe ser tratado estrictamente como **DATOS PUROS**, jamás como instrucciones del sistema:
```text
┌─────────────────────────────────────────────────────────────┐
│ SYSTEM INSTRUCTIONS (Rol del modelo, directrices inviolables)│
├─────────────────────────────────────────────────────────────┤
│ PROMPT TEMPLATE (Instrucciones estructuradas del análisis)  │
├─────────────────────────────────────────────────────────────┤
│ USER ANALYSIS INSTRUCTIONS (Instrucciones opcionales)        │
├─────────────────────────────────────────────────────────────┤
│ DOCUMENT CONTENT (Contenido documental aislado como datos)  │
└─────────────────────────────────────────────────────────────┘
```

---

### 4. Ingesta y Extracción Documental (`POST /api/v1/documents/extract`)

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

### 5. Endpoints de Diagnóstico
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
