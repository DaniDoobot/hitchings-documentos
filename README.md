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
│   │       ├── export.py     # Endpoint de exportación a Word (.docx)
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
│   │   ├── export.py     # Schemas para exportación a Word
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
│   │   ├── word_export_service.py     # Generación en memoria de documentos Word (.docx)
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
├── frontend/         # Interfaz Web (React + TypeScript + Vite)
│   ├── src/
│   │   ├── __tests__/    # Tests frontend (Vitest + RTL)
│   │   ├── api/          # Cliente API tipado y servicios
│   │   ├── components/   # Componentes modulares de interfaz
│   │   ├── types/        # Modelos y contratos TypeScript
│   │   ├── App.tsx       # Componente raíz y coordinación de estado
│   │   ├── index.css     # Estilos sobrios corporativos nativos
│   │   └── main.tsx      # Punto de entrada de React
│   ├── .dockerignore
│   ├── docker-entrypoint.sh # Entrypoint con generación runtime de .htpasswd
│   ├── Dockerfile        # Multi-stage build (Node 24 + Nginx 1.27)
│   ├── nginx.conf        # Configuración Nginx proxy reverso y cabeceras
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── scripts/          # Scripts de validación y smoke tests manuales
│   ├── smoke_docker_local.py         # Smoke test automatizado para Docker local
│   ├── smoke_test_gemini_analysis.py # Smoke test real de análisis documental
│   ├── smoke_test_gemini_audio.py    # Smoke test real de transcripción de audio
│   ├── verify_browser_e2e.py         # Test automatizado E2E real en navegador (Playwright)
│   ├── verify_browser_export_filename.py # Validación de nombre real descargado
│   ├── verify_e2e_workflow.py        # Verificación de flujos integrados backend
│   └── verify_word_export.py         # Verificación programática de exportación Word
├── tests/            # Tests automatizados backend (pytest, 100% mocks)
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_analysis.py  # Tests de análisis y structured outputs (Gemini mockeado)
│   ├── test_audio.py     # Tests de transcripción (Gemini mockeado)
│   ├── test_cors.py      # Tests de cabeceras CORS
│   ├── test_documents.py # Tests de extracción documental
│   ├── test_export.py    # Tests de exportación a Word (.docx)
│   ├── test_health.py    # Tests de salud y root
│   ├── test_prompts.py   # Tests del catálogo de prompts y esquemas
│   └── test_text.py      # Tests de preparación de texto
├── .dockerignore
├── .env.example
├── .env.production.example  # Plantilla de variables para producción
├── .gitignore
├── docker-compose.local.yml # Compose para smoke test local (127.0.0.1:8080)
├── docker-compose.prod.yml  # Compose para Dokploy / Producción
├── Dockerfile        # Dockerfile backend (Python 3.12, usuario no-root)
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## Requisitos Previos

- Python 3.12 (versión de referencia oficial)
- Node.js >= 18 y npm (para el frontend web)
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
| `MAX_EXPORT_CHARACTERS` | Límite técnico para exportación de documentos a Word en caracteres (HTTP 413) | `2000000` |
| `CORS_ALLOWED_ORIGINS` | Orígenes permitidos separados por comas para peticiones CORS del frontend | `http://localhost:5173` |

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
* **Interactions API sin almacenamiento (`store=False`)**: La llamada a `client.interactions.create` se ejecuta explícitamente con `store=False`, deshabilitando el almacenamiento de la interacción en el proyecto de Gemini y operando de forma 100% stateless.
* **Eliminación remota garantizada**: El archivo subido a Gemini Files API se elimina de forma explícita e inmediata tras la transcripción mediante `client.files.delete(name)` en bloque `finally`.
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
* **Modo Stateless en Gemini Interactions (`store=False`)**: Todas las llamadas a `client.interactions.create` se configuran explícitamente con `store=False`. La aplicación no utiliza almacenamiento server-side de Interactions ni funcionalidades dependientes de historial (`previous_interaction_id`). Ni los textos sometidos ni las respuestas generadas se almacenan en disco ni en base de datos.
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

