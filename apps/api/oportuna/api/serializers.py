"""Response serializers shared by public and admin APIs."""

from __future__ import annotations

from datetime import UTC, datetime

from oportuna.domain.dates import (
    deadline_label,
    deadline_urgency,
    effective_deadline,
    ensure_utc,
    format_date_range,
)
from oportuna.domain.ranking import RankCandidate
from oportuna.domain.taxonomy import (
    CATEGORIES,
    COST_TYPES,
    LIFECYCLES,
    MODALITIES,
    REVIEW_STATES,
    TECH_TAGS,
    VERIFICATION_STATES,
    country_name,
    tech_label,
)


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return ensure_utc(value).isoformat()


def _int_or_none(value) -> int | None:
    return int(value) if value is not None else None


def deadline_info(opportunity) -> dict:
    registration = opportunity.registration_deadline
    submission = opportunity.submission_deadline
    effective = effective_deadline(registration, submission)
    kind = None
    if effective is not None:
        if registration is not None and ensure_utc(registration) == ensure_utc(effective):
            kind = "registration"
        else:
            kind = "submission"
    return {
        "registration_deadline": iso(registration),
        "submission_deadline": iso(submission),
        "effective": iso(effective),
        "kind": kind,
        "label": deadline_label(effective),
        "urgency": deadline_urgency(effective),
        "is_open": opportunity.lifecycle in {"open", "rolling"},
    }


def verification_info(opportunity) -> dict:
    return {
        "state": opportunity.verification_state,
        "label": (
            "Finalizado" if opportunity.verification_state == "closed" else VERIFICATION_STATES.get(opportunity.verification_state, opportunity.verification_state)
        ),
        "confidence": round(opportunity.confidence_score, 3),
        "confidence_pct": int(round(opportunity.confidence_score * 100)),
        "reasons": opportunity.confidence_reasons or [],
        "conflict_count": opportunity.conflict_count,
        "review_state": opportunity.review_state,
        "review_label": REVIEW_STATES.get(opportunity.review_state, opportunity.review_state),
        "review_reason": opportunity.review_reason,
        "published": opportunity.published,
        "last_checked_at": iso(opportunity.last_checked_at),
        "last_verified_at": iso(opportunity.last_verified_at),
        "is_demo": opportunity.is_demo,
    }


def _primary_source(opportunity) -> dict | None:
    links = [link for link in opportunity.sources if link.source is not None]
    if not links:
        return None
    best = max(links, key=lambda link: link.authority)
    return {
        "name": best.source.name,
        "slug": best.source.slug,
        "authority": best.authority,
        "url": best.source_url,
        "retrieved_at": iso(best.retrieved_at),
    }


def eligibility_summary(opportunity) -> list[str]:
    requirements = opportunity.eligibility or {}
    labels: list[str] = []
    mapping = {
        "countries": "Países admitidos",
        "min_age": "Edad mínima",
        "max_age": "Edad máxima",
        "students_only": "Solo estudiantes",
        "experience_levels": "Nivel requerido",
        "team_required": "Equipo obligatorio",
        "invite_only": "Solo por invitación",
    }
    for key, label in mapping.items():
        value = requirements.get(key)
        if value in (None, "", [], {}):
            continue
        if isinstance(value, list):
            rendered = ", ".join(str(v) for v in value)
        elif isinstance(value, bool):
            rendered = "Sí" if value else "No"
        else:
            rendered = str(value)
        labels.append(f"{label}: {rendered}")
    return labels


def prizes_summary(opportunity) -> str | None:
    prizes = opportunity.prizes or []
    labels = [p.get("label") for p in prizes if isinstance(p, dict) and p.get("label")]
    if not labels:
        return None
    return " · ".join(labels[:3])


def commitment_minutes(opportunity) -> int | None:
    if opportunity.duration_minutes is None and opportunity.prep_time_minutes is None:
        return None
    return (opportunity.duration_minutes or 0) + (opportunity.prep_time_minutes or 0)


