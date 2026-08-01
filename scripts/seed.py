"""
Seed script for Inmobiliaria — populates the database with realistic test data.

Usage:
    cd /home/userwil/Inmobiliaria
    python scripts/seed.py

Requires: PostgreSQL + Redis running (docker compose up -d postgres redis)
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.database import AsyncSessionLocal, engine
from app.domain.models import (
    Base,
    User,
    Role,
    UserRole,
    BuyerProfile,
    SellerProfile,
    AgentProfile,
    Property,
    PropertyPhoto,
    PropertyType,
    PropertyOperation,
    PropertyStatus,
    Project,
    Match,
    Inquiry,
    InquiryStatus,
    ContactPreference,
    Favorite,
    LoginAttempt,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Datos semilla ───────────────────────────────────────────────────────────

COLOMBIAN_CITIES = [
    ("Bogotá", 4.7110, -74.0721),
    ("Medellín", 6.2476, -75.5658),
    ("Cali", 3.4516, -76.5320),
    ("Barranquilla", 10.9639, -74.7964),
    ("Cartagena", 10.3997, -75.5144),
    ("Bucaramanga", 7.1193, -73.1227),
    ("Pereira", 4.8087, -75.6906),
    ("Santa Marta", 11.2408, -74.1990),
]

NEIGHBORHOODS = {
    "Bogotá": ["Chapinero", "Usaquén", "Fontibón", "Teusaquillo", "Suba", "Kennedy", "Engativá", "Bosa"],
    "Medellín": ["El Poblado", "Laureles", "Envigado", "Sabaneta", "Robledo", "Belén", "Guayabal"],
    "Cali": ["San Antonio", "Granada", "Ciudad Jardín", "Pance", "El Peñón", "Menga"],
    "Barranquilla": ["Alto Prado", "Riomar", "Villa Country", "Buenavista", "Miramar"],
    "Cartagena": ["Bocagrande", "Castillogrande", "Manga", "Crespo", "El Laguito"],
    "Bucaramanga": ["Cabecera", "El Jardín", "Real de Minas", "Cañaveral", "Terrazas"],
    "Pereira": ["Circunvalar", "Pinares", "Álamos", "Cuba", "Boston"],
    "Santa Marta": ["El Rodadero", "Pozos Colorados", "Bello Horizonte", "Centro Histórico"],
}

PROPERTY_FEATURES = [
    "piscina", "parqueadero", "gimnasio", "salón social", "zona BBQ",
    "jardín", "terraza", "balcón", "depósito", "cuarto de servicio",
    "ascensor", "vigilancia 24h", "conjunto cerrado", "ciclovía",
    "parque infantil", "zona de mascotas", "sauna", "turco", "jacuzzi",
    "chimenea", "estudio", "walking closet", "cocina integral", "gas natural",
]

PROPERTY_TITLES = {
    PropertyType.apartment: [
        "Apartamento moderno en {neighborhood}",
        "Apartaestudio luminoso {neighborhood}",
        "Hermoso apartamento familiar {neighborhood}",
        "Penthouse de lujo en {neighborhood}",
        "Apartamento con vista {neighborhood}",
    ],
    PropertyType.house: [
        "Casa amplia en {neighborhood}",
        "Casa familiar {neighborhood}",
        "Casa de dos pisos {neighborhood}",
        "Casa campestre {neighborhood}",
        "Casa esquinera {neighborhood}",
    ],
    PropertyType.office: [
        "Oficina ejecutiva {neighborhood}",
        "Consultorio médico {neighborhood}",
        "Oficina en centro empresarial {neighborhood}",
    ],
    PropertyType.commercial: [
        "Local comercial {neighborhood}",
        "Bodega industrial {neighborhood}",
        "Local en centro comercial {neighborhood}",
    ],
    PropertyType.land: [
        "Lote residencial {neighborhood}",
        "Terreno comercial {neighborhood}",
        "Lote campestre {neighborhood}",
    ],
}

FIRST_NAMES = [
    "Carlos", "María", "Juan", "Ana", "Pedro", "Laura", "Diego", "Sofía",
    "Andrés", "Valentina", "Felipe", "Isabella", "Santiago", "Camila",
    "Nicolás", "Daniela", "Mateo", "Gabriela", "Samuel", "Luciana",
]

LAST_NAMES = [
    "García", "Rodríguez", "Martínez", "López", "Hernández", "González",
    "Pérez", "Sánchez", "Ramírez", "Torres", "Flores", "Rivera", "Gómez",
    "Díaz", "Morales", "Ortiz", "Ruiz", "Jiménez", "Rojas", "Vargas",
]


def random_features() -> list[str]:
    """Pick 3-8 random features."""
    n = random.randint(3, 8)
    return random.sample(PROPERTY_FEATURES, n)


def random_location(city: str) -> tuple[float, float]:
    """Return (lat, lon) with small random offset from city center."""
    base = next((c for c in COLOMBIAN_CITIES if c[0] == city), COLOMBIAN_CITIES[0])
    return (
        base[1] + random.uniform(-0.05, 0.05),
        base[2] + random.uniform(-0.05, 0.05),
    )


async def seed(session: AsyncSession):
    """Main seed function."""
    print("🌱 Sembrando datos de prueba para Inmobiliaria...\n")

    # ── 1. Roles ──────────────────────────────────────────────────────────────
    roles = {}
    for role_name in ["super_admin", "admin", "agent", "seller", "buyer"]:
        role = Role(name=role_name)
        session.add(role)
        roles[role_name] = role
    await session.flush()
    print(f"  ✅ {len(roles)} roles creados")

    # ── 2. Admin ──────────────────────────────────────────────────────────────
    admin = User(
        username="admin",
        email="admin@inmobiliaria.com",
        password_hash=pwd_context.hash("Admin123!"),
        is_active=True,
        consent_given_at=datetime.now(timezone.utc),
    )
    session.add(admin)
    session.add(UserRole(user_id=admin.id, role_id=roles["super_admin"].id))
    await session.flush()
    print(f"  ✅ Admin: admin@inmobiliaria.com / Admin123!")

    # ── 3. Agentes ────────────────────────────────────────────────────────────
    agents = []
    agencies = ["Inmobiliaria Prime", "Hogar Colombia", "Fincaraíz Pro"]
    for i in range(3):
        user = User(
            username=f"agent{i+1}",
            email=f"agent{i+1}@inmobiliaria.com",
            password_hash=pwd_context.hash("Agent123!"),
            is_active=True,
            consent_given_at=datetime.now(timezone.utc),
        )
        session.add(user)
        session.add(UserRole(user_id=user.id, role_id=roles["agent"].id))

        profile = AgentProfile(
            user_id=user.id,
            license_number=f"LIC-{1000+i:04d}",
            agency_name=agencies[i],
        )
        session.add(profile)
        agents.append(user)
    await session.flush()
    print(f"  ✅ {len(agents)} agentes creados (agent1/agent2/agent3 / Agent123!)")

    # ── 4. Vendedores ─────────────────────────────────────────────────────────
    sellers = []
    for i in range(5):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        user = User(
            username=f"seller{i+1}",
            email=f"seller{i+1}@inmobiliaria.com",
            password_hash=pwd_context.hash("Seller123!"),
            is_active=True,
            consent_given_at=datetime.now(timezone.utc),
        )
        session.add(user)
        session.add(UserRole(user_id=user.id, role_id=roles["seller"].id))

        profile = SellerProfile(
            user_id=user.id,
            phone=f"300{random.randint(1000000, 9999999)}",
            company_name=f"Inversiones {last}" if random.random() > 0.5 else None,
        )
        session.add(profile)
        sellers.append(user)
    await session.flush()
    print(f"  ✅ {len(sellers)} vendedores creados (seller1-seller5 / Seller123!)")

    # ── 5. Compradores ────────────────────────────────────────────────────────
    buyers = []
    for i in range(20):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        user = User(
            username=f"buyer{i+1}",
            email=f"buyer{i+1}@inmobiliaria.com",
            password_hash=pwd_context.hash("Buyer123!"),
            is_active=True,
            consent_given_at=datetime.now(timezone.utc),
        )
        session.add(user)
        session.add(UserRole(user_id=user.id, role_id=roles["buyer"].id))

        city = random.choice(COLOMBIAN_CITIES)[0]
        profile = BuyerProfile(
            user_id=user.id,
            budget_min=random.choice([80_000_000, 150_000_000, 250_000_000, 400_000_000, 600_000_000]),
            budget_max=random.choice([200_000_000, 350_000_000, 500_000_000, 800_000_000, 1_200_000_000]),
            preferred_locations=[{"city": city, "lat": random_location(city)[0], "lon": random_location(city)[1], "radius_km": 10}],
            rooms_min=random.randint(1, 3),
            bathrooms_min=random.randint(1, 2),
            area_min=random.choice([40, 60, 80]),
            area_max=random.choice([100, 150, 200, 300]),
            preferred_features=random_features(),
            preferred_property_types=[random.choice([t.value for t in PropertyType])],
        )
        session.add(profile)
        buyers.append(user)
    await session.flush()
    print(f"  ✅ {len(buyers)} compradores creados (buyer1-buyer20 / Buyer123!)")

    # ── 6. Propiedades ────────────────────────────────────────────────────────
    properties = []
    photo_id = 0
    for _ in range(50):
        city_name, city_lat, city_lon = random.choice(COLOMBIAN_CITIES)
        neighborhood = random.choice(NEIGHBORHOODS[city_name])
        prop_type = random.choice(list(PropertyType))
        operation = random.choice(list(PropertyOperation))

        # Price ranges by type
        price_ranges = {
            PropertyType.apartment: (120_000_000, 800_000_000),
            PropertyType.house: (200_000_000, 2_500_000_000),
            PropertyType.office: (80_000_000, 500_000_000),
            PropertyType.commercial: (150_000_000, 1_200_000_000),
            PropertyType.land: (50_000_000, 3_000_000_000),
        }
        price_min, price_max = price_ranges[prop_type]
        price = round(random.randint(price_min, price_max) / 1_000_000) * 1_000_000

        status = random.choice([PropertyStatus.published, PropertyStatus.published, PropertyStatus.published, PropertyStatus.reserved])

        lat, lon = random_location(city_name)
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point
        location = from_shape(Point(lon, lat), srid=4326)

        title_template = random.choice(PROPERTY_TITLES.get(prop_type, ["Propiedad en {neighborhood}"]))
        title = title_template.format(neighborhood=neighborhood)

        owner = random.choice(sellers + agents)
        agent = random.choice(agents) if random.random() > 0.5 else None

        prop = Property(
            type=prop_type,
            operation=operation,
            status=status,
            price=price,
            area_m2=random.randint(40, 500),
            location=location,
            rooms=random.randint(1, 5),
            bathrooms=random.randint(1, 4),
            features=random_features(),
            title=title,
            description=f"Hermosa propiedad en {neighborhood}, {city_name}. "
                        f"Cuenta con {random.randint(1, 4)} habitaciones y excelente ubicación. "
                        f"Ideal para {"familia" if random.random() > 0.5 else "inversión"}.",
            is_active=True,
            owner_id=owner.id,
            agent_id=agent.id if agent else None,
            published_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60)),
        )
        session.add(prop)

        # 1-3 photos per property
        for j in range(random.randint(1, 3)):
            photo_id += 1
            photo = PropertyPhoto(
                property_id=prop.id,
                url=f"https://picsum.photos/seed/{prop.id}_{j}/800/600",
                s3_key=f"properties/{prop.id}/photo_{j}.jpg",
                order=j,
            )
            session.add(photo)

        properties.append(prop)
    await session.flush()
    print(f"  ✅ {len(properties)} propiedades creadas (con {photo_id} fotos)")

    # ── 7. Matches ─────────────────────────────────────────────────────────────
    matches_created = 0
    for buyer in random.sample(buyers, 10):
        for prop in random.sample(properties, random.randint(3, 8)):
            score = round(random.uniform(35, 98), 2)
            match = Match(
                buyer_id=buyer.id,
                property_id=prop.id,
                score=score,
                score_breakdown={
                    "price": round(random.uniform(20, 30), 2),
                    "location": round(random.uniform(15, 25), 2),
                    "features": round(random.uniform(10, 25), 2),
                    "area": round(random.uniform(10, 20), 2),
                },
                computed_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 72)),
            )
            session.add(match)
            matches_created += 1
    await session.flush()
    print(f"  ✅ {matches_created} matches generados")

    # ── 8. Consultas / Inquiries ──────────────────────────────────────────────
    inquiries_created = 0
    for _ in range(30):
        buyer = random.choice(buyers)
        prop = random.choice(properties)
        inquiry = Inquiry(
            from_user_id=buyer.id,
            to_user_id=prop.owner_id,
            property_id=prop.id,
            message=random.choice([
                "Me interesa esta propiedad, ¿está disponible?",
                "Hola, quisiera agendar una visita.",
                "¿Cuál es el precio final? ¿Hay espacio para negociar?",
                "¿Podrían enviarme más fotos?",
                "Estoy interesado, ¿aceptan crédito hipotecario?",
            ]),
            contact_preference=random.choice([ContactPreference.email, ContactPreference.phone, ContactPreference.both]),
            status=random.choice([InquiryStatus.pending, InquiryStatus.pending, InquiryStatus.responded]),
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 10)),
        )
        if inquiry.status == InquiryStatus.responded:
            inquiry.response_message = "Gracias por tu interés. La propiedad está disponible. ¿Qué día te queda bien para una visita?"
            inquiry.updated_at = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48))
        session.add(inquiry)
        inquiries_created += 1
    await session.flush()
    print(f"  ✅ {inquiries_created} consultas creadas")

    # ── 9. Favoritos ──────────────────────────────────────────────────────────
    favs = set()
    for _ in range(40):
        buyer = random.choice(buyers)
        prop = random.choice(properties)
        favs.add((buyer.id, prop.id))
    for user_id, prop_id in favs:
        session.add(Favorite(user_id=user_id, property_id=prop_id))
    print(f"  ✅ {len(favs)} favoritos creados")

    await session.commit()
    print(f"\n🎉 Seed completo. Datos listos para probar.")


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await seed(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
