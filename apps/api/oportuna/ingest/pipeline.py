"""Ingestion pipeline: adapter -> normalize -> deduplicate -> verify -> publish gate."""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from oportuna.config import get_settings
from oportuna.db.models import (
    DuplicateCandidate,
    FieldProvenance,
    IngestionRun,
    Opportunity,
    OpportunityChange,
    OpportunitySource,
    Source,
    VerificationCheck,
)
from oportuna.domain.dates import derive_lifecycle, ensure_utc, utcnow
from oportuna.domain.dedup import DedupRecord, compare
from oportuna.domain.normalize import (
    extract_year,
    normalize_text,
    normalize_url,
    registrable_domain,
    slugify,
    tokenize,
    truncate,
)
from oportuna.domain.ranking import baseline_quality
from oportuna.domain.taxonomy import (
    COST_TYPES,
    MODALITIES,
    classify_category,
    extract_tech_tags,
)
from oportuna.domain.trust import TrustSignals, compute_confidence, publication_decision
from oportuna.ingest.adapters import get_adapter
from oportuna.ingest.http import Fetcher, FetchError
from oportuna.ingest.types import RawOpportunity

logger = logging.getLogger("oportuna.ingest")

CRITICAL_FIELDS = {
    "event_start",
    "event_end",
    "registration_deadline",
    "submission_deadline",
    "cost_type",
    "country",
    "official_url",
}

FIELD_CONFIDENCE = {
    "country": 0.55,
    "city": 0.55,
    "category": 0.6,
    "tech_tags": 0.6,
    "language": 0.5,
    "modality": 0.6,
}


@dataclass
class RunStats:
    found: int = 0
    created: int = 0
    updated: int = 0
    duplicated: int = 0
    published: int = 0
    review: int = 0
    errors: int = 0
    skipped: int = 0
    messages: list[str] = field(default_factory=list)


@dataclass
class ProcessResult:
    status: str
    published: bool
    reason: str


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _diff_days(a: datetime | None, b: datetime | None) -> float | None:
    a, b = _aware(a), _aware(b)
    if a is None or b is None:
        return None
    return abs((a - b).total_seconds()) / 86400


def _slug_for(session: Session, title: str, official_url: str) -> str:
    base = slugify(title, max_length=170)
    digest = hashlib.sha1(normalize_url(official_url).encode("utf-8")).hexdigest()[:6]
    candidate = f"{base}-{digest}"
    counter = 1
    while session.scalar(select(Opportunity.id).where(Opportunity.slug == candidate)):
        counter += 1
        candidate = f"{base}-{digest}-{counter}"
    return candidate[:220]


def _derive_state(raw: RawOpportunity) -> tuple[str, str]:
    lifecycle, registration_state = derive_lifecycle(
        event_start=raw.event_start,
        event_end=raw.event_end,
        registration_deadline=raw.registration_deadline,
        rolling=raw.rolling,
        cancelled=raw.cancelled,
    )
    if raw.stated_lifecycle == "finished":
        return "finished", "closed"
    if raw.stated_lifecycle == "cancelled":
        return "cancelled", "closed"
    if raw.stated_lifecycle == "closed" and lifecycle not in {"finished", "cancelled"}:
        return "closed", "closed"
    if raw.stated_lifecycle == "open" and lifecycle not in {"finished", "cancelled"}:
        return "open", registration_state
    return lifecycle, registration_state