def opportunity_card(opportunity, *, reasons: list[dict] | None = None) -> dict:
    now = datetime.now(UTC)
    category = opportunity.category
    deadline = deadline_info(opportunity)
    duration = opportunity.duration_minutes
    commitment = commitment_minutes(opportunity)
    return {
        "id": str(opportunity.id),
        "slug": opportunity.slug,
        "title": opportunity.title,
        "summary": opportunity.summary,
        "category": {
            "key": category,
            "label": CATEGORIES.get(category, {}).get("label", category),
        },
        "subcategory": opportunity.subcategory,
        "tech_tags": [
            {"key": tag, "label": TECH_TAGS.get(tag, {}).get("label", tag)}
            for tag in (opportunity.tech_tags or [])
        ],
        "modality": {
            "key": opportunity.modality,
            "label": MODALITIES.get(opportunity.modality, opportunity.modality),
        },
        "country": {
            "code": opportunity.country,
            "name": country_name(opportunity.country),
        }
        if opportunity.country
        else None,
        "city": opportunity.city,
        "language": opportunity.language,
        "organizer": opportunity.organizer,
        "official_url": opportunity.official_url,
        "registration_url": opportunity.registration_url,
        "event_start": iso(opportunity.event_start),
        "event_end": iso(opportunity.event_end),
        "event_range": format_date_range(opportunity.event_start, opportunity.event_end),
        "deadline": deadline,
        "lifecycle": {
            "key": opportunity.lifecycle,
            "label": LIFECYCLES.get(opportunity.lifecycle, opportunity.lifecycle),
        },
        "registration_state": opportunity.registration_state,
        "verification": verification_info(opportunity),
        "source": _primary_source(opportunity),
        "cost": {
            "type": opportunity.cost_type,
            "label": COST_TYPES.get(opportunity.cost_type, opportunity.cost_type),
            "amount": opportunity.cost_amount,
            "currency": opportunity.currency,
        },
        "prizes_summary": prizes_summary(opportunity),
        "duration_minutes": duration,
        "prep_time_minutes": opportunity.prep_time_minutes,
        "commitment_minutes": commitment,
        "duration_known": duration is not None,
        "eligibility": opportunity.eligibility or {},
        "eligibility_summary": eligibility_summary(opportunity),
        "team_min": opportunity.team_min,
        "team_max": opportunity.team_max,
        "quality_score": round(opportunity.quality_score, 1),
        "reasons": reasons or [],
        "first_seen_at": iso(opportunity.first_seen_at),
        "last_checked_at": iso(opportunity.last_checked_at),
        "is_demo": opportunity.is_demo,
        "now": iso(now),
    }


def provenance_rows(session, opportunity) -> list[dict]:
    from sqlalchemy import select

    from oportuna.db.models import FieldProvenance, Source

    rows = session.scalars(
        select(FieldProvenance)
        .where(FieldProvenance.opportunity_id == opportunity.id)
        .order_by(FieldProvenance.field.asc(), FieldProvenance.observed_at.desc())
    ).all()
    source_ids = {row.source_id for row in rows if row.source_id}
    sources = {}
    if source_ids:
        for source in session.scalars(select(Source).where(Source.id.in_(source_ids))).all():
            sources[source.id] = source
    result = []
    for row in rows:
        source = sources.get(row.source_id)
        result.append(
            {
                "field": row.field,
                "value": (row.value or {}).get("value"),
                "observed_at": iso(row.observed_at),
                "method": row.method,
                "confidence": round(row.confidence, 2),
                "is_official": row.is_official,
                "note": row.note,
                "source": (
                    {
                        "name": source.name,
                        "slug": source.slug,
                        "authority": source.authority,
                    }
                    if source
                    else None
                ),
            }
        )
    return result


