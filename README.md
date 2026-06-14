# SisCalib — Sistema de Gestão Metrológica (fatia fina)

App standalone para controle de calibração de instrumentos. FastAPI + SQLite + frontend vanilla.

## Rodar em desenvolvimento
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m uvicorn backend.main:app --reload --port 8080
```
Acesse http://localhost:8080

## Rodar via Docker
```bash
docker build -t siscalib:latest .
docker run -d --name siscalib --restart unless-stopped \
  -p 8080:8080 -v siscalib_data:/data siscalib:latest
```

## Importar o inventário
1. Abra **Importar** no menu.
2. Envie o CSV (ex.: `CMASM_Controle de Calibracao ... .csv`).
3. Revise o relatório dry-run (linhas válidas / avisos / erros).
4. Clique **Confirmar importação**.

## Cadastro metrológico
- Os domínios (famílias RBC/INMETRO, tipos, grandezas, unidades) são semeados no startup
  (`python -m backend.dominios`, idempotente).
- Use **Novo** no Inventário (ou **Editar** na ficha) para preencher: classificação, faixa,
  resolução/EMP, localização, estado operacional, anexos (foto/PDF) e o IGP (5 variáveis 1–3).
- O **IGP** (Índice Global de Prioridade) é calculado automaticamente: faixas 18–21 máxima,
  14–17 média, 11–13 baixa, 7–10 muito baixa.

## Backup
O estado todo está em `/data/siscalib.db` — basta copiar esse arquivo.

## Testes
```bash
.venv/bin/python -m pytest tests/ -q
```

## Fora desta fatia (próximas entregas da Fase 1)
Autenticação JWT, QR Code/etiquetas, upload de certificado PDF, gestão de
laboratórios, página pública por seção, export PDF. Ver
`docs/superpowers/specs/2026-06-14-siscalib-fatia-fina-design.md`.
