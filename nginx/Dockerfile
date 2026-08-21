# ── Stage 1: build the React frontend ─────────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# Same-origin API base: nginx proxies /api/v1 → api backend, so the browser
# talks to the same host instead of a hardcoded localhost URL.
ENV VITE_API_URL=/api/v1
RUN npm run build

# ── Stage 2: nginx serving the built SPA + proxying the API ───────────────
FROM nginx:alpine

# Remove the base image's default.conf, which otherwise competes with our
# vhost (same listen port) and serves /usr/share/nginx/html.
RUN rm -f /etc/nginx/conf.d/default.conf

COPY --from=frontend-build /build/dist /app/static
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/conf.d /etc/nginx/conf.d