def opportunity_detail(session, opportunity, *, viewer=None, related=None) -> dict:
    card = opportunity_card(opportunity)
    from sqlalchemy import select

    from oportuna.db.models import OpportunityChange, SavedOpportunity, VerificationCheck

    changes = session.scalars(
        select(OpportunityChange)
        .where(OpportunityChange.opportunity_id == opportunity.id)
        .order_by(OpportunityChange.created_at.desc())
        .limit(30)
    ).all()
    checks = session.scalars(
        select(VerificationCheck)
        .where(VerificationCheck.opportunity_id == opportunity.id)
        .order_by(VerificationCheck.checked_at.desc())
        .limit(10)
    ).all()
    saved = None
    if viewer is not None:
        row = session.scalars(
            select(SavedOpportunity).where(
                SavedOpportunity.user_id == viewer.id,
                SavedOpportunity.opportunity_id == opportunity.id,
            )
        ).first()
        if row:
            saved = {"state": row.state, "useful": row.useful, "notes": row.notes}

    sources = []
    for link in opportunity.sources:
        if link.source is None:
            continue
        sources.append(
            {
                "name": link.source.name,
                "slug": link.source.slug,
                "homepage_url": link.source.homepage_url,
                "authority": link.authority,
                "source_url": link.source_url,
                "external_id": link.external_id,
                "retrieved_at": iso(link.retrieved_at),
                "notes": link.source.access_notes,
            }
        )

    card.update(
        {
            "description": opportunity.description,
            "registration_open_at": iso(opportunity.registration_open_at),
            "submission_deadline": iso(opportunity.submission_deadline),
            "results_at": iso(opportunity.results_at),
            "phases": opportunity.phases or [],
            "timezone": opportunity.timezone,
            "duration_minutes": opportunity.duration_minutes,
            "prep_time_minutes": opportunity.prep_time_minutes,
            "commitment_minutes": commitment_minutes(opportunity),
            "commitment_note": opportunity.commitment_note,
            "prizes": opportunity.prizes or [],
            "team_min": opportunity.team_min,
            "team_max": opportunity.team_max,
            "provenance": provenance_rows(session, opportunity),
            "changes": [
                {
                    "field": change.field,
                    "old_value": (change.old_value or {}).get("value") if change.old_value else None,
                    "new_value": (change.new_value or {}).get("value") if change.new_value else None,
                    "actor": change.actor,
                    "reason": change.reason,
                    "created_at": iso(change.created_at),
                }
                for change in changes
            ],
            "checks": [
                {
                    "outcome": check.outcome,
                    "checked_at": iso(check.checked_at),
                    "http_status": check.http_status,
                    "evidence": check.evidence,
                }
                for check in checks
            ],
            "sources": sources,
            "saved": saved,
            "related": related or [],
            "next_steps": build_next_steps(opportunity),
        }
    )
    return card


def build_next_steps(opportunity) -> list[dict]:
    steps: list[dict] = []
    if opportunity.registration_url:
        steps.append(
            {
                "kind": "register",
                "label": "Abrir el enlace de registro o envío",
                "detail": "Se abre en la web del organizador. Oportuna no inscribe por ti.",
            }
        )
    if opportunity.eligibility:
        steps.append(
            {
                "kind": "verify_eligibility",
                "label": "Confirmar requisitos en la fuente oficial",
                "detail": "Comprueba edad, país, equipo y nivel antes de invertir tiempo.",
            }
        )
    deadline = effective_deadline(opportunity.registration_deadline, opportunity.submission_deadline)
    if deadline is not None and opportunity.lifecycle in {"open", "rolling"}:
        steps.append(
            {
                "kind": "calendar",
                "label": "Añadir la fecha límite a tu calendario",
                "detail": deadline_label(deadline),
            }
        )
    if opportunity.verification_state in {"pending", "conflict"}:
        steps.append(
            {
                "kind": "trust",
                "label": "Verificar antes de participar",
                "detail": opportunity.review_reason or "La información aún no está confirmada.",
            }
        )
    if not steps:
        steps.append(
            {
                "kind": "source",
                "label": "Revisar la web oficial",
                "detail": "La ficha conserva la fuente original y la última comprobación.",
            }
        )
    return steps[:4]


