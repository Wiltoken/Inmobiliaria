# Análisis de Referencia — 10 Sitios Inmobiliarios Más Visitados

**Objetivo**: Identificar mejores prácticas de UX, diseño, funcionalidades y oportunidades de mejora para Inmobiliaria Platform.
**Fecha**: Agosto 2026
**Mercado objetivo**: Colombia (alineado con competidores locales Fincaraíz y Metrocuadrado)

---

## 1. Plataformas Analizadas

| # | Plataforma | Visitantes/mes | Enfoque | Modelo |
|---|-----------|----------------|---------|--------|
| 1 | Zillow | 75.8M | EE.UU. — búsqueda + valoración | Marketplace + datos |
| 2 | Realtor.com | 31M | EE.UU. — MLS oficial | Conexión MLS |
| 3 | Redfin | 9.8M | EE.UU. — technology-powered brokerage | Corretaje tech |
| 4 | Trulia | 7.2M | EE.UU. — neighborhood insights | Datos de barrio |
| 5 | Casas.com | 6.5M | España/Latam — búsqueda tradicional | Portal de listados |
| 6 | Remax.com | 1.9M | Global — franchise brokerage | Red de agentes |
| 7 | Movoto | 1.7M | EE.UU. — lead generation | Captación de leads |
| 8 | Century21 | 1.5M | Global — franchise brokerage | Red de agentes |
| 9 | ColdwellBanker | 1M | Global — luxury brokerage | Agentes premium |
| 10 | Brújula.com | 935K | Latam — búsqueda tradicional | Portal de listados |

**Referencias locales (Colombia)**:
- **Fincaraiz.com.co** — portal #1 en Colombia, parte de Grupo Classifieds
- **Metrocuadrado.com** — portal competitivo con herramientas financieras

---

## 2. Análisis por Dimensión de Producto

### 2.1 Búsqueda y Descubrimiento

#### Patrón dominante: Map-first search
Zillow, Redfin y Realtor priorizan el mapa como superficie principal de búsqueda. El usuario NO llena formularios — navega el mapa y los filtros se aplican en tiempo real.

**Elementos clave observados**:
- **Mapa como canvas principal** (Zillow, Redfin, Metrocuadrado): el mapa ocupa 60-70% del viewport, los resultados en panel lateral
- **Draw-your-search** (Zillow, Redfin): el usuario dibuja un polígono en el mapa para definir el área de búsqueda — más preciso que "radio en km"
- **Filtros en tiempo real**: sin botón "Buscar" — cada cambio de filtro actualiza resultados instantáneamente
- **Búsqueda por código** (Fincaraiz): cada propiedad tiene un código único, búsqueda directa con un solo campo
- **Autocompletado predictivo**: direcciones, barrios, ciudades, códigos postales

#### Lo que Inmobiliaria YA tiene
- Búsqueda geoespacial con PostGIS + ST_DWithin ✅
- Filtros por tipo, precio, radio, habitaciones, features ✅
- Búsqueda textual con pg_trgm ✅

#### Oportunidades de mejora
| Prioridad | Funcionalidad | Valor |
|-----------|--------------|-------|
| 🔴 Alta | Mapa interactivo en búsqueda (no solo texto) | La navegación visual es el estándar |
| 🔴 Alta | Draw-your-search en mapa | Diferencial — ningún colombiano lo tiene |
| 🟡 Media | Autocompletado de ubicaciones | Reduce fricción de búsqueda significativamente |
| 🟡 Media | Filtros instantáneos sin recarga | Percepción de velocidad y fluidez |

### 2.2 Página de Detalle de Propiedad

#### Patrón dominante: Data-rich, visual-first
La página de detalle es la superficie más crítica — donde el usuario decide contactar.

