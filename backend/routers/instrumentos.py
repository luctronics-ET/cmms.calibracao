"""Endpoints de inventário."""
from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Instrumento
from backend.servico import instrumento_para_out
from backend.schemas import ListaInstrumentos, InstrumentoOut

router = APIRouter(prefix="/api/v1", tags=["instrumentos"])


@router.get("/instrumentos", response_model=ListaInstrumentos)
def listar(
    db: Session = Depends(get_db),
    busca: str | None = Query(None),
    disciplina: str | None = Query(None),
    sistema: str | None = Query(None),
    status: str | None = Query(None),
):
    hoje = date.today()
    itens = [instrumento_para_out(i, hoje) for i in db.query(Instrumento).all()]

    if busca:
        b = busca.lower()
        itens = [i for i in itens if b in " ".join(
            filter(None, [i.codigo_interno, i.serial, i.equipamento, i.modelo])).lower()]
    if disciplina:
        itens = [i for i in itens if i.disciplina == disciplina.upper()]
    if sistema:
        itens = [i for i in itens if (i.sistema or "") == sistema]
    if status:
        itens = [i for i in itens if i.status == status.upper()]

    itens.sort(key=lambda i: (i.codigo_interno or "").lower())
    return ListaInstrumentos(total=len(itens), itens=itens)


@router.get("/instrumentos/{inst_id}", response_model=InstrumentoOut)
def obter(inst_id: int, db: Session = Depends(get_db)):
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    return instrumento_para_out(inst, date.today())
