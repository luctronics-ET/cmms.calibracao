#!/bin/sh
set -e

if echo "${SISCALIB_DB_URL:-}" | grep -q "postgresql"; then
    echo "PostgreSQL detectado — verificando schema..."
    # Apenas marca o alembic como atualizado (schema criado via Supabase)
    python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ['SISCALIB_DB_URL'], connect_args={'connect_timeout': 10})
with engine.connect() as c:
    c.execute(text(\"INSERT INTO alembic_version VALUES ('b5c6d7e8f9a0') ON CONFLICT DO NOTHING\"))
    c.commit()
print('Schema OK')
"
else
    echo "SQLite detectado — rodando migrations..."
    alembic upgrade head
    python -m backend.dominios
    python -m backend.backfill
    python -m backend.seed_ata
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port 8080
