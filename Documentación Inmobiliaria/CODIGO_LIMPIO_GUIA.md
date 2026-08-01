# Guía de Código Limpio — Inmobiliaria Platform

**Versión:** 1.0  
**Fecha:** Julio 2026  
**Base normativa:** DIAN "Lineamientos de Desarrollo de Software V1.3" — Numeral 9.1, ISO 25010 (Mantenibilidad)  
**Propósito:** Estandarizar las prácticas de desarrollo para garantizar código mantenible y de calidad  

---

## 1. Principios SOLID Aplicados al Proyecto

Los principios SOLID se aplican explícitamente en la arquitectura del proyecto. A continuación, ejemplos concretos del codebase.

### 1.1 Single Responsibility Principle (SRP)

**Definición:** Una clase debe tener una única razón para cambiar.

**Ejemplo correcto en el proyecto:**

```python
# app/core/exceptions.py — solo excepciones de autenticación
class AuthException(HTTPException):
    """Base auth exception — defaults to 401."""
    ...

class InvalidCredentialsError(AuthException):
    """Wrong username or password."""
    ...

# app/core/security.py — solo hashing y JWT
class PolicyViolation:
    """Single responsibility: representa una violación de política."""
    ...
```

**Ejemplo incorrecto (violación):**

```python
# ❌ NO HACER — esta clase mezcla responsabilidades
class UserManager:
    def authenticate(self): ...        # auth
    def send_email(self): ...           # email
    def calculate_matching_score(self): ...  # matching
    def generate_report(self): ...      # reporting
```

### 1.2 Open/Closed Principle (OCP)

**Definición:** Las entidades de software deben ser abiertas para extensión, cerradas para modificación.

**Ejemplo en el proyecto — adapters/ports pattern:**

```python
# app/ports/captcha.py — interfaz (cerrada para modificación)
class CaptchaVerifier(Protocol):
    """Interfaz para verificación de CAPTCHA."""
    async def verify(self, token: str, ip: str) -> bool: ...
    async def get_score(self, token: str) -> float | None: ...

# app/adapters/google_recaptcha.py — extensión sin modificar el código base
class GoogleRecaptchaVerifier:
    """Implementación para Google reCAPTCHA v3."""
    async def verify(self, token: str, ip: str) -> bool:
        ...
```

### 1.3 Liskov Substitution Principle (LSP)

**Definición:** Los objetos de una clase derivada deben poder sustituir objetos de la clase base sin comportamiento alterado.

**Ejemplo en el proyecto:**

```python
# app/domain/models.py — herencia correcta
class User(Base):
    """Usuario base con autenticación."""
    ...

class AgentProfile(Base):
    """Agente inmobiliario — extiende User con campos específicos."""
    user: Mapped[User] = relationship("User", back_populates="agent_profile")
```

### 1.4 Interface Segregation Principle (ISP)

**Definición:** Es mejor muchas interfaces específicas que una interfaz general.

**Ejemplo en el proyecto:**

```python
# app/ports/captcha.py — interfaz pequeña y específica
class CaptchaVerifier(Protocol):
    async def verify(self, token: str, ip: str) -> bool: ...

# app/ports/ — múltiples interfaces pequeñas
class StoragePort(Protocol): ...
class CachePort(Protocol): ...
class DatabasePort(Protocol): ...
```

### 1.5 Dependency Inversion Principle (DIP)

**Definición:** Depender de abstracciones, no de concreciones.

**Ejemplo en el proyecto — Dependency Injection en FastAPI:**

```python
# app/api/v1/deps.py — inyección de dependencias
async def get_current_user(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client),
) -> User:
    """Invierte la dependencia: el endpoint depende de abstracciones."""
    ...

# app/adapters/database.py — implementación concreta
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provee la implementación concreta de la sesión de BD."""
    ...
```

## 2. Clean Architecture / Hexagonal en Inmobiliaria

### 2.1 Estructura de Capas