**Elementos clave observados**:
- **Galería de fotos full-width** con zoom, swipe y tour virtual 3D (Zillow, Redfin)
- **Estimación de precio** con nivel de confianza + histórico (Zestimate, Redfin Estimate)
- **Score de caminabilidad / transporte** (Walk Score, Transit Score, Bike Score en Redfin)
- **Datos del vecindario**: escuelas cercanas con ratings, niveles de ruido, crimen, amenidades (Trulia)
- **Historial de precio**: cambios de precio, días en mercado (Zillow, Redfin)
- **Calculadora de hipoteca** integrada en la misma página (Zillow, Metrocuadrado)
- **Botón de contacto prominente** sticky al hacer scroll, con opciones: llamar, email, chat
- **Recorrido virtual 3D / Matterport** (Zillow, Redfin, Realtor)
- **Tour virtual autoguiado vs agendado** (Redfin programa visitas directamente)

#### Lo que Inmobiliaria YA tiene
- Galería de fotos con carga lazy ✅
- Score de matching con breakdown por factor ✅
- Datos de ubicación y características ✅
- Formulario de contacto ✅

#### Oportunidades de mejora
| Prioridad | Funcionalidad | Valor |
|-----------|--------------|-------|
| 🔴 Alta | Score de matching visible en listado (no solo en detalle) | Diferencial competitivo fuerte |
| 🟡 Media | Calculadora de crédito hipotecario integrada | Reduce fricción en decisión de compra |
| 🟡 Media | Historial de precio (si la propiedad cambió de valor) | Transparencia = confianza |
| 🟢 Baja | Recorrido virtual 3D | Alto costo de producción, bajo retorno inmediato |
| 🟢 Baja | Datos del vecindario (escuelas, transporte, comercios) | Requiere integraciones externas |

### 2.3 Perfiles de Usuario y Personalización

#### Patrón dominante: Saved searches + alertas
La personalización no es solo "guardar favoritos" — es un sistema de alertas proactivo.

**Elementos clave observados**:
- **Saved searches con alertas por email/push** (Zillow, Redfin): el usuario guarda una búsqueda con filtros y recibe notificaciones cuando aparecen nuevas propiedades
- **Alertas de cambio de precio** en propiedades guardadas (Redfin, Fincaraiz app)
- **Perfil de preferred lender** (Zillow): integración con entidades financieras
- **Historial de propiedades vistas** (Zillow, Redfin): "Recently viewed" para retomar búsqueda
- **Owner dashboard** con analytics de visitas a tu propiedad publicada (Zillow)
- **Comparación lado a lado** de propiedades guardadas

#### Lo que Inmobiliaria YA tiene
- BuyerProfile con preferencias, presupuesto, ubicaciones ✅
- Matching engine con score ✅
- Favorites ✅
- Role-based dashboards ✅

#### Oportunidades de mejora
| Prioridad | Funcionalidad | Valor |
|-----------|--------------|-------|
| 🔴 Alta | Alertas de nuevas propiedades que matchean preferencias | Matching engine YA calcula scores — solo falta la notificación |
| 🟡 Media | Alertas de cambio de precio en favoritos | Fidelización y retorno a la plataforma |
| 🟡 Media | Historial de propiedades vistas | Experiencia de usuario fluida entre sesiones |
| 🟢 Baja | Comparación lado a lado de propiedades | Nice-to-have, no bloquea conversión |

### 2.4 Panel de Agentes Inmobiliarios

#### Patrón dominante: Agent tools + lead management
Los agentes son el motor económico de estas plataformas. Su panel no es solo estadísticas.

**Elementos clave observados**:
- **CRM integrado**: gestión de leads, pipeline de ventas, seguimiento de clientes (Zillow Premier Agent)
- **My Listings** con analytics: vistas, saves, inquiries por propiedad
- **Agent profile público** con foto, reviews, especialidad, listings activos (Redfin, Realtor)
- **Tour scheduling**: el comprador agenda visita directamente desde el listing
- **Comparables (comps)**: herramienta para que el agente vea propiedades similares vendidas recientemente
- **Performance dashboard**: métricas de negocio (leads/mes, tasa de conversión, tiempo de respuesta)

