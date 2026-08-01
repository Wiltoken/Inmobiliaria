# Changelog

Todas las versiones notables de Inmobiliaria Platform documentadas aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-07-31

### Added
- **Fundación**: Copia de auth-login-platform (FastAPI, JWT, RBAC, PostgreSQL, Redis) como base hexagonal
- **Modelos de dominio**: 15+ entidades — Property, Match, Inquiry, BuyerProfile, SellerProfile, AgentProfile, Project, PropertyPhoto, Favorite
- **Property Management API**: CRUD completo con búsqueda geoespacial (PostGIS + ST_DWithin) y textual (pg_trgm), carga de fotos vía S3/MinIO, workflow de estados (draft→published→reserved→sold→archived)
- **Matching Engine**: Algoritmo de scoring ponderado (precio 30%, ubicación 25%, features 25%, área 20%) con cache Redis y score_breakdown JSONB
- **Perfiles**: Buyer (preferencias, presupuesto, ubicaciones), Seller (datos de contacto, empresa), Agent (licencia, agencia)
- **Inquiries**: Flujo de contacto comprador-vendedor con estados (pending→responded→closed)
- **Favorites**: Guardado de propiedades con restricción UNIQUE
- **Admin**: Moderación de propiedades (approve/reject), listado de usuarios con filtro por rol
- **Agent Dashboard**: Estadísticas, listados, clientes, matches de clientes, inquiries delegados
- **Infraestructura producción**: Nginx (SSL, rate limiting, security headers), PgBouncer (connection pooling), MinIO (S3-compatible), Celery (workers asíncronos + beat para backups)
- **Backups**: Scripts automatizados con pg_dump, compresión gzip, rotación de 7 días
- **Makefile**: Comandos unificados (dev, prod, deploy, test, lint, backup, restore, migrate)
- **Documentación**: 7 documentos técnicos (arquitectura, infraestructura, API, despliegue, seguridad, desarrollo, operaciones)
- **Tests**: 35 tests unitarios e integración (matching algorithm, property CRUD, search)

### Dependencies
- FastAPI 0.115+, SQLAlchemy 2.0 async, PostgreSQL 16 + PostGIS, Redis 7
- GeoAlchemy2, pg_trgm, Celery, MinIO, PgBouncer, Nginx