def build_fields(raw: RawOpportunity, source: Source, now: datetime) -> dict[str, Any]:
    title = truncate(raw.title, 400)
    summary = truncate(raw.summary, 600)
    description = truncate(raw.description, 12000)
    tags = list(dict.fromkeys(raw.tech_tags or extract_tech_tags(title, summary, description)))
    category = raw.category or classify_category(title, summary, description)
    if category is None:
        category = "eventos"

    modality = raw.modality if raw.modality in MODALITIES else "unknown"
    cost_type = raw.cost_type if raw.cost_type in COST_TYPES else "unknown"
    country = raw.country.upper() if raw.country and len(raw.country) == 2 else None
    language = raw.language.lower()[:8] if raw.language else None

    lifecycle, registration_state = _derive_state(raw)
    official_url = raw.official_url.strip()
    canonical_url = normalize_url(raw.canonical_url if hasattr(raw, "canonical_url") and raw.canonical_url else official_url)

    event_start = _aware(raw.event_start)
    event_end = _aware(raw.event_end)
    if event_start and event_end and event_end < event_start:
        event_end = None

    edition_year = (event_start.year if event_start else None) or extract_year(title, summary)

    search_text = normalize_text(
        " ".join(
            filter(
                None,
                [
                    title,
                    summary,
                    description,
                    raw.organizer,
                    raw.city,
                    country,
                    " ".join(tags),
                    category,
                ],
            )
        )
    )

    return {
        "title": title,
        "summary": summary,
        "description": description,
        "category": category,
        "subcategory": raw.subcategory,
        "tech_tags": tags,
        "tech_tags_text": "|" + "|".join(tags) + "|" if tags else "",
        "modality": modality,
        "country": country,
        "city": truncate(raw.city, 120) if raw.city else None,
        "timezone": raw.timezone,
        "language": language,
        "organizer": truncate(raw.organizer, 200) if raw.organizer else None,
        "organizer_url": raw.organizer_url,
        "official_url": official_url,
        "registration_url": raw.registration_url,
        "canonical_url": canonical_url,
        "edition_year": edition_year,
        "event_start": event_start,
        "event_end": event_end,
        "registration_open_at": _aware(raw.registration_open_at),
        "registration_deadline": _aware(raw.registration_deadline),
        "submission_deadline": _aware(raw.submission_deadline),
        "results_at": _aware(raw.results_at),
        "phases": raw.phases,
        "rolling": raw.rolling,
        "duration_minutes": raw.duration_minutes if (raw.duration_minutes or 0) > 0 else None,
        "prep_time_minutes": raw.prep_time_minutes if (raw.prep_time_minutes or 0) > 0 else None,
        "commitment_note": None,
        "cost_type": cost_type,
        "cost_amount": raw.cost_amount,
        "currency": raw.currency,
        "prizes": raw.prizes,
        "eligibility": raw.eligibility,
        "team_min": raw.team_min,
        "team_max": raw.team_max,
        "lifecycle": lifecycle,
        "registration_state": registration_state,
        "registration_state_source": source.slug,
        "last_checked_at": now,
        "last_changed_at": now,
        "search_text": search_text,
        "is_demo": source.is_demo,
    }


def _has_actionable_date(raw: RawOpportunity) -> bool:
    return raw.has_actionable_date()


def _official_domain_match(raw: RawOpportunity, source: Source) -> bool:
    official = registrable_domain(raw.official_url)
    provider = registrable_domain(source.homepage_url or source.endpoint)
    return bool(official and provider and official == provider)


def _provenance_values(raw: RawOpportunity, fields: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": fields["title"],
        "summary": fields["summary"] or None,
        "description": fields["description"] or None,
        "category": fields["category"],
        "tech_tags": fields["tech_tags"] or None,
        "modality": fields["modality"],
        "country": fields["country"],
        "city": fields["city"],
        "language": fields["language"],
        "organizer": fields["organizer"],
        "official_url": fields["official_url"],
        "registration_url": fields["registration_url"],
        "event_start": fields["event_start"].isoformat() if fields["event_start"] else None,
        "event_end": fields["event_end"].isoformat() if fields["event_end"] else None,
        "registration_deadline": (
            fields["registration_deadline"].isoformat() if fields["registration_deadline"] else None
        ),
        "submission_deadline": (
            fields["submission_deadline"].isoformat() if fields["submission_deadline"] else None
        ),
        "cost": (
            {"type": fields["cost_type"], "amount": fields["cost_amount"], "currency": fields["currency"]}
            if fields["cost_type"] != "unknown"
            else None
        ),
        "prizes": fields["prizes"] or None,
        "eligibility": fields["eligibility"] or None,
        "duration": fields["duration_minutes"],
    }