#### Lo que Inmobiliaria YA tiene
- Agent dashboard con stats, listings, clientes, matches ✅
- AgentProfile con licencia ✅

#### Oportunidades de mejora
| Prioridad | Funcionalidad | Valor |
|-----------|--------------|-------|
| 🔴 Alta | Agent profile público con foto, bio y listings | Crítico para generar confianza comprador-agente |
| 🟡 Media | CRM ligero: pipeline de leads (nuevo → contactado → visita → cerrado) | Convierte el dashboard en herramienta de trabajo |
| 🟡 Media | Analytics por propiedad: vistas, saves, inquiries | Datos que el agente necesita para asesorar al vendedor |
| 🟢 Baja | Tour scheduling integrado | Requiere integración de calendario |

### 2.5 Publicación de Propiedades

#### Patrón dominante: Wizard guiado + smart defaults
Publicar una propiedad debe ser trivial para maximizar inventario.

**Elementos clave observados**:
- **Wizard paso a paso** con indicador de progreso (no un formulario monolítico)
- **Autocompletado de dirección** con geocodificación automática
- **Sugerencia de precio** basado en comparables del mercado (Zestimate para vendedores)
- **Photo quality checker**: feedback automático sobre calidad de fotos (Zillow)
- **Vista previa en tiempo real** de cómo se verá el listing
- **Publicación desde app móvil** con cámara integrada
- **Campos condicionales**: solo mostrar tipo de arriendo si es "rent", solo VIS si aplica

#### Lo que Inmobiliaria YA tiene
- Property CRUD con estados (draft → published → sold) ✅
- Photo upload con S3/MinIO ✅
- Geospatial location ✅

#### Oportunidades de mejora
| Prioridad | Funcionalidad | Valor |
|-----------|--------------|-------|
| 🟡 Media | Wizard de publicación guiado con pasos | Mejora conversión de vendedores que publican |
| 🟡 Media | Sugerencia de precio por comparables en la zona | Diferencial — ningún portal colombiano lo ofrece bien |
| 🟡 Media | Vista previa en tiempo real del listing | Reduce publicaciones con errores |
| 🟢 Baja | Publicación desde cámara móvil | Requiere app nativa |

### 2.6 Mapa y Geovisualización

#### Patrón dominante: El mapa ES la interfaz
El mapa no es un widget — es la superficie principal de interacción.

**Elementos clave observados**:
- **Clustering de pins** con contador al hacer zoom (Zillow, Redfin, Metrocuadrado)
- **Heatmap de precios**: visualización de zonas caras/baratas (Zillow, Trulia)
- **Pins con precio** en el marcador mismo (sin hacer click)
- **Transiciones animadas** al mover/zoom del mapa
- **School districts overlay**, flood zones, commute time radius (Trulia, Redfin)
- **Street View integrado** para "caminar" el barrio

#### Lo que Inmobiliaria YA tiene
- PostGIS con ubicación geoespacial ✅
- Búsqueda por radio con ST_DWithin ✅

#### Oportunidades de mejora
| Prioridad | Funcionalidad | Valor |
|-----------|--------------|-------|
| 🔴 Alta | Mapa interactivo de búsqueda con clustering | Estándar de industria — esperado por el usuario |
| 🟡 Media | Pins con precio visible sin click | Reduce clicks para explorar, mejora velocidad de decisión |
| 🟡 Media | Heatmap de precios por zona | Herramienta de análisis tanto para compradores como agentes |
| 🟢 Baja | Street View / Google Maps embed | Dependencia externa, baja diferenciación |

### 2.7 Mobile Experience

#### Patrón dominante: Progressive Web App o nativa
El tráfico mobile en bienes raíces supera el 60%. No tener mobile-first es perder la mitad del mercado.

**Elementos clave observados**:
- **App nativa** con notificaciones push (Zillow, Redfin, Fincaraiz)
- **PWA con soporte offline** para guardar búsquedas sin conexión (Redfin)
- **Búsqueda por voz** en app
- **Realidad aumentada**: apuntar cámara a un edificio y ver si está en venta (Zillow AR)
- **Bottom navigation** con acciones principales (Fincaraiz app)
- **Share sheet nativo** para compartir propiedad por WhatsApp

