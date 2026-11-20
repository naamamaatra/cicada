"""
Database connection, engine configuration, and session management.
Supports SQLite (development) and PostgreSQL (production).
"""

import os
from pathlib import Path
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from backend.db.base import Base

# Load environment variables if .env exists
load_dotenv()

# Determine database URL from environment or fallback to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./storage/sentinelops.db")

# Ensure storage directory exists if using local SQLite file
if DATABASE_URL.startswith("sqlite"):
    # Strip sqlite:/// to get file path
    db_path_str = DATABASE_URL.replace("sqlite:///", "")
    if db_path_str and not db_path_str.startswith(":memory:"):
        db_path = Path(db_path_str).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)

# Engine connection arguments
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False


# Create SQLAlchemy Engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)


# Enforce SQLite foreign key constraints
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Ensure SQLite enforces foreign key constraints like PostgreSQL.
    """
    if "sqlite" in str(dbapi_connection.__class__).lower():
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency or context generator for database sessions.
    Ensures safe commit/rollback and cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine: Engine = engine) -> None:
    """
    Initialize and create all database tables defined in Base metadata.
    """
    Base.metadata.create_all(bind=target_engine)


# Auto-initialize default tables on load for zero-config startup & tests
try:
    init_db(engine)
except Exception:
    pass

