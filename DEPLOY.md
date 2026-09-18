# 🚀 Guía de Deploy - Inmobiliaria

## Arquitectura de Producción

```
┌─────────────────────────────────────────────────────────────┐
│                    CLOUDFLARE PAGES                         │
│                    (Frontend React)                         │
│                    https://inmobiliaria.pages.dev           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAILWAY                                  │
│                    (Backend FastAPI)                        │
│                    https://xxx.up.railway.app               │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│        NEON             │   │        UPSTASH          │
│   (PostgreSQL)          │   │        (Redis)          │
│   0.5GB gratis          │   │   10K comandos/día      │
└─────────────────────────┘   └─────────────────────────┘
```

---

## Paso 1: Neon PostgreSQL (Base de Datos)

### Crear cuenta y base de datos

1. Ve a [neon.tech](https://neon.tech) y crea una cuenta gratis
2. Crea un nuevo proyecto
3. Copia el **Connection String** (formato: `postgresql+asyncpg://...`)
4. Guarda el password en un lugar seguro

### Variables de entorno

```
DATABASE_URL=postgresql+asyncdb://neondb_owner:xxxx@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require
```

---

## Paso 2: Upstash Redis (Cache)

### Crear cuenta

1. Ve a [upstash.com](https://upstash.com) y crea una cuenta gratis
2. Crea una nueva base de datos Redis
3. Copia el **Redis URL** (formato: `rediss://...`)

### Variables de entorno

```
REDIS_URL=rediss://xxxx@xxx.upstash.io:6379
```

---

## Paso 3: Railway (Backend FastAPI)

### Crear cuenta y proyecto

1. Ve a [railway.app](https://railway.app) y crea una cuenta
2. Click "New Project" → "Deploy from GitHub repo"
3. Selecciona el repositorio `Wiltoken/Inmobiliaria`
4. Railway detectará automáticamente el `Procfile`

### Configurar variables de entorno

En el dashboard de Railway, ve a **Variables** y agrega:

```bash
# Genera un secret key
python -c "import secrets; print(secrets.token_urlsafe(64))"

SECRET_KEY=tu-secret-key-generado
DATABASE_URL=tu-url-de-neon
REDIS_URL=tu-url-de-upstash
APP_ENV=production
LOG_LEVEL=INFO
APP_BASE_URL=https://tu-app.up.railway.app
CORS_ORIGINS=https://tu-cloudflare.pages.dev
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASSWORD=tu-api-key-de-resend
SMTP_FROM=noreply@tudominio.com
```

### Deploy automático

Railway hará deploy automáticamente cada vez que hagas push a `main`.

---

## Paso 4: Cloudflare Pages (Frontend React)

### Crear cuenta y proyecto

1. Ve a [pages.cloudflare.com](https://pages.cloudflare.com) y crea una cuenta
2. Click "Create a project" → "Connect to Git"
3. Selecciona el repositorio `Wiltoken/Inmobiliaria`
4. Configura:
   - **Production branch**: `main`
   - **Build command**: `cd frontend && npm install && npm run build`
   - **Build output directory**: `frontend/dist`

### Variables de entorno

En el dashboard de Cloudflare Pages → Settings → Environment variables:

```
VITE_API_URL=https://tu-app.up.railway.app/api/v1
```

### Deploy automático

Cloudflare hará deploy automáticamente cada vez que hagas push a `main`.

---

## Paso 5: Dominio Personalizado (Opcional)

### Cloudflare Pages

1. En el dashboard → Custom domains
2. Agrega tu dominio (ej: `inmobiliaria.com`)
3. Cloudflare te dará los DNS records

### DNS Records

| Tipo | Nombre | Valor |
|------|--------|-------|
| CNAME | @ | tu-proyecto.pages.dev |
| CNAME | www | tu-proyecto.pages.dev |

---

## Verificación Post-Deploy

### 1. Backend Health Check

```bash
curl https://tu-app.up.railway.app/health
# Debe retornar: {"status": "ok"}
```

### 2. Frontend

Abre `https://tu-cloudflare.pages.dev` en el navegador.

### 3. API Docs

Visita `https://tu-app.up.railway.app/docs` para ver Swagger.

---

## troubleshooting

### Errores comunes

| Error | Solución |
|-------|----------|
| `CORS error` | Verifica que `CORS_ORIGINS` incluya tu dominio de Cloudflare |
| `Database connection refused` | Verifica que `DATABASE_URL` sea correcto en Railway |
| `Redis connection refused` | Verifica que `REDIS_URL` sea correcto en Railway |
| `Build failed` | Revisa los logs en Cloudflare/Railway dashboard |

### Logs

- **Railway**: Dashboard → Deployments → Click en el deploy → Logs
- **Cloudflare**: Dashboard → Pages → Click en el proyecto → Logs

---

## Costos

| Servicio | Tier | Costo |
|----------|------|-------|
| Cloudflare Pages | Free | $0 |
| Railway | Free (crédito $5) | $0 → $5/mes después |
| Neon | Free | $0 |
| Upstash | Free | $0 |
| Resend | Free (3K emails) | $0 |
| **Total** | | **$0 → $5/mes** |

---

## Deploy con un solo comando

```bash
# 1. Push a GitHub
git add -A
git commit -m "feat: deploy configuration"
git push

# 2. Railway y Cloudflare harán deploy automáticamente
```

---

## URLs de Producción

| Servicio | URL |
|----------|-----|
| Frontend | https://inmobiliaria.pages.dev |
| Backend | https://xxx.up.railway.app |
| API Docs | https://xxx.up.railway.app/docs |
| Health | https://xxx.up.railway.app/health |