#### Lo que Inmobiliaria YA tiene
- PWA con manifest y service worker ✅
- Bottom navigation mobile ✅
- Diseño responsive ✅

#### Oportunidades de mejora
| Prioridad | Funcionalidad | Valor |
|-----------|--------------|-------|
| 🟡 Media | Notificaciones push para alertas de matching | Diferencial en mobile |
| 🟡 Media | Soporte offline para propiedades guardadas | Útil en Colombia donde conectividad es variable |
| 🟢 Baja | Compartir propiedad por WhatsApp con preview rico | Bajo esfuerzo, alto uso en LATAM |

### 2.8 Confianza y Transparencia

#### Patrón dominante: Datos abiertos generan confianza
En bienes raíces la confianza es el principal factor de conversión.

**Elementos clave observados**:
- **Fotos verificadas** con badge de "verified" (Zillow, Realtor)
- **Reviews de agentes** con rating (Redfin, Zillow)
- **Precio estimado vs precio listado** con explicación de diferencia
- **Días en mercado** visibles (urgencia de venta)
- **Historial de transacciones** del agente (cuántas propiedades vendió)
- **Sello de seguridad / compliance** visible (Ley 1581 en Colombia)

#### Lo que Inmobiliaria YA tiene
- RBAC con roles ✅
- Audit logging ✅
- Compliance framework documentado ✅

#### Oportunidades de mejora
| Prioridad | Funcionalidad | Valor |
|-----------|--------------|-------|
| 🟡 Media | Badge de propiedad verificada | Reduce riesgo percibido de estafas |
| 🟡 Media | Días en mercado visibles en listing | Transparencia que genera urgencia |
| 🟢 Baja | Ratings y reviews de agentes | Requiere volumen de transacciones |

### 2.9 Herramientas Financieras Integradas

#### Patrón dominante: La decisión de compra incluye el financiamiento
Separar "buscar" de "financiar" es perder al usuario en el medio.

**Elementos clave observados**:
- **Calculadora de hipoteca** con tasa de interés local, cuota mensual, down payment (Zillow, Metrocuadrado)
- **Pre-calificación crediticia** conectada con entidades financieras (Zillow Home Loans, Redfin)
- **Simulador de crédito** hipotecario (Metrocuadrado)
- **Compra de cartera** (Metrocuadrado)
- **VIS calculator**: ¿aplicas para subsidio de vivienda? (Fincaraiz)

#### Lo que Inmobiliaria YA tiene
- No tiene herramientas financieras ❌

#### Oportunidades de mejora
| Prioridad | Funcionalidad | Valor |
|-----------|--------------|-------|
| 🔴 Alta | Calculadora de cuota mensual según precio y tasa | Cierra el ciclo "buscar → poder pagar" |
| 🟡 Media | Simulador de crédito con datos de bancos colombianos | Diferencial fuerte — Metrocuadrado lo tiene pero es básico |
| 🟢 Baja | Verificador de elegibilidad VIS | Nicho importante en Colombia |

---

## 3. Matriz de Prioridades para Inmobiliaria

### 🔴 Críticas (alto impacto, alineadas con lo que ya tenés)

| # | Funcionalidad | Por qué ahora | Esfuerzo estimado |
|---|--------------|---------------|-------------------|
| 1 | **Mapa interactivo en búsqueda** | Estándar de industria. Tu PostGIS YA está listo | Medio |
| 2 | **Alertas de matching por email/push** | El matching engine YA calcula scores — solo falta notificar | Bajo |
| 3 | **Calculadora de cuota hipotecaria** | Cierra el ciclo de decisión. Sin esto, el usuario se va a otro lado | Bajo |
| 4 | **Agent profile público** | Crítico para confianza comprador-agente | Bajo-Medio |

