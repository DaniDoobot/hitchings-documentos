#!/bin/sh
# docker-entrypoint.sh — genera .htpasswd en runtime y arranca Nginx
set -e

# ----------------------------------------------------------------
# Validar que las credenciales de Basic Auth están presentes
# ----------------------------------------------------------------
if [ -z "${APP_BASIC_AUTH_USER}" ]; then
    echo "ERROR: APP_BASIC_AUTH_USER no está definida. El contenedor no puede arrancar sin protección Basic Auth."
    exit 1
fi

if [ -z "${APP_BASIC_AUTH_PASSWORD}" ]; then
    echo "ERROR: APP_BASIC_AUTH_PASSWORD no está definida. El contenedor no puede arrancar sin protección Basic Auth."
    exit 1
fi

# ----------------------------------------------------------------
# Generar /etc/nginx/.htpasswd con htpasswd (apache2-utils)
# La contraseña se pasa por stdin para evitar que aparezca en
# la lista de procesos o en logs del sistema.
# ----------------------------------------------------------------
printf '%s' "${APP_BASIC_AUTH_PASSWORD}" \
    | htpasswd -ci /etc/nginx/.htpasswd "${APP_BASIC_AUTH_USER}"

echo "INFO: Basic Auth configurada para el usuario '${APP_BASIC_AUTH_USER}'."

# ----------------------------------------------------------------
# Arrancar Nginx en primer plano
# ----------------------------------------------------------------
exec nginx -g 'daemon off;'
