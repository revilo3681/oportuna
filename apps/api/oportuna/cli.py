"""Operational CLI for seeding, manual ingestion and diagnostics."""

from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import func, select

from oportuna.db.base import Base, get_engine, get_session_factory
from oportuna.db.models import IngestionRun, Opportunity, Source, User
from oportuna.ingest.pipeline import ingest_all
from oportuna.security import hash_password
from oportuna.seed import seed_all


def _session():
    return get_session_factory()()


def cmd_init(args) -> None:
    Base.metadata.create_all(bind=get_engine())
    session = _session()
    try:
        print(json.dumps(seed_all(session), ensure_ascii=False, indent=2))
    finally:
        session.close()


async def _ingest(slugs: list[str] | None) -> None:
    session = _session()
    try:
        runs = await ingest_all(session, slugs=slugs)
        print(
            json.dumps(
                [
                    {
                        "source": str(run.source_id),
                        "status": run.status,
                        "found": run.items_found,
                        "created": run.items_created,
                        "updated": run.items_updated,
                        "published": run.items_published,
                        "review": run.items_review,
                        "errors": run.errors,
                        "duration_ms": run.duration_ms,
                        "error_detail": run.error_detail,
                    }
                    for run in runs
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        session.close()


def cmd_ingest(args) -> None:
    asyncio.run(_ingest(args.slug or None))


def cmd_stats(args) -> None:
    session = _session()
    try:
        published = session.scalar(
            select(func.count()).select_from(Opportunity).where(Opportunity.published.is_(True))
        )
        review = session.scalar(
            select(func.count()).select_from(Opportunity).where(Opportunity.review_state == "needs_review")
        )
        total = session.scalar(select(func.count()).select_from(Opportunity))
        sources = session.scalar(select(func.count()).select_from(Source))
        runs = session.scalar(select(func.count()).select_from(IngestionRun))
        print(
            json.dumps(
                {
                    "opportunities": total,
                    "published": published,
                    "review": review,
                    "sources": sources,
                    "runs": runs,
                },
                indent=2,
            )
        )
    finally:
        session.close()


def cmd_create_admin(args) -> None:
    session = _session()
    try:
        existing = session.scalars(select(User).where(User.email == args.email.lower())).first()
        if existing:
            existing.role = "admin"
            session.commit()
            print(f"admin role ensured for {existing.email}")
            return
        user = User(
            email=args.email.lower(),
            password_hash=hash_password(args.password),
            display_name=args.name or "Administración",
            role="admin",
        )
        session.add(user)
        session.commit()
        print(f"admin created: {user.email}")
    finally:
        session.close()


def cmd_sources(args) -> None:
    session = _session()
    try:
        for source in session.scalars(select(Source).order_by(Source.slug)).all():
            print(
                f"{source.slug:34} {source.kind:8} enabled={source.enabled!s:5} "
                f"authority={source.authority} last={source.last_status or '-'}"
            )
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Oportuna CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create tables and seed sources (development only)")
    init.set_defaults(func=cmd_init)

    ingest = sub.add_parser("ingest", help="run ingestion now")
    ingest.add_argument("--slug", action="append", help="limit to a source slug (repeatable)")
    ingest.set_defaults(func=cmd_ingest)

    stats = sub.add_parser("stats", help="show catalog counts")
    stats.set_defaults(func=cmd_stats)

    create_admin = sub.add_parser("create-admin", help="create or promote an admin user")
    create_admin.add_argument("--email", required=True)
    create_admin.add_argument("--password", required=True)
    create_admin.add_argument("--name", default=None)
    create_admin.set_defaults(func=cmd_create_admin)

    sources = sub.add_parser("sources", help="list sources")
    sources.set_defaults(func=cmd_sources)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
