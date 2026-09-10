#!/bin/sh
# docker-entrypoint.sh — valida configuración y arranca Nginx
set -e

# ----------------------------------------------------------------
# Validar configuración real de Nginx en runtime (con backend resoluble)
# ----------------------------------------------------------------
nginx -t

# ----------------------------------------------------------------
# Arrancar Nginx en primer plano
# ----------------------------------------------------------------
exec nginx -g 'daemon off;'

