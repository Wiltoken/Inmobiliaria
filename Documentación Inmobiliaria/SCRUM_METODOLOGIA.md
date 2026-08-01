# Metodología Scrum Adaptada — Inmobiliaria Platform

**Versión:** 1.0  
**Fecha:** Julio 2026  
**Base normativa:** DIAN "Lineamientos de Desarrollo de Software V1.3" — Numeral 9.1  
**Framework de referencia:** Scrum Guide 2020  

---

## 1. Marco Scrum Adaptado para Inmobiliaria

### 1.1 Los Tres Pilares de Scrum

| Pilar | Aplicación en Inmobiliaria |
|-------|---------------------------|
| **Transparencia** | Product Backlog visible en GitHub Projects, Definition of Done compartida |
| **Inspección** | Daily standups, Sprint Review, métricas de calidad |
| **Adaptación** | Sprint Retrospective, ajuste de prioridades en Sprint Planning |

### 1.2 Roles Scrum

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCT OWNER                            │
│  Maximiza el valor del producto, gestiona el backlog       │
│  →Responsable: 1 persona                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    SCRUM MASTER                            │
│  Facilita eventos, elimina impedimentos                    │
│  →Responsable: 1 persona                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  DEVELOPMENT TEAM                           │
│  Implementa el incremento, ownership técnico               │
│  →3-9 desarrolladores (cross-functional)                   │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Eventos Scrum

| Evento | Duración | Frecuencia | Participantes | Entregable |
|--------|----------|------------|---------------|------------|
| **Sprint** | 2 semanas | Continuo | Todos | Incremento de software |
| **Sprint Planning** | 4 horas | Inicio de sprint | Todos | Sprint Backlog, Definition of Done |
| **Daily Scrum** | 15 min | Diario | Development Team | Impediment log actualizado |
| **Sprint Review** | 2 horas | Fin de sprint | Todos | Incremento demostrado, feedback |
| **Sprint Retrospective** | 1.5 horas | Fin de sprint | Scrum Team | Action items de mejora |

### 1.4 Artefactos Scrum

| Artefacto | Descripción | Ubicación | Ownership |
|-----------|-------------|-----------|-----------|
| **Product Backlog** | Lista priorizada de todo el trabajo | GitHub Projects | Product Owner |
| **Sprint Backlog** | Elementos seleccionados para el sprint actual | GitHub Projects | Development Team |
| **Incremento** | Sumatoria de todos los elementos completados | `main` branch | Development Team |
| **Definition of Done** | Criterios de completitud | Este documento | Todos |

## 2. Ciclo de Vida del Desarrollo (Numeral 9.1 DIAN)

El ciclo de vida del proyecto Inmobiliaria se alinea con el numeral 9.1 del documento DIAN:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CICLO DE VIDA INMOBILIARIA                              │
│                                                                             │
│  ┌─────────┐   ┌──────────────┐   ┌───────────┐   ┌──────────┐         │
│  │INICIACIÓN│ → │PLANIFICACIÓN │ → │DESARROLLO │ → │PRUEBAS   │         │
│  │          │   │              │   │           │   │          │         │
│  │Sprint 0 │   │Sprint 1..N   │   │ coding     │   │pytest    │         │
│  │4 semanas│   │2 semanas/spr │   │git workflow│   │sonar     │         │
│  └─────────┘   └──────────────┘   └───────────┘   └──────────┘         │
│                                                              │             │
│       ┌──────────────────────────────────────────────────────┘             │
│       ▼                                                                     │
│  ┌────────────┐   ┌──────────────┐   ┌────────────────────┐              │
│  │DESPLIEGUE  │ → │ESTABILIZACIÓN│ → │MANTENIMIENTO       │              │
│  │            │   │              │   │                    │              │
│  │docker comp │   │smoke tests   │   │soporte + releases  │              │
│  │github act. │   │hotfixes      │   │                      │              │
│  └────────────┘   └──────────────┘   └────────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 3. Sprint 0: Fundamentos del Proyecto

### 3.1 Objetivo del Sprint 0

Establecer las bases técnicas y organizacionales del proyecto antes de iniciar el desarrollo iterativo.

### 3.2 Entregables del Sprint 0

