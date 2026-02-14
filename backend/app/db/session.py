"""Database session management."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Create engine - handle SQLite specially for check_same_thread
connect_args = {}
pool_config = {}

if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # SQLite doesn't support connection pooling the same way
    pool_config = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,  # Recycle connections every 30 minutes
    }
else:
    # PostgreSQL/MySQL connection pooling configuration
    pool_config = {
        "pool_size": 20,          # Number of connections to keep open
        "max_overflow": 40,       # Additional connections allowed beyond pool_size
        "pool_pre_ping": True,    # Test connections before using them
        "pool_recycle": 3600,     # Recycle connections after 1 hour
    }

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.debug,
    **pool_config,
)

# Enable foreign key enforcement for SQLite
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Type alias for dependency injection
DbSession = Annotated[Session, Depends(get_db)]