```
app/
├── api/v1/              # 🎯 ADAPTERS (Driving) — Controllers/Endpoints
│   ├── properties.py     # Endpoints REST para propiedades
│   ├── auth.py          # Endpoints de autenticación
│   ├── matches.py       # Endpoints de matching
│   └── deps.py          # Dependency injection
│
├── core/                # 🎯 APPLICATION LAYER — Casos de uso
│   ├── security.py      # Lógica de autenticación
│   ├── matching.py      # Algoritmo de matching
│   ├── exceptions.py    # Excepciones de dominio
│   └── middleware.py    # Middleware HTTP
│
├── domain/              # 🎯 DOMAIN LAYER — Entidades y lógica de dominio
│   ├── models.py        # Entidades ORM (User, Property, Match...)
│   └── schemas.py       # Esquemas Pydantic (validación)
│
├── ports/               # 🎯 PORTS — Interfaces/abstracciones
│   ├── captcha.py       # Puerto para CAPTCHA
│   └── ...
│
└── adapters/            # 🎯 ADAPTERS (Driven) — Implementaciones
    ├── database.py      # Implementación SQLAlchemy
    ├── redis_client.py  # Implementación Redis
    ├── s3_storage.py    # Implementación MinIO/S3
    └── google_recaptcha.py  # Implementación reCAPTCHA
```

### 2.2 Flujo de Dependencias

```
Request HTTP
    │
    ▼
api/v1/ (Driving Adapter)
    │  ←─── depende de abstracciones (ports)
    ▼
core/ (Application Services)
    │  ←─── depende de domain
    ▼
domain/ (Domain Model) — NO tiene dependencias externas
    │
    ▲
    │  ←─── implementa puertos
    │
adapters/ (Driven Adapters)
    │
    ▼
Infraestructura Externa (PostgreSQL, Redis, MinIO)
```

## 3. Convenciones de Nombres

### 3.1 Regla General

| Tipo | Convención | Ejemplo | Fuente |
|------|-----------|---------|--------|
| Código Python | Inglés | `def authenticate_user()` | — |
| Documentación dominio | Español | "perfil del comprador", "inmueble" | Documentación, comentarios |
| Variables | snake_case | `user_id`, `price_max` | PEP 8 |
| Clases | PascalCase | `UserProfile`, `PropertyMatch` | PEP 8 |
| Constantes | UPPER_SNAKE | `MAX_LOGIN_ATTEMPTS`, `ALGORITHM` | PEP 8 |
| Funciones | snake_case | `hash_password()`, `verify_token()` | PEP 8 |
| Módulos | snake_case | `matching.py`, `security.py` | PEP 8 |
| Archivos de tests | test_*.py | `test_matching.py`, `test_security.py` | pytest |
| Enums | PascalCase + valores UPPER_SNAKE | `PropertyStatus.ACTIVE` | Python enum |

### 3.2 Ejemplos Concretos del Proyecto

```python
# ✅ CORRECTO
from app.core.security import hash_password, verify_password
from app.domain.models import Property, PropertyStatus, PropertyType

MAX_RETRY_ATTEMPTS = 5
ALGORITHM = "HS256"

class UserProfile(Base):
    async def authenticate(self, password: str) -> bool:
        return verify_password(password, self.password_hash)

# ❌ INCORRECTO
from app.Core.Security import HashPassword  # PascalCase en módulos
from app.models import user, prop_status    # nombres ambiguos
MaxRetryAttempts = 5                       # PascalCase para constante
def AuthenticateUser(password):            # PascalCase para función
```

## 4. Type Hints Obligatorios (mypy strict mode)

### 4.1 Configuración

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### 4.2 Reglas

- **Todos** los parámetros de función deben tener type hints
- **Todos** los retornos de función deben tener type hints
- **Usar** `Optional[T]` o `T | None` (no `T = None` sin hint)
- **Usar** `TYPE_CHECKING` para imports circulares

### 4.3 Ejemplos del Proyecto

```python
# ✅ CORRECTO
def validate_password(password: str) -> list[PolicyViolation]:
    ...

async def get_user_by_id(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> User | None:
    ...

def _build_payload(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    roles: list[str],
    jti: str,
    token_type: str,
    expires_delta: timedelta,
) -> dict[str, Any]:
    ...

# ❌ INCORRECTO
def validate_password(password):         # Falta type hints
    return []

async def get_user(user_id):            # Falta tipos
    ...
```

## 5. Reglas de Funciones

