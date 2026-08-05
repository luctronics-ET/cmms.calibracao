# Guia de Deploy — SisCalib

## Render.com (produção — gratuito)

### Primeiro deploy
1. Acesse [render.com](https://render.com) → **New + → Web Service**
2. Conecte o GitHub → selecione `luctronics-ET/cmms.calibracao`
3. O Render detecta `render.yaml` automaticamente
4. Confirme:
   - Name: `siscalib-cmasm`
   - Runtime: Docker
   - Plan: Free
5. **Add Disk:**
   - Name: `siscalib-data`
   - Mount Path: `/data`
   - Size: 1 GB
6. **Environment Variable:** `SISCALIB_DATA` = `/data`
7. Clique **Create Web Service**

URL de produção: `https://siscalib-cmasm.onrender.com`

### Redeploy
Push para `main` → redeploy automático.

### Importar banco de produção
```bash
# Via Render Shell (Dashboard → Shell)
# Upload do siscalib.db local para /data/
```

---

## Docker (servidor próprio)

```bash
docker build -t siscalib:latest .
docker run -d --name siscalib --restart unless-stopped \
  -p 8080:8080 \
  -v siscalib_data:/data \
  siscalib:latest
```

### Backup
```bash
docker cp siscalib:/data/siscalib.db ./backup_$(date +%Y%m%d).db
docker cp siscalib:/data/uploads/ ./uploads_backup/
```

### Atualizar imagem
```bash
docker pull # ou rebuild
docker stop siscalib && docker rm siscalib
docker run -d ... # mesmo comando acima
```

---

## Desenvolvimento local

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.dominios
.venv/bin/python -m backend.seed_ata
.venv/bin/uvicorn backend.main:app --reload --port 8080
```

Acesse: http://localhost:8080

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SISCALIB_DATA` | `data/` | Diretório SQLite + uploads |
| `SISCALIB_DB_URL` | `sqlite:///data/siscalib.db` | Override da URL do banco |
