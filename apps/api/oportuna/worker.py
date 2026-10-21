"""Background worker: ingestion, periodic re-checks, alerts and digests."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from arq.connections import RedisSettings
from sqlalchemy import func, or_, select

from oportuna.config import get_settings
from oportuna.db.base import get_session_factory
from oportuna.db.models import (
    Alert,
    Opportunity,
    SavedOpportunity,
    Source,
    User,
    VerificationCheck,
)
from oportuna.domain.dates import deadline_label, effective_deadline, ensure_utc, utcnow
from oportuna.domain.normalize import registrable_domain
from oportuna.ingest.http import Fetcher, FetchError
from oportuna.ingest.pipeline import ingest_all, run_source

logger = logging.getLogger("oportuna.worker")
settings = get_settings()


async def ingest_source_job(ctx: dict, source_id: str) -> dict:
    session = get_session_factory()()
    try:
        source = session.get(Source, uuid.UUID(source_id))
        if source is None:
            return {"ok": False, "error": "fuente no encontrada"}
        run = await run_source(session, source)
        return {
            "ok": run.status == "ok",
            "source": source.slug,
            "found": run.items_found,
            "created": run.items_created,
            "review": run.items_review,
            "errors": run.errors,
        }
    finally:
        session.close()


async def ingest_all_job(ctx: dict) -> dict:
    session = get_session_factory()()
    try:
        runs = await ingest_all(session)
        return {
            "ok": True,
            "sources": len(runs),
            "created": sum(run.items_created for run in runs),
            "published": sum(run.items_published for run in runs),
            "errors": sum(run.errors for run in runs),
        }
    finally:
        session.close()


async def verify_due_job(ctx: dict) -> dict:
    """Re-check pages of opportunities with imminent deadlines.

    Reachability is recorded as evidence only. It never marks registration open.
    """
    session = get_session_factory()()
    checked = 0
    reachable = 0
    try:
        now = utcnow()
        effective = func.coalesce(Opportunity.registration_deadline, Opportunity.submission_deadline)
        rows = session.scalars(
            select(Opportunity)
            .where(
                Opportunity.published.is_(True),
                Opportunity.is_demo.is_(False),
                Opportunity.lifecycle.in_(["open", "rolling"]),
                effective.is_not(None),
                effective <= now + timedelta(days=7),
                or_(Opportunity.last_checked_at.is_(None), Opportunity.last_checked_at < now - timedelta(hours=6)),
            )
            .order_by(effective.asc())
            .limit(12)
        ).all()
        fetcher = Fetcher(
            timeout_seconds=settings.http_timeout_seconds,
            user_agent=settings.http_user_agent,
            max_bytes=settings.http_max_bytes,
            min_interval_seconds=settings.ingest_min_interval_seconds,
        )
        for opportunity in rows:
            url = opportunity.official_url
            outcome = "check_failed"
            status = None
            evidence: dict = {"url": url, "kind": "deadline_recheck"}
            try:
                result = await fetcher.fetch_text(
                    url,
                    allowed_domains=[registrable_domain(url)],
                    respect_robots=True,
                )
                outcome = "reachable"
                status = result.status
                reachable += 1
                evidence["content_type"] = result.content_type
            except FetchError as exc:
                outcome = "unreachable"
                status = exc.status
                evidence["error"] = str(exc)
            session.add(
                VerificationCheck(
                    opportunity_id=opportunity.id,
                    checked_at=now,
                    outcome=outcome,
                    http_status=status,
                    evidence=evidence,
                    notes="Comprobación de plazo; no confirma que la inscripción siga abierta.",
                )
            )
            opportunity.last_checked_at = now
            session.commit()
            checked += 1
        return {"ok": True, "checked": checked, "reachable": reachable}
    finally:
        session.close()


async def deadline_alerts_job(ctx: dict) -> dict:
    session = get_session_factory()()
    created = 0
    try:
        now = utcnow()
        effective = func.coalesce(Opportunity.registration_deadline, Opportunity.submission_deadline)
        rows = session.execute(
            select(SavedOpportunity, Opportunity)
            .join(Opportunity, Opportunity.id == SavedOpportunity.opportunity_id)
            .where(
                SavedOpportunity.state != "dismissed",
                Opportunity.lifecycle.in_(["open", "rolling"]),
                effective.is_not(None),
                effective >= now,
                effective <= now + timedelta(days=3),
            )
        ).all()
        for saved, opportunity in rows:
            exists = session.scalar(
                select(func.count())
                .select_from(Alert)
                .where(
                    Alert.user_id == saved.user_id,
                    Alert.opportunity_id == opportunity.id,
                    Alert.kind == "deadline_soon",
                    Alert.created_at >= now - timedelta(days=2),
                )
            )
            if exists:
                continue
            deadline = effective_deadline(
                opportunity.registration_deadline, opportunity.submission_deadline
            )
            session.add(
                Alert(
                    user_id=saved.user_id,
                    opportunity_id=opportunity.id,
                    kind="deadline_soon",
                    title=f"Cierra pronto: {opportunity.title}",
                    body=deadline_label(deadline),
                    payload={"slug": opportunity.slug, "deadline": ensure_utc(deadline).isoformat()},
                    scheduled_for=now,
                )
            )
            created += 1
        session.commit()
        return {"ok": True, "created": created}
    finally:
        session.close()


async def daily_digest_job(ctx: dict) -> dict:
    session = get_session_factory()()
    created = 0
    try:
        now = utcnow()
        start = now - timedelta(hours=24)
        new_count = session.scalar(
            select(func.count())
            .select_from(Opportunity)
            .where(
                Opportunity.published.is_(True),
                Opportunity.first_seen_at >= start,
            )
        ) or 0
        if new_count == 0:
            return {"ok": True, "created": 0, "new": 0}
        top = session.scalars(
            select(Opportunity)
            .where(Opportunity.published.is_(True))
            .order_by(Opportunity.quality_score.desc())
            .limit(3)
        ).all()
        body = " · ".join(item.title for item in top)
        users = session.scalars(
            select(User).where(User.deleted_at.is_(None), User.role != "admin")
        ).all()
        for user in users:
            exists = session.scalar(
                select(func.count())
                .select_from(Alert)
                .where(
                    Alert.user_id == user.id,
                    Alert.kind == "digest",
                    Alert.created_at >= now - timedelta(hours=20),
                )
            )
            if exists:
                continue
            session.add(
                Alert(
                    user_id=user.id,
                    kind="digest",
                    title=f"{new_count} oportunidades nuevas en las últimas 24 h",
                    body=body,
                    payload={"count": new_count},
                    scheduled_for=now,
                )
            )
            created += 1
        session.commit()
        return {"ok": True, "created": created, "new": new_count}
    finally:
        session.close()


class WorkerSettings:
    functions = [ingest_source_job, ingest_all_job, verify_due_job, deadline_alerts_job, daily_digest_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 4
    job_timeout = 900
    keep_result = 3600
    max_tries = 2
    health_check_interval = 30