def _record_provenance(
    session: Session, opportunity: Opportunity, source: Source, raw: RawOpportunity, fields: dict
) -> None:
    rows = session.scalars(
        select(FieldProvenance).where(FieldProvenance.opportunity_id == opportunity.id)
    ).all()
    index = {(row.field, row.source_id): row for row in rows}
    now = utcnow()
    for field_name, value in _provenance_values(raw, fields).items():
        if value in (None, "", [], {}):
            continue
        key = (field_name, source.id)
        confidence = FIELD_CONFIDENCE.get(field_name, min(source.authority / 100, 0.95))
        if key in index:
            row = index[key]
            row.value = {"value": value}
            row.observed_at = now
            row.confidence = confidence
            row.is_official = raw.confirmed
            row.note = raw.confirmation_note or None
        else:
            session.add(
                FieldProvenance(
                    opportunity_id=opportunity.id,
                    field=field_name,
                    source_id=source.id,
                    value={"value": value},
                    observed_at=now,
                    method=source.kind,
                    confidence=confidence,
                    is_official=raw.confirmed,
                    note=raw.confirmation_note or None,
                )
            )


def _upsert_source_link(
    session: Session, opportunity: Opportunity, source: Source, raw: RawOpportunity
) -> OpportunitySource:
    link = None
    if raw.external_id:
        link = session.scalars(
            select(OpportunitySource).where(
                OpportunitySource.opportunity_id == opportunity.id,
                OpportunitySource.source_id == source.id,
                OpportunitySource.external_id == raw.external_id,
            )
        ).first()
    if link is None:
        link = session.scalars(
            select(OpportunitySource).where(
                OpportunitySource.opportunity_id == opportunity.id,
                OpportunitySource.source_id == source.id,
                OpportunitySource.source_url == raw.source_url,
            )
        ).first()
    if link is None:
        link = OpportunitySource(
            opportunity_id=opportunity.id,
            source_id=source.id,
            source_url=raw.source_url,
            external_id=raw.external_id,
            retrieved_at=utcnow(),
            raw_excerpt=truncate(raw.raw_excerpt or raw.summary, 1500),
            authority=source.authority,
        )
        session.add(link)
    else:
        link.source_url = raw.source_url
        link.external_id = raw.external_id or link.external_id
        link.retrieved_at = utcnow()
        link.raw_excerpt = truncate(raw.raw_excerpt or raw.summary, 1500)
        link.authority = source.authority
    return link


def _find_duplicates(
    session: Session, raw: RawOpportunity, fields: dict, *, exclude_id=None
) -> tuple[Opportunity | None, float, list[dict], bool, bool]:
    settings = get_settings()
    canonical = fields["canonical_url"]
    candidates: dict[str, Opportunity] = {}

    for row in session.scalars(
        select(Opportunity).where(Opportunity.canonical_url == canonical).limit(5)
    ).all():
        candidates[str(row.id)] = row

    tokens = sorted(tokenize(fields["title"], drop_generic=True), key=len, reverse=True)[:2]
    for token in tokens:
        for row in session.scalars(
            select(Opportunity).where(Opportunity.title.ilike(f"%{token}%")).limit(40)
        ).all():
            candidates[str(row.id)] = row

    if fields.get("organizer"):
        for row in session.scalars(
            select(Opportunity)
            .where(Opportunity.organizer.ilike(f"%{fields['organizer'][:40]}%"))
            .limit(30)
        ).all():
            candidates[str(row.id)] = row

    new_record = DedupRecord(
        name=fields["title"],
        organizer=fields["organizer"],
        canonical_url=canonical,
        city=fields["city"],
        country=fields["country"],
        modality=fields["modality"],
        description=fields["description"] or fields["summary"],
        event_start=fields["event_start"],
        event_end=fields["event_end"],
        edition_year=fields["edition_year"],
    )

    best: tuple[Opportunity | None, float, list[dict], bool, bool] = (None, 0.0, [], False, False)
    for candidate in candidates.values():
        if exclude_id is not None and candidate.id == exclude_id:
            continue
        existing = DedupRecord(
            name=candidate.title,
            organizer=candidate.organizer,
            canonical_url=candidate.canonical_url,
            city=candidate.city,
            country=candidate.country,
            modality=candidate.modality,
            description=candidate.description,
            event_start=_aware(candidate.event_start),
            event_end=_aware(candidate.event_end),
            edition_year=candidate.edition_year,
        )
        result = compare(
            new_record,
            existing,
            review_threshold=settings.duplicate_review_threshold,
            merge_threshold=settings.duplicate_merge_threshold,
        )
        if result.score > best[1]:
            best = (candidate, result.score, result.reasons, result.auto_merge, result.review)
    return best


