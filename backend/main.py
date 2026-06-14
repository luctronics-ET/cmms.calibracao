"""App FastAPI do SisCalib."""
from fastapi import FastAPI
from backend.routers import instrumentos, importacao

app = FastAPI(title="SisCalib", version="0.1.0")
app.include_router(instrumentos.router)
app.include_router(importacao.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
