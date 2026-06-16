"""Catálogo de calibração = visão derivada dos itens de contrato.

Read-only: cada linha é um item (serviço de calibração) de um contrato,
com preço, saldo e vigência, agrupável por laboratório. A fonte é o contrato;
não há cadastro paralelo.
"""
from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import ItemContrato, Contrato
from backend.servico import catalogo_item_para_out
from backend.schemas import ListaCatalogoItens

router = APIRouter(prefix="/api/v1", tags=["catalogo"])


@router.get("/catalogo", response_model=ListaCatalogoItens)
def listar(laboratorio_id: int | None = Query(None),
           apenas_vigentes: bool = Query(False),
           db: Session = Depends(get_db)):
    hoje = date.today()
    q = db.query(ItemContrato).join(Contrato)
    if laboratorio_id is not None:
        q = q.filter(Contrato.laboratorio_id == laboratorio_id)
    q = q.order_by(Contrato.numero, ItemContrato.numero)
    rows = [catalogo_item_para_out(i, hoje) for i in q.all()]
    if apenas_vigentes:
        rows = [r for r in rows if r.vigente]
    return ListaCatalogoItens(total=len(rows), itens=rows)