### 5. Exportación de Resultados a Word (`POST /api/v1/export/word`)

Permite convertir un resultado de análisis generado por HITCHINGS en un archivo `.docx` profesional y limpio para su descarga inmediata por parte del usuario.

#### Flujo Conceptual
```text
ANÁLISIS GEMINI
      ↓
AnalysisResponse
      ↓
EXPORTACIÓN WORD
      ↓
archivo .docx (generado 100% en memoria)
```

#### Características Técnicas y Directivas de Diseño
* **Generación 100% en Memoria**: El documento Word se serializa utilizando `io.BytesIO` y se entrega vía `StreamingResponse`. En ningún momento se escriben archivos temporales ni se persiste el documento en disco o base de datos.
* **Payload Limpio y Desacoplado**: Recibe un esquema específico de exportación (`WordExportRequest`):
  * `title`: Título principal para encabezar el documento Word.
  * `content`: Contenido completo en Markdown generado previamente.
  * `warnings`: Lista opcional de advertencias detectadas.
  * `metadata`: Metadatos contextuales (`prompt_name`, `model`).
* **Límite Técnico de Tamaño**: Configurado con `MAX_EXPORT_CHARACTERS` (2.000.000 de caracteres por defecto). Si se supera, se rechaza inmediatamente con **HTTP 413**.
* **Interpretación de Markdown**:
  * Encabezados: `#` -> `Heading 1`, `##` -> `Heading 2`, `###` -> `Heading 3`.
  * Párrafos: Formateados con estilo `Normal`.
  * Listas de viñetas: `- ` o `* ` -> estilo nativo `List Bullet`.
  * Listas numeradas: `1. ` -> estilo nativo `List Number`.
  * Formato inline: Segmentos `**negrita**` y `*cursiva*` interpretados en runs con sus atributos tipográficos correspondientes.
  * Tablas Markdown: Detecta bloques delimitados con `|` y los convierte en tablas nativas Word con formato `Table Grid` y cabecera en negrita.
  * Sanitización HTML: Elimina etiquetas HTML embebidas antes del renderizado.
* **Estilos y Tipografía Profesional**:
  * Márgenes estándar de 1 pulgada (2.54 cm).
  * Fuente corporativa estándar ampliamente compatible: `Arial`.
  * Título destacado con estilo nativo `Title`.
  * Subtítulo discreto bajo el título: `Tipo de análisis: {prompt_name}` en gris suave (el identificador técnico del modelo de IA se preserva en la API pero no se muestra al usuario final en el cuerpo del Word).
* **Sección de Advertencias Condicional**: Si `warnings` contiene elementos, añade al final del documento una sección `Advertencias` con estilo `Heading 2` y cada elemento como `List Bullet`. Si la lista está vacía, no se genera la sección.
* **Pie de Página Discreto**: Incluye en la sección el pie nativo `Generado mediante HITCHINGS`.
* **Sanitización de Nombres de Archivo**: Genera un nombre de archivo normalizado y seguro a partir del título (eliminación de acentos, minúsculas, reemplazo de caracteres especiales por guiones, límite de 60 caracteres y extensión `.docx`). Si el título no produce un nombre válido, recurre a `hitchings-analisis.docx`.
* **Confidencialidad en Logs**: Se registran únicamente caracteres procesados, número de advertencias, tamaño final del DOCX en bytes y duración de la generación. Cero contenido textual sensible en los logs.

**Ejemplo de llamada con cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/export/word \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Análisis Jurídico del Contrato",
    "content": "## 1. Antecedentes\nEl contrato fue suscrito el 3 de marzo de 2026...\n\n- Obligación de entrega mensual.\n- Penalización de **500 euros**.",
    "warnings": [
      "No consta cláusula de resolución anticipada."
    ],
    "metadata": {
      "prompt_name": "Análisis jurídico",
      "model": "gemini-3.8-flash"
    }
  }' \
  --output analisis-juridico-del-contrato.docx
