"""App FastAPI do SisCalib."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.routers import instrumentos, importacao, dashboard

app = FastAPI(title="SisCalib", version="0.1.0")
app.include_router(instrumentos.router)
app.include_router(importacao.router)
app.include_router(dashboard.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