| Entregable | Descripción | Archivo/Directorio |
|-----------|-------------|-------------------|
| Visión del producto | Descripción del producto mínimo viable | `openspec/` |
| Equipo formado | Roles asignados, disponibilidad | GitHub Teams |
| Backlog inicial | Primeras 20-30 historias de usuario | GitHub Projects |
| Arquitectura definida | ADRs aprobados, diagrama de componentes | `Documentación Inmobiliaria/ARCHITECTURE.md` |
| Definition of Done | Criterios de completitud | Este documento (sección 5) |
| Definition of Ready | Criterios para aceptar una HU en sprint | Sección 4.3 |
| Entorno de desarrollo | Docker Compose dev, CI/CD pipeline | `docker-compose.dev.yml`, `.github/workflows/` |
| Producto de backlog priorizado | Primeras 15 HU con criterios de aceptación | GitHub Projects |

### 3.3 Definition of Ready (DoR)

Una historia de usuario está **ready** para entrar en un sprint si cumple:

- [ ] El título y la descripción son claros
- [ ] Los criterios de aceptación están definidos (formato Given/When/Then)
- [ ] La estimación está asignada (story points)
- [ ] La prioridad está clasificada (CRÍTICA | ALTA | MEDIA | BAJA)
- [ ] Las dependencias están identificadas
- [ ] Los requisitos no funcionales están especificados
- [ ] El diseño técnico ha sido revisado por el arquitecto (si aplica)

## 4. Formato de Historia de Usuario

Basado en la plantilla FT-IIT-2006 del documento DIAN:

```markdown
## HU-XXX: [Título]

**Como** [rol de usuario]  
**Quiero** [funcionalidad]  
**Para** [beneficio de negocio]

### Información General

| Campo | Valor |
|-------|-------|
| ID | HU-XXX |
| Prioridad | CRÍTICA / ALTA / MEDIA / BAJA |
| Estimación | [X] story points |
| Sprint asignado | [Sprint N] |
| Estado | [To Do / In Progress / Done] |

### Criterios de Aceptación

**Escenario 1:** [Nombre del escenario]

- **Dado** [contexto inicial]
- **Cuando** [acción realizada por el actor]
- **Entonces** [resultado esperado]

**Escenario 2:** [Nombre del escenario]

- **Dado** [contexto inicial]
- **Cuando** [acción realizada]
- **Entonces** [resultado esperado]

### Prototipos / Mockups

[Referencia a Figma / imagen / link]

### Requisitos No Funcionales

| Requisito | Criterio |
|-----------|----------|
| Seguridad | JWT, RBAC, rate limiting |
| Rendimiento | Tiempo de respuesta < 500ms |
| Disponibilidad | 99.9% uptime |
| Accesibilidad | WCAG 2.1 AA |
| Compatibilidad | API REST JSON, OpenAPI 3.0 |

### Criterios de Đone (Definition of Done)

- [ ] Código implementado y merged en `main`
- [ ] Pruebas unitarias passing (cobertura ≥ 80%)
- [ ] Pruebas de integración passing
- [ ] Análisis estático passing (ruff, mypy, bandit)
- [ ] Code review aprobado por al menos 1 par
- [ ] Documentación actualizada
- [ ] Desplegable en entorno de staging
```

### Ejemplo Concreto del Proyecto

```markdown
## HU-007: Búsqueda de propiedades con filtros geoespaciales

**Como** comprador  
**Quiero** buscar propiedades dentro de un radio específico desde un punto en el mapa  
**Para** encontrar rápidamente inmuebles en la zona que me interesa

### Información General

| Campo | Valor |
|-------|-------|
| ID | HU-007 |
| Prioridad | ALTA |
| Estimación | 8 story points |
| Sprint asignado | Sprint 3 |
| Estado | Done |

### Criterios de Aceptación

**Escenario 1:** Búsqueda por radio desde Bogotá

- **Dado** que el usuario ha iniciado sesión como comprador
- **Cuando** ingresa "Bogotá Centro" y selecciona radio de 5km
- **Entonces** el sistema retorna propiedades dentro del radio ordenadas por score de matching

**Escenario 2:** Sin resultados en el área

- **Dado** que no existen propiedades en el radio especificado
- **Cuando** el usuario realiza la búsqueda
- **Entonces** el sistema muestra mensaje "No se encontraron propiedades en esta zona"

### Requisitos No Funcionales

| Requisito | Criterio |
|-----------|----------|
| Seguridad | JWT válido requerido, solo usuarios autenticados |
| Rendimiento | Retorno de resultados < 500ms para радиус 10km |
| Almacenamiento | Índices PostGIS GIST en `location` column |
```

