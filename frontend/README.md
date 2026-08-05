# Inmobiliaria Frontend

Plataforma inmobiliaria con React + Vite + Tailwind CSS.

## Requisitos

- Node.js 18+
- npm 9+

## Instalación

```bash
cd frontend
npm install
```

## Desarrollo

```bash
npm run dev
```

La aplicación estará disponible en http://localhost:3000

## Variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

## PWA

La aplicación soporta PWA. Para generar los iconos, reemplaza los archivos en `/public` con iconos reales de 192x192 y 512x512 píxeles.

## Estructura del proyecto

```
frontend/
├── public/              # Archivos estáticos
│   ├── icon-192.png     # Icono PWA pequeño
│   ├── icon-512.png     # Icono PWA grande
│   └── favicon.svg      # Favicon
├── src/
│   ├── components/      # Componentes React
│   │   ├── analytics/   # Dashboard de analíticas BI
│   │   ├── auth/        # Rutas protegidas
│   │   ├── dashboard/   # Dashboards por rol
│   │   ├── layout/      # Layout principal
│   │   ├── properties/  # Componentes de propiedades
│   │   └── ui/          # Componentes base
│   ├── hooks/           # Hooks personalizados
│   ├── lib/             # Utilidades (API, auth, audit)
│   ├── pages/           # Páginas principales
│   ├── App.jsx          # Router principal
│   ├── main.jsx         # Entry point
│   └── index.css        # Tailwind + estilos
└── package.json
```

## Roles de usuario

- **Comprador**: Dashboard personalizado, búsqueda, favoritos, matches
- **Vendedor**: Dashboard, gestión de propiedades, consultas
- **Agente**: Dashboard, métricas, clientes, matches
- **Admin**: Dashboard general, usuarios, propiedades, analíticas

## API Endpoints

La aplicación se conecta al backend en `VITE_API_URL`. Endpoints principales:

- `POST /auth/login` - Inicio de sesión
- `POST /auth/register` - Registro
- `GET /properties` - Listar propiedades
- `GET /properties/:id` - Detalle de propiedad
- `POST /audit/user-action` - Registrar acción de usuario
- `GET /admin/analytics` - Dashboard BI (admin)
