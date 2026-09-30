"""Async engine + sessions for DATABASE_URL (sqlite+aiosqlite locally, postgresql+asyncpg in production)."""

from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from server.config import get_settings

_engine: AsyncEngine | None = None
_sessions: async_sessionmaker[AsyncSession] | None = None


def make_engine(url: str) -> AsyncEngine:
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite":
        return create_async_engine(url, pool_pre_ping=True)
    if parsed.database and parsed.database != ":memory:":
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    # timeout: wait for the single writer lock instead of failing under concurrent sessions
    engine = create_async_engine(url, connect_args={"timeout": 30})

    @event.listens_for(engine.sync_engine, "connect")
    def _pragmas(conn, _record):
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")  # off by default in SQLite
        cursor.execute("PRAGMA journal_mode=WAL")  # readers don't block the writer
        cursor.close()

    return engine


def sessions() -> async_sessionmaker[AsyncSession]:
    global _engine, _sessions
    if _sessions is None:
        _engine = make_engine(get_settings().database_url)
        _sessions = async_sessionmaker(_engine, expire_on_commit=False)
    return _sessions


def use_engine(engine: AsyncEngine) -> None:
    """Tests: point the app at another engine (e.g. in-memory SQLite)."""
    global _engine, _sessions
    _engine, _sessions = engine, async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    """FastAPI dependency: one session per request."""
    async with sessions()() as db:
        yield db
