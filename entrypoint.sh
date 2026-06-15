#!/bin/sh
set -e
alembic upgrade head
python -m backend.dominios
python -m backend.backfill
python -m backend.seed_ata
exec uvicorn backend.main:app --host 0.0.0.0 --port 8080
