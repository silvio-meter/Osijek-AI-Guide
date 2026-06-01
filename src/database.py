"""
Database configuration for Osijek AI Guide (Lega)

Using SQLAlchemy + SQLite for development.
Easy to migrate to PostgreSQL later.
"""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Compute absolute path to data/lega.db relative to this file
# This makes the DB location reliable no matter where uvicorn / scripts are started from.
BASE_DIR = Path(__file__).resolve().parent.parent  # project root
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "lega.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine
# connect_args needed for SQLite to allow multiple threads (FastAPI)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency for FastAPI routes.
    Provides a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Call this on startup or via CLI."""
    # Import all models here so they are registered with Base.
    # We import inside the function to avoid circular imports at module load time.
    from models.user import User  # noqa: F401
    from models.refresh_token import RefreshToken  # noqa: F401
    from models.point_of_interest import PointOfInterest  # noqa: F401
    from models.event import Event  # noqa: F401

    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialized at: {DB_PATH}")