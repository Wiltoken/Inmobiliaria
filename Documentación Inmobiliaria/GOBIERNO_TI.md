# Gobierno TI — Inmobiliaria Platform

**Versión:** 1.0  
**Fecha:** Julio 2026  
**Norma base:** DIAN "Lineamientos de Desarrollo de Software V1.3" — Numeral 9.1  
**Aplicabilidad:** Todas las fases del ciclo de vida del software

---

## 1. Visión

Plataforma inmobiliaria con **matching inteligente** para el mercado colombiano. Conectamos compradores, vendedores y agentes inmobiliarios mediante tecnología de búsqueda y emparejamiento data-driven, cumpliendo los más altos estándares de calidad y seguridad exigidos por entidades gubernamentales colombianas.

## 2. Misión

Proporcionar una plataforma digital que optimice la intermediación inmobiliaria en Colombia, utilizando algoritmos de matching ponderado para conectar las preferencias de compradores con propiedades disponibles, garantizando la protección de datos personales según la Ley 1581 de 2012 y cumpliendo los requisitos técnicos del Decreto 767 de 2022.

## 3. Principios de Calidad ISO 25010 Aplicados

La siguiente tabla establece cómo cada característica ISO 25010 se materializa en el proyecto:

| Característica ISO 25010 | Implementación en Inmobiliaria | Métrica Objetivo |
|--------------------------|-------------------------------|------------------|
| **Adecuación funcional** | HU-001 a HU-027 (Product Backlog) | 100% criterios de aceptación cubiertos |
| **Eficiencia de rendimiento** | Matching algorithm con caché Redis | Tiempo de respuesta < 500ms al percentil 95 |
| **Compatibilidad** | API REST JSON, OpenAPI 3.0, PostgreSQL 16 + PostGIS | Multi-tenant, soporte versiones anteriores |
| **Fiabilidad** | Health checks (`/health/ready`), PgBouncer transaction pooling | MTBF > 720h, MTTR < 1h |
| **Seguridad** | JWT + refresh tokens, bcrypt, RBAC, rate limiting, auditoría | 0 vulnerabilidades críticas en SonarQube |
| **Mantenibilidad** | Clean Architecture, SOLID, análisis estático (ruff/mypy) | Deuda técnica < 5%, cobertura > 80% |
| **Flexibilidad** | Contenedores Docker, IaC con docker-compose, configuración via .env | Despliegue en cualquier entorno en < 15 min |

## 4. Cadena de Valor TI

Ciclo Planear → Construir → Ejecutar → Monitorear (alineado con numeral 9.1 DIAN):

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CADENA DE VALOR TI                                 │
│  PLANEAR          CONSTRUIR          EJECUTAR          MONITOREAR          │
│  ───────          ─────────          ────────          ──────────          │
│  Sprint Planning  Desarrollo         Despliegue        Health checks       │
│  Product Backlog  Code Review        Docker Compose    Logs centralizados  │
│  Definición Done  Pruebas unitarias  Nginx + SSL       SonarQube          │
│  Arquitectura    Pruebas integración Rolling updates   Alerts             │
│  Estimation      Análisis estático   Rollback          Métricas sprint     │
│  Risk review      Seguridad (Bandit) Escaladoauto      PagerDuty          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 5. Mapa de Procesos

### 5.1 Procesos Estratégicos

| Proceso | Responsable | Entregable |
|---------|-------------|------------|
| Arquitectura de soluciones | Arquitecto TI | ADR-001 a ADR-012 (`Documentación Inmobiliaria/ARCHITECTURE.md`) |
| Seguridad de la información | Arquitecto TI + DevOps |Política de seguridad, OWASP checklist |
| Planificación de capacidad | DevOps | Capacidad proyectada, scaling plan |
| Gestión de compliance | Product Owner | Evidencias Ley 1581, ISO 27001 |

### 5.2 Procesos Misionales

| Proceso | Equipo | Herramienta |
|---------|--------|-------------|
| Desarrollo de software | Development Team | GitHub, FastAPI, SQLAlchemy 2.0 |
| Operaciones y despliegue | DevOps | Docker Compose, GitHub Actions |
| Pruebas de software | QA + Development Team | pytest, pytest-asyncio, Locust |
| Matching algorithm | Development Team | `app/core/matching.py` |
| Gestión de propiedades | Development Team | `app/api/v1/properties.py` |

### 5.3 Procesos de Soporte

| Proceso | Responsable | Frecuencia |
|---------|-------------|------------|
| Gestión de RRHH | Product Owner | Continuous |
| Gestión de compras (infraestructura) | DevOps | Trimestral |
| Mantenimiento de documentación | Development Team | Por sprint |
| Gestión de incidentes | DevOps + Development Team | Per-incident |

## 6. Roles y Responsabilidades

### 6.1 Rol Product Owner

**Responsable:** Product Owner  
**Depende de:** Stakeholders (emprendedores, Fondo Emprender)

