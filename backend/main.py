"""App FastAPI do SisCalib."""
from fastapi import FastAPI
from backend.routers import instrumentos

app = FastAPI(title="SisCalib", version="0.1.0")
app.include_router(instrumentos.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