def _record_changes(
    session: Session,
    opportunity: Opportunity,
    changed: Iterable[tuple[str, Any, Any]],
    *,
    source: Source | None,
    actor: str = "system",
    reason: str | None = None,
) -> None:
    for field_name, old, new in changed:
        session.add(
            OpportunityChange(
                opportunity_id=opportunity.id,
                field=field_name,
                old_value={"value": _jsonable(old)},
                new_value={"value": _jsonable(new)},
                source_id=source.id if source else None,
                actor=actor,
                reason=reason,
                created_at=utcnow(),
            )
        )


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return ensure_utc(value).isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _apply_fields(
    opportunity: Opportunity, fields: dict, *, allow_overwrite: bool
) -> tuple[list[tuple[str, Any, Any]], list[str]]:
    changed: list[tuple[str, Any, Any]] = []
    conflicts: list[str] = []
    for key, value in fields.items():
        if key in {"search_text", "last_changed_at", "is_demo"}:
            continue
        if _empty(value):
            continue
        old = getattr(opportunity, key, None)
        if _empty(old):
            setattr(opportunity, key, value)
            changed.append((key, old, value))
        elif old != value:
            if allow_overwrite and key not in CRITICAL_FIELDS:
                setattr(opportunity, key, value)
                changed.append((key, old, value))
            elif allow_overwrite and key in CRITICAL_FIELDS:
                setattr(opportunity, key, value)
                changed.append((key, old, value))
            elif key in CRITICAL_FIELDS:
                conflicts.append(key)
    return changed, conflicts


