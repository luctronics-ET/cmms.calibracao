# SisCalib — Sistema de Gestão Metrológica

**CMASM-132 · Marinha do Brasil**  
Controle de instrumentos de medição, calibrações, laboratórios e contratos/ATAs.

## Acesso

| Ambiente | URL |
|---|---|
| Produção (Render) | https://siscalib-cmasm.onrender.com |
| Local | http://localhost:8080 |

> **Free tier:** o Render hiberna após 15 min sem uso. O primeiro acesso pode demorar ~30s.

## Estrutura

```
cmms.calibracao/
├── backend/                  ← FastAPI + SQLAlchemy
│   ├── main.py               ← App, rotas, middleware
│   ├── models.py             ← ORM (instrumento, calibracao, laboratorio, contrato)
│   ├── schemas.py            ← Pydantic I/O
│   ├── db.py                 ← SQLite em $SISCALIB_DATA/siscalib.db
│   ├── routers/              ← Um arquivo por domínio
│   ├── servico.py            ← Lógica de negócio (status, IGP, alertas)
│   └── calibracao.py         ← Cálculo de validade e status
├── frontend/                 ← HTML/JS vanilla + CSS govbr
│   ├── app.js                ← SDK, tema, navegação, helpers
│   ├── siscalib.css          ← Design system (dark/light, tokens CSS)
│   ├── index.html            ← Dashboard de KPIs
│   ├── inventario.html       ← Lista + filtros + exportação + etiquetas QR
│   ├── cadastro.html         ← Cadastro e edição de instrumento
│   ├── calibracao.html       ← Histórico e registro de calibrações
│   ├── laboratorios.html     ← Gestão de laboratórios acreditados
│   ├── contratos.html        ← Contratos/ATAs + itens + saldo
│   ├── catalogo.html         ← Catálogo de preços por laboratório
│   ├── alertas.html          ← Vencidos, a vencer, acreditações
│   ├── importar.html         ← Upload CSV do inventário
│   ├── etiquetas.html        ← Geração de etiquetas QR
│   ├── ficha.html            ← Ficha pública do instrumento (via QR)
│   └── publica.html          ← Painel público por setor
├── alembic/                  ← Migrations do banco SQLite
├── tests/                    ← Pytest (API + lógica de negócio)
├── docs/                     ← Documentação
│   ├── SisCalib-Manual-Usuario.docx
│   ├── schema.md
│   └── deploy.md
├── Dockerfile                ← Imagem Docker (python:3.12-slim)
├── render.yaml               ← Deploy no Render.com
├── entrypoint.sh             ← alembic + seeds + uvicorn
└── requirements.txt
```

## Rodar localmente

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.dominios   # domínios metrológicos (idempotente)
.venv/bin/python -m backend.seed_ata   # ATA 129/2025 (lab + contrato + itens)
.venv/bin/uvicorn backend.main:app --reload --port 8080
```

## Docker

```bash
docker build -t siscalib:latest .
docker run -d -p 8080:8080 -v siscalib_data:/data siscalib:latest
```

## Deploy (Render.com)

Push para `main` → redeploy automático via `render.yaml`.  
Primeiro deploy: ver `docs/deploy.md`.

## Importar inventário

1. Menu → **Importar**
2. Envie CSV com colunas: `tag,descricao,fabricante,modelo,n_serie,patrimonio,setor,familia,tipo,grandeza,unidade,faixa_min,faixa_max,resolucao`
3. Revise o dry-run → **Confirmar importação**

## Testes

```bash
.venv/bin/python -m pytest -q
```

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SISCALIB_DATA` | `data/` | Diretório do SQLite e uploads |
| `SISCALIB_DB_URL` | `sqlite:///data/siscalib.db` | URL completa do banco |

## Documentação

- `docs/SisCalib-Manual-Usuario.docx` — manual do usuário (10 capítulos)
- `docs/schema.md` — schema detalhado das tabelas
- `docs/deploy.md` — guia de deploy
- `PRD-SisCalib.md` — requisitos e status por fase
- `TODO.md` — pendências priorizadas
