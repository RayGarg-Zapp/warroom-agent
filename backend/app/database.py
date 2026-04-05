"""
WarRoom Agent — database setup.

Uses a synchronous SQLAlchemy engine (suitable for the SQLite MVP).
Call ``init_db()`` at application startup to create all tables.
"""

from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # required for SQLite
    if settings.DATABASE_URL.startswith("sqlite")
    else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables defined on ``Base.metadata``.

    Import your model modules *before* calling this so that every table is
    registered on the metadata.
    """
    Base.metadata.create_all(bind=engine)
