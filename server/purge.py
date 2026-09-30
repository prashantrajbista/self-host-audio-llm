"""Permanent removal, as the privacy policy promises (client/lib/site.ts RETENTION_DAYS):
- CVs and interviews soft-deleted more than RETENTION_DAYS ago: rows and stored files removed
- recordings of interviews older than RETENTION_DAYS: file removed, the interview (transcript, report) kept

Run daily, e.g. cron: 0 3 * * *  cd /app && uv run python -m server.purge
Idempotent: a file that fails to delete keeps its row, so the next run retries it."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from server.config import get_settings
from server.storage import BlobStore, get_storage
from server.store.db import sessions
from server.store.models import Cv, InterviewSession

logger = logging.getLogger(__name__)

RETENTION_DAYS = 30


async def _remove_file(store: BlobStore, key: str | None) -> bool:
    if not key:
        return True
    try:
        await store.delete(key)
        return True
    except Exception:
        logger.exception("could not delete %s; will retry next run", key)
        return False


async def purge(db: AsyncSession, store: BlobStore, now: datetime | None = None) -> dict:
    cutoff = (now or datetime.now(UTC)) - timedelta(days=RETENTION_DAYS)
    counts = {"sessions": 0, "cvs": 0, "recordings": 0}

    for row in await db.scalars(select(InterviewSession).where(InterviewSession.deleted_at < cutoff)):
        if await _remove_file(store, row.recording_key):
            await db.execute(delete(InterviewSession).where(InterviewSession.id == row.id))
            counts["sessions"] += 1

    for cv in await db.scalars(select(Cv).where(Cv.deleted_at < cutoff)):
        if await _remove_file(store, cv.storage_key):
            await db.execute(delete(Cv).where(Cv.id == cv.id))  # sessions keep their row; cv_id becomes NULL
            counts["cvs"] += 1

    old = select(InterviewSession).where(InterviewSession.recording_key.is_not(None), InterviewSession.created_at < cutoff)
    for row in await db.scalars(old):
        if await _remove_file(store, row.recording_key):
            await db.execute(update(InterviewSession).where(InterviewSession.id == row.id).values(recording_key=None))
            counts["recordings"] += 1

    await db.commit()
    return counts


async def main() -> None:
    async with sessions()() as db:
        counts = await purge(db, get_storage(get_settings()))
    print(f"purged: {counts}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
