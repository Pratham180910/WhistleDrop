from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Base class for future SQLAlchemy models (Milestone 2)
Base = declarative_base()

# Lazy/cached engine and sessionmaker
_engine = None
_SessionLocal = None


def get_engine():
    """Initializes and returns the SQLAlchemy engine using DATABASE_URL."""
    global _engine
    if _engine is None:
        db_url = settings.sync_database_url
        if not db_url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not configured. "
                "Please configure DATABASE_URL in your .env file."
            )
        _engine = create_engine(
            db_url,
            pool_pre_ping=True,
        )
    return _engine


def get_sessionmaker():
    """Returns the session factory bound to the active engine."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session per request."""
    session_factory = get_sessionmaker()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