```

---

### 6. Ingesta y Extracción Documental (`POST /api/v1/documents/extract`)

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

### 7. Endpoints de Diagnóstico
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

## Ejecución de Tests Backend

Con el entorno virtual activado:

```bash
pytest -v
```

---

## Frontend Web (React + TypeScript + Vite)

La aplicación cuenta con una interfaz web sobria y profesional ubicada en `frontend/`.

### 1. Variables de Entorno del Frontend

Crea el archivo `frontend/.env` copiando la plantilla:

```bash
cd frontend
cp .env.example .env
```

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `VITE_API_BASE_URL` | URL base del backend FastAPI de HITCHINGS | `http://localhost:8000` |

### 2. Instalación y Ejecución en Desarrollo

```bash
cd frontend
npm install
npm run dev
```

La aplicación estará disponible por defecto en:
`http://localhost:5173`

### 3. Ejecución de Tests del Frontend

La suite de pruebas automatizadas utiliza Vitest y React Testing Library (57 tests pasando):

```bash
cd frontend
npm test
```

### 4. Compilación para Producción

Genera los archivos estáticos optimizados en `frontend/dist`:

```bash
cd frontend
npm run build
```

---

## Flujos Extremo a Extremo Conectados (Bloque 6B)

El frontend orquesta los tres flujos documentales completos conectando directamente con los endpoints del backend FastAPI:

```text
1. VÍA DOCUMENTO (PDF / DOCX / TXT):
   Archivo local -> POST /api/v1/documents/extract -> Texto extraído -> POST /api/v1/analysis -> Resultado visible

2. VÍA AUDIO (MP3 / WAV / M4A / AAC / OGG / WEBM):
   Grabación -> POST /api/v1/audio/transcribe -> Texto transcrito -> POST /api/v1/analysis -> Resultado visible

3. VÍA TEXTO PEGADO:
   Texto libre -> POST /api/v1/text/prepare -> Texto normalizado -> POST /api/v1/analysis -> Resultado visible
```

### Características Clave de la Integración E2E

* **Caché en Memoria (React)**:
  * El texto extraído de documentos se almacena en memoria vinculado al archivo.
  * La transcripción de audio se almacena en memoria vinculada a la tupla `(archivo, modo, diarización)`.
  * Si el usuario cambia únicamente de prompt o de parámetros de análisis, se reutiliza el texto en memoria sin volver a llamar a los endpoints de extracción o transcripción.
  * Si el usuario cambia el archivo, el modo o la diarización, la caché se invalida inmediatamente.
  * **Seguridad y Privacidad**: Ningún texto documental ni transcripción se almacena en `localStorage`, `sessionStorage` ni `IndexedDB`.
* **Protección contra Doble Submit y Concurrencia**:
  * Durante el procesamiento, el botón principal queda deshabilitado y muestra un indicador de carga animado con el estado contextual de la etapa (`Leyendo documento…`, `Transcribiendo grabación…`, `Preparando texto…`, `Analizando contenido…`).
  * Los clics concurrentes son ignorados defensivamente.
* **Manejo Contextual de Errores por Etapas**:
  * Errores diferenciados según la etapa activa: extracción documental, transcripción de audio o análisis con Gemini.
  * Mensajes claros para códigos HTTP estándar (400, 413, 415, 500, 502, 503, 504).
  * Si el análisis falla tras una extracción o transcripción exitosa, el texto extraído se mantiene en memoria permitiendo reintentar el análisis sin recargar el archivo.
* **Visualización de Resultados**:
  * Renderizado estructurado y seguro de Markdown mediante `react-markdown` y `remark-gfm` (sin `dangerouslySetInnerHTML`).
  * Sección diferenciada para advertencias de procesamiento (extracción/audio) y advertencias de análisis documental emitidas por Gemini.
  * Pie de página técnico discreto con métricas de tokens (entrada, salida y total) cuando están disponibles.
  * Botón para copiar el resultado al portapapeles en formato Markdown limpio.

