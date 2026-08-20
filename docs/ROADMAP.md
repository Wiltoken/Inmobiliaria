# Roadmap de Producción — Inmobiliaria

> Última actualización: 2026-08-20
> Estado: plan de producción-readiness por etapas (slices). Cada etapa es una unidad de trabajo verificable e independiente.

---

## Resumen ejecutivo

Plataforma inmobiliaria FastAPI (backend hexagonal) + React (frontend Vite). El **backend está ~70% maduro** (seguridad, RBAC, soft-delete Ley 1581, admin, tests). El **producto de cara al usuario está lejos de producción**: hay una brecha grave de contratos entre lo que el frontend espera y lo que el backend devuelve, y la infraestructura de despliegue no arranca.

---

## Bloqueantes críticos (sin esto no hay producción)

### A) Contratos frontend ↔ backend rotos
- Lista de propiedades: frontend lee `items`, backend devuelve `properties`.
- Mapa: frontend lee `location.*`, backend devuelve `lat`/`lon` a nivel raíz.
- Refresh token: `/auth/refresh` no devuelve `refresh_token` → las sesiones mueren tras el primer refresh.
- Matches: `items` vs `matches`.
- BI analytics: camelCase (frontend) vs snake_case (backend) → crash de render.
- Filtros de búsqueda: frontend envía arrays → 422.

### B) Infraestructura que no arranca
- Nginx: sin certificados (no hay certbot) + healthcheck del api falla (imagen sin `curl`).
- PgBouncer: `userlist.txt` con hash placeholder.
- Celery worker: `include` apunta a un módulo inexistente.
- `make dev` roto (compose.dev sin `image`/`build`).

### C) Bugs de datos
- Búsqueda geo (PostGIS): `location` es JSONB (no `geometry`), `ST_DWithin` sobre JSONB → SQL inválido.
- Drift modelo ↔ migraciones (`inquiries.response_message`, enum `closed`, índice GIST).
- Roles/admin no se siembran por migraciones → `register` da 500 en una DB limpia.
- `scripts/seed.py` referencia una columna inexistente (`inquiry.updated_at`).

### D) Seguridad
- CORS `allow_origins=["*"]` + `allow_credentials=True`.
- Logout no revoca la sesión en el servidor.
- reCAPTCHA declarado pero no implementado.

---

## Slices por etapas

### Etapa 0 — "Que ande de verdad" (corrección, sin features nuevas)
Objetivo: que el producto funcione end-to-end con lo que ya existe.

- [ ] Corregir contratos frontend ↔ backend (paginación, ubicación, matches, BI, filtros).
- [ ] Devolver `refresh_token` en `/auth/refresh` + logout con revocación server-side.
- [ ] Arreglar drift de migraciones + migración de seed de roles + bugs de `seed.py`.

**Salida verificable:** login → buscar → ver detalle → contactar, sin 422 ni `undefined`.

### Etapa 1 — Seguridad y cumplimiento
- [ ] CORS restringido.
- [ ] Verificación de email.
- [ ] reCAPTCHA real.
- [ ] SMTP/S3 async (o a background); forgot-password con email real.
- [ ] Enforce de inactividad de sesión (`require_session_active` sin usar).
- [ ] Segmentar caché PWA por usuario.

### Etapa 2 — Infraestructura de despliegue
- [ ] Arreglar compose dev/prod, nginx + certbot, pgbouncer, healthchecks.
- [ ] Celery worker + jobs reales; backups/restore.
- [ ] CI/CD: build de imagen, push a registry, migraciones, smoke tests.

### Etapa 3 — Features core faltantes
- [ ] Publicación de propiedades (flujo del vendedor).
- [ ] Páginas de favoritos, mensajes y perfil.
- [ ] Bandeja de inquiries / chat.
- [ ] Decidir pagos (Wompi / MercadoPago / PayU) sí/no.

### Etapa 4 — Observabilidad + escalado
- [ ] Métricas (Prometheus) + tracing (Sentry/OTel).
- [ ] Logging unificado.
- [ ] PostGIS real (`geometry`) + geocodificación.
- [ ] CDN + load testing.

### Etapa 5 — Calidad y cierre
- [ ] Tests del frontend (interceptores, auth, páginas, hooks).
- [ ] e2e en CI + escaneo de seguridad.
- [ ] README/runbook de producción.

---

## Herramientas / APIs / artefactos a decidir

| Categoría | Opciones (Colombia-friendly) | Estado |
|-----------|------------------------------|--------|
| Email transaccional | SendGrid / Mailgun / Amazon SES | smtplib síncrono, a medias |
| Storage de fotos | MinIO (dev) → S3 (prod) | boto3 síncrono, sin configurar |
| Pagos | Wompi / MercadoPago / PayU | No existe |
| SMS/WhatsApp | Twilio / MessageBird | No existe |
| Geocodificación | Nominatim / Mapbox / Google | No existe |
| Observabilidad | Sentry + Prometheus + Grafana | Sin métricas ni tracing |
| Hosting | VPS / EC2 / Fly.io / Render | Sin pipeline |
| Postgres gestionado | RDS / Supabase / Neon | — |
| Redis gestionado | Upstash / ElastiCache | — |
| CDN | Cloudflare | Sin CDN |

**Artefactos internos faltantes:** migración de seed de roles, `.env.production`, `backup.sh`/`restore.sh`, runbook de deploy, tests del frontend.

---

## Convenciones

- Cada etapa se implementa en work units commiteables (conventional commits).
- Verificación por etapa: backend `pytest`, frontend `npm test` + `npm run build`.
- No se avanza a la siguiente etapa con una etapa previa sin verificar.
