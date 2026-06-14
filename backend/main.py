"""App FastAPI do SisCalib."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.routers import instrumentos, importacao, dashboard, dominios, exportacao, calibracoes

app = FastAPI(title="SisCalib", version="0.2.0")
app.include_router(instrumentos.router)
app.include_router(importacao.router)
app.include_router(dashboard.router)
app.include_router(dominios.router)
app.include_router(exportacao.router)
app.include_router(calibracoes.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


DATA = Path(__file__).resolve().parent.parent / "data"
UPLOADS = DATA / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS)), name="uploads")

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
