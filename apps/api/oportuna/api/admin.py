"""Admin API: supervision, review queue, corrections, duplicates and metrics."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from oportuna.api.deps import require_admin
from oportuna.api.schemas import (
    IngestIn,
    OpportunityPatchIn,
    ResolveDuplicateIn,
    ReviewNoteIn,
    SourceIn,
    SourcePatchIn,
)
from oportuna.api.serializers import (
    iso,
    opportunity_card,
    opportunity_detail,
    provenance_rows,
    source_dict,
)
from oportuna.config import get_settings
from oportuna.db.base import get_db
from oportuna.db.models import (
    DuplicateCandidate,
    FieldProvenance,
    IngestionRun,
    Opportunity,
    OpportunityChange,
    OpportunitySource,
    SavedOpportunity,
    Source,
    User,
    VerificationCheck,
)
from oportuna.domain.dates import derive_lifecycle, ensure_utc, utcnow
from oportuna.domain.normalize import normalize_text
from oportuna.domain.taxonomy import CATEGORIES, country_name

router = APIRouter(prefix="/admin", tags=["admin"])


def _audit_value(value):
    if isinstance(value, datetime):
        return ensure_utc(value).isoformat()
    if isinstance(value, dict):
        return {key: _audit_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_audit_value(item) for item in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


@router.get("/stats")
def admin_stats(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    now = utcnow()
    settings = get_settings()

    def opp_count(*conditions) -> int:
        return db.scalar(select(func.count()).select_from(Opportunity).where(*conditions)) or 0

    total = opp_count()
    published = opp_count(Opportunity.published.is_(True))
    review = opp_count(Opportunity.review_state == "needs_review")
    conflicts = opp_count(Opportunity.verification_state == "conflict")
    stale = opp_count(
        Opportunity.published.is_(True),
        Opportunity.last_checked_at.is_not(None),
        Opportunity.last_checked_at < now - timedelta(days=settings.auto_publish_max_age_days),
    )
    duplicates = db.scalar(
        select(func.count()).select_from(DuplicateCandidate).where(DuplicateCandidate.status == "open")
    ) or 0
    sources_total = db.scalar(select(func.count()).select_from(Source)) or 0
    sources_enabled = db.scalar(
        select(func.count()).select_from(Source).where(Source.enabled.is_(True))
    ) or 0
    sources_failing = db.scalar(
        select(func.count()).select_from(Source).where(Source.consecutive_failures > 0)
    ) or 0

    since = now - timedelta(hours=24)
    run_rows = db.execute(
        select(
            func.coalesce(func.sum(IngestionRun.items_found), 0),
            func.coalesce(func.sum(IngestionRun.items_created), 0),
            func.coalesce(func.sum(IngestionRun.items_updated), 0),
            func.coalesce(func.sum(IngestionRun.items_published), 0),
            func.coalesce(func.sum(IngestionRun.items_review), 0),
            func.coalesce(func.sum(IngestionRun.errors), 0),
            func.coalesce(func.sum(IngestionRun.cost_usd), 0.0),
            func.count(IngestionRun.id),
        ).where(IngestionRun.started_at >= since)
    ).one()

    by_category = db.execute(
        select(Opportunity.category, func.count())
        .where(Opportunity.published.is_(True))
        .group_by(Opportunity.category)
    ).all()
    by_country = db.execute(
        select(Opportunity.country, func.count())
        .where(Opportunity.published.is_(True), Opportunity.country.is_not(None))
        .group_by(Opportunity.country)
        .order_by(func.count().desc())
        .limit(15)
    ).all()
    by_language = db.execute(
        select(Opportunity.language, func.count())
        .where(Opportunity.published.is_(True), Opportunity.language.is_not(None))
        .group_by(Opportunity.language)
    ).all()
    by_region = db.execute(
        select(Source.region, func.count(OpportunitySource.id))
        .join(OpportunitySource, OpportunitySource.source_id == Source.id)
        .join(Opportunity, Opportunity.id == OpportunitySource.opportunity_id)
        .where(Opportunity.published.is_(True))
        .group_by(Source.region)
    ).all()

    runs = db.scalars(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(12)).all()
    source_names = {
        source.id: source.name
        for source in db.scalars(select(Source)).all()
    }

    last_checked = db.scalar(select(func.max(Opportunity.last_checked_at)))
    avg_confidence = db.scalar(
        select(func.avg(Opportunity.confidence_score)).where(Opportunity.published.is_(True))
    )
    freshness_hours = None
    if last_checked:
        freshness_hours = round((now - ensure_utc(last_checked)).total_seconds() / 3600, 1)

    return {
        "totals": {
            "opportunities": total,
            "published": published,
            "review_queue": review,
            "conflicts": conflicts,
            "stale_published": stale,
            "open_duplicates": duplicates,
            "sources": sources_total,
            "sources_enabled": sources_enabled,
            "sources_failing": sources_failing,
            "avg_confidence": round(float(avg_confidence or 0), 3),
            "freshness_hours": freshness_hours,
            "last_checked_at": iso(last_checked),
        },
        "ingestion_24h": {
            "found": int(run_rows[0] or 0),
            "created": int(run_rows[1] or 0),
            "updated": int(run_rows[2] or 0),
            "published": int(run_rows[3] or 0),
            "review": int(run_rows[4] or 0),
            "errors": int(run_rows[5] or 0),
            "cost_usd": float(run_rows[6] or 0),
            "runs": int(run_rows[7] or 0),
        },
        "coverage": {
            "category": [
                {"key": key, "label": CATEGORIES.get(key, {}).get("label", key), "count": count}
                for key, count in by_category
            ],
            "country": [
                {"code": code, "label": country_name(code) or code, "count": count}
                for code, count in by_country
            ],
            "language": [{"key": key or "unknown", "count": count} for key, count in by_language],
            "region": [{"key": key or "unknown", "count": count} for key, count in by_region],
        },
        "recent_runs": [
            {
                "id": str(run.id),
                "source": source_names.get(run.source_id, "—"),
                "status": run.status,
                "started_at": iso(run.started_at),
                "finished_at": iso(run.finished_at),
                "items_found": run.items_found,
                "items_created": run.items_created,
                "items_updated": run.items_updated,
                "items_published": run.items_published,
                "items_review": run.items_review,
                "errors": run.errors,
                "duration_ms": run.duration_ms,
                "cost_usd": run.cost_usd,
                "error_detail": run.error_detail,
            }
            for run in runs
        ],
    }


@router.get("/sources")
def admin_sources(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    sources = db.scalars(select(Source).order_by(Source.name)).all()
    counts = dict(
        db.execute(
            select(OpportunitySource.source_id, func.count(OpportunitySource.opportunity_id))
            .join(Opportunity, Opportunity.id == OpportunitySource.opportunity_id)
            .group_by(OpportunitySource.source_id)
        ).all()
    )
    return {"sources": [source_dict(source, published=counts.get(source.id, 0)) for source in sources]}


@router.post("/sources")
def create_source(
    payload: SourceIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.scalars(select(Source).where(Source.slug == payload.slug)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe una fuente con ese slug")
    source = Source(**payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return {"source": source_dict(source)}


@router.patch("/sources/{source_id}")
def update_source(
    source_id: uuid.UUID,
    payload: SourcePatchIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    data = payload.model_dump(exclude_unset=True)
    if data.get("enabled") is True:
        source.consecutive_failures = 0
        source.disabled_reason = None
        source.last_error = None
    for key, value in data.items():
        setattr(source, key, value)
    db.commit()
    db.refresh(source)
    return {"source": source_dict(source)}


@router.post("/sources/{source_id}/run")
async def run_source_now(
    source_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    job_id = await _enqueue("ingest_source_job", str(source.id))
    return {"queued": True, "job_id": job_id, "source": source.slug}


@router.post("/ingest")
async def ingest_now(
    payload: IngestIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(Source).where(Source.enabled.is_(True))
    if payload.slugs:
        query = query.where(Source.slug.in_(payload.slugs))
    sources = db.scalars(query).all()
    jobs = []
    for source in sources:
        jobs.append({"slug": source.slug, "job_id": await _enqueue("ingest_source_job", str(source.id))})
    return {"queued": len(jobs), "jobs": jobs}


async def _enqueue(function_name: str, *args) -> str | None:
    settings = get_settings()
    try:
        pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        try:
            job = await pool.enqueue_job(function_name, *args)
        finally:
            await pool.aclose()
        return job.job_id if job else None
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=(
                "La cola de trabajos no está disponible (Redis). "
                f"Detalle: {type(exc).__name__}."
            ),
        ) from exc


@router.get("/review")
def review_queue(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    rows = db.scalars(
        select(Opportunity)
        .where(Opportunity.review_state == "needs_review")
        .options(selectinload(Opportunity.sources).joinedload(OpportunitySource.source))
        .order_by(Opportunity.created_at.desc())
        .limit(limit)
    ).all()
    items = []
    for row in rows:
        card = opportunity_card(row)
        card["review_reason"] = row.review_reason
        card["conflict_count"] = row.conflict_count
        card["confidence_reasons"] = row.confidence_reasons
        items.append(card)
    return {"items": items, "total": len(items)}


@router.get("/opportunities")
def admin_opportunities(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    q: str = "",
    review_state: str | None = None,
    verification_state: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
):
    conditions = []
    if q:
        for token in normalize_text(q).split()[:5]:
            conditions.append(Opportunity.search_text.contains(token))
    if review_state:
        conditions.append(Opportunity.review_state == review_state)
    if verification_state:
        conditions.append(Opportunity.verification_state == verification_state)
    total = db.scalar(select(func.count()).select_from(Opportunity).where(*conditions)) or 0
    rows = db.scalars(
        select(Opportunity)
        .where(*conditions)
        .options(selectinload(Opportunity.sources).joinedload(OpportunitySource.source))
        .order_by(Opportunity.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [opportunity_card(row) for row in rows],
        "total": total,
        "page": page,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.get("/opportunities/{opportunity_id}")
def admin_opportunity(
    opportunity_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.scalars(
        select(Opportunity)
        .where(Opportunity.id == opportunity_id)
        .options(selectinload(Opportunity.sources).joinedload(OpportunitySource.source))
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")
    detail = opportunity_detail(db, row)
    detail["decisions"] = {
        "published": row.published,
        "review_state": row.review_state,
        "review_reason": row.review_reason,
        "verification_state": row.verification_state,
        "confidence": row.confidence_score,
        "conflict_count": row.conflict_count,
    }
    return detail


@router.post("/opportunities/{opportunity_id}/approve")
def approve_opportunity(
    opportunity_id: uuid.UUID,
    payload: ReviewNoteIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(Opportunity, opportunity_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")
    row.review_state = "approved"
    row.published = True
    row.published_at = row.published_at or utcnow()
    row.last_verified_at = utcnow()
    row.review_reason = payload.note or "Aprobado manualmente por administración"
    db.add(
        OpportunityChange(
            opportunity_id=row.id,
            field="review_state",
            old_value={"value": "needs_review"},
            new_value={"value": "approved"},
            source_id=None,
            actor="admin",
            reason=row.review_reason,
            created_at=utcnow(),
        )
    )
    db.commit()
    return {"ok": True, "published": True}


@router.post("/opportunities/{opportunity_id}/hide")
def hide_opportunity(
    opportunity_id: uuid.UUID,
    payload: ReviewNoteIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(Opportunity, opportunity_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")
    previous = row.review_state
    row.review_state = "hidden"
    row.published = False
    row.review_reason = payload.note or "Ocultado manualmente por administración"
    db.add(
        OpportunityChange(
            opportunity_id=row.id,
            field="review_state",
            old_value={"value": previous},
            new_value={"value": "hidden"},
            source_id=None,
            actor="admin",
            reason=row.review_reason,
            created_at=utcnow(),
        )
    )
    db.commit()
    return {"ok": True, "published": False}


@router.patch("/opportunities/{opportunity_id}")
def patch_opportunity(
    opportunity_id: uuid.UUID,
    payload: OpportunityPatchIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(Opportunity, opportunity_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        old = getattr(row, key)
        if old == value:
            continue
        setattr(row, key, value)
        db.add(
            OpportunityChange(
                opportunity_id=row.id,
                field=key,
                old_value={"value": _audit_value(old)},
                new_value={"value": _audit_value(value)},
                source_id=None,
                actor="admin",
                reason="Corrección manual",
                created_at=utcnow(),
            )
        )
    if "tech_tags" in data:
        row.tech_tags_text = "|" + "|".join(data["tech_tags"] or []) + "|" if data["tech_tags"] else ""
    if "lifecycle" not in data and (
        "event_start" in data or "event_end" in data or "registration_deadline" in data
    ):
        lifecycle, registration_state = derive_lifecycle(
            event_start=row.event_start,
            event_end=row.event_end,
            registration_deadline=row.registration_deadline,
            rolling=row.rolling,
        )
        row.lifecycle = lifecycle
        row.registration_state = registration_state
    row.search_text = normalize_text(
        " ".join(
            filter(
                None,
                [
                    row.title,
                    row.summary,
                    row.description,
                    row.organizer,
                    row.city,
                    row.country,
                    " ".join(row.tech_tags or []),
                    row.category,
                ],
            )
        )
    )
    row.last_changed_at = utcnow()
    db.commit()
    return {"ok": True}


@router.get("/duplicates")
def duplicate_queue(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    status: str = "open",
    limit: int = Query(default=50, ge=1, le=200),
):
    rows = db.scalars(
        select(DuplicateCandidate)
        .where(DuplicateCandidate.status == status)
        .order_by(DuplicateCandidate.score.desc())
        .limit(limit)
    ).all()
    left_ids = {row.left_id for row in rows} | {row.right_id for row in rows}
    opportunities = {
        row.id: row
        for row in db.scalars(select(Opportunity).where(Opportunity.id.in_(left_ids))).all()
    }
    items = []
    for row in rows:
        left = opportunities.get(row.left_id)
        right = opportunities.get(row.right_id)
        if not left or not right:
            continue
        items.append(
            {
                "id": str(row.id),
                "score": row.score,
                "reasons": row.reasons,
                "status": row.status,
                "created_at": iso(row.created_at),
                "left": {
                    "id": str(left.id),
                    "slug": left.slug,
                    "title": left.title,
                    "published": left.published,
                    "event_start": iso(left.event_start),
                    "organizer": left.organizer,
                    "official_url": left.official_url,
                    "source_count": len(left.sources),
                },
                "right": {
                    "id": str(right.id),
                    "slug": right.slug,
                    "title": right.title,
                    "published": right.published,
                    "event_start": iso(right.event_start),
                    "organizer": right.organizer,
                    "official_url": right.official_url,
                    "source_count": len(right.sources),
                },
            }
        )
    return {"items": items, "total": len(items)}


@router.post("/duplicates/{candidate_id}/resolve")
def resolve_duplicate(
    candidate_id: uuid.UUID,
    payload: ResolveDuplicateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    candidate = db.get(DuplicateCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    if candidate.status != "open":
        raise HTTPException(status_code=409, detail="Este par ya fue resuelto")
    if payload.action == "reject":
        candidate.status = "rejected"
        candidate.resolved_at = utcnow()
        candidate.resolved_by = admin.id
        candidate.note = payload.note
        db.commit()
        return {"ok": True, "action": "rejected"}

    left = db.get(Opportunity, candidate.left_id)
    right = db.get(Opportunity, candidate.right_id)
    if left is None or right is None:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")
    # Keep the richer record as canonical.
    if right.quality_score > left.quality_score:
        left, right = right, left

    for link in db.scalars(
        select(OpportunitySource).where(OpportunitySource.opportunity_id == right.id)
    ).all():
        duplicate = db.scalars(
            select(OpportunitySource).where(
                OpportunitySource.opportunity_id == left.id,
                OpportunitySource.source_id == link.source_id,
                OpportunitySource.source_url == link.source_url,
            )
        ).first()
        if duplicate:
            db.delete(link)
        else:
            link.opportunity_id = left.id
    for provenance in db.scalars(
        select(FieldProvenance).where(FieldProvenance.opportunity_id == right.id)
    ).all():
        provenance.opportunity_id = left.id
    for change in db.scalars(
        select(OpportunityChange).where(OpportunityChange.opportunity_id == right.id)
    ).all():
        change.opportunity_id = left.id
    for check in db.scalars(
        select(VerificationCheck).where(VerificationCheck.opportunity_id == right.id)
    ).all():
        check.opportunity_id = left.id
    for saved in db.scalars(
        select(SavedOpportunity).where(SavedOpportunity.opportunity_id == right.id)
    ).all():
        duplicate = db.scalars(
            select(SavedOpportunity).where(
                SavedOpportunity.user_id == saved.user_id,
                SavedOpportunity.opportunity_id == left.id,
            )
        ).first()
        if duplicate:
            db.delete(saved)
        else:
            saved.opportunity_id = left.id

    right.published = False
    right.review_state = "hidden"
    right.review_reason = f"Fusionada en {left.slug} (decisión manual)"
    left.conflict_count = 0
    for other in db.scalars(
        select(DuplicateCandidate).where(
            or_(
                DuplicateCandidate.left_id == right.id,
                DuplicateCandidate.right_id == right.id,
            ),
            DuplicateCandidate.id != candidate.id,
            DuplicateCandidate.status == "open",
        )
    ).all():
        other.status = "merged"
        other.resolved_at = utcnow()
        other.resolved_by = admin.id
        other.note = f"Fusionada en {left.slug}"

    candidate.status = "merged"
    candidate.resolved_at = utcnow()
    candidate.resolved_by = admin.id
    candidate.note = payload.note
    db.add(
        OpportunityChange(
            opportunity_id=left.id,
            field="duplicate_merge",
            old_value={"value": str(right.id)},
            new_value={"value": str(left.id)},
            source_id=None,
            actor="admin",
            reason=payload.note or "Duplicado fusionado manualmente",
            created_at=utcnow(),
        )
    )
    db.commit()
    return {"ok": True, "action": "merged", "canonical": left.slug, "hidden": right.slug}


@router.get("/runs")
def ingestion_runs(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    rows = db.scalars(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit)).all()
    names = {source.id: source.name for source in db.scalars(select(Source)).all()}
    return {
        "items": [
            {
                "id": str(run.id),
                "source": names.get(run.source_id, "—"),
                "status": run.status,
                "started_at": iso(run.started_at),
                "finished_at": iso(run.finished_at),
                "items_found": run.items_found,
                "items_created": run.items_created,
                "items_updated": run.items_updated,
                "items_duplicated": run.items_duplicated,
                "items_published": run.items_published,
                "items_review": run.items_review,
                "errors": run.errors,
                "cost_usd": run.cost_usd,
                "duration_ms": run.duration_ms,
                "summary": run.summary,
                "error_detail": run.error_detail,
            }
            for run in rows
        ]
    }


@router.get("/audit")
def audit_log(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    opportunity_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=300),
):
    query = select(OpportunityChange).order_by(OpportunityChange.created_at.desc()).limit(limit)
    if opportunity_id:
        query = query.where(OpportunityChange.opportunity_id == opportunity_id)
    rows = db.scalars(query).all()
    slugs = {
        row.id: row.slug
        for row in db.scalars(
            select(Opportunity).where(Opportunity.id.in_({r.opportunity_id for r in rows}))
        ).all()
    }
    return {
        "items": [
            {
                "id": str(row.id),
                "opportunity_id": str(row.opportunity_id),
                "slug": slugs.get(row.opportunity_id),
                "field": row.field,
                "old_value": (row.old_value or {}).get("value") if row.old_value else None,
                "new_value": (row.new_value or {}).get("value") if row.new_value else None,
                "actor": row.actor,
                "reason": row.reason,
                "created_at": iso(row.created_at),
            }
            for row in rows
        ]
    }


@router.get("/explain/{opportunity_id}")
def explain_opportunity(
    opportunity_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.scalars(
        select(Opportunity)
        .where(Opportunity.id == opportunity_id)
        .options(selectinload(Opportunity.sources).joinedload(OpportunitySource.source))
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")
    return {
        "opportunity": {
            "id": str(row.id),
            "slug": row.slug,
            "title": row.title,
            "published": row.published,
            "lifecycle": row.lifecycle,
            "verification_state": row.verification_state,
            "review_state": row.review_state,
            "review_reason": row.review_reason,
            "confidence": row.confidence_score,
            "confidence_reasons": row.confidence_reasons,
            "conflict_count": row.conflict_count,
            "quality_score": row.quality_score,
            "last_checked_at": iso(row.last_checked_at),
            "last_verified_at": iso(row.last_verified_at),
            "deadlines": {
                "registration": iso(row.registration_deadline),
                "submission": iso(row.submission_deadline),
                "event_start": iso(row.event_start),
                "event_end": iso(row.event_end),
            },
        },
        "provenance": provenance_rows(db, row),
        "rule": (
            "Publicada automáticamente porque supera los controles estrictos."
            if row.review_state == "published"
            else "No publicada automáticamente: revisa el motivo y las señales de confianza."
        ),
    }
