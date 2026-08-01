# Plan de Calidad y Pruebas — Inmobiliaria Platform

**Versión:** 1.0  
**Fecha:** Julio 2026  
**Base normativa:** DIAN "Lineamientos de Desarrollo de Software V1.3" — Numerales 9.2 a 9.14  
**Alcance:** Todas las pruebas de software del proyecto  

---

## 1. Estrategia de Pruebas

### 1.1 Pirámide de Testing

```
                              ╱╲
                             ╱  ╲
                            ╱ E2E╲          10% — E2E (2 tests)
                           ╱──────╲
                          ╱Integr.╲        20% — Integración (9 tests)
                         ╱──────────╲
                        ╱  Unitarias  ╲    70% — Unitarias (28 tests)
                       ╱──────────────╲
                      ╱────────────────╲
                     ╱    ANALISIS      ╲
                    ╱   ESTATICO         ╲
                   ╱──────────────────────╲

         Total tests: ~39 tests (unit + integration)
         Coverage objetivo: ≥ 80%
```

### 1.2 Cobertura Actual por Tipo

| Nivel | Tests | Cobertura | Archivos Clave |
|-------|-------|-----------|----------------|
| **Unitarios** | 28 tests | 80% | `tests/unit/` |
| **Integración** | 9 tests | 65% | `tests/integration/` |
| **E2E** | 2 tests | — | `tests/e2e/` |
| **Total** | **39 tests** | **~78%** | — |

### 1.3 Objetivos de Cobertura

| Componente | Cobertura Mínima | Componentes Críticos |
|-----------|-------------------|---------------------|
| `app/core/` | 85% | `security.py`, `matching.py`, `exceptions.py` |
| `app/domain/` | 80% | `models.py`, `schemas.py` |
| `app/adapters/` | 75% | `database.py`, `redis_client.py` |
| `app/api/v1/` | 70% | `auth.py`, `properties.py`, `matches.py` |
| **Global** | **80%** | — |

## 2. Pruebas Unitarias

### 2.1 Stack Tecnológico

| Componente | Herramienta | Propósito |
|------------|-------------|----------|
| Framework | `pytest 8.3+` | Ejecución de tests |
| Async | `pytest-asyncio 0.25+` | Tests asíncronos con `async def` |
| Coverage | `pytest-cov 6.0+` | Medición de cobertura |
| Mocking | `fakeredis 2.26+` | Redis falso para tests |

### 2.2 Estructura de Tests Unitarios

```
tests/unit/
├── __init__.py
├── test_config.py      # 11,675 bytes — Configuración y settings
├── test_matching.py    # 9,146 bytes — Algoritmo de matching
├── test_schemas.py     # 12,580 bytes — Validación Pydantic
└── test_security.py    # 22,185 bytes — Hashing, JWT, passwords
```

### 2.3 Ejemplo de Test Unitario

```python
# tests/unit/test_security.py — hash_password
async def test_hash_password_returns_hash():
    """hash_password returns a bcrypt hash that can be verified."""
    password = "TestPassword123!"
    hashed = hash_password(password)
    
    assert hashed != password
    assert hashed.startswith("$2b$")  # bcrypt prefix
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


async def test_hash_password_raises_on_policy_violation():
    """hash_password raises PasswordPolicyError for weak passwords."""
    with pytest.raises(PasswordPolicyError) as exc_info:
        hash_password("short")
    
    violations = exc_info.value.violations
    assert len(violations) > 0
    assert violations[0]["field"] == "password"
```

### 2.4 Ejecución

```bash
# Ejecutar todos los tests unitarios
make test-unit

# Ejecutar con cobertura
make test-cov

# Output esperado
# tests/unit/test_config.py::test_settings_load ✓
# tests/unit/test_matching.py::test_score_calculation ✓
# tests/unit/test_security.py::test_hash_password_returns_hash ✓
# --- 28 passed, 0 failed, coverage: 80% ---
```

## 3. Pruebas de Integración

### 3.1 Componentes Probados

| Componente | Descripción | Archivo |
|-----------|-------------|---------|
| Auth Service | Login, logout, refresh tokens | `tests/integration/test_auth_service.py` |
| Rate Limiter | Token bucket algorithm | `tests/integration/test_rate_limiter.py` |
| Properties API | CRUD de propiedades | `tests/integration/test_properties.py` |

### 3.2 Tests de Integración Actuales