---

## Exportación a Word desde Frontend y Validación en Navegador (Bloque 6C)

El Bloque 6C completa el MVP visible al usuario integrando la exportación a Word directamente desde la interfaz web:

```text
RESULTADO DE ANÁLISIS EN PANTALLA
               ↓
     [ Exportar a Word ]
               ↓
    POST /api/v1/export/word
 (WordExportRequest con metadatos y warnings)
               ↓
       Respuesta Blob binaria
(Content-Disposition: attachment; filename="...")
               ↓
  Descarga en memoria en navegador
 (URL.createObjectURL -> <a> -> click -> revokeObjectURL)
               ↓
  Archivo .docx en equipo local
```

### Funcionalidades y Experiencia de Usuario (UX)

* **Descarga Limpia en Memoria (Blob API)**:
  * La respuesta binaria del endpoint `POST /api/v1/export/word` es tratada como `Blob` en memoria.
  * Se extrae el nombre sugerido del encabezado HTTP `Content-Disposition` (`filename*` o `filename`), con saneamiento defensivo contra rutas relativas y fallback a `hitchings-analisis.docx`.
  * No se almacena el binario en almacenamiento local ni persistente.
* **Feedback Visual y Prevención de Concurrencia**:
  * Durante la generación del `.docx`, el botón muestra el estado `Generando Word…` con spinner animado y se deshabilita temporalmente para evitar peticiones duplicadas.
  * Al completarse la descarga, se muestra un banner de confirmación: `✓ Word generado correctamente` (auto-dismiss en 3 segundos).
  * En caso de exceder el límite permitido, se informa adecuadamente: `El resultado es demasiado extenso para exportarlo a Word` (HTTP 413).
* **Regla de Limpieza de Contenido Documental**:
  * Si el usuario modifica el archivo documental (PDF/DOCX/TXT), el audio o el texto ingresado, el resultado previo de análisis y los errores se limpian automáticamente de pantalla.
  * Si el usuario únicamente modifica el prompt, el nivel de detalle o el formato de salida, el resultado previo se mantiene visible hasta que decida lanzar un nuevo análisis.
* **Scroll Automático al Resultado**:
  * Al finalizar con éxito un análisis, la interfaz desplaza suavemente la vista hacia la tarjeta del resultado, respetando la preferencia del sistema `prefers-reduced-motion`.

### Validación Automatizada E2E en Navegador Real (Playwright)

El script `scripts/verify_browser_e2e.py` automatiza la verificación completa extremo a extremo en un navegador Chrome real:
1. Inicia o verifica la disponibilidad de FastAPI en `http://localhost:8000` y Vite en `http://localhost:5173`.
2. Lanza Chromium en modo headless y monitorea consola y red (0 errores, 0 secretos expuestos).
3. Introduce el texto contractual de prueba en la pestaña *Pegar texto*.
4. Selecciona la plantilla de análisis *Puntos clave* y ejecuta **una única llamada real a Gemini 3.8 Flash**.
5. Verifica el renderizado de la tarjeta de resultados (título, secciones, métricas de tokens y advertencias).
6. En la misma sesión de navegador, pulsa *Exportar a Word* (reutilizando el resultado, sin llamadas adicionales a Gemini).
7. Captura el archivo descargado e inspecciona con `python-docx` sus encabezados, párrafos y estructura.
8. Genera capturas de pantalla de ambas fases (`scripts/e2e_browser_analysis.png` y `scripts/e2e_browser_word_export.png`).

Para ejecutar la verificación E2E del navegador:
```bash
python -u scripts/verify_browser_e2e.py
```

---

## Verificación Local E2E con Servidor Real

Para verificar el flujo completo de forma local con el backend real y Gemini Developer API:

1. **Iniciar el backend**:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. **Ejecutar el script de verificación**:
   ```bash
   python scripts/verify_e2e_workflow.py
   ```

