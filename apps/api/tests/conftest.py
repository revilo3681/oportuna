from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from oportuna.db.base import Base, get_db, make_engine
from oportuna.db.models import Opportunity, OpportunitySource, Profile, Source, User
from oportuna.main import app
from oportuna.security import hash_password

UTC = UTC


@pytest.fixture()
def engine(tmp_path):
    url = f"sqlite:///{tmp_path / 'oportuna-test.db'}"
    engine = make_engine(url)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@pytest.fixture()
def session(session_factory) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(session_factory) -> Generator[TestClient, None, None]:
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_user(
    session: Session,
    *,
    email: str = "person@example.com",
    password: str = "correct-horse-battery",
    role: str = "user",
) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name="Persona de prueba",
        role=role,
    )
    session.add(user)
    session.flush()
    session.add(Profile(user_id=user.id))
    session.commit()
    return user


def create_source(session: Session, slug: str = "test-source") -> Source:
    source = Source(
        slug=slug,
        name="Fuente de prueba",
        kind="ics",
        homepage_url=f"https://{slug}.example.edu/",
        endpoint=f"https://{slug}.example.edu/calendar.ics",
        region="global",
        languages=["en"],
        authority=80,
        config={},
        access_notes="Prueba",
    )
    session.add(source)
    session.commit()
    return source


def create_opportunity(
    session: Session,
    *,
    slug: str = "global-ai-hackathon-2026",
    title: str = "Global AI Hackathon 2026",
    category: str = "hackathons",
    tags: list[str] | None = None,
    published: bool = True,
    lifecycle: str = "open",
    confidence: float = 0.9,
    verification_state: str = "verified",
    review_state: str = "published",
    deadline_days: int | None = 10,
    country: str | None = "PE",
    modality: str = "online",
    eligibility: dict | None = None,
    organizer: str = "OpenAI Community",
    cost_type: str = "free",
    **overrides,
) -> Opportunity:
    now = datetime.now(UTC)
    tags = tags or ["ai"]
    source = session.query(Source).first() or create_source(session)
    opportunity = Opportunity(
        slug=slug,
        title=title,
        summary="Un hackathon para construir con IA.",
        description="Descripción de prueba.",
        category=category,
        subcategory="hackathon",
        tech_tags=tags,
        tech_tags_text="|" + "|".join(tags) + "|",
        modality=modality,
        country=country,
        city=None,
        language="en",
        organizer=organizer,
        official_url=f"https://{slug}.example.com/",
        canonical_url=f"https://{slug}.example.com/",
        event_start=now + timedelta(days=12),
        event_end=now + timedelta(days=14),
        registration_deadline=now + timedelta(days=deadline_days) if deadline_days else None,
        duration_minutes=2880,
        cost_type=cost_type,
        prizes=[{"type": "cash", "label": "Premios en efectivo"}],
        eligibility=eligibility or {},
        lifecycle=lifecycle,
        registration_state="open" if deadline_days else "unknown",
        verification_state=verification_state,
        confidence_score=confidence,
        confidence_reasons=[{"code": "authority", "label": "Fuente oficial", "impact": "positive", "weight": 0.2}],
        review_state=review_state,
        published=published,
        quality_score=confidence * 100,
        search_text=f"{title} ia hackathon online peru",
        last_checked_at=now,
        last_verified_at=now,
        **overrides,
    )
    session.add(opportunity)
    session.flush()
    session.add(
        OpportunitySource(
            opportunity_id=opportunity.id,
            source_id=source.id,
            source_url=opportunity.official_url,
            external_id=slug,
            authority=source.authority,
            retrieved_at=now,
        )
    )
    session.commit()
    return opportunity


@pytest.fixture()
def sample_opportunity(session) -> Opportunity:
    return create_opportunity(session)


@pytest.fixture()
def auth_client(client, session_factory):
    session = session_factory()
    create_user(session)
    session.close()
    response = client.post(
        "/api/auth/login",
        json={"email": "person@example.com", "password": "correct-horse-battery"},
    )
    assert response.status_code == 200, response.text
    return client


@pytest.fixture()
def admin_client(client, session_factory):
    session = session_factory()
    create_user(session, email="admin@example.com", password="admin-password-123", role="admin")
    session.close()
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin-password-123"},
    )
    assert response.status_code == 200, response.text
    return client