### 🟡 Estratégicas (alto impacto, requiere más inversión)

| # | Funcionalidad | Por qué no ahora | Esfuerzo estimado |
|---|--------------|------------------|-------------------|
| 5 | Draw-your-search en mapa | Diferencial fuerte, pero requiere mapa funcional primero | Medio |
| 6 | CRM ligero para agentes | Convierte el dashboard en herramienta de trabajo real | Alto |
| 7 | Sugerencia de precio por comparables | Diferencial — pero necesita datos históricos de transacciones | Alto |
| 8 | Historial de propiedades vistas | Mejora UX entre sesiones | Bajo |

### 🟢 Nice-to-have (menor impacto inmediato)

| # | Funcionalidad | Nota |
|---|--------------|------|
| 9 | Comparación lado a lado | Bajo retorno inmediato |
| 10 | Recorrido virtual 3D | Alto costo de producción |
| 11 | Datos de vecindario | Requiere APIs externas |
| 12 | Realidad aumentada | Experimental, no probado en Colombia |
| 13 | Búsqueda por voz | Nicho, baja adopción |

---

## 4. Lo que NADIE en Colombia está haciendo bien (ventaja competitiva)

Estas son las oportunidades donde Inmobiliaria puede diferenciarse:

### 4.1 Matching personalizado con scoring transparente ⭐⭐⭐
Ningún portal colombiano hace matching real. Fincaraiz y Metrocuadrado son catálogos con búsqueda. Inmobiliaria YA tiene un motor de scoring ponderado con breakdown por factor. Esto es tu principal diferencial — **hacelo visible**, no lo escondas en segundo plano.

**Idea**: Mostrar "85% match" en cada propiedad del listado, con tooltip que explique POR QUÉ (precio, ubicación, features). Como el Zestimate pero para afinidad, no para precio.

### 4.2 Onboarding guiado de preferencias ⭐⭐⭐
Zillow y Redfin infieren preferencias de tu comportamiento. Inmobiliaria puede preguntarlas explícitamente en un onboarding de 3 pasos y devolver matches inmediatos en la primera sesión. Esto es mágico para el usuario nuevo.

### 4.3 Dashboard multi-rol real ⭐⭐
Los portales colombianos tratan a comprador, vendedor y agente como tres experiencias completamente separadas. Inmobiliaria puede unificarlas con cambio de rol fluido y datos compartidos (ej: un usuario puede ser comprador Y vendedor).

### 4.4 Agentes como curadores, no como intermediarios ⭐⭐
En el modelo tradicional, el agente publica y espera. En Inmobiliaria, el agente puede buscar propiedades para sus clientes usando los mismos filtros + matching, y compartir listas curadas directamente.

---

## 5. Recomendación de Hoja de Ruta

### Fase 1: Experiencia de búsqueda (próximo sprint)
1. Mapa interactivo en página de búsqueda
2. Score de matching visible en PropertyCard
3. Alertas de nuevas propiedades que matchean preferencias

### Fase 2: Conversión (siguiente sprint)
4. Calculadora de cuota hipotecaria integrada
5. Agent profile público con foto, bio y listings
6. Historial de propiedades vistas

### Fase 3: Herramientas de agente (mediano plazo)
7. CRM ligero con pipeline de leads
8. Analytics por propiedad (vistas, saves, inquiries)
9. Sugerencia de precio por comparables

---

## 6. Conclusión

Inmobiliaria tiene una base técnica sólida (PostGIS, matching engine, hexagonal architecture, CI/CD, tests) que la mayoría de portales no tienen. Lo que falta no es potencia — es **superficie**: hacer visible y accesible lo que ya existe, y agregar las 3-4 funcionalidades que el mercado colombiano espera pero no encuentra.

El diferencial estratégico es el **matching personalizado transparente**. Ningún competidor lo ofrece. Si la primera experiencia de un usuario en Inmobiliaria es "respondé 5 preguntas y te mostramos propiedades que realmente te sirven, con explicación de por qué", el producto se vende solo.
