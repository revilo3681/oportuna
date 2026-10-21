"""Scheduler process.

It enqueues jobs on a wall-clock cadence. The worker has no cron jobs of its own,
so scheduling lives here and can be scaled independently.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from arq import create_pool
from arq.connections import RedisSettings

from oportuna.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("oportuna.scheduler")


async def main() -> None:
    settings = get_settings()
    if not settings.scheduler_enabled:
        logger.info("scheduler disabled by configuration")
        return

    pool = None
    last_ingest: datetime | None = None
    last_verify: datetime | None = None
    last_alerts: datetime | None = None
    last_digest: datetime | None = None

    while True:
        now = datetime.now(UTC)
        try:
            if pool is None:
                pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
                logger.info("connected to redis queue")

            if last_ingest is None or now - last_ingest >= timedelta(
                minutes=settings.ingest_interval_minutes
            ):
                await pool.enqueue_job("ingest_all_job")
                last_ingest = now
                logger.info("enqueued ingest_all_job")

            if last_verify is None or now - last_verify >= timedelta(
                minutes=settings.verify_interval_minutes
            ):
                await pool.enqueue_job("verify_due_job")
                last_verify = now
                logger.info("enqueued verify_due_job")

            if last_alerts is None or now - last_alerts >= timedelta(hours=6):
                await pool.enqueue_job("deadline_alerts_job")
                last_alerts = now

            if now.hour == settings.digest_hour_utc and (
                last_digest is None or now.date() != last_digest.date()
            ):
                await pool.enqueue_job("daily_digest_job")
                last_digest = now
                logger.info("enqueued daily_digest_job")

        except Exception as exc:  # noqa: BLE001 - keep the scheduler alive
            logger.warning("scheduler loop error: %s", exc)
            if pool is not None:
                try:
                    await pool.aclose()
                except Exception:  # noqa: BLE001
                    pass
            pool = None
            await asyncio.sleep(15)
            continue

        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
