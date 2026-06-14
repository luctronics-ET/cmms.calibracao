"""Configuração do banco SQLite via SQLAlchemy 2.0."""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATA_DIR = Path(os.getenv("SISCALIB_DATA", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_URL = os.getenv("SISCALIB_DB_URL", f"sqlite:///{DATA_DIR / 'siscalib.db'}")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