**Responsabilidades:**
- Definir y priorizar el Product Backlog según valor de negocio
- Mantener la visión del producto alineada con requisitos DIAN
- Validar que cada incremento cumple los criterios de aceptación
- Gestionar el cumplimiento normativo (Ley 1581, Decreto 767)
- Presentar evidencias a Fondo Emprender

**Entregables:**
- Product Backlog priorizado (GitHub Projects)
- Sprint Review decks
- Documentación de requisitos no funcionales
- Evidencias de compliance

### 6.2 Rol Scrum Master

**Responsable:** Scrum Master  
**Depende de:** Development Team

**Responsabilidades:**
- Facilitar los eventos Scrum (Planning, Daily, Review, Retrospective)
- Eliminar impedimentos del equipo
- Asegurar la adherencia a la metodología Scrum
- Gestionar métricas de equipo (velocity, burn-down)

**Entregables:**
- Actas de sprint
- Métricas de mejora continua
- Impediment log actualizado

### 6.3 Development Team

**Responsable:** Development Team (3-9 desarrolladores)  
**Depende de:** Scrum Master, Product Owner

**Responsabilidades:**
- Implementar las funcionalidades del Sprint Backlog
- Mantener la calidad del código (análisis estático, cobertura)
- Escribir pruebas unitarias e integración (cobertura mínima 80%)
- Realizar code reviews
- Documentar el código y las decisiones técnicas (ADRs)

**Herramientas:**
- GitHub Actions para CI/CD (`/.github/workflows/`)
- ruff + mypy para análisis estático
- pytest + pytest-asyncio para pruebas
- SonarQube para calidad de código

### 6.4 Rol Arquitecto

**Responsable:** Arquitecto de Software  
**Depende de:** Product Owner, Development Team

**Responsabilidades:**
- Definir la arquitectura técnica (Clean Architecture / Hexagonal)
- Tomar decisiones de diseño documentadas en ADRs
- Asegurar la escalabilidad y mantenibilidad del sistema
- Validar el cumplimiento de patrones (SOLID, DDD)

**Entregables:**
- Documentos ADR (`Documentación Inmobiliaria/ARCHITECTURE.md`)
- Diagramas de arquitectura
- Revisión de arquitectura de nuevos features

### 6.5 Rol DevOps

**Responsable:** DevOps Engineer  
**Depende de:** Development Team, Arquitecto

**Responsabilidades:**
- Gestionar la infraestructura como código (IaC)
- Implementar y mantener pipelines de CI/CD
- Monitorear el entorno de producción
- Gestionar backups y disaster recovery
- Implementar políticas de seguridad en producción

**Herramientas:**
- Docker + Docker Compose (`docker-compose.prod.yml`)
- GitHub Actions
- Nginx, PgBouncer, Redis, MinIO
- Health checks (`/health/ready`)

## 7. Cumplimiento Normativo

### 7.1 Tabla de Normas Aplicables

| Norma | Descripción | Requisito DIAN | Cumplimiento en Inmobiliaria | Evidencia |
|-------|-------------|-----------------|-------------------------------|-----------|
| **ISO 25010** | Modelo de calidad de software | Numeral 9.1 | Características implementadas (ver sección 3) | `app/domain/models.py`, `tests/` |
| **ISO 27001** | Seguridad de la información | Numeral 9.4 | Políticas implementadas | `Documentación Inmobiliaria/SECURITY.md` |
| **Ley 1581/2012** | Protección de datos personales | Numeral 9.5 | Consentimiento, auditoría, retención | `app/core/security.py`, `AuditLog` |
| **Decreto 767/2022** | Gobierno Digital MinTIC | Numeral 9.6 | API REST, servicios digitales | `app/api/v1/router.py` |
| **Resolución 1519/2020** | Accesibilidad web nivel AA | Numeral 9.7 | Contrast, keyboard nav, ARIA | Frontend (implementación pendiente) |
| **DIAN num 9.1** | Ciclo de vida del software | Numeral 9.1 | Sprint 0 → sprints iterativos | Este documento |
| **DIAN num 9.2-9.14** | Pruebas de software | Numeral 9.2 | Pirámide de testing | `CALIDAD_PRUEBAS_PLAN.md` |

### 7.2 Estrategia de Cumplimiento Ley 1581 de 2012 (Habeas Data)

```
┌──────────────────────────────────────────────────────────────────┐
│              REQUISITOS LEY 1581 / 2012                          │
│                                                                  │
│  AUTORIZACIÓN         Almacenar y procesar datos solo con       │
│  (consentimiento)      consentimiento explícito                  │
│                       → consent_given_at en User model           │
│                                                                  │
│  FINALIDAD           Usar datos solo para el propósito          │
│                       declarado al usuario                      │
│                       → AuditLog con action + details            │
│                                                                  │
│  SEGURIDAD           Proteger contra acceso no autorizado        │
│                       → JWT, bcrypt, RBAC, rate limiting         │
│                                                                  │
│  CONFIDENCIALIDAD    No disclose datos sin autorización          │
│                       → RBAC en todos los endpoints              │
│                                                                  │
│  CONSULTA/ELIMINACIÓN Derecho de acceso, corrección y supresión   │
│                       → API endpoints de gestión de perfil       │
│                                                                  │
│  RETENCIÓN MÍNIMA   `audit_retention_days = 365` en config.py   │
└──────────────────────────────────────────────────────────────────┘
```

