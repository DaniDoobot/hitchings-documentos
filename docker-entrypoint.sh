#!/bin/sh
set -e

# Ejecutar migraciones automáticas de base de datos con Alembic si DATABASE_URL está definida
if [ -n "$DATABASE_URL" ]; then
    echo "Aplicando migraciones de base de datos (Alembic upgrade head)..."
    alembic upgrade head
fi

exec "$@"