def _evaluate(
    opportunity: Opportunity,
    raw: RawOpportunity,
    source: Source,
    fields: dict,
    *,
    now: datetime,
    extra_conflicts: int = 0,
) -> ProcessResult:
    settings = get_settings()
    conflicts = opportunity.conflict_count + extra_conflicts if opportunity.id else extra_conflicts

    dates_coherent = True
    if opportunity.event_start and opportunity.event_end:
        dates_coherent = ensure_utc(opportunity.event_end) >= ensure_utc(opportunity.event_start)
    if opportunity.registration_deadline and opportunity.event_end:
        delta = _diff_days(opportunity.registration_deadline, opportunity.event_end)
        if delta is not None and delta > 120:
            dates_coherent = False

    provenance_count = len(
        [v for v in _provenance_values(raw, fields).values() if v not in (None, "", [], {})]
    )
    signals = TrustSignals(
        source_authority=source.authority,
        confirmed=raw.confirmed,
        official_domain_match=_official_domain_match(raw, source),
        platform_of_record=source.kind == "devpost",
        has_official_url=bool(opportunity.official_url),
        has_registration_url=bool(opportunity.registration_url),
        has_event_dates=bool(opportunity.event_start),
        dates_coherent=dates_coherent,
        contradictions=conflicts,
        provenance_fields=provenance_count,
        last_checked_at=opportunity.last_checked_at,
        now=now,
    )
    confidence = compute_confidence(signals)
    opportunity.confidence_score = confidence.score
    opportunity.confidence_reasons = confidence.reasons

    verification_state = confidence.verification_state
    if conflicts > 0:
        verification_state = "conflict"
    elif opportunity.lifecycle in {"closed", "finished", "cancelled"}:
        verification_state = "closed"
    opportunity.verification_state = verification_state

    decision = publication_decision(
        verification_state=verification_state,
        confidence=opportunity.confidence_score,
        lifecycle=opportunity.lifecycle,
        official_url=opportunity.official_url,
        last_checked_at=opportunity.last_checked_at,
        contradictions=conflicts,
        has_actionable_date=_has_actionable_date(raw),
        thresholds={
            "min_confidence": settings.auto_publish_min_confidence,
            "max_age_days": settings.auto_publish_max_age_days,
        },
        now=now,
    )

    if opportunity.review_state in {"approved", "hidden"}:
        opportunity.published = opportunity.review_state == "approved"
        reason = "Revisión manual conservada"
    else:
        opportunity.published = decision.publish
        opportunity.review_state = decision.review_state
        opportunity.review_reason = decision.reason
        reason = decision.reason
        if decision.publish and opportunity.published_at is None:
            opportunity.published_at = now

    if verification_state == "verified":
        opportunity.last_verified_at = now

    value_weight = {
        "hackathons": 0.72,
        "formacion": 0.78,
        "eventos": 0.62,
        "startups": 0.72,
    }.get(opportunity.category, 0.55)
    opportunity.quality_score = baseline_quality(
        opportunity.confidence_score, value_weight, opportunity.lifecycle in {"open", "rolling"}
    )
    return ProcessResult(status="evaluated", published=opportunity.published, reason=reason)


def _create_opportunity(
    session: Session, source: Source, raw: RawOpportunity, fields: dict, now: datetime
) -> Opportunity:
    fields = dict(fields)
    fields["slug"] = _slug_for(session, fields["title"], fields["canonical_url"])
    fields["first_seen_at"] = now
    fields["review_state"] = "needs_review"
    opportunity = Opportunity(**fields)
    session.add(opportunity)
    session.flush()
    _upsert_source_link(session, opportunity, source, raw)
    _record_provenance(session, opportunity, source, raw, fields)
    session.add(
        OpportunityChange(
            opportunity_id=opportunity.id,
            field="created",
            old_value=None,
            new_value={"value": {"source": source.slug, "url": raw.official_url}},
            source_id=source.id,
            actor="system",
            reason="Primera detección",
        )
    )
    session.add(
        VerificationCheck(
            opportunity_id=opportunity.id,
            checked_at=now,
            outcome="confirmed" if raw.confirmed else "lead",
            evidence={
                "source": source.slug,
                "url": raw.official_url,
                "note": raw.confirmation_note,
                "excerpt": truncate(raw.raw_excerpt, 500),
            },
        )
    )
    return opportunity