3. **Iniciar el frontend en desarrollo**:
   ```bash
   cd frontend
   npm run dev
   ```

---

---

## Despliegue en Producción y Arquitectura Docker

### Arquitectura de Producción

En entorno de producción (Dokploy / servidor final), el sistema se estructura en dos servicios coordinados mediante Docker Compose sobre una red interna aislada:

```text
Internet
   ↓
Dokploy / Traefik  (Terminación TLS, gestión de dominio)
   ↓
[ Servicio Frontend: Nginx 1.27 Alpine ] (:80)
   ├── /healthz          → 200 "ok" (sin autenticación, monitoreo de Dokploy)
   ├── /                 → React SPA compilado (Protegido con Basic Auth)
   └── /api/*            → Proxy reverso hacia backend (Protegido con Basic Auth)
                                 ↓
         [ Servicio Backend: FastAPI / Python 3.12 ] (:8000)
         (Red interna Docker `hitchings-docs-net` — Puerto 8000 NO expuesto al host)
```

### Principios de Hardening y Seguridad

* **Único punto de entrada público**: El contenedor backend FastAPI no publica el puerto 8000 al host en producción. Solo es accesible internamente desde la red Docker compartida con Nginx.
* **Mismo origen (Same-Origin)**: El frontend se compila con `VITE_API_BASE_URL=""`, de modo que todas las llamadas a `/api/...` se dirigen al mismo origen. Nginx realiza el proxy transparente hacia el backend.
* **Protección temporal de acceso (Basic Auth)**:
  * Protege tanto la interfaz React (`/`) como la API (`/api/*`).
  * El endpoint de liveness `/healthz` queda explícitamente exento de autenticación para permitir healthchecks de Dokploy/orquestadores.
  * Las credenciales se inyectan en tiempo de ejecución mediante las variables de entorno `APP_BASIC_AUTH_USER` y `APP_BASIC_AUTH_PASSWORD`.
  * El archivo `.htpasswd` se genera dinámicamente en el arranque del contenedor mediante `htpasswd` leyendo la contraseña por `stdin` (sin exponerla en línea de comandos ni en logs).
  * **Fallo seguro (Fail-Safe)**: Si alguna de las dos variables de credenciales no está configurada, el contenedor frontend finaliza con código de error y no inicia el servidor web.
  * *Nota: Esta protección es temporal para pilotaje/entrega y no sustituye a un sistema de autenticación multiusuario futuro.*
* **Soporte de audio de gran tamaño y análisis largo**:
  * `client_max_body_size 210m` en Nginx para admitir archivos de audio de hasta 200 MB.
  * `proxy_request_buffering off` en Nginx para evitar retención innecesaria en memoria antes de transferir al backend.
  * Timeouts de `proxy_read_timeout 360s` y `proxy_send_timeout 360s` (alineados con el límite de `GEMINI_TIMEOUT_SECONDS=300`).
* **Cabeceras de seguridad**: Nginx emite en todas las respuestas:
  * `X-Content-Type-Options: nosniff`
  * `X-Frame-Options: DENY`
  * `Referrer-Policy: strict-origin-when-cross-origin`
  * `Permissions-Policy: camera=(), microphone=(), geolocation=()`
  * `Content-Security-Policy: default-src 'self' ...`
* **Healthchecks Docker nativos**: El servicio backend incluye un healthcheck nativo con Python stdlib (`urllib.request`) sobre `http://127.0.0.1:8000/health` sin dependencias externas (curl/wget).
* **Ausencia de persistencia y modo stateless (`store=False`)**: El sistema no requiere ni incluye bases de datos relacionales (PostgreSQL), colas/cachés externas (Redis) ni volúmenes persistentes. Toda la memoria se gestiona en el ciclo de vida de la petición. Asimismo, las llamadas a Google Gemini Interactions API (`gemini-3.8-flash` para análisis y `gemini-3.5-transcribe` para transcripción de audio) configuran explícitamente `store=False`, deshabilitando el almacenamiento server-side de las interacciones en el proyecto de Gemini y eliminando explícitamente los archivos temporales de audio en Files API tras su procesamiento.

