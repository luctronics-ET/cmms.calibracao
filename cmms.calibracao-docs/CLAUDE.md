# CLAUDE.md — cmms.calibracao

Guidance para Claude Code ao trabalhar neste repositório.

## O que é

**SisCalib** — Sistema de Gestão Metrológica do CMASM-132 / Marinha do Brasil.  
FastAPI + SQLAlchemy/Alembic + SQLite + frontend HTML/JS vanilla, num único container Docker.  
Idioma do projeto: **português** (código, commits, docs, UI).

## Arquitetura

```
browser (HTML/JS vanilla)
    └── FastAPI (uvicorn :8080)
            ├── backend/routers/     ← endpoints REST
            ├── backend/models.py    ← SQLAlchemy ORM
            ├── backend/schemas.py   ← Pydantic I/O
            ├── backend/db.py        ← SQLite em $SISCALIB_DATA/siscalib.db
            └── alembic/             ← migrations versionadas
frontend/                            ← servido como static via FastAPI
data/                                ← volume persistente (db + uploads)
```

## Como rodar localmente

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.dominios   # semeia domínios (idempotente)
.venv/bin/python -m backend.seed_ata   # semeia ATA 129/2025
.venv/bin/uvicorn backend.main:app --reload --port 8080
```

## Docker

```bash
docker build -t siscalibracao:latest .
docker run -d -p 8080:8080 -v siscalibracao_data:/data siscalibracao:latest
```

## Deploy (Render.com)

- Arquivo: `render.yaml` na raiz
- Disco persistente: `/data` (1GB)
- Variável de ambiente: `SISCALIB_DATA=/data`
- URL: `https://siscalib-cmasm.onrender.com`

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SISCALIB_DATA` | `data/` | Diretório para SQLite e uploads |
| `SISCALIB_DB_URL` | `sqlite:///data/siscalib.db` | URL completa do banco (override) |

## Banco de dados

- SQLite em `$SISCALIB_DATA/siscalib.db`
- Migrations via Alembic — sempre rodar `alembic upgrade head` antes de usar
- Backup: copiar `siscalib.db` e `uploads/`
- Schema documentado em `docs/schema.md`

## Convenções

- Migrations: criar via `alembic revision --autogenerate -m "descrição"`
- Routers: um arquivo por domínio em `backend/routers/`
- Nunca commitar `data/siscalib.db` (está no `.gitignore`)
- Testes: `python -m pytest -q`

## Documentação

- `PRD-SisCalib.md` — requisitos e status por fase
- `TODO.md` — pendências priorizadas
- `docs/schema.md` — schema detalhado das tabelas
- `docs/deploy.md` — guia de deploy (Render, Docker, local)
- `docs/manual-usuario.md` — manual do usuário
