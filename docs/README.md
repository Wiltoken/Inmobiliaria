# Inmobiliaria — Documentación

## Índice

| Documento | Descripción | ¿Para quién? |
|-----------|-------------|---------------|
| [README.md](../README.md) | Vista general, quick start, comandos | Todos |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Diseño del sistema, ADRs, modelo de dominio, algoritmo de matching | Arquitectos, Tech Leads |
| [INFRASTRUCTURE.md](INFRASTRUCTURE.md) | Topología de servicios, scaling, networking, recursos | DevOps, SRE |
| [API.md](API.md) | Referencia completa de 26 endpoints con ejemplos | Frontend, Integradores |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Deploy en producción, SSL, migraciones, variables de entorno | DevOps |
| [SECURITY.md](SECURITY.md) | Flujo JWT, matriz RBAC, rate limiting, OWASP, Ley 1581 | Security, Compliance |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Setup local, tests, code style, arquitectura hexagonal | Desarrolladores |
| [OPERATIONS.md](OPERATIONS.md) | Runbooks diarios/semanales/mensuales, backups, restore, monitoreo | Operadores |
| [CHANGELOG.md](../CHANGELOG.md) | Historial de versiones y cambios | Todos |

## Guía rápida por perfil

### 🏗️ Arquitecto / Tech Lead
1. [ARCHITECTURE.md](ARCHITECTURE.md) — sistema completo, ADRs, decisiones de diseño
2. [INFRASTRUCTURE.md](INFRASTRUCTURE.md) — cómo escala en producción

### 🔧 Desarrollador
1. [DEVELOPMENT.md](DEVELOPMENT.md) — levantar el proyecto local
2. [API.md](API.md) — referencia de endpoints
3. [ARCHITECTURE.md](ARCHITECTURE.md) — entender el diseño hexagonal

### 🚀 DevOps
1. [INFRASTRUCTURE.md](INFRASTRUCTURE.md) — servicios y topología
2. [DEPLOYMENT.md](DEPLOYMENT.md) — pasos para producción
3. [OPERATIONS.md](OPERATIONS.md) — monitoreo y runbooks

### 🔒 Seguridad / Compliance
1. [SECURITY.md](SECURITY.md) — auth, RBAC, OWASP, Ley 1581
2. [ARCHITECTURE.md](ARCHITECTURE.md) — ADRs de seguridad

## Diagramas

Todos los diagramas están en formato ASCII dentro de cada documento para máxima portabilidad. No requieren herramientas externas para visualizarse.