def rank_candidate(opportunity) -> RankCandidate:
    return RankCandidate(
        id=str(opportunity.id),
        title=opportunity.title,
        category=opportunity.category,
        tech_tags=list(opportunity.tech_tags or []),
        modality=opportunity.modality,
        country=opportunity.country,
        city=opportunity.city,
        language=opportunity.language,
        cost_type=opportunity.cost_type,
        cost_amount=opportunity.cost_amount,
        event_start=opportunity.event_start,
        event_end=opportunity.event_end,
        registration_deadline=effective_deadline(
            opportunity.registration_deadline, opportunity.submission_deadline
        ),
        duration_minutes=opportunity.duration_minutes,
        prep_time_minutes=opportunity.prep_time_minutes,
        lifecycle=opportunity.lifecycle,
        verification_state=opportunity.verification_state,
        confidence=opportunity.confidence_score,
        eligibility=opportunity.eligibility or {},
        prizes=opportunity.prizes or [],
        team_min=opportunity.team_min,
        team_max=opportunity.team_max,
        organizer=opportunity.organizer,
        has_certificate=False,
    )


def profile_dict(user) -> dict:
    profile = user.profile
    if profile is None:
        return {
            "interests": [],
            "level": None,
            "goals": [],
            "country": None,
            "city": None,
            "travel_radius_km": None,
            "modalities": [],
            "languages": [],
            "availability": {},
            "time_preferences": [],
            "budget": None,
            "eligibility": {},
            "preferences": {},
            "onboarded_at": None,
            "completeness": 0,
        }
    data = {
        "interests": profile.interests or [],
        "level": profile.level,
        "goals": profile.goals or [],
        "country": profile.country,
        "city": profile.city,
        "travel_radius_km": profile.travel_radius_km,
        "modalities": profile.modalities or [],
        "languages": profile.languages or [],
        "availability": profile.availability or {},
        "time_preferences": profile.time_preferences or [],
        "budget": profile.budget,
        "eligibility": profile.eligibility or {},
        "preferences": profile.preferences or {},
        "onboarded_at": iso(profile.onboarded_at),
    }
    data["completeness"] = profile_completeness(data)
    return data


def profile_completeness(profile: dict) -> int:
    checks = [
        bool(profile.get("interests")),
        bool(profile.get("modalities")),
        bool(profile.get("country")),
        bool(profile.get("availability")),
        bool(profile.get("level")),
        bool(profile.get("goals")),
        bool(profile.get("time_preferences")),
        bool(profile.get("languages")),
        bool(profile.get("budget")),
    ]
    return int(round(sum(1 for c in checks if c) / len(checks) * 100))


def public_user(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "created_at": iso(user.created_at),
        "profile": profile_dict(user),
    }


def source_dict(source, *, published: int = 0) -> dict:
    return {
        "id": str(source.id),
        "slug": source.slug,
        "name": source.name,
        "kind": source.kind,
        "homepage_url": source.homepage_url,
        "endpoint": source.endpoint,
        "region": source.region,
        "languages": source.languages or [],
        "authority": source.authority,
        "enabled": source.enabled,
        "frequency_minutes": source.frequency_minutes,
        "last_run_at": iso(source.last_run_at),
        "last_status": source.last_status,
        "last_error": source.last_error,
        "consecutive_failures": source.consecutive_failures,
        "disabled_reason": source.disabled_reason,
        "access_notes": source.access_notes,
        "terms_url": source.terms_url,
        "config": source.config or {},
        "published_count": published,
    }


def tech_label_safe(tag: str) -> str:
    return tech_label(tag)