## 5. Definition of Done (DoD)

### 5.1 Criterios Obligatorios

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DEFINITION OF DONE                                   │
│                                                                             │
│  ✅ Código implementado en branch feature, merged a main via PR           │
│  ✅ Code review aprobado (mínimo 1 approval, sin unresolved comments)     │
│  ✅ Pruebas unitarias passing (mínimo 80% coverage)                        │
│  ✅ Pruebas de integración passing                                         │
│  ✅ Análisis estático passing (ruff, mypy, bandit)                          │
│  ✅ Documentación actualizada (docstrings, ADRs si aplica)                │
│  ✅ Incremento desplegable en entorno de staging                           │
│  ✅ Criterios de aceptación verificados                                    │
│  ✅ SonarQube: 0 vulnerabilidades críticas, deuda técnica < 5%            │
│  ✅ OWASP ZAP scan passing (para features con datos sensibles)            │
│  ✅ Feature flag deshabilitado (si aplica)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Checklist de Despliegue

- [ ] Migraciones de base de datos aplicadas
- [ ] Variables de entorno configuradas en staging
- [ ] Health checks respondiendo OK
- [ ] Logs sin errores ERROR/CRITICAL
- [ ] Métricas de rendimiento dentro de umbrales
- [ ] Backup realizado antes del despliegue
- [ ] Rollback plan documentado

## 6. Sprints de Desarrollo

### 6.1 Duración y Configuración

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| Duración del sprint | 2 semanas (10 días hábiles) | Equilibrio entre velocidad y planificación |
| Sprints por release | 2-3 sprints | Feature completo |
| Daily standup | Diario 15:00 Colombia | overlap con timezone del equipo |
| Sprint Planning | Lunes 9:00 | Inicio de sprint |
| Sprint Review | Viernes 14:00 (último día) | Demo a stakeholders |
| Retrospective | Viernes 16:00 (último día) | Mejora continua |

### 6.2 Flujo de Trabajo Git

```
feature/HU-007-geo-search
    │
    ├── Crear branch desde main
    │   git checkout -b feature/HU-007-geo-search
    │
    ├── Desarrollo + pruebas
    │   (mínimo 80% coverage, ruff clean, mypy strict)
    │
    ├── Pull Request → main
    │   ├── Título: "feat(properties): add geospatial search HU-007"
    │   ├── Description: Link a HU en GitHub Projects
    │   ├── Checklist: DoD items verificados
    │   └── Required reviewers: 1 (del equipo)
    │
    ├── GitHub Actions CI/CD
    │   ├── ruff check
    │   ├── mypy type check
    │   ├── pytest (unit + integration)
    │   ├── pytest-cov (cobertura ≥ 80%)
    │   ├── bandit security scan
    │   └── Docker build test
    │
    └── Merge a main
        └── Despliegue automático a staging
```

## 7. Métricas Scrum

### 7.1 Métricas de Equipo

| Métrica | Fórmula | Objetivo | Herramienta |
|---------|---------|----------|------------|
| **Velocity** | Story points completados por sprint | Tendencia creciente o estable | GitHub Projects |
| **Burn-down** | Trabajo restante vs tiempo | Línea descendente | GitHub Projects |
| **Defect Escape Rate** | Defectos encontrados en producción / total defectos | < 5% | Bug tracker |
| **Lead Time** | Tiempo desde idea hasta producción | Reducción continua | GitHub Projects |
| **Cycle Time** | Tiempo desde "In Progress" hasta "Done" | < 3 días por HU | GitHub Projects |

### 7.2 Métricas de Calidad