### 5.1 Máximo 20 Líneas por Función

```python
# ✅ CORRECTO — función pequeña y focused
def hash_password(password: str) -> str:
    """Hash a password using bcrypt via passlib CryptContext."""
    violations = validate_password(password)
    if violations:
        raise PasswordPolicyError([v.to_dict() for v in violations])
    return pwd_context.hash(password)

# ❌ INCORRECTO — función de 50 líneas haciendo demasiado
async def process_user_registration(request: Request) -> Response:
    # 50 líneas de lógica mezclada
    # validación, parsing, DB ops, email, logging...
```

### 5.2 Un Solo Nivel de Abstracción

```python
# ✅ CORRECTO — cada función tiene un solo nivel
def authenticate_user(username: str, password: str) -> User:
    user = find_user_by_username(username)
    if user is None:
        raise InvalidCredentialsError()
    if not verify_password(password, user.password_hash):
        record_failed_attempt(user)
        raise InvalidCredentialsError()
    return user

# ❌ INCORRECTO — múltiples niveles mezclados
def authenticate_user(username: str, password: str) -> User:
    # Demasiado bajo nivel mezclado con lógica de negocio
    query = f"SELECT * FROM users WHERE username = '{username}'"  # SQL injection!
    cursor.execute(query)
    row = cursor.fetchone()
    if row is None:
        log.warning("user_not_found", username=username)
        return None
    ...
```

### 5.3 Máximo 3 Parámetros

```python
# ✅ CORRECTO — 3 parámetros claros
def create_jwt_payload(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    roles: list[str],
) -> dict[str, Any]:
    ...

# Alternativa: usar un objeto de configuración
class TokenConfig:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    roles: list[str]

def create_jwt_payload(config: TokenConfig) -> dict[str, Any]:
    ...

# ❌ INCORRECTO — 7 parámetros
def create_user(
    username: str,
    email: str,
    password: str,
    tenant_id: uuid.UUID,
    is_active: bool,
    is_locked: bool,
    created_by: uuid.UUID,
) -> User:
    ...
```

## 6. Manejo de Errores

### 6.1 Excepciones Custom del Proyecto

El proyecto define excepciones específicas en `app/core/exceptions.py`:

```python
# ✅ CORRECTO — excepciones específicas y documentadas
class AuthException(HTTPException):
    """Base auth exception — defaults to 401, overridable via status_code."""
    ...

class InvalidCredentialsError(AuthException):
    """Wrong username or password."""
    ...

class AccountLockedError(AuthException):
    """Account locked due to too many failed attempts."""
    ...

# ❌ INCORRECTO — excepciones genéricas o silenciadas
try:
    result = do_something()
except Exception:  # Demasiado amplio
    pass  # Silenciando errores

try:
    result = do_something()
except ValueError:
    pass  # Silenciando errores
```

### 6.2 Reglas de Manejo de Errores

1. **Nunca silenciar excepciones** sin documentación del por qué
2. **Usar excepciones específicas** del dominio (`InvalidCredentialsError`, no `Exception`)
3. **Re-lanzar** excepciones después de logging: `raise`
4. **No usar excepciones para control de flujo** — usar `if/else`
5. **Logging en WARNING o ERROR** para errores que requieren atención

### 6.3 Logging con structlog

```python
import structlog

log = structlog.get_logger()

# ✅ CORRECTO — niveles apropiados
log.debug("user_login_attempt", username=username, ip=ip_address)
log.info("user_logged_in", user_id=str(user.id))
log.warning("invalid_credentials", username=username, attempts=attempts)
log.error("database_connection_failed", error=str(exc), retry=retry_count)

# ❌ INCORRECTO
print("user logged in")  # No usar print
log.info("Processing")   # Mensaje sin contexto
log.critical("Error")    # Sin información de debugging
```

## 7. Comentarios

### 7.1 Regla de Oro: Explicar POR QUÉ, No QUÉ