def _process_record(
    session: Session, source: Source, raw: RawOpportunity, now: datetime
) -> ProcessResult:
    if not raw.title.strip() or not raw.official_url.strip():
        return ProcessResult("skipped", False, "Registro incompleto")
    fields = build_fields(raw, source, now)
    if fields["category"] not in {"hackathons", "eventos", "formacion", "startups"}:
        return ProcessResult("skipped", False, "Categoría no admitida")

    # Exact provenance match first: same source + external id.
    existing: Opportunity | None = None
    if raw.external_id:
        link = session.scalars(
            select(OpportunitySource).where(
                OpportunitySource.source_id == source.id,
                OpportunitySource.external_id == raw.external_id,
            )
        ).first()
        if link:
            existing = session.get(Opportunity, link.opportunity_id)

    dedup_score = 0.0
    dedup_reasons: list[dict] = []
    auto_merge = False
    needs_review = False
    matched: Opportunity | None = None
    if existing is None:
        matched, dedup_score, dedup_reasons, auto_merge, needs_review = _find_duplicates(
            session, raw, fields
        )
        # Only unambiguously identical records are merged automatically; ambiguous
        # matches become a new record plus a review pair.
        if auto_merge:
            existing = matched

    if existing is not None:
        allow_overwrite = source.id in {s.source_id for s in existing.sources}
        if not allow_overwrite:
            existing_authority = max([s.authority for s in existing.sources] or [0])
            allow_overwrite = source.authority >= existing_authority

        extra_conflicts = 0
        if not allow_overwrite and any(
            [
                _diff_days(existing.event_start, fields["event_start"]),
                _diff_days(existing.registration_deadline, fields["registration_deadline"]),
            ]
        ):
            difference = _diff_days(existing.event_start, fields["event_start"])
            if difference is not None and difference > 3:
                extra_conflicts += 1
            deadline_difference = _diff_days(
                existing.registration_deadline, fields["registration_deadline"]
            )
            if deadline_difference is not None and deadline_difference > 1:
                extra_conflicts += 1

        changed, conflicts = _apply_fields(existing, fields, allow_overwrite=allow_overwrite)
        if conflicts:
            extra_conflicts += len(set(conflicts))
        existing.conflict_count += extra_conflicts
        existing.last_checked_at = now
        existing.last_changed_at = now
        _record_changes(
            session,
            existing,
            changed,
            source=source,
            reason=f"Actualización desde {source.name}",
        )
        _upsert_source_link(session, existing, source, raw)
        _record_provenance(session, existing, source, raw, fields)
        session.add(
            VerificationCheck(
                opportunity_id=existing.id,
                checked_at=now,
                outcome="confirmed" if raw.confirmed else "lead",
                evidence={
                    "source": source.slug,
                    "url": raw.official_url,
                    "dedup_score": dedup_score,
                    "note": raw.confirmation_note,
                },
            )
        )
        result = _evaluate(existing, raw, source, fields, now=now)
        return ProcessResult("merged", existing.published, result.reason)

    opportunity = _create_opportunity(session, source, raw, fields, now)
    result = _evaluate(opportunity, raw, source, fields, now=now)
    if needs_review and dedup_score > 0:
        opportunity.published = False
        opportunity.review_state = "needs_review"
        opportunity.review_reason = (
            f"Posible duplicado (similitud {dedup_score:.2f}); pendiente de revisión."
        )
        if matched is not None:
            _ensure_duplicate_candidate(session, opportunity, matched, dedup_score, dedup_reasons)
    return ProcessResult("created", opportunity.published, result.reason)


def _ensure_duplicate_candidate(
    session: Session,
    left: Opportunity,
    right: Opportunity,
    score: float,
    reasons: list[dict],
) -> None:
    if left.id == right.id:
        return
    a, b = sorted([left.id, right.id], key=str)
    existing = session.scalars(
        select(DuplicateCandidate).where(
            DuplicateCandidate.left_id == a, DuplicateCandidate.right_id == b
        )
    ).first()
    if existing is None:
        session.add(
            DuplicateCandidate(
                left_id=a,
                right_id=b,
                score=score,
                reasons=reasons,
                status="open",
            )
        )


