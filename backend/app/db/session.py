from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()


def _prepare_sqlite_path(url: str) -> None:
    # sqlite+aiosqlite:///./.ledgerlens/ledgerlens.db → make sure the folder exists
    if url.startswith("sqlite") and ":memory:" not in url:
        raw = url.split("///", 1)[-1]
        Path(raw).expanduser().parent.mkdir(parents=True, exist_ok=True)


_prepare_sqlite_path(settings.database_url)

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)

if not settings.is_postgres:

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - trivial
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
