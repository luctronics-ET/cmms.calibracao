"""Backfill de calibrações de origem — roda no startup (após dominios)."""
from __future__ import annotations
from backend.db import SessionLocal
from backend.servico import backfill_calibracoes_origem


def main() -> None:
    db = SessionLocal()
    try:
        n = backfill_calibracoes_origem(db)
        print(f"backfill_calibracoes: {n} calibração(ões) de origem criada(s)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
