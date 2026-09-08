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
│   │       ├── analysis.py   # Endpoint de análisis documental con Gemini
│   │       ├── audio.py      # Endpoint de transcripción de audio
│   │       ├── documents.py  # Endpoint de extracción de documentos
│   │       ├── prompts.py    # Catálogo de prompts configurados
│   │       └── text.py       # Preparación de texto pegado
│   ├── core/         # Configuración central (Pydantic Settings) y logging
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── logging.py
│   ├── data/         # Almacenamiento versionado de configuración
│   │   └── default_prompts.json
│   ├── models/       # Modelos de dominio
│   │   └── __init__.py
│   ├── schemas/      # Esquemas de validación Pydantic
│   │   ├── __init__.py
│   │   ├── analysis.py   # Schemas para análisis y structured outputs
│   │   ├── audio.py      # Schemas para transcripción y segmentos
│   │   ├── documents.py  # Schemas para extracción documental
│   │   ├── health.py     # Schema para healthcheck
│   │   ├── prompts.py    # Schemas para catálogo y peticiones de análisis
│   │   └── text.py       # Schemas para preparación de texto
│   ├── services/     # Lógica de negocio y orquestación
│   │   ├── __init__.py
│   │   ├── analysis_prompt_builder.py # Constructor desacoplado System/Input
│   │   ├── analysis_service.py        # Orquestación de análisis y Gemini Interactions
│   │   ├── audio_transcription.py     # Orquestación de audio y ciclo Files API
│   │   ├── document_extractor.py      # Orquestación de extracción documental
│   │   ├── gemini_client.py           # Wrapper oficial SDK google-genai
│   │   ├── prompt_service.py          # Gestión y consulta del catálogo de prompts
│   │   ├── text_service.py            # Validación y normalización de texto
│   │   └── extractors/                # Extractores por formato
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
├── scripts/          # Scripts de validación y smoke tests manuales
│   ├── smoke_test_gemini_analysis.py # Smoke test real de análisis documental
│   └── smoke_test_gemini_audio.py    # Smoke test real de transcripción de audio
├── tests/            # Tests automatizados (pytest, 100% mocks)
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_analysis.py  # Tests de análisis y structured outputs (Gemini mockeado)
│   ├── test_audio.py     # Tests de transcripción (Gemini mockeado)
│   ├── test_documents.py # Tests de extracción documental
│   ├── test_health.py    # Tests de salud y root
│   ├── test_prompts.py   # Tests del catálogo de prompts y esquemas
│   └── test_text.py      # Tests de preparación de texto
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
| `GEMINI_ANALYSIS_MODEL` | Modelo de Gemini utilizado para el análisis documental | `gemini-3.8-flash` |
| `GEMINI_ANALYSIS_THINKING_LEVEL` | Nivel de razonamiento del modelo de análisis (`low`, `medium`, `high`) | `medium` |
| `GEMINI_TIMEOUT_SECONDS` | Tiempo límite en segundos para llamadas a Gemini | `300` |
| `GEMINI_MAX_RETRIES` | Número de reintentos para fallos transitorios | `2` |
| `MAX_DOCUMENT_SIZE_MB` | Límite técnico por archivo documental (HTTP 413 si se supera) | `25` |
| `MAX_AUDIO_SIZE_MB` | Límite técnico por archivo de audio (HTTP 413 si se supera) | `200` |
| `MAX_TEXT_CHARACTERS` | Límite técnico por texto pegado en caracteres (HTTP 413 si se supera) | `5000000` |
| `MAX_ANALYSIS_INPUT_TOKENS` | Límite operativo de tokens de entrada para análisis individual (HTTP 413) | `900000` |

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

---

### 4. Análisis Documental con Gemini (`POST /api/v1/analysis`)

Núcleo del procesamiento analítico de HITCHINGS. Permite someter cualquier contenido textual normalizado (procedente de extracción documental PDF/DOCX/TXT, transcripción de audio o texto pegado) a un examen riguroso mediante la API oficial **Google Gemini Interactions API**, aplicando el prompt seleccionado y sus parámetros de configuración.

#### Pipeline Técnico de Ejecución
```text
CONTENIDO NORMALIZADO
       ↓
VALIDACIONES PREVIAS (no vacío, límite caracteres, existencia y actividad del prompt)
       ↓
TOKEN PREFLIGHT (conteo oficial con count_tokens, rechazo HTTP 413 si > MAX_ANALYSIS_INPUT_TOKENS)
       ↓
PROMPT BUILDER DESACOPLADO (System Instruction inviolable vs. User Input estructurado)
       ↓
GEMINI INTERACTIONS API (gemini-3.8-flash, thinking_level, schema JSON)
       ↓
STRUCTURED OUTPUT (extracción y validación estricta con Pydantic)
       ↓
RESPUESTA API (título, contenido en Markdown, advertencias, métricas de tokens)
```