| Métrica | Objetivo | Actual | Herramienta |
|---------|----------|--------|------------|
| Code coverage | ≥ 80% | 80% | pytest-cov |
| Deuda técnica | < 5% | 3.2% | SonarQube |
| Vulnerabilidades críticas | 0 | 0 | Bandit + OWASP ZAP |
| Pruebas passing | 100% | 100% | GitHub Actions |
| Code smells | < 10 por sprint | 4 | SonarQube |

### 7.3 Dashboard de Métricas

Las métricas se visualizan en:
- **GitHub Projects** → Sprint Burn-down, Velocity
- **SonarQube** → Code coverage, Debt, Vulnerabilities
- **GitHub Actions** → CI/CD status, test results
- **PagerDuty** → Incidentes, MTTR

## 8. Herramientas

### 8.1 Stack de Herramientas

| Categoría | Herramienta | Uso |URL/Referencia |
|-----------|------------|-----|---------------|
| Project Management | GitHub Projects | Product Backlog, Sprint Board | github.com/org/inmobiliaria |
| Version Control | Git + GitHub | Source code, branches, PRs | github.com/org/inmobiliaria |
| CI/CD | GitHub Actions | Automatización de build, test, deploy | `.github/workflows/` |
| Análisis Estático | ruff + mypy + bandit | Code quality, types, security | `pyproject.toml` |
| Testing | pytest + pytest-asyncio | Unit, integration, e2e tests | `tests/` |
| Quality Gate | SonarQube | Code coverage, debt, smells | (self-hosted o cloud) |
| Load Testing | Locust | Pruebas de rendimiento | `tests/load/` |
| Security Scanning | OWASP ZAP + Bandit | Vulnerability scanning | CI/CD pipeline |
| Documentation | openspec + Markdown | Specs, ADRs, guides | `Documentación Inmobiliaria/` |
| API Documentation | FastAPI OpenAPI | Interactive API docs | `/docs` |

### 8.2 Configuración de GitHub Actions (CI)

Ubicación: `.github/workflows/ci.yml`

```yaml
# Verificación: ruff, mypy, pytest, coverage
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Ruff lint
        run: ruff check app/
      - name: Mypy type check
        run: mypy app/
      - name: Run tests
        run: pytest tests/ -v --cov=app --cov-report=xml
      - name: SonarQube
        uses: sonarsource/sonarqube-scan-action@master
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

## 9. Reglas de Compromiso del Equipo

### 9.1 Compromisos del Development Team

1. **Participación activa** en todos los eventos Scrum
2. **Transparencia** sobre impedimentos y riesgos
3. **Auto-organización** para completar el Sprint Backlog
4. **Calidad primero** — no comprometer la calidad por velocidad
5. **Code review** — revisar PRs de compañeros dentro de 24h
6. **Documentación** — documentar decisiones técnicas en ADRs

### 9.2 Compromisos del Product Owner

1. **Disponibilidad** para clarificar requisitos dentro de 24h
2. **Priorización** del backlog actualizada antes de cada sprint
3. **Decisiones de negocio** tomadas oportunamente
4. **Stakeholder management** — gestionar expectativas de clientes

### 9.3 Compromisos del Scrum Master

1. **Facilitación** efectiva de todos los eventos
2. **Eliminación de impedimentos** dentro de su alcance
3. **Coaching** del equipo en prácticas ágiles
4. **Protección del equipo** de interrupciones externas

## 10. Gestión de Excepciones

### 10.1 Sprint Interrumpido

Si un sprint debe ser interrumpido:

1. Documentar el motivo en GitHub Issues
2. Cancelar el sprint en GitHub Projects
3. Re-estimar las HU no completadas
4. Planificar un nuevo sprint con las HU restantes
5. Revisar en retrospectiva qué causó la interrupción

### 10.2 Historias de Usuario No Completadas

Las HU no completadas al final del sprint:

1. Regresar al Product Backlog con la etiqueta "incomplete"
2. Re-estimar considerando el trabajo restante
3. Priorizar nuevamente en el siguiente sprint planning
4. **No transferir story points** al siguiente sprint

---

**Documento controlado** — cualquier cambio debe ser aprobado por el Scrum Master y el Product Owner.  
**Archivo base:** `Documentación Inmobiliaria/SCRUM_METODOLOGIA.md`
