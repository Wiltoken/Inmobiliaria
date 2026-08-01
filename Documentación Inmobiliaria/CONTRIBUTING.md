# Contributing

¡Gracias por contribuir a Inmobiliaria!

## Arquitectura

El proyecto sigue **arquitectura hexagonal** (ports/adapters):

```
app/
├── api/v1/       ← Driving Adapters (FastAPI routers)
├── core/         ← Domain Services (matching, security)
├── domain/       ← Domain Models (SQLAlchemy, Pydantic)
├── ports/        ← Interfaces (ABCs para DB, cache, storage)
└── adapters/     ← Driven Adapters (Postgres, Redis, S3)
```

**Regla de oro**: el dominio nunca importa de adapters. Los adapters implementan puertos.

## Cómo contribuir

1. **Creá un issue** primero — discutamos el cambio antes de codear
2. **Branch**: `feature/nombre-corto` desde `main`
3. **Commits**: [Conventional Commits](https://www.conventionalcommits.org/)
   - `feat(domain): descripción`
   - `fix(auth): descripción`
   - `docs(api): descripción`
4. **Tests**: Todo feature nuevo requiere tests. `make test` debe pasar.
5. **PR**: Describí el qué y el por qué. Referenciá el issue.

## Setup local

```bash
git clone https://github.com/Wiltoken/Inmobiliaria.git
cd Inmobiliaria
cp .env.example .env
make dev      # levanta postgres + redis + api (hot reload)
make migrate  # corre migraciones
make test     # 109 tests deben pasar
```

## Estilo de código

- Python 3.13+, type hints en TODO
- FastAPI depende de Pydantic v2 (no mezclar con v1)
- SQLAlchemy 2.0 async (no sync session)
- Nombres en inglés para código, español para docs/comentarios de dominio

## Documentación

- `docs/ARCHITECTURE.md` para decisiones de diseño
- `docs/API.md` para endpoints
- `docs/DEVELOPMENT.md` para guía de desarrollo