#### Características Técnicas y Directivas de Diseño
* **Modelo Configurable**: Gobernado por la variable de entorno `GEMINI_ANALYSIS_MODEL` (`gemini-3.8-flash` por defecto), sin nombres hardcodeados.
* **Nivel de Pensamiento (Thinking Level)**: Configurable mediante `GEMINI_ANALYSIS_THINKING_LEVEL` (`medium` por defecto; valores admitidos: `low`, `medium`, `high`).
* **Límite Operativo de Tokens (Pre-vuelo)**: Configurado con `MAX_ANALYSIS_INPUT_TOKENS` (900.000 tokens por defecto). Antes de invocar la generación, se realiza un conteo oficial de tokens (`client.models.count_tokens`). Si se supera el límite operativo, se rechaza de inmediato con **HTTP 413** sin invocar `interactions.create`.
* **Cero Herramientas Externas**: No se habilitan ni conectan herramientas como Google Search, URL Context, File Search, Function Calling ni RAG. El análisis se realiza estrictamente sobre el material suministrado.
* **Sin Persistencia**: Ni los textos sometidos ni las respuestas generadas se almacenan en disco ni en base de datos.
* **Separación de Instrucciones y Mitigación de Prompt Injection**:
  * `system_instruction`: Se transmiten de forma nativa e independiente las directrices inviolables del sistema: deber de veracidad estricta, prohibición de invención/alucinación, obligación de reportar omisiones y directriz explícita de tratar el contenido documental como datos pasivos no confiables.
  * `input`: Contiene de manera delimitada por capas la plantilla del prompt, las opciones de salida (`detail_level`, `output_format`), las instrucciones adicionales del usuario y el texto documental encapsulado dentro de un bloque ` ```document_content `. Cualquier directriz imperativa encontrada dentro del documento ("ignora instrucciones", etc.) es tratada como dato textual objeto de examen, no como orden ejecutable.
* **Salida Estructurada Fiable (Structured Output)**: La petición a Gemini especifica `response_format` con esquema JSON derivado del modelo Pydantic `AnalysisModelOutput` (`title`, `content`, `warnings`). La respuesta recibida es validada estrictamente con Pydantic; cualquier desviación o JSON incompleto es capturado y mapeado a **HTTP 502**.
* **Métricas de Uso Expuestas**: El bloque `usage` (`input_tokens`, `output_tokens`, `total_tokens`) se extrae de `interaction.usage` y se devuelve en la respuesta para facilitar el control de consumo.
* **Confidencialidad Técnica en Logs**: Se mantiene una política estricta de no registrar textos documentales, fragmentos, respuestas generadas, claves de API ni directrices completas del prompt. Únicamente se registran métricas cuantitativas técnicas (prompt_id, modelo, niveles configurados, recuentos de tokens y duración en milisegundos).

**Ejemplo de llamada con cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "text": "El 3 de marzo de 2026, Empresa Alfa y Empresa Beta firmaron un contrato de servicios por 12 meses...",
    "prompt_id": "key-points",
    "options": {
      "detail_level": "standard",
      "output_format": "sections",
      "additional_instructions": "Focalizar en las penalizaciones por retraso."
    }
  }'
```

**Ejemplo de respuesta (JSON):**
```json
{
  "prompt_id": "key-points",
  "prompt_name": "Puntos clave",
  "model": "gemini-3.8-flash",
  "options": {
    "detail_level": "standard",
    "output_format": "sections",
    "additional_instructions": "Focalizar en las penalizaciones por retraso."
  },
  "title": "Análisis de Puntos Clave: Contrato de Prestación de Servicios",
  "content": "## 1. Elementos Esenciales\n- **Firma del acuerdo:** Celebración de contrato bilateral...\n\n## 2. Régimen Sancionador\n- Penalización económica de 500 euros...",
  "warnings": [
    "El documento no especifica el precio total ni las obligaciones económicas de Empresa Beta."
  ],
  "usage": {
    "input_tokens": 807,
    "output_tokens": 705,
    "total_tokens": 1808
  }
}
```

#### Smoke Test de Verificación Real
Para verificar de forma aislada y puntual la integración real con Gemini:
```bash
python scripts/smoke_test_gemini_analysis.py --prompt key-points
```
Realiza una única interacción real utilizando un texto sintético breve y no confidencial, validando autenticación, conteo previo de tokens, llamada a `interactions.create`, validación del esquema Pydantic y reporte de uso.

---

### 5. Ingesta y Extracción Documental (`POST /api/v1/documents/extract`)

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

### 6. Endpoints de Diagnóstico
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
