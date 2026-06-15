"""Endpoint público (sem login) — ficha resumida do instrumento p/ QR Code."""
from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Instrumento
from backend.servico import instrumento_publico_para_out
from backend.schemas import InstrumentoPublicoOut

router = APIRouter(prefix="/api/v1/publico", tags=["publico"])


@router.get("/instrumentos/{inst_id}", response_model=InstrumentoPublicoOut)
def ficha_publica(inst_id: int, db: Session = Depends(get_db)):
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    return instrumento_publico_para_out(inst, date.today())
