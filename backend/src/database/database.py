"""
Database connection and initialization for the Agentic Learning Platform.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
import os
from pathlib import Path

# Database path - relative to backend directory
DB_PATH = Path(__file__).parent.parent.parent / "learning.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=False  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized at: {DB_PATH}")


def get_db():
    """
    Dependency for getting DB session.
    Use in FastAPI with Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_db():
    """Reset database - WARNING: Deletes all data!"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database reset complete")
