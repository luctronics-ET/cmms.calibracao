# Guia de Deploy — SisCalib

## Render.com (recomendado — gratuito)

### Primeiro deploy
1. Acesse [render.com](https://render.com) e faça login
2. Clique em **"New +"** → **"Web Service"**
3. Conecte o GitHub → selecione **`luctronics-ET/cmms.calibracao`**
4. O Render detecta o `render.yaml` automaticamente
5. Confirme as configurações:
   - **Name:** `siscalib-cmasm`
   - **Runtime:** Docker
   - **Plan:** Free
6. Adicione o disco persistente:
   - **Name:** `siscalib-data`
   - **Mount Path:** `/data`
   - **Size:** `1 GB`
7. Adicione a variável de ambiente:
   - `SISCALIB_DATA` = `/data`
8. Clique **"Create Web Service"**

Build leva ~3 minutos. URL: `https://siscalib-cmasm.onrender.com`

> **Nota:** No free tier o Render hiberna após 15min sem uso. O primeiro acesso após hibernação demora ~30s.

### Redeploy
Push para `main` no GitHub dispara redeploy automático.

---

## Docker local

```bash
docker build -t siscalibracao:latest .
docker run -d --name siscalibracao --restart unless-stopped \
  -p 8080:8080 \
  -v siscalibracao_data:/data \
  siscalibracao:latest
```

Acesse: http://localhost:8080

### Parar / remover
```bash
docker stop siscalibracao
docker rm siscalibracao
```

### Backup do banco
```bash
docker cp siscalibracao:/data/siscalib.db ./backup_$(date +%Y%m%d).db
```

---

## Desenvolvimento local

```bash
# Setup
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Banco
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.dominios   # domínios metrológicos
.venv/bin/python -m backend.seed_ata   # ATA 129/2025 (lab + contrato + itens)

# Servidor com hot-reload
.venv/bin/uvicorn backend.main:app --reload --port 8080
```

---

## Importar inventário de produção

Após o deploy, para carregar os instrumentos reais:

1. Acesse o app → menu **Importar**
2. Envie o arquivo CSV do inventário
3. Revise o relatório dry-run
4. Clique **Confirmar importação**

Ou via upload direto do banco SQLite:
```bash
# Render: via shell do dashboard ou scp
# Docker: docker cp siscalib.db siscalibracao:/data/siscalib.db
```