```python
# ✅ CORRECTO — explica el WHY
# Necesitamos esperar 100ms entre reintentos para evitar
# sobrecargar el servicio externo de reCAPTCHA
await asyncio.sleep(0.1)
await verify_captcha(token)

# Usamos bcrypt en lugar de SHA-256 porque bcrypt es
# intentionally lento (key stretching) para resistir rainbow tables
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ❌ INCORRECTO — dice el QUÉ (el código ya dice eso)
# Iterate through the list
for item in items:
    process(item)

# Get the user
user = get_user_by_id(user_id)
```

### 7.2 Docstrings

```python
def hash_password(password: str) -> str:
    """Hash a password using bcrypt via passlib CryptContext.

    Raises PasswordPolicyError if the password does not meet policy requirements.
    """
    violations = validate_password(password)
    if violations:
        raise PasswordPolicyError([v.to_dict() for v in violations])
    return pwd_context.hash(password)
```

## 8. Refactoring

### 8.1 Cuándo Refactorizar

| Señal | Acción |
|--------|--------|
| Función > 20 líneas | Extraer método |
| Función con > 3 parámetros | Crear objeto de configuración o拆分 |
| Clase > 200 líneas | Extraer clase o módulo |
| Duplicación de código | Extraer a función común |
| Nombre de variable ambiguo | Renombrar |
| Comentario que explica QUÉ | Reescribir código para que se auto-documente |
| Code smell detectado | Boy scout rule: deja el código mejor de lo que lo encontraste |

### 8.2 Técnicas de Refactoring

**Extract Method:**
```python
# Antes
def process_registration(data: dict) -> User:
    # validate email
    if '@' not in data['email']:
        raise ValueError("Invalid email")
    # validate password
    if len(data['password']) < 8:
        raise ValueError("Password too short")
    # create user
    user = User(email=data['email'], password=hash(data['password']))
    # save
    db.save(user)
    return user

# Después
def process_registration(data: dict) -> User:
    _validate_email(data['email'])
    _validate_password(data['password'])
    user = _create_user(data)
    db.save(user)
    return user
```

### 8.3 Boy Scout Rule

> "Dejar el código más limpio de lo que lo encontraste."

- Si modificas una función, deja los type hints correctos
- Si ves un nombre de variable confuso, renómbralo
- Si encuentras código duplicado, extráelo
- Si hay un code smell obvio, arréglalo

## 9. Code Smells a Evitar

### 9.1 Lista de Code Smells

| Code Smell | Descripción | Solución |
|------------|-------------|----------|
| **Long Method** | Función > 20 líneas | Extraer método |
| **Large Class** | Clase > 200 líneas | Extraer clase |
| **Primitive Obsession** | Usar primitivos en lugar de objetos | Crear Value Objects |
| **Feature Envy** | Clase que usa mucho los datos de otra | Mover método a la otra clase |
| **Shotgun Surgery** | Cambio en un lugar requiere cambios en muchos otros | Acoplar información |
| **Dead Code** | Código sin uso | Eliminar |
| **Magic Numbers** | Números sin nombre | Crear constantes |
| **God Class** | Clase que lo sabe todo | Dividir responsabilidades |

### 9.2 Ejemplos del Proyecto

```python
# ✅ Primitive Obsession — EVITADO con tipos específicos
# En app/domain/models.py
class BuyerProfile(Base):
    budget_min: Mapped[float | None]   # ✅ float en lugar de generic
    budget_max: Mapped[float | None]
    preferred_locations: Mapped[dict | None]   # ✅ dict con estructura definida

# ✅ Magic Numbers — EVITADO con constantes
# En app/core/security.py
ALGORITHM = "HS256"  # ✅ Constante en lugar de "HS256" hardcodeado
MAX_LOGIN_ATTEMPTS = 3  # ✅ Constante con nombre descriptivo
```

## 10. Revisiones de Código

### 10.1 Checklist de Code Review

**Antes de aprobar un PR, verificar:**

- [ ] Type hints completos (mypy passing)
- [ ] Sin type: ignore (solo si es absolutamente necesario y documentado)
- [ ] Code coverage no decreased (mantener ≥ 80%)
- [ ] ruff passing (sin advertencias)
- [ ] bandit passing (sin vulnerabilidades)
- [ ] Docstrings para funciones públicas
- [ ] No código comentado sin explicación
- [ ] No hardcoded secrets o credentials
- [ ] Variables con nombres descriptivos
- [ ] Funciones < 20 líneas
- [ ] Parámetros < 4
- [ ] Excepciones específicas (no Exception genérica)
- [ ] Logging apropiado
- [ ] Tests para nueva funcionalidad
- [ ] No decremento en métricas de SonarQube

