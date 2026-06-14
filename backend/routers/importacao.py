"""Endpoints de importação do CSV legado."""
from __future__ import annotations
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.importacao import processar_csv
from backend.models import Instrumento, Disciplina
from backend.schemas import PreviewResposta, CommitResposta

router = APIRouter(prefix="/api/v1/importacao", tags=["importacao"])


@router.post("/preview", response_model=PreviewResposta)
async def preview(arquivo: UploadFile = File(...)):
    conteudo = await arquivo.read()
    return processar_csv(conteudo)


@router.post("/commit", response_model=CommitResposta)
async def commit(arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    conteudo = await arquivo.read()
    resultado = processar_csv(conteudo)
    inseridos = ignorados = 0
    for linha in resultado["linhas"]:
        if any(p["severidade"] == "erro" for p in linha["problemas"]):
            ignorados += 1
            continue
        d = dict(linha["dados"])
        disc = d.get("disciplina")
        d["disciplina"] = Disciplina(disc) if disc in ("ELE", "MEC") else None
        db.add(Instrumento(**{k: v for k, v in d.items()
                              if k in Instrumento.__table__.columns.keys()}))
        inseridos += 1
    db.commit()
    return CommitResposta(inseridos=inseridos, ignorados=ignorados)
