"""App FastAPI do SisCalib."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.routers import instrumentos, importacao, dashboard, dominios, exportacao, calibracoes, laboratorios, contratos, catalogo, publico

app = FastAPI(title="sisCalibracao", version="0.2.0")
app.include_router(instrumentos.router)
app.include_router(importacao.router)
app.include_router(dashboard.router)
app.include_router(dominios.router)
app.include_router(exportacao.router)
app.include_router(calibracoes.router)
app.include_router(laboratorios.router)
app.include_router(contratos.router)
app.include_router(catalogo.router)
app.include_router(publico.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.middleware("http")
async def _no_cache_estaticos(request, call_next):
    """Força revalidação dos estáticos (HTML/JS/CSS) — evita o browser servir
    versão velha após deploy. no-cache mantém ETag/304 (revalida, não re-baixa)."""
    resp = await call_next(request)
    p = request.url.path
    if not p.startswith("/api/") and (p == "/" or p.endswith((".html", ".js", ".css"))):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


DATA = Path(__file__).resolve().parent.parent / "data"
UPLOADS = DATA / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS)), name="uploads")

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