```
tests/integration/
├── __init__.py
├── test_auth_service.py    # 8,595 bytes — Flujo completo auth
├── test_properties.py      # 8,084 bytes — CRUD propiedades
└── test_rate_limiter.py   # 6,506 bytes — Rate limiting
```

### 3.3 Ejemplo de Test de Integración

```python
# tests/integration/test_auth_service.py
async def test_login_success_returns_tokens(test_client: AsyncClient, test_user: User):
    """Successful login returns access and refresh tokens."""
    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "ValidPass1!",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_invalid_credentials_returns_401(
    test_client: AsyncClient,
    test_user: User,
):
    """Invalid credentials return 401 with error code."""
    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "WrongPassword",
        },
    )
    
    assert response.status_code == 401
    data = response.json()["detail"]
    assert data["error_code"] == "AUTH_INVALID_CREDENTIALS"
```

### 3.4 Fixtures de Integration Tests

```python
# tests/conftest.py — Fixtures para integración
@pytest_asyncio.fixture
async def test_db(test_settings: AuthSettings) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh in-memory SQLite DB for each test."""
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_client(test_settings: AuthSettings) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX AsyncClient wired to the FastAPI app via ASGI transport."""
    # Parche del módulo de base de datos para usar el motor de test
    ...
```

## 4. Pruebas Funcionales

### 4.1 Casos de Prueba por Historia de Usuario

Formato basado en FT-IIT-1849 (DIAN):

```markdown
## Caso de Prueba FT-IIT-001: Autenticación de usuario

### Datos de Entrada
- Username: `testuser@example.com`
- Password: `ValidPass1!`

### Pasos
1. Navegar a `/api/v1/auth/login`
2. Ingresar username y password
3. Hacer click en "Iniciar sesión"

### Resultado Esperado
- Código HTTP: 200
- Response body contiene `access_token` y `refresh_token`
- Redirección a dashboard

### Criterio de Aceptación
HU-001: Como usuario quiero iniciar sesión para acceder a mi cuenta
```

### 4.2 Casos de Prueba para HU-007 (Búsqueda Geoespacial)

| ID | Escenario | Entrada | Resultado Esperado | Estado |
|----|-----------|---------|-------------------|--------|
| FT-007-01 | Búsqueda con radio válido | Bogotá, 5km | Lista de propiedades ordenadas por distancia | ✅ Implementado |
| FT-007-02 | Sin resultados en área | Zona rural sin propiedades | Mensaje "No se encontraron propiedades" | ⏳ Pendiente |
| FT-007-03 | Radio inválido | Radio negativo | Error 400 con mensaje de validación | ⏳ Pendiente |

## 5. Pruebas de Rendimiento

### 5.1 Herramienta: Locust

**Ubicación:** `tests/load/` (por crear)

### 5.2 Escenarios de Carga

| Escenario | Usuarios Concurrentes | Objetivo |
|-----------|---------------------|----------|
| Login burst | 100 | Tiempo respuesta < 500ms |
| Búsqueda de propiedades | 50 | Tiempo respuesta < 500ms |
| Matching algorithm | 30 | Tiempo respuesta < 1s |
| Health check | 200 | 100% success rate |

### 5.3 Configuración de Locust

```python
# tests/load/test_api_load.py
from locust import HttpUser, task, between

class InmobiliariaUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    @task(3)
    def search_properties(self):
        """Búsqueda de propiedades — más frecuente."""
        self.client.get("/api/v1/properties/?operation=sale&limit=20")

    @task(1)
    def view_property_detail(self):
        """Detalle de propiedad."""
        self.client.get("/api/v1/properties/{property_id}")

    @task(1)
    def health_check(self):
        """Health check endpoint."""
        self.client.get("/health/ready")
```

### 5.4 Métricas de Rendimiento Objetivo

| Métrica | Objetivo | Crítico | Crítico + |
|---------|----------|---------|-----------|
| Tiempo respuesta (p50) | < 200ms | < 500ms | < 1s |
| Tiempo respuesta (p95) | < 300ms | < 500ms | < 2s |
| Tiempo respuesta (p99) | < 500ms | < 1s | < 5s |
| Throughput | > 100 req/s | > 50 req/s | > 20 req/s |
| Error rate | < 1% | < 5% | < 10% |

### 5.5 Ejecución de Load Tests

