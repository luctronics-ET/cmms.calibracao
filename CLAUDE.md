# CLAUDE.md — cmms.calibracao

Guidance para Claude Code ao trabalhar neste repositório.  
Idioma do projeto: **português** (código, commits, docs, UI).

## O que é

**SisCalib** — Sistema de Gestão Metrológica do CMASM-132 / Marinha do Brasil.  
FastAPI + SQLAlchemy/Alembic + SQLite + HTML/JS vanilla, num único container Docker.

## Arquitetura

```
browser (HTML/JS vanilla — frontend/)
    └── FastAPI :8080  (backend/)
            ├── routers/         ← endpoints REST por domínio
            ├── models.py        ← SQLAlchemy ORM
            ├── schemas.py       ← Pydantic I/O
            ├── servico.py       ← lógica de negócio (IGP, alertas, status)
            ├── calibracao.py    ← cálculo de validade e status de calibração
            └── db.py            ← SQLite em $SISCALIB_DATA/siscalib.db
alembic/                         ← migrations versionadas
tests/                           ← pytest
data/                            ← volume persistente (db + uploads) — não commitar
```

## Domínios e routers

| Router | Prefixo | Responsabilidade |
|---|---|---|
| instrumentos | `/api/v1/instrumentos` | CRUD + filtros + exportação + etiquetas |
| calibracoes | `/api/v1/calibracoes` | histórico, upload PDF, vínculo contrato |
| laboratorios | `/api/v1/laboratorios` | CRUD + alertas de acreditação |
| contratos | `/api/v1/contratos` | contratos/ATAs + itens + saldo |
| catalogo | `/api/v1/catalogo` | visão derivada de itens vigentes |
| dashboard | `/api/v1/dashboard` | KPIs e alertas para index.html |
| dominios | `/api/v1/dominios` | listas de grandezas, unidades, famílias |
| importacao | `/api/v1/importacao` | upload CSV dry-run + confirmação |
| exportacao | `/api/v1/exportacao` | PDF, XLS, CSV |
| publico | `/publico` | ficha por QR e painel por setor (sem auth) |

## Frontend

- `app.js` — SDK HTTP, tema dark/light, shell (sidebar + nav), helpers
- `siscalib.css` — CSS vars govbr, design system dark/light
- Cada página HTML é autocontida: carrega `app.js`, chama `montarShell()`, faz fetch à API
- Não há build step — HTML/JS/CSS servidos como static via FastAPI

## Rodar localmente

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.dominios
.venv/bin/python -m backend.seed_ata
.venv/bin/uvicorn backend.main:app --reload --port 8080
```

## Banco de dados

- Arquivo: `$SISCALIB_DATA/siscalib.db` (default: `data/siscalib.db`)
- Nova migration: `alembic revision --autogenerate -m "descrição"`
- Aplicar: `alembic upgrade head`
- Backup: copiar `siscalib.db` + pasta `uploads/`
- Nunca commitar `data/siscalib.db` (`.gitignore`)

## Deploy

- **Render.com:** push → redeploy automático via `render.yaml`
- **Docker:** `docker build + run -v siscalib_data:/data`
- Disco persistente em `/data` — essencial para o SQLite sobreviver a redeploys

## Convenções

- Commits em português, formato: `tipo(escopo): descrição`
- Testes: `pytest -q` — cobrir routers e lógica de negócio
- Não criar cópias `.bak` nem versionar `data/`
- Schema documentado em `docs/schema.md` — atualizar a cada migration
