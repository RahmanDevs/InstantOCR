import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Arahkan koneksi langsung ke file db.sqlite3 milik Django
ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "app" / "db.sqlite3"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Connect to engine via sqlalchemy with concurrency timeout
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30}
)

# Enable WAL mode for SQLite to support concurrent FastAPI & Django reads/writes
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

# Dependency injection for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
