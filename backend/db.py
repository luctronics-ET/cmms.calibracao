"""Configuração do banco via SQLAlchemy 2.0.
Suporta SQLite (dev local) e PostgreSQL (produção Supabase).
"""
import os
from pathlib import Path
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# PostgreSQL (Supabase) em produção, SQLite em desenvolvimento
DB_URL = os.getenv("SISCALIB_DB_URL")

if not DB_URL:
    # Fallback SQLite local
    DATA_DIR = Path(os.getenv("SISCALIB_DATA", "data"))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_URL = f"sqlite:///{DATA_DIR / 'siscalib.db'}"

IS_SQLITE = DB_URL.startswith("sqlite")

if IS_SQLITE:
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    # PostgreSQL — pool padrão, sem check_same_thread
    engine = create_engine(
        DB_URL,
        pool_pre_ping=True,        # detecta conexões mortas
        pool_size=5,
        max_overflow=10,
        connect_args={"connect_timeout": 10},
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