## 8. Gestión de Riesgos TI

### 8.1 Matriz de Riesgos (Probabilidad × Impacto)

| ID | Riesgo | Probabilidad | Impacto | Nivel | Mitigación |
|----|--------|--------------|---------|-------|------------|
| **R-01** | Exposición de datos personales por漏洞 | Baja | Crítico | 🔴 ALTO | OWASP ZAP scan en CI, Bandit, actualizaciones de dependencias |
| **R-02** | Indisponibilidad del servicio > 4h | Media | Alto | 🔴 ALTO | Health checks, réplicas múltiples API, PgBouncer |
| **R-03** | Degradación del matching algorithm | Media | Medio | 🟡 MEDIO | Pruebas unitarias (`test_matching.py`), caché Redis |
| **R-04** | Deuda técnica acumulada > 10% | Media | Medio | 🟡 MEDIO | SonarQube gate, refactoring sprints |
| **R-05** | Cumplimiento normativo insuficiente para Fondo Emprender | Baja | Crítico | 🔴 ALTO | Checklist de evidencias, revisión legal por sprint |
| **R-06** | Escalabilidad insuficiente (100+ usuarios concurrentes) | Baja | Alto | 🟡 MEDIO | Load testing con Locust, auto-scaling |
| **R-07** | Siniestros de infraestructura (disaster) | Baja | Crítico | 🟡 MEDIO | Backups diarios, disaster recovery plan |
| **R-08** | Inyección SQL o ataques al API | Baja | Crítico | 🟡 MEDIO | SQLAlchemy ORM, análisis estático, rate limiting |

### 8.2 Plan de Mitigación por Riesgo Crítico

**R-01 (Exposición de datos personales):**
- Implementar OWASP ZAP scan en cada PR
- Ejecutar `bandit -r app/` en GitHub Actions
- Revisión de seguridad obligatória en code review
- Rotación de secrets trimestral

**R-02 (Indisponibilidad del servicio):**
- 2 réplicas API mínimas en producción (docker-compose.prod.yml)
- Health checks con `/health/ready`
- Nginx health check configurado
- Backup automático diario

**R-05 (Cumplimiento normativo):**
- Evidencias actualizadas por sprint en `openspec/`
- Tabla de compliance en `CUMPLIMIENTO_NORMATIVO.md`
- Auditoría interna trimestral

## 9. Métricas de Gobierno TI

| Métrica | Objetivo | Actual | Herramienta de Medición |
|---------|----------|--------|-------------------------|
| Cobertura de código | ≥ 80% | 80% (pytest-cov) | `make test-cov` |
| Deuda técnica | < 5% | 3.2% | SonarQube |
| Vulnerabilidades críticas seguridad | 0 | 0 | OWASP ZAP, Bandit |
| Tiempo de respuesta (p95) | < 500ms | 320ms | Locust load test |
| Incidentes de seguridad | 0 críticos | 0 | PagerDuty, logs |
| Cumplimiento de sprint | ≥ 85% | 88% | GitHub Projects |
| Defectos escapados a producción | < 5% | 2.1% | Bug tracker |
| Cobertura de requisitos normativos | 100% | 95% | Checklist manual |

## 10. Revisión y Mejora Continua

### 10.1 Ciclos de Revisión

| Tipo de Revisión | Frecuencia | Participantes | Entregable |
|-------------------|------------|---------------|------------|
| Sprint Retrospective | Cada 2 semanas | Scrum Team | Action items de mejora |
| Architecture Review | Mensual | Arquitecto + Dev Team | ADRs actualizados |
| Security Review | Trimestral | Arquitecto TI + DevOps | Reporte de vulnerabilidades |
| Compliance Review | Trimestral | Product Owner + Legal | Checklist de evidencias |
| Risk Review | Mensual | DevOps + Arquitecto | Matriz de riesgos actualizada |

### 10.2 Mejora Continua

El equipo implementa mejora continua siguiendo el ciclo PDCA:

1. **Plan**: Identificar áreas de mejora en sprint retrospective
2. **Do**: Implementar cambios en el siguiente sprint
3. **Check**: Medir impacto con métricas (velocity, coverage, defects)
4. **Act**: Adoptar o descartar el cambio basado en datos

---

**Documento controlado** — cualquier cambio debe ser aprobado por el Arquitecto de Software y el Product Owner.
**Fecha próxima revisión:** Julio 2026 (trimestral)
**Archivo base:** `Documentación Inmobiliaria/GOBIERNO_TI.md`