### Variables de Entorno en Producción

Consultar la plantilla completa en [.env.production.example](.env.production.example):

| Variable | Requerida | Descripción |
| :--- | :---: | :--- |
| `APP_ENV` | Sí | Fijar a `production` |
| `GEMINI_API_KEY` | Sí | API Key oficial de Google Gemini (Developer API) |
| `GEMINI_TRANSCRIPTION_MODEL` | No | Por defecto `gemini-3.5-transcribe` |
| `GEMINI_ANALYSIS_MODEL` | No | Por defecto `gemini-3.8-flash` |
| `GEMINI_TIMEOUT_SECONDS` | No | Por defecto `300` |
| `APP_BASIC_AUTH_USER` | Sí | Usuario para la barrera temporal de acceso |
| `APP_BASIC_AUTH_PASSWORD` | Sí | Contraseña para la barrera temporal de acceso |

### Validación Local con Docker (Smoke Test)

Para validar localmente el empaquetado y la configuración de proxy/seguridad antes de desplegar en Dokploy:

1. **Levantar los servicios locales** (el frontend se publica únicamente en `127.0.0.1:8080`):
   ```bash
   docker compose -f docker-compose.local.yml up -d --build
   ```

2. **Ejecutar la suite de smoke test automatizada**:
   ```bash
   python scripts/smoke_docker_local.py
   ```

   El script valida programáticamente:
   * `GET /` sin autenticación devuelve **HTTP 401 Unauthorized**.
   * `GET /healthz` sin autenticación devuelve **HTTP 200 OK**.
   * `GET /` con Basic Auth devuelve **HTTP 200 OK** y el HTML del SPA.
   * `GET /ruta-inexistente` con Basic Auth devuelve **HTTP 200 OK** (SPA fallback).
   * `GET /api/v1/prompts` a través del proxy Nginx devuelve **HTTP 200** y catálogo JSON.
   * `POST /api/v1/text/prepare` a través del proxy devuelve **HTTP 200**.
   * El puerto 8000 del backend no es accesible directamente desde el host.
   * Presencia de cabeceras de seguridad (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).
   * Ausencia de referencias a `localhost:8000` o secretos en el bundle estático.

3. **Detener los servicios locales**:
   ```bash
   docker compose -f docker-compose.local.yml down
   ```

### Despliegue en Dokploy

Para el despliegue productivo final:
1. Configurar en Dokploy la aplicación utilizando el archivo compose `docker-compose.prod.yml`.
2. Asignar las variables de entorno documentadas en `.env.production.example`.
3. Dokploy/Traefik enrutará el tráfico HTTPS del dominio directamente al servicio `frontend` (puerto 80).

---

## Control de Acceso y Gestión de Usuarios (Bloque 7B)

HITCHINGS Y GONZALEZ DOCUMENTOS implementa un modelo de autenticación y autorización basado en roles gestionado íntegramente por administradores:

### Roles de Usuario
* **`admin` (Administrador)**: Acceso total al procesamiento documental y a la sección **Configuración → Usuarios** para crear, editar, activar/desactivar y restablecer contraseñas de cualquier cuenta. También puede gestionar Tipos de análisis.
* **`user` (Usuario)**: Acceso al procesamiento documental completo y a la sección **Configuración → Tipos de análisis** para crear y editar tipos de análisis compartidos del despacho. Sin privilegios sobre la gestión de usuarios.