```bash
# Ejecutar load test con 100 usuarios por 5 minutos
locust -f tests/load/test_api_load.py \
  --host=http://localhost:8000 \
  --users=100 \
  --spawn-rate=10 \
  --run-time=5m \
  --headless \
  --html=tests/load/report.html
```

## 6. Pruebas de Seguridad

### 6.1 OWASP ZAP Scan

```bash
# Scan básico en staging
docker run -v $(pwd):/zap/wrk:rw \
  owasp/zap2docker-stable zap-baseline.py \
  -t https://staging.inmobiliaria.com \
  -J zap_report.json

# Scan completo con autenticación
docker run -v $(pwd):/zap/wrk:rw \
  owasp/zap2docker-stable zap-full-scan.py \
  -t https://staging.inmobiliaria.com \
  -z "-config spider.context.name=Inmobiliaria" \
  -J zap_full_report.json
```

### 6.2 JWT Security Testing

```python
# tests/unit/test_security.py — Pruebas JWT
async def test_decode_token_raises_on_expired():
    """decode_token raises TokenExpiredError for expired tokens."""
    # Crear token con TTL muy corto
    token = create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=["buyer"],
        jti="test-jti",
    )
    
    # Simulamos token expirado cambiando el clock
    with freeze_time("2030-01-01"):
        with pytest.raises(TokenExpiredError):
            decode_token(token, expected_type="access")


async def test_decode_token_raises_on_invalid_signature():
    """decode_token raises InvalidTokenError for tampered tokens."""
    token = create_access_token(...)
    tampered = token[:-5] + "xxxxx"  # Corromper firma
    
    with pytest.raises(InvalidTokenError):
        decode_token(tampered, expected_type="access")
```

### 6.3 SQL Injection Testing

```python
# tests/integration/test_properties.py
async def test_search_properties_sql_injection_prevention(test_client: AsyncClient):
    """SQL injection attempts are sanitized by SQLAlchemy ORM."""
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "1 OR 1=1",
        "<script>alert('xss')</script>",
        "UNION SELECT * FROM users--",
    ]
    
    for malicious in malicious_inputs:
        response = await test_client.get(
            f"/api/v1/properties/?title={malicious}"
        )
        # Debe retornar 200 con resultados vacíos, no error 500
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or "results" in data or "data" in data
```

### 6.4 Bandit Security Scan

```bash
# Ejecutar Bandit en CI
bandit -r app/ -f json -o tests/security/bandit_report.json

# Reglas críticas verificadas:
# - B301: pickle — disabled en el proyecto
# - B303: md5 — no usado
# - B308: mark_safe — no usado en templates
# - B310: urllib_urlopen — no usado
# - B312: yaml.load — safe_load usado
```

## 7. Pruebas de Accesibilidad

### 7.1 Requisitos Resolución 1519/2020 (Nivel AA)

| Criterio | Verificación | Herramienta |
|----------|-------------|-------------|
| Contraste de color | Ratio mínimo 4.5:1 para texto normal | axe DevTools |
| Navegación por teclado | Tab, Enter, Escape funcionan | Manual testing |
| ARIA labels | Elementos interactivos tienen labels | axe DevTools |
| Focus visible | Indicador de foco visible | Manual testing |
| Alt text | Imágenes tienen texto alternativo | axe DevTools |

### 7.2 Checklist de Accesibilidad

- [ ] Contraste de color cumple AA (4.5:1 normal, 3:1 grande)
- [ ] Navegación por teclado completa (Tab, Shift+Tab, Enter)
- [ ] Skip links para salto de contenido principal
- [ ] ARIA landmarks definidos (`role="main"`, `role="navigation"`)
- [ ] Labels en todos los inputs de formulario
- [ ] Mensajes de error accesibles (`aria-describedby`)
- [ ] Timeout de sesión informado (donde aplique)
- [ ] Imágenes con `alt` descriptivo
- [ ] No contenido parpadeante > 3 veces/segundo

## 8. Automatización de Pruebas API

### 8.1 Postman/Newman Collections

```bash
# Exportar colección desde Postman
postman_collection_export.json

# Ejecutar con Newman en CI
newman run postman_collection_export.json \
  --environment=staging_environment.json \
  --reporters=cli,junit \
  --reporter-junit-export=tests/api/junit-report.xml
```

### 8.2 Colecciones Principales

