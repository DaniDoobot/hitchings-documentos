# ============================================================
# HITCHINGS Documentos — Frontend Dockerfile
# Multi-stage: builder (Node 24 Alpine) + runtime (Nginx Alpine)
# ============================================================

# -----------------------------------------------------------
# Etapa 1: builder — instala dependencias y construye el SPA
# -----------------------------------------------------------
FROM node:24-alpine AS builder

WORKDIR /app

# Copiar manifiestos de dependencias primero para aprovechar caché
COPY package.json package-lock.json ./

# Instalar dependencias exactas según lock-file
RUN npm ci

# Copiar el resto del código fuente
COPY . .

# Construir para producción con URL de API vacía (mismo origen)
# En producción, las peticiones a /api/... irán al mismo servidor
ENV VITE_API_BASE_URL=""

RUN npm run build

# -----------------------------------------------------------
# Etapa 2: runtime — Nginx Alpine sirviendo el SPA
# -----------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

# Instalar apache2-utils para htpasswd (generación de .htpasswd)
RUN apk add --no-cache apache2-utils

# Copiar configuración de Nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Copiar artefactos de build del frontend
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar y habilitar el entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# El puerto 80 queda documentado; el expose real lo gestiona Compose/Traefik
EXPOSE 80

# Las credenciales Basic Auth se inyectan en runtime — nunca en la imagen
CMD ["/docker-entrypoint.sh"]