### 10.2 Pull Request Template

```markdown
## Description
<!-- Describe qué hace este PR y por qué -->

## Related Issue
<!-- Link a la HU o issue: Closes #HU-XXX -->

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
<!-- Cómo se probó el cambio -->
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Manual testing performed

## Checklist
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Screenshots (if applicable)
<!-- Agregar screenshots para cambios de UI -->
```

## 11. Análisis Estático

### 11.1 Herramientas y Configuración

| Herramienta | Propósito | Config |
|-------------|-----------|--------|
| **ruff** | Linting, format | `ruff check app/`, `ruff format app/` |
| **mypy** | Type checking | `mypy app/` (strict mode) |
| **bandit** | Security scanning | `bandit -r app/` |
| **safety** | Dependency vulnerabilities | `safety check` |

### 11.2 Comandos en Makefile

```makefile
# .env que usa el proyecto
lint:
    python -m ruff check app/ --fix

lint-check:
    python -m ruff check app/

format:
    python -m ruff format app/

test-cov:
    python -m pytest tests/ -v --cov=app --cov-report=html
```

### 11.3 Integración CI/CD

```yaml
# .github/workflows/ci.yml
- name: Run Ruff
  run: pip install ruff && ruff check app/

- name: Run Mypy
  run: pip install mypy && mypy app/

- name: Run Bandit
  run: pip install bandit && bandit -r app/

- name: Run Tests with Coverage
  run: pytest tests/ -v --cov=app --cov-fail-under=80
```

## 12. Complejidad Ciclomática

### 12.1 Límite por Función

| Complejidad | Clasificación | Acción |
|-------------|---------------|--------|
| 1-5 | Baja | Aceptable, bien estructurada |
| 6-10 | Media | Considerar refactoring si > 8 |
| 11-15 | Alta | Refactoring necesario |
| 16+ | Muy alta | Priorizar refactoring urgente |

### 12.2 Ejemplo de Complejidad Alta (EVITAR)

```python
# ❌ INCORRECTO — complejidad 12
def process_payment(order: Order) -> PaymentResult:
    if order.total > 0:
        if order.customer.credit_limit >= order.total:
            if order.items:
                if all(item.available for item in order.items):
                    if order.shipping_address:
                        if validate_address(order.shipping_address):
                            if payment_method := get_payment_method(order):
                                result = payment_method.charge(order.total)
                                if result.success:
                                    return PaymentResult.success(result)
                                else:
                                    return PaymentResult.failed(result.error)
                            else:
                                return PaymentResult.failed("No payment method")
                        else:
                            return PaymentResult.failed("Invalid address")
                    else:
                        return PaymentResult.failed("No shipping address")
                else:
                    return PaymentResult.failed("Items unavailable")
            else:
                return PaymentResult.failed("No items")
        else:
            return PaymentResult.failed("Insufficient credit")
    else:
        return PaymentResult.failed("Invalid total")
```

**Refactoring con early returns (complejidad 3):**

```python
# ✅ CORRECTO — complejidad 3
def process_payment(order: Order) -> PaymentResult:
    if order.total <= 0:
        return PaymentResult.failed("Invalid total")
    if order.customer.credit_limit < order.total:
        return PaymentResult.failed("Insufficient credit")
    if not order.items or not all(item.available for item in order.items):
        return PaymentResult.failed("Items unavailable")
    if not order.shipping_address or not validate_address(order.shipping_address):
        return PaymentResult.failed("Invalid address")
    payment_method = get_payment_method(order)
    if not payment_method:
        return PaymentResult.failed("No payment method")
    result = payment_method.charge(order.total)
    if not result.success:
        return PaymentResult.failed(result.error)
    return PaymentResult.success(result)
```

---

**Documento controlado** — cualquier cambio debe ser aprobado por el Arquitecto de Software.  
**Archivo base:** `Documentación Inmobiliaria/CODIGO_LIMPIO_GUIA.md`
