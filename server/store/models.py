"""Database schema. Portable types only (SQLite locally, Postgres in production); change via Alembic:
edit here, then `uv run alembic revision --autogenerate -m "..."` and review the generated migration."""

import uuid
from datetime import UTC, date, datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

JSON = sa.JSON().with_variant(JSONB(), "postgresql")
FREE_CREDITS = 2
SESSION_STATUSES = ("created", "live", "scoring", "scored", "failed", "abandoned")


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class SoftDelete:
    """Rows are never removed: deleting sets deleted_at, and every query in repo.py filters it out.
    Stored files stay too (see repo.delete_cv)."""

    deleted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(sa.String(64), primary_key=True)  # the auth provider's user id
    credits: Mapped[int] = mapped_column(default=FREE_CREDITS)
    pass_until: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    # first-touch marketing source (landing page, referrer, utm_*), set once from the browser after sign-in
    attribution: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_now)

    __table_args__ = (sa.CheckConstraint("credits >= 0", name="credits_non_negative"),)


class Cv(SoftDelete, Base):
    __tablename__ = "cvs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(sa.String(64), index=True)
    file_name: Mapped[str] = mapped_column(sa.String(255))
    storage_key: Mapped[str | None] = mapped_column(sa.String(512))  # original file; None for pasted text
    raw_text: Mapped[str] = mapped_column(sa.Text)  # anonymized (server.agent.anonymize) for uploads since Oct 2026
    cv_profile: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_now)


class InterviewSession(SoftDelete, Base):
    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(sa.String(64))
    pack_id: Mapped[str] = mapped_column(sa.String(64))
    role: Mapped[str] = mapped_column(sa.String(80))
    seniority: Mapped[str] = mapped_column(sa.String(16))
    interview_type: Mapped[str] = mapped_column(sa.String(16))
    cv_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("cvs.id", ondelete="SET NULL"))
    jd_text: Mapped[str | None] = mapped_column(sa.Text)
    elements: Mapped[dict | None] = mapped_column(JSON)  # Civil Service: chosen behaviours, strengths, experience
    interview_date: Mapped[date | None] = mapped_column(sa.Date)  # the candidate's real interview, when given
    plan: Mapped[list | None] = mapped_column(JSON)  # questions, set by the prepare step
    status: Mapped[str] = mapped_column(sa.String(16), default="created")
    charged: Mapped[bool] = mapped_column(default=False)  # a credit was taken (refunded on failure)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    record: Mapped[dict | None] = mapped_column(JSON)  # timed turns + question boundaries
    report: Mapped[dict | None] = mapped_column(JSON)  # scoring output
    overall_score: Mapped[int | None]
    verdict: Mapped[str | None] = mapped_column(sa.String(32))
    recording_key: Mapped[str | None] = mapped_column(sa.String(512))
    recording_status: Mapped[str | None] = mapped_column(sa.String(16))  # processing | ready | failed (voice disguise)
    share_slug: Mapped[str | None] = mapped_column(sa.String(32), unique=True)
    share_fields: Mapped[dict | None] = mapped_column(JSON)
    is_public: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_now)

    __table_args__ = (
        sa.CheckConstraint(f"status in {SESSION_STATUSES}", name="valid_status"),
        sa.Index("ix_sessions_user_created", "user_id", "created_at"),
    )


class Payment(Base):
    """One completed purchase. The unique ids make grants idempotent: Stripe retries webhooks, and a
    delayed payment method can report the same checkout twice (completed, then async_payment_succeeded)."""

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(sa.String(64), index=True)
    provider: Mapped[str] = mapped_column(sa.String(16), default="stripe")
    event_id: Mapped[str] = mapped_column(sa.String(255), unique=True)
    session_id: Mapped[str] = mapped_column(sa.String(255), unique=True)  # the checkout; one grant per checkout
    product: Mapped[str] = mapped_column(sa.String(32))
    amount_total: Mapped[int | None]  # smallest currency unit, e.g. cents
    currency: Mapped[str | None] = mapped_column(sa.String(8))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_now)


class ContactMessage(Base):
    """Messages from the contact form. Read them straight from the database (no inbox yet)."""

    __tablename__ = "contact_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String(100))
    email: Mapped[str] = mapped_column(sa.String(254))
    topic: Mapped[str] = mapped_column(sa.String(32))
    message: Mapped[str] = mapped_column(sa.Text)
    user_id: Mapped[str | None] = mapped_column(sa.String(64), index=True)  # set when sent while signed in
    handled: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_now, index=True)
