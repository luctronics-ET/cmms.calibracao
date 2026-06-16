# sisCalibracao — Sistema de Gestão Metrológica

App standalone para controle de calibração de instrumentos de medição (CMASM-132).
FastAPI + SQLAlchemy/Alembic + SQLite + frontend HTML/JS vanilla, em 1 container Docker.

## Rodar em desenvolvimento
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.dominios   # semeia domínios (idempotente)
.venv/bin/python -m backend.seed_ata   # semeia ATA 129/2025 (lab + contrato + itens)
.venv/bin/python -m uvicorn backend.main:app --reload --port 8080
```
Acesse http://localhost:8080

## Rodar via Docker
```bash
docker build -t siscalibracao:latest .
docker run -d --name siscalibracao --restart unless-stopped \
  -p 8080:8080 -v siscalibracao_data:/data siscalibracao:latest
```
O `entrypoint.sh` roda `alembic upgrade head` + seeds + uvicorn.

## Funcionalidades
- **Inventário** (~500 instrumentos): busca, filtro por coluna, ordenação, edição em
  massa, exportação (PDF/XLS/CSV), etiquetas QR.
- **Cadastro metrológico**: famílias RBC/INMETRO, tipos, grandezas, unidades; faixa,
  resolução/EMP, localização (Setor); IGP (Índice Global de Prioridade, 5 fatores 1–3).
- **Calibrações**: histórico por instrumento, validade/status derivados da última
  calibração, upload de certificado PDF, vínculo opcional a item de contrato vigente
  (consome saldo, herda preço/laboratório).
- **Laboratórios**: cadastro, acreditação RBC/CGCRE, alerta de vencimento.
- **Contratos/ATAs**: fornecedor = laboratório (FK); itens com saldo; visão Vigentes /
  Finalizados (vencido ou esgotado).
- **Catálogo**: visão derivada dos itens de contrato (preço, saldo, vigência por lab).
- **Alertas** in-app: vencidos / a vencer; acreditações e contratos a vencer.
- **Páginas públicas** (sem login): ficha do instrumento por QR e painel por setor.
- **Tema** claro/escuro e sidebar retrátil.

## Importar o inventário
1. Abra **Importar** no menu.
2. Envie o CSV do inventário.
3. Revise o relatório dry-run (linhas válidas / avisos / erros).
4. Clique **Confirmar importação**.

## Backup
Todo o estado está em `/data/siscalib.db` — basta copiar esse arquivo
(uploads em `/data/uploads/`).

## Testes
```bash
.venv/bin/python -m pytest -q
```

## Documentação
- `PRD-SisCalib.md` — requisitos e status por fase.
- `TODO.md` — pendências priorizadas.
- `docs/superpowers/` — specs e planos por feature.
