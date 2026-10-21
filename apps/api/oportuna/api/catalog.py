"""Public catalog, detail, dashboard and transparency endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from oportuna.api.deps import optional_user
from oportuna.api.serializers import (
    opportunity_card,
    opportunity_detail,
    rank_candidate,
    source_dict,
)
from oportuna.config import get_settings
from oportuna.db.base import get_db
from oportuna.db.models import Opportunity, OpportunitySource, Source, User
from oportuna.domain.dates import (
    deadline_label,
    effective_deadline,
    ensure_utc,
    format_date_range,
    utcnow,
)
from oportuna.domain.ics import build_calendar
from oportuna.domain.normalize import normalize_text
from oportuna.domain.ranking import DEFAULT_WEIGHTS, rank_candidates
from oportuna.domain.taxonomy import (
    BUDGETS,
    CATEGORIES,
    COST_TYPES,
    GOALS,
    LANGUAGES,
    LEVELS,
    LIFECYCLES,
    MODALITIES,
    REGIONS,
    REVIEW_STATES,
    TECH_TAGS,
    TIME_BUCKETS,
    VERIFICATION_STATES,
    country_name,
)

router = APIRouter(tags=["catalog"])

OPEN_STATES = ("open", "rolling")


def visible_opportunities():
    return select(Opportunity).where(
        Opportunity.published.is_(True),
        Opportunity.is_demo.is_(False),
    )


def _query_options():
    return (
        selectinload(Opportunity.sources).joinedload(OpportunitySource.source),
    )


@router.get("/opportunities")
def list_opportunities(
    db: Session = Depends(get_db),
    q: str = "",
    category: list[str] = Query(default=[]),
    tech: list[str] = Query(default=[]),
    modality: str | None = None,
    country: str | None = None,
    language: str | None = None,
    cost: str | None = None,
    days: int | None = Query(default=None, ge=1, le=365),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    include_closed: bool = False,
    sort: str = "relevance",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=60),
):
    now = utcnow()
    conditions = [
        Opportunity.published.is_(True),
        Opportunity.is_demo.is_(False),
    ]
    if not include_closed:
        conditions.append(Opportunity.lifecycle.in_(OPEN_STATES))

    normalized_q = normalize_text(q)
    for token in [t for t in normalized_q.split() if t][:6]:
        conditions.append(Opportunity.search_text.contains(token))

    if category:
        valid = [c for c in category if c in CATEGORIES]
        if valid:
            conditions.append(Opportunity.category.in_(valid))
    if tech:
        for tag in [t for t in tech if t in TECH_TAGS][:4]:
            conditions.append(Opportunity.tech_tags_text.contains(f"|{tag}|"))
    if modality and modality in MODALITIES:
        conditions.append(Opportunity.modality == modality)
    if country:
        conditions.append(Opportunity.country == country.upper())
    if language:
        conditions.append(Opportunity.language == language.lower())
    if cost == "free":
        conditions.append(Opportunity.cost_type == "free")
    elif cost == "paid":
        conditions.append(Opportunity.cost_type == "paid")

    effective = func.coalesce(Opportunity.registration_deadline, Opportunity.submission_deadline)
    if days:
        conditions.append(effective.is_not(None))
        conditions.append(effective >= now)
        conditions.append(effective <= now + timedelta(days=days))
    if date_from:
        conditions.append(effective.is_not(None))
        conditions.append(effective >= ensure_utc(date_from))
    if date_to:
        conditions.append(effective.is_not(None))
        conditions.append(effective <= ensure_utc(date_to))

    total = db.scalar(select(func.count()).select_from(Opportunity).where(*conditions)) or 0

    if sort == "newest":
        ordering = (Opportunity.first_seen_at.desc(),)
    elif sort == "deadline":
        ordering = (effective.is_(None), effective.asc())
    elif sort == "confidence":
        ordering = (Opportunity.confidence_score.desc(), Opportunity.quality_score.desc())
    else:
        ordering = (Opportunity.quality_score.desc(), Opportunity.confidence_score.desc())

    rows = db.scalars(
        select(Opportunity)
        .where(*conditions)
        .options(*_query_options())
        .order_by(*ordering)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "items": [opportunity_card(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
        "facets": _facets(db),
        "applied": {
            "q": q,
            "category": category,
            "tech": tech,
            "modality": modality,
            "country": country,
            "language": language,
            "cost": cost,
            "days": days,
            "include_closed": include_closed,
            "sort": sort,
        },
    }


def _facets(db: Session) -> dict:
    rows = db.scalars(
        visible_opportunities().where(Opportunity.lifecycle.in_(OPEN_STATES)).limit(3000)
    ).all()
    categories: dict[str, int] = {}
    tags: dict[str, int] = {}
    modalities: dict[str, int] = {}
    costs: dict[str, int] = {}
    countries: dict[str, int] = {}
    languages: dict[str, int] = {}
    for row in rows:
        categories[row.category] = categories.get(row.category, 0) + 1
        for tag in row.tech_tags or []:
            tags[tag] = tags.get(tag, 0) + 1
        modalities[row.modality] = modalities.get(row.modality, 0) + 1
        costs[row.cost_type] = costs.get(row.cost_type, 0) + 1
        if row.country:
            countries[row.country] = countries.get(row.country, 0) + 1
        if row.language:
            languages[row.language] = languages.get(row.language, 0) + 1
    return {
        "category": [
            {"key": key, "label": CATEGORIES.get(key, {}).get("label", key), "count": count}
            for key, count in sorted(categories.items(), key=lambda item: -item[1])
        ],
        "tech": [
            {"key": key, "label": TECH_TAGS.get(key, {}).get("label", key), "count": count}
            for key, count in sorted(tags.items(), key=lambda item: -item[1])[:20]
        ],
        "modality": [
            {"key": key, "label": MODALITIES.get(key, key), "count": count}
            for key, count in sorted(modalities.items(), key=lambda item: -item[1])
        ],
        "cost": [
            {"key": key, "label": COST_TYPES.get(key, key), "count": count}
            for key, count in sorted(costs.items(), key=lambda item: -item[1])
        ],
        "country": [
            {"key": key, "label": country_name(key) or key, "count": count}
            for key, count in sorted(countries.items(), key=lambda item: -item[1])[:20]
        ],
        "language": [
            {"key": key, "label": LANGUAGES.get(key, key.upper()), "count": count}
            for key, count in sorted(languages.items(), key=lambda item: -item[1])
        ],
    }


@router.get("/opportunities/{slug}")
def get_opportunity(
    slug: str,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(optional_user),
):
    opportunity = db.scalars(
        select(Opportunity)
        .where(Opportunity.slug == slug)
        .options(*_query_options())
    ).first()
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")
    is_admin = viewer is not None and viewer.role == "admin"
    if not opportunity.published and not is_admin:
        raise HTTPException(status_code=404, detail="Oportunidad no publicada")
    if opportunity.is_demo:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")

    related_rows = db.scalars(
        visible_opportunities()
        .where(
            Opportunity.id != opportunity.id,
            Opportunity.category == opportunity.category,
            Opportunity.lifecycle.in_(OPEN_STATES),
        )
        .options(*_query_options())
        .order_by(Opportunity.quality_score.desc())
        .limit(8)
    ).all()
    tags = set(opportunity.tech_tags or [])
    related_sorted = sorted(
        related_rows,
        key=lambda row: (-len(tags & set(row.tech_tags or [])), -row.quality_score),
    )[:3]

    return opportunity_detail(
        db,
        opportunity,
        viewer=viewer,
        related=[opportunity_card(row) for row in related_sorted],
    )


@router.get("/opportunities/{slug}/ics")
def opportunity_ics(slug: str, db: Session = Depends(get_db)):
    opportunity = db.scalars(
        select(Opportunity).where(Opportunity.slug == slug, Opportunity.published.is_(True))
    ).first()
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")
    items = []
    deadline = effective_deadline(opportunity.registration_deadline, opportunity.submission_deadline)
    if deadline:
        items.append(
            {
                "uid": opportunity.slug,
                "title": opportunity.title,
                "date": deadline,
                "kind": "deadline",
                "description": deadline_label(deadline),
                "url": opportunity.official_url,
            }
        )
    if opportunity.event_start:
        items.append(
            {
                "uid": opportunity.slug,
                "title": opportunity.title,
                "date": opportunity.event_start,
                "end": opportunity.event_end,
                "kind": "event",
                "description": format_date_range(opportunity.event_start, opportunity.event_end),
                "url": opportunity.official_url,
                "location": opportunity.city or (country_name(opportunity.country) or None),
            }
        )
    payload = build_calendar(items, name="Oportuna")
    return Response(
        content=payload,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{opportunity.slug}.ics"'},
    )


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), viewer: User | None = Depends(optional_user)):
    now = utcnow()
    profile = None
    if viewer is not None:
        from oportuna.api.serializers import profile_dict

        profile_data = profile_dict(viewer)
        if profile_data["interests"] or profile_data["modalities"]:
            profile = profile_data

    rows = db.scalars(
        visible_opportunities()
        .where(Opportunity.lifecycle.in_(OPEN_STATES))
        .options(*_query_options())
        .order_by(Opportunity.quality_score.desc())
        .limit(400)
    ).all()

    ranked = rank_candidates([rank_candidate(row) for row in rows], profile, limit=24)
    by_id = {str(row.id): row for row in rows}
    priority_items = []
    for item in ranked[:8]:
        opportunity = by_id.get(item.candidate.id)
        if opportunity is None:
            continue
        priority_items.append(opportunity_card(opportunity, reasons=item.reasons))
    priority_count = sum(1 for item in ranked if item.score >= 55)

    week_ago = now - timedelta(days=7)
    new_rows = [
        row for row in rows if ensure_utc(row.first_seen_at) >= week_ago
    ]
    new_rows.sort(key=lambda row: ensure_utc(row.first_seen_at), reverse=True)
    new_items = [opportunity_card(row) for row in new_rows[:4]]

    upcoming_rows = []
    for row in rows:
        deadline = effective_deadline(row.registration_deadline, row.submission_deadline)
        if deadline and now <= ensure_utc(deadline) <= now + timedelta(days=7):
            upcoming_rows.append((ensure_utc(deadline), row))
    upcoming_rows.sort(key=lambda item: item[0])
    upcoming_items = [opportunity_card(row) for _, row in upcoming_rows[:4]]
    upcoming_count = len(upcoming_rows)

    categories = []
    for key, meta in CATEGORIES.items():
        members = [row for row in rows if row.category == key]
        categories.append(
            {
                "key": key,
                "label": meta["label"],
                "tagline": meta["tagline"],
                "count": len(members),
                "next_deadline": _soonest_deadline(members),
            }
        )

    total_open = len(rows)
    sources_count = db.scalar(
        select(func.count()).select_from(Source).where(Source.enabled.is_(True))
    ) or 0
    last_checked = db.scalar(select(func.max(Opportunity.last_checked_at)))
    published_total = db.scalar(
        select(func.count())
        .select_from(Opportunity)
        .where(Opportunity.published.is_(True), Opportunity.is_demo.is_(False))
    ) or 0

    greeting_note = _daily_note(total_open, upcoming_count, len(new_rows), profile is not None)

    return {
        "personalized": profile is not None,
        "profile_completeness": (profile or {}).get("completeness", 0),
        "summary": {
            "new": len(new_rows),
            "upcoming": upcoming_count,
            "priority": priority_count,
            "priority_label": "Para ti" if profile else "Destacadas",
            "open_total": total_open,
            "published_total": published_total,
            "categories": len([c for c in categories if c["count"]]),
            "active_sources": sources_count,
        },
        "note": greeting_note,
        "priority": priority_items,
        "new": new_items,
        "upcoming": upcoming_items,
        "categories": categories,
        "freshness": {
            "last_checked_at": ensure_utc(last_checked).isoformat() if last_checked else None,
            "generated_at": now.isoformat(),
        },
        "weights": DEFAULT_WEIGHTS,
    }


def _soonest_deadline(rows: list[Opportunity]) -> datetime | None:
    deadlines = [
        ensure_utc(d)
        for row in rows
        if (d := effective_deadline(row.registration_deadline, row.submission_deadline)) is not None
    ]
    return min(deadlines) if deadlines else None


def _daily_note(total: int, upcoming: int, new: int, personalized: bool) -> str:
    if total == 0:
        return (
            "Aún no hay oportunidades validadas. La ingesta inicial puede tardar unos minutos; "
            "mientras tanto, revisa las fuentes y su política de acceso."
        )
    pieces = [f"{total} oportunidades abiertas y verificadas"]
    if new:
        pieces.append(f"{new} detectadas esta semana")
    if upcoming:
        pieces.append(f"{upcoming} cierran en los próximos 7 días")
    if not personalized:
        pieces.append("Completa tu perfil para ordenar por tus intereses y tu tiempo")
    return " · ".join(pieces) + "."


@router.get("/taxonomy")
def taxonomy(db: Session = Depends(get_db)):
    countries = db.scalars(
        select(Opportunity.country)
        .where(Opportunity.published.is_(True), Opportunity.country.is_not(None))
        .distinct()
    ).all()
    try:
        import pycountry

        all_countries = sorted(
            [
                {"code": country.alpha_2, "name": country_name(country.alpha_2)}
                for country in pycountry.countries
            ],
            key=lambda item: item["name"] or "",
        )
    except Exception:  # pragma: no cover - defensive
        all_countries = []

    return {
        "categories": [
            {"key": key, **meta}
            for key, meta in CATEGORIES.items()
        ],
        "tech": [{"key": key, **meta} for key, meta in TECH_TAGS.items()],
        "modalities": MODALITIES,
        "costs": COST_TYPES,
        "lifecycles": LIFECYCLES,
        "verification_states": VERIFICATION_STATES,
        "review_states": REVIEW_STATES,
        "levels": LEVELS,
        "goals": GOALS,
        "time_buckets": TIME_BUCKETS,
        "budgets": BUDGETS,
        "languages": LANGUAGES,
        "regions": REGIONS,
        "countries": sorted(
            [{"code": code, "name": country_name(code)} for code in countries if code],
            key=lambda item: item["name"] or "",
        ),
        "countries_all": all_countries,
    }


@router.get("/sources")
def public_sources(db: Session = Depends(get_db)):
    sources = db.scalars(select(Source).order_by(Source.name)).all()
    counts = dict(
        db.execute(
            select(OpportunitySource.source_id, func.count(OpportunitySource.opportunity_id))
            .join(Opportunity, Opportunity.id == OpportunitySource.opportunity_id)
            .where(Opportunity.published.is_(True))
            .group_by(OpportunitySource.source_id)
        ).all()
    )
    items = []
    for source in sources:
        payload = source_dict(source, published=counts.get(source.id, 0))
        payload.pop("config", None)
        items.append(payload)
    return {
        "sources": items,
        "note": (
            "Solo se consultan endpoints públicos configurados, con allowlist de dominio, "
            "límites de frecuencia y respeto de robots.txt. No se eluden protecciones anti-bots."
        ),
    }


@router.get("/methodology")
def methodology(db: Session = Depends(get_db)):
    totals = {
        "published": db.scalar(
            select(func.count())
            .select_from(Opportunity)
            .where(Opportunity.published.is_(True), Opportunity.is_demo.is_(False))
        )
        or 0,
        "verified": db.scalar(
            select(func.count())
            .select_from(Opportunity)
            .where(Opportunity.verification_state == "verified")
        )
        or 0,
        "pending_review": db.scalar(
            select(func.count())
            .select_from(Opportunity)
            .where(Opportunity.review_state == "needs_review")
        )
        or 0,
        "sources": db.scalar(select(func.count()).select_from(Source)) or 0,
    }
    return {
        "totals": totals,
        "weights": DEFAULT_WEIGHTS,
        "verification_states": VERIFICATION_STATES,
        "publication_policy": {
            "summary": "Publicación automática solo para registros verificados; el resto va a revisión.",
            "min_confidence": get_settings().auto_publish_min_confidence,
            "max_age_days": get_settings().auto_publish_max_age_days,
            "gates": [
                "Verificado sobre una fuente oficial o plataforma de referencia",
                "Fecha de celebración o plazo de participación confirmado",
                "Sin contradicciones abiertas",
                "Última comprobación dentro del límite",
            ],
        },
        "confidence_signals": [
            "Autoridad de la fuente",
            "Confirmación oficial",
            "Recencia de la comprobación",
            "Coherencia de fechas",
            "Enlace de registro localizado",
            "Contradicciones detectadas",
        ],
        "trust_rules": [
            "Nunca se inventan eventos, fechas, premios ni enlaces.",
            "Una fecha inferida no se muestra como confirmada.",
            "La ficha conserva fuente y última comprobación.",
            "Un enlace que carga no implica que la inscripción esté abierta.",
            "Las oportunidades cerradas se conservan como historial, no como ofertas activas.",
        ],
        "update_policy": [
            "Fuentes de convocatorias: revisión diaria o según frecuencia configurada.",
            "Cierres próximos: comprobación más frecuente.",
            "Eventos lejanos: revisión periódica menos frecuente.",
            "Fallos: reintentos limitados y desactivación con alerta tras fallos consecutivos.",
        ],
    }