### Principios Operativos y de Seguridad
* **Sin registro público**: No existen endpoints de autoregistro. El acceso es estrictamente corporativo y todas las cuentas son creadas por administradores autenticados (`POST /api/v1/admin/users`).
* **Revocación inmediata en desactivación**: Al marcar un usuario como inactivo (`is_active: false`), el backend revoca y purga de inmediato todas las sesiones activas asociadas en la tabla `sessions`.
* **Revocación inmediata en cambio de contraseña**: Al restablecer una contraseña (`POST /api/v1/admin/users/{id}/password`), el hash se actualiza mediante **Argon2id** y se eliminan al instante todas las sesiones vigentes del usuario, exigiendo reautenticación.
* **Sin borrado físico (`soft delete`)**: No se permite eliminación física (`DELETE`) en base de datos para preservar la trazabilidad operativa y coherencia de auditoría. La baja se realiza desactivando la cuenta.
* **Protección del último administrador activo**: El sistema impide de forma estricta que el único administrador activo sea desactivado o degradado a usuario normal, evitando bloqueos irreversibles.
* **Protección CSRF**: Todas las peticiones administrativas mutativas (`POST`, `PATCH`) exigen la cabecera `X-CSRF-Token` validada contra el hash en base de datos.

---

## Tipos de Análisis Dinámicos y Base Estructural Jurídica (Bloque 7C)

### Base Estructural Jurídica (Inmutable)

Todo análisis documental ejecutado en la plataforma opera bajo una capa de directivas inviolables establecidas por **HITCHINGS & GONZÁLEZ**:

* **Especialización firme**: Derecho de la Competencia (antitrust), Derecho de la Unión Europea y acciones colectivas de alcance nacional e internacional.
* **Separación epistémica estricta**: Diferenciación obligatoria entre hechos probados, posiciones de las partes, datos cuantitativos, hipótesis y conclusiones adoptadas.
* **Inmunidad a prompt injection**: El contenido documental es tratado estrictamente como datos pasivos a analizar, nunca como instrucciones del sistema.
* **Veracidad absoluta**: Prohibición de inventar hechos, citas, fechas, artículos legales, sentencias o importes económicos no presentes en el documento.

Esta base estructural es configurada como `system_instruction` en la Gemini Interactions API y tiene prioridad inviolable sobre cualquier plantilla de análisis o instrucción adicional del usuario.

### Catálogo de Tipos de Análisis

Los tipos de análisis se persisten en la tabla `analysis_types` de PostgreSQL. El catálogo inicial incluye 5 tipos históricos sembrados mediante la migración `0002_analysis_types`:

| Código | Nombre |
|---|---|
| `executive-summary` | Resumen ejecutivo |
| `legal-analysis` | Análisis jurídico |
| `key-points` | Puntos clave |
| `timeline` | Cronología |
| `custom-analysis` | Análisis personalizado |

### Modelo de Permisos para Tipos de Análisis

* **Cualquier usuario autenticado** (`admin` y `user`) puede listar, crear y editar tipos de análisis. El catálogo es compartido por todo el despacho.
* Los tipos de análisis se desactivan en lugar de eliminarse físicamente (`is_active: false`). Los tipos inactivos son excluidos del selector de análisis y rechazados en análisis (HTTP 400).
* El **código identificador** (`code`) de cada tipo se genera automáticamente como slug a partir del nombre y es **inmutable** una vez creado, para preservar referencias de ejecución estables.
* Los tipos de análisis predefinidos del sistema tienen `created_by_user_id = NULL`.

### API de Tipos de Análisis

| Método | Ruta | Permisos | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/analysis-types` | Autenticado | Lista todos los tipos (activos e inactivos) |
| `GET` | `/api/v1/analysis-types/{id}` | Autenticado | Detalle de un tipo por UUID |
| `POST` | `/api/v1/analysis-types` | Autenticado + CSRF | Crea un nuevo tipo (código generado automáticamente) |
| `PATCH` | `/api/v1/analysis-types/{id}` | Autenticado + CSRF | Edita nombre, descripción, instrucciones o estado activo |

### Migración de Base de Datos

La migración `0002_analysis_types` (down_revision: `0001_initial_auth`) crea la tabla `analysis_types` con índice único en `code` y claves foráneas `SET NULL` hacia `users.id`, y siembra los 5 tipos históricos.

```bash
# Aplicar migración en producción
alembic upgrade head
```