async def run_source(
    session: Session,
    source: Source,
    *,
    fetcher: Fetcher | None = None,
) -> IngestionRun:
    settings = get_settings()
    now = utcnow()
    run = IngestionRun(source_id=source.id, started_at=now, status="running")
    session.add(run)
    session.flush()
    started = time.monotonic()

    if not source.enabled:
        run.status = "skipped"
        run.summary = {"reason": "fuente deshabilitada"}
        run.finished_at = utcnow()
        session.commit()
        return run

    fetcher = fetcher or Fetcher(
        timeout_seconds=settings.http_timeout_seconds,
        user_agent=settings.http_user_agent,
        max_bytes=settings.http_max_bytes,
        min_interval_seconds=settings.ingest_min_interval_seconds,
    )
    stats = RunStats()
    try:
        adapter = get_adapter(source.kind)
        raws = await adapter.fetch(source, fetcher)
    except FetchError as exc:
        run.status = "error"
        run.errors = 1
        run.error_detail = f"{exc} ({exc.url})"
        run.finished_at = utcnow()
        run.duration_ms = int((time.monotonic() - started) * 1000)
        source.last_run_at = now
        source.last_status = "error"
        source.last_error = str(exc)[:800]
        source.consecutive_failures += 1
        if source.consecutive_failures >= 5 and source.enabled:
            source.enabled = False
            source.disabled_reason = (
                "Deshabilitada tras 5 fallos consecutivos. Revisa acceso, límites y condiciones."
            )
        session.commit()
        logger.warning("source %s failed: %s", source.slug, exc)
        return run
    except Exception as exc:  # noqa: BLE001 - one bad adapter must not stop the pipeline
        run.status = "error"
        run.errors = 1
        run.error_detail = f"Error inesperado: {exc}"
        run.finished_at = utcnow()
        run.duration_ms = int((time.monotonic() - started) * 1000)
        source.last_run_at = now
        source.last_status = "error"
        source.last_error = str(exc)[:800]
        source.consecutive_failures += 1
        session.commit()
        logger.exception("source %s crashed", source.slug)
        return run

    stats.found = len(raws)
    for raw in raws:
        try:
            with session.begin_nested():
                result = _process_record(session, source, raw, now)
            if result.status == "created":
                stats.created += 1
            elif result.status == "created_review":
                stats.created += 1
                stats.review += 1
            elif result.status == "merged":
                stats.duplicated += 1
                stats.updated += 1
            elif result.status == "updated":
                stats.updated += 1
            else:
                stats.skipped += 1
            if result.published:
                stats.published += 1
            else:
                stats.review += 1
        except Exception as exc:  # noqa: BLE001 - isolate a single bad record
            stats.errors += 1
            stats.messages.append(f"{raw.title[:80]}: {exc}")
            logger.exception("record failed: %s", raw.title)

    source.last_run_at = now
    source.last_status = "ok"
    source.last_error = None
    source.consecutive_failures = 0

    run.status = "ok"
    run.items_found = stats.found
    run.items_created = stats.created
    run.items_updated = stats.updated
    run.items_duplicated = stats.duplicated
    run.items_published = stats.published
    run.items_review = stats.review
    run.errors = stats.errors
    run.finished_at = utcnow()
    run.duration_ms = int((time.monotonic() - started) * 1000)
    run.summary = {
        "skipped": stats.skipped,
        "messages": stats.messages[:20],
        "request_count": fetcher.request_count,
        "source_kind": source.kind,
    }
    session.commit()
    logger.info(
        "source %s: found=%s created=%s updated=%s review=%s errors=%s",
        source.slug,
        stats.found,
        stats.created,
        stats.updated,
        stats.review,
        stats.errors,
    )
    return run


async def ingest_all(session: Session, *, slugs: list[str] | None = None) -> list[IngestionRun]:
    query = select(Source).where(Source.enabled.is_(True))
    if slugs:
        query = query.where(Source.slug.in_(slugs))
    sources = session.scalars(query.order_by(Source.slug)).all()
    fetcher = Fetcher(
        timeout_seconds=get_settings().http_timeout_seconds,
        user_agent=get_settings().http_user_agent,
        max_bytes=get_settings().http_max_bytes,
        min_interval_seconds=get_settings().ingest_min_interval_seconds,
    )
    runs = []
    for source in sources:
        runs.append(await run_source(session, source, fetcher=fetcher))
    return runs
