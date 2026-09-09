FROM python:3.12-slim

# Evitar escritura de archivos .pyc y forzar salida stdout/stderr sin buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Crear usuario sin privilegios para mayor seguridad
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY app ./app

# Asignar permisos y cambiar a usuario no privilegiado
RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "\
import urllib.request, sys; \
req = urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5); \
sys.exit(0) if req.status == 200 else sys.exit(1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
