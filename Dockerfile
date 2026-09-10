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

# Copiar el código de la aplicación, migraciones y scripts
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts ./scripts
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Asignar permisos y cambiar a usuario no privilegiado
RUN chmod +x /docker-entrypoint.sh \
    && chown -R appuser:appgroup /app /docker-entrypoint.sh
USER appuser

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