| Colección | Endpoints | Frecuencia |
|-----------|-----------|------------|
| Auth API | login, logout, refresh, register | Cada PR |
| Properties API | CRUD, search, filters | Cada PR |
| Matching API | score calculation | Semanal |
| Health API | /health, /health/ready | Daily (monitoring) |

## 9. Análisis Estático

### 9.1 Ruff (Linting)

```bash
# Verificar código
ruff check app/

# Verificar y auto-fix
ruff check app/ --fix

# Formatear código
ruff format app/
```

**Reglas habilitadas:**
- `E` — Errores de sintaxis (Pyflakes)
- `F` — Convenciones de código (Pyflakes)
- `I` — Importaciones (isort)
- `N` — Convenciones de nombres
- `UP` — Compatibilidad Python 3.13
- `B` — Bugs (flake8-bugbear)
- `C4` — Comprehensions (flake8-comprehensions)

### 9.2 Mypy (Type Checking)

```bash
# Type checking estricto
mypy app/

# Configuración en pyproject.toml
[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### 9.3 Safety (Dependencies)

```bash
# Verificar vulnerabilidades en dependencias
pip install safety
safety check

# En CI
safety check --json --output tests/security/safety_report.json
```

## 10. Gestión de Defectos

### 10.1 Severidad de Defectos

| Severidad | Descripción | SLA de Corrección | Ejemplo |
|-----------|-------------|-------------------|---------|
| **Bloqueante** | Imposibilita uso del sistema | 4 horas | Login no funciona, pérdida de datos |
| **Crítica** | Funcionalidad principal afecta significativamente | 24 horas | Búsqueda no retorna resultados, errores 500 |
| **Alta** | Funcionalidad con workaround disponible | 72 horas | Rate limiting muy agresivo, timeout en casos edge |
| **Media** | Impacto menor en funcionalidad | 1 sprint | Typo en mensaje de error, UI responsive en tablet |
| **Baja** | Mejora o cosmetic issue | Backlog | Color de botón podría ser mejor, mensaje de help |

### 10.2 Workflow de Defectos

```
┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐
│ REPORTADO │ → │ ASIGNADO  │ → │ CORREGIDO │ → │ VERIFICADO│ → │ CERRADO  │
│           │   │           │   │           │   │           │   │           │
│ Defect    │   │ Dev       │   │ PR merged │   │ QA verify │   │ Done      │
│ reported  │   │ assigned  │   │           │   │           │   │           │
└───────────┘   └───────────┘   └───────────┘   └───────────┘   └───────────┘
     │                │                 │                │                │
     ▼                ▼                 ▼                ▼                ▼
  Triage          Working           Fix merged        Test             Closed
  review          on fix            to main           passed           and
                                                                 documented
```

### 10.3 Criterios de Defect Escape Rate

| Métrica | Fórmula | Objetivo |
|---------|---------|----------|
| Defect Escape Rate | Defectos producción / Total defectos | < 5% |
| Defectos por Sprint | Número de defectosreportados | Tendencia decreciente |
| MTTR | Mean Time to Repair | < 24h para crítica |

## 11. Métricas de Calidad

### 11.1 Dashboard de Métricas

| Métrica | Valor Actual | Objetivo | Estado |
|---------|-------------|----------|--------|
| Code Coverage | 78% | 80% | 🟡 Cerca |
| Vulnerabilidades Críticas | 0 | 0 | ✅ Cumplido |
| Code Smells | 4 | < 10 | ✅ Cumplido |
| Deuda Técnica | 3.2% | < 5% | ✅ Cumplido |
| Defect Escape Rate | 2.1% | < 5% | ✅ Cumplido |
| Tests Passing | 100% | 100% | ✅ Cumplido |

### 11.2 Herramientas de Reporte

| Herramienta | Métrica | Ubicación |
|-------------|---------|-----------|
| pytest-cov | Cobertura por archivo | Terminal + HTML report |
| SonarQube | Debt, smells, coverage | Dashboard web |
| GitHub Actions | Test results, lint | PR checks |
| OWASP ZAP | Vulnerabilidades | JSON report |

### 11.3 Reporting Semanal

Cada sprint review incluye:
- Cobertura de código por módulo
- Nuevos code smells detectados
- Defectos escapados a producción
- Análisis de tendencia

---

**Documento controlado** — cualquier cambio debe ser aprobado por el Arquitecto de Software y QA Lead.  
**Archivo base:** `Documentación Inmobiliaria/CALIDAD_PRUEBAS_PLAN.md`
