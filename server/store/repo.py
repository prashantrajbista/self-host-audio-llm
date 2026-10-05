"""Every query the app makes. Functions reading or changing user data take the user id and filter by it:
this is the access control (there is no row-level security), so keep new queries here and scoped."""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from server.notify import notify
from server.store.models import ContactMessage, Cv, InterviewSession, Payment, Profile


class NoCredits(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite hands datetimes back without tzinfo; everything stored is UTC."""
    return dt.replace(tzinfo=UTC) if dt and dt.tzinfo is None else dt


async def profile(db: AsyncSession, uid: str) -> Profile:
    """The user's profile, created (with the free credits) on first use."""
    if found := await db.get(Profile, uid):
        return found
    db.add(Profile(user_id=uid))
    try:
        await db.commit()
        notify(f"New user signed up ({uid}).")
    except IntegrityError:  # created concurrently by another request
        await db.rollback()
    return await db.get(Profile, uid, populate_existing=True)


async def set_attribution(db: AsyncSession, uid: str, attribution: dict) -> None:
    """First touch wins: later calls (other devices, cleared storage) don't overwrite it."""
    p = await profile(db, uid)
    if p.attribution is None:
        p.attribution = attribution
        await db.commit()


def has_pass(p: Profile) -> bool:
    return bool(p.pass_until and _aware(p.pass_until) > _now())


async def list_cvs(db: AsyncSession, uid: str) -> list[Cv]:
    return list(await db.scalars(
        select(Cv).where(Cv.user_id == uid, Cv.deleted_at.is_(None)).order_by(Cv.created_at.desc())
    ))


async def get_cv(db: AsyncSession, uid: str, cv_id: uuid.UUID) -> Cv | None:
    return await db.scalar(select(Cv).where(Cv.id == cv_id, Cv.user_id == uid, Cv.deleted_at.is_(None)))


async def add_cv(db: AsyncSession, uid: str, **fields) -> Cv:
    cv = Cv(user_id=uid, **fields)
    db.add(cv)
    await db.commit()
    return cv


async def delete_cv(db: AsyncSession, uid: str, cv_id: uuid.UUID) -> bool:
    """Soft delete: hidden from the user and from new interviews; row and stored file are kept."""
    done = await db.execute(
        update(Cv).where(Cv.id == cv_id, Cv.user_id == uid, Cv.deleted_at.is_(None)).values(deleted_at=_now())
    )
    await db.commit()
    return done.rowcount == 1


async def delete_session(db: AsyncSession, uid: str, session_id: uuid.UUID) -> bool:
    """Soft delete: hidden from the user's history; row, report and recording are kept."""
    done = await db.execute(
        update(InterviewSession)
        .where(InterviewSession.id == session_id, InterviewSession.user_id == uid, InterviewSession.deleted_at.is_(None))
        .values(deleted_at=_now())
    )
    await db.commit()
    return done.rowcount == 1


async def create_session(db: AsyncSession, uid: str, **fields) -> InterviewSession:
    """Checks the user can pay but doesn't charge: `charge` does, when the interview goes live."""
    p = await profile(db, uid)
    if p.credits <= 0 and not has_pass(p):
        raise NoCredits
    if fields.get("cv_id") and not await get_cv(db, uid, fields["cv_id"]):
        raise ValueError("unknown CV")
    row = InterviewSession(user_id=uid, **fields)
    db.add(row)
    await db.commit()
    return row


async def get_session(db: AsyncSession, uid: str, session_id: uuid.UUID) -> InterviewSession | None:
    return await db.scalar(select(InterviewSession).where(
        InterviewSession.id == session_id, InterviewSession.user_id == uid, InterviewSession.deleted_at.is_(None)
    ))


async def list_sessions(db: AsyncSession, uid: str, limit: int = 50) -> list[InterviewSession]:
    return list(await db.scalars(
        select(InterviewSession)
        .where(InterviewSession.user_id == uid, InterviewSession.status != "created", InterviewSession.deleted_at.is_(None))
        .order_by(InterviewSession.created_at.desc())
        .limit(limit)
    ))


async def set_plan(db: AsyncSession, uid: str, session_id: uuid.UUID, plan: list) -> None:
    await db.execute(
        update(InterviewSession)
        .where(InterviewSession.id == session_id, InterviewSession.user_id == uid, InterviewSession.status == "created")
        .values(plan=plan)
    )
    await db.commit()


async def charge(db: AsyncSession, uid: str, session_id: uuid.UUID) -> bool:
    """Start the interview and pay for it, atomically: the session must still be 'created' (so it's paid
    once), then a credit is taken unless a pass is active. False = not startable or can't pay."""
    now = _now()
    started = await db.execute(
        update(InterviewSession)
        .where(InterviewSession.id == session_id, InterviewSession.user_id == uid, InterviewSession.status == "created")
        .values(status="live", started_at=now)
    )
    if started.rowcount != 1:
        await db.rollback()
        return False
    p = await db.get(Profile, uid)  # exists: create_session made it
    if p is None:
        await db.rollback()
        return False
    if not has_pass(p):
        paid = await db.execute(
            update(Profile).where(Profile.user_id == uid, Profile.credits > 0).values(credits=Profile.credits - 1)
        )
        if paid.rowcount != 1:
            await db.rollback()
            return False
        await db.execute(update(InterviewSession).where(InterviewSession.id == session_id).values(charged=True))
    await db.commit()
    return True


async def refund(db: AsyncSession, session_id: uuid.UUID) -> None:
    """Give back the credit of a failed or empty interview; at most once."""
    uid = await db.scalar(
        select(InterviewSession.user_id).where(InterviewSession.id == session_id, InterviewSession.charged.is_(True))
    )
    if uid is None:
        return
    undone = await db.execute(
        update(InterviewSession)
        .where(InterviewSession.id == session_id, InterviewSession.charged.is_(True))
        .values(charged=False)
    )
    if undone.rowcount == 1:
        await db.execute(update(Profile).where(Profile.user_id == uid).values(credits=Profile.credits + 1))
    await db.commit()


async def share_session(db: AsyncSession, uid: str, session_id: uuid.UUID, fields: dict) -> str | None:
    """Publish a scored session's card with these choices; returns its slug (reused while shared)."""
    row = await get_session(db, uid, session_id)
    if not row or row.status != "scored":
        return None
    row.share_slug = row.share_slug or secrets.token_urlsafe(9)  # 12 chars, unguessable
    row.share_fields = fields
    row.is_public = True
    await db.commit()
    return row.share_slug


async def unshare_session(db: AsyncSession, uid: str, session_id: uuid.UUID) -> bool:
    """Unpublish and drop the slug: an old link stays dead even if the card is shared again later."""
    done = await db.execute(
        update(InterviewSession)
        .where(InterviewSession.id == session_id, InterviewSession.user_id == uid, InterviewSession.deleted_at.is_(None))
        .values(is_public=False, share_slug=None)
    )
    await db.commit()
    return done.rowcount == 1


async def get_shared(db: AsyncSession, slug: str) -> InterviewSession | None:
    """Public lookup (no user): only published, scored, not deleted."""
    return await db.scalar(select(InterviewSession).where(
        InterviewSession.share_slug == slug,
        InterviewSession.is_public.is_(True),
        InterviewSession.status == "scored",
        InterviewSession.deleted_at.is_(None),
    ))


async def grant(
    db: AsyncSession, uid: str, *, product: str, credits: int = 0, pass_days: int = 0, event_id: str, session_id: str,
    amount_total: int | None = None, currency: str | None = None, provider: str = "stripe",
) -> bool:
    """Record a purchase and give what it bought, in one transaction. False = this event or checkout was
    already processed (nothing granted twice)."""
    await profile(db, uid)  # buyer may not have used the app since signing up
    db.add(Payment(
        user_id=uid, provider=provider, event_id=event_id, session_id=session_id, product=product, amount_total=amount_total, currency=currency,
    ))
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return False
    p = await db.get(Profile, uid)
    p.credits += credits
    if pass_days:
        # stack on any pass time left
        p.pass_until = max(_now(), _aware(p.pass_until) or _now()) + timedelta(days=pass_days)
    await db.commit()
    return True


async def add_contact_message(db: AsyncSession, **fields) -> None:
    db.add(ContactMessage(**fields))
    await db.commit()


async def update_session(db: AsyncSession, session_id: uuid.UUID, **fields) -> None:
    """Gateway-internal writes (transcript, status, report) for a session it is already running."""
    await db.execute(update(InterviewSession).where(InterviewSession.id == session_id).values(**fields))
    await db.commit()
