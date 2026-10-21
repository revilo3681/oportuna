"""Idempotent seed data: real, verified public sources and an optional admin user.

No demo opportunities are seeded. The catalog is populated by real ingestion; the
only seeded records are the source registry itself.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from oportuna.config import get_settings
from oportuna.db.models import Source, User
from oportuna.security import hash_password

logger = logging.getLogger("oportuna.seed")

DEFAULT_SOURCES: list[dict] = [
    {
        "slug": "devpost",
        "name": "Devpost",
        "kind": "devpost",
        "homepage_url": "https://devpost.com/",
        "endpoint": "https://devpost.com/api/hackathons",
        "region": "global",
        "languages": ["en"],
        "authority": 85,
        "frequency_minutes": 360,
        "config": {"statuses": ["open"], "per_page": 100, "max_items": 80},
        "access_notes": (
            "API JSON pública de listados de hackathons. Se consulta el endpoint oficial con "
            "User-Agent identificable, sin rastrear HTML ni eludir protecciones. La fecha de "
            "envío no es una fecha de inscripción: se guarda como submission_deadline."
        ),
        "terms_url": "https://devpost.com/terms-of-service",
    },
    {
        "slug": "pytorch-events",
        "name": "PyTorch Foundation — Events",
        "kind": "jsonld",
        "homepage_url": "https://pytorch.org/events/",
        "endpoint": "https://pytorch.org/events/",
        "region": "global",
        "languages": ["en"],
        "authority": 90,
        "frequency_minutes": 720,
        "config": {"require_tech": True, "max_items": 40, "respect_robots": True},
        "access_notes": (
            "Página pública de eventos. Solo se leen los bloques schema.org Event ya publicados "
            "para indexación; no se ejecuta JavaScript ni se accede a áreas privadas."
        ),
        "terms_url": "https://pytorch.org/",
    },
    {
        "slug": "berkeley-events",
        "name": "UC Berkeley Events",
        "kind": "ics",
        "homepage_url": "https://events.berkeley.edu/",
        "endpoint": "https://events.berkeley.edu/live/ical/events",
        "region": "norteamerica",
        "languages": ["en"],
        "authority": 80,
        "frequency_minutes": 720,
        "config": {
            "lookahead_days": 120,
            "max_items": 40,
            "require_tech": True,
            "default_country": "US",
            "language": "en",
        },
        "access_notes": (
            "Calendario iCalendar público de la universidad. Se respeta robots.txt y el límite "
            "de peticiones; los eventos sin relación tecnológica se descartan."
        ),
        "terms_url": "https://events.berkeley.edu/",
    },
    {
        "slug": "mit-events",
        "name": "MIT Calendar",
        "kind": "ics",
        "homepage_url": "https://calendar.mit.edu/",
        "endpoint": "https://calendar.mit.edu/calendar.ics",
        "region": "norteamerica",
        "languages": ["en"],
        "authority": 82,
        "frequency_minutes": 720,
        "config": {
            "lookahead_days": 120,
            "max_items": 40,
            "require_tech": True,
            "default_country": "US",
            "language": "en",
        },
        "access_notes": "Feed iCalendar público del calendario institucional del MIT.",
        "terms_url": "https://calendar.mit.edu/",
    },
    {
        "slug": "cornell-events",
        "name": "Cornell Events",
        "kind": "ics",
        "homepage_url": "https://events.cornell.edu/",
        "endpoint": "https://events.cornell.edu/calendar.ics",
        "region": "norteamerica",
        "languages": ["en"],
        "authority": 78,
        "frequency_minutes": 720,
        "config": {
            "lookahead_days": 120,
            "max_items": 40,
            "require_tech": True,
            "default_country": "US",
            "language": "en",
        },
        "access_notes": "Feed iCalendar público del calendario institucional de Cornell.",
        "terms_url": "https://events.cornell.edu/",
    },
    {
        "slug": "stanford-events",
        "name": "Stanford Events",
        "kind": "ics",
        "homepage_url": "https://events.stanford.edu/",
        "endpoint": "https://events.stanford.edu/calendar.ics",
        "region": "norteamerica",
        "languages": ["en"],
        "authority": 80,
        "frequency_minutes": 720,
        "config": {
            "lookahead_days": 120,
            "max_items": 40,
            "require_tech": True,
            "default_country": "US",
            "language": "en",
        },
        "access_notes": "Feed iCalendar público del calendario institucional de Stanford.",
        "terms_url": "https://events.stanford.edu/",
    },
    {
        "slug": "opportunities-for-africans",
        "name": "Opportunities For Africans",
        "kind": "rss",
        "homepage_url": "https://www.opportunitiesforafricans.com/",
        "endpoint": "https://www.opportunitiesforafricans.com/feed/",
        "region": "africa",
        "languages": ["en"],
        "authority": 45,
        "frequency_minutes": 720,
        "config": {"max_items": 20, "require_tech": True},
        "access_notes": (
            "Feed RSS público. Se trata como pista de descubrimiento: no se publica sin "
            "confirmación oficial y las fechas solo se extraen cuando el texto las declara."
        ),
        "terms_url": "https://www.opportunitiesforafricans.com/",
    },
    {
        "slug": "github-hackathons",
        "name": "GitHub — hackathon repositories",
        "kind": "github",
        "homepage_url": "https://github.com/",
        "endpoint": "https://api.github.com/search/repositories",
        "region": "global",
        "languages": ["en"],
        "authority": 40,
        "enabled": False,
        "frequency_minutes": 1440,
        "config": {"query": "topic:hackathon", "per_page": 20, "max_items": 15},
        "access_notes": (
            "Deshabilitada por defecto. La API de búsqueda de GitHub es pública pero tiene un "
            "límite estricto sin token y los repositorios no son convocatorias: sus resultados "
            "quedan como pistas para revisión, nunca publicados automáticamente."
        ),
        "terms_url": "https://docs.github.com/en/site-policy/github-terms/github-terms-of-service",
    },
]


def seed_sources(session: Session) -> int:
    created = 0
    for payload in DEFAULT_SOURCES:
        existing = session.scalars(select(Source).where(Source.slug == payload["slug"])).first()
        if existing:
            continue
        data = dict(payload)
        data.setdefault("enabled", True)
        session.add(Source(**data))
        created += 1
    session.commit()
    return created


def seed_admin(session: Session) -> User | None:
    settings = get_settings()
    email = (settings.seed_admin_email or "").strip().lower()
    password = settings.seed_admin_password or ""
    if not email or not password:
        return None
    existing = session.scalars(select(User).where(User.email == email)).first()
    if existing:
        if existing.role != "admin":
            existing.role = "admin"
            session.commit()
        return existing
    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name="Administración",
        role="admin",
    )
    session.add(user)
    session.commit()
    logger.info("admin user seeded: %s", email)
    return user


def seed_all(session: Session) -> dict[str, int | bool]:
    sources = seed_sources(session)
    admin = seed_admin(session)
    return {"sources_created": sources, "admin_ready": admin is not None}


if __name__ == "__main__":
    from oportuna.db.base import get_session_factory

    session = get_session_factory()()
    try:
        print(seed_all(session))
    finally:
        session.close()
