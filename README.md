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
│   │   └── routes.py
│   ├── core/         # Configuración central (Pydantic Settings) y logging
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── logging.py
│   ├── models/       # Modelos de dominio y persistencia
│   │   └── __init__.py
│   ├── schemas/      # Esquemas de validación Pydantic
│   │   ├── __init__.py
│   │   └── health.py
│   ├── services/     # Lógica de negocio (análisis, extracción, Gemini)
│   │   └── __init__.py
│   ├── utils/        # Utilidades y funciones auxiliares
│   │   └── __init__.py
│   ├── __init__.py
│   └── main.py       # Entrada FastAPI, ciclo de vida y handlers de error
├── tests/            # Tests automatizados (pytest)
│   ├── __init__.py
│   ├── conftest.py
│   └── test_health.py
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Requisitos Previos

- Python 3.12 o superior (compatible con Python 3.14)
- Git
- Docker (opcional, para despliegue local en contenedor)

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

> **Nota de seguridad:** Nunca subas el archivo `.env` con claves reales al control de versiones. Ya se encuentra excluido en `.gitignore`.

---

## Instalación Local

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

---

## Ejecución del Servidor

Con el entorno virtual activado:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El servidor estará accesible en `http://localhost:8000`.

### Endpoints Iniciales:
- **`GET /`**: Comprueba que el servicio está activo.
- **`GET /health`**: Healthcheck JSON estructurado (`{"status": "ok", "service": "hitchings-documentos"}`).
- **`GET /docs`**: Documentación interactiva OpenAPI (Swagger UI).
- **`GET /redoc`**: Documentación interactiva ReDoc.

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
