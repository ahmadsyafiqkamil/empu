"""SQLite engine with WAL (API and worker are separate processes) and enforced foreign keys."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from empu import models  # noqa: F401  (registers the tables on SQLModel.metadata)
from empu.config import Settings, get_settings


def make_engine(db_url: str) -> Engine:
    is_sqlite = db_url.startswith("sqlite")
    if db_url.startswith("sqlite:///") and ":memory:" not in db_url:
        Path(db_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(db_url, connect_args={"check_same_thread": False} if is_sqlite else {})
    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _pragmas(dbapi_conn, _record) -> None:
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA busy_timeout=5000")
            cur.close()

    return engine


def init_db(engine: Engine, *, reset: bool = False) -> None:
    if reset:
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


@lru_cache
def get_engine_cached(db_url: str) -> Engine:
    return make_engine(db_url)


def get_engine(settings: Settings | None = None) -> Engine:
    s = settings or get_settings()
    eng = get_engine_cached(s.db_url)
    init_db(eng)
    return eng


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
