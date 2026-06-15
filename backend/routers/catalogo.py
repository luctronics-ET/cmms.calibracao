"""Endpoints do catálogo de preços de calibração."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import CatalogoPreco, TipoInstrumento, ItemContrato
from backend.servico import catalogo_para_out
from backend.schemas import CatalogoPrecoIn, CatalogoPrecoOut, ListaCatalogo

router = APIRouter(prefix="/api/v1", tags=["catalogo"])


def _get_cat(db: Session, cat_id: int) -> CatalogoPreco:
    cat = db.get(CatalogoPreco, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Item de catálogo não encontrado")
    return cat


def _validar_fks(db: Session, dados: CatalogoPrecoIn) -> None:
    if not db.get(TipoInstrumento, dados.tipo_id):
        raise HTTPException(status_code=404, detail="Tipo de instrumento não encontrado")
    if dados.item_contrato_id is not None and not db.get(ItemContrato, dados.item_contrato_id):
        raise HTTPException(status_code=404, detail="Item de contrato não encontrado")


def _aplicar(cat: CatalogoPreco, dados: CatalogoPrecoIn) -> None:
    for campo, valor in dados.model_dump().items():
        setattr(cat, campo, valor)


@router.get("/catalogo", response_model=ListaCatalogo)
def listar(db: Session = Depends(get_db), tipo_id: int | None = Query(None)):
    q = db.query(CatalogoPreco)
    if tipo_id is not None:
        q = q.filter(CatalogoPreco.tipo_id == tipo_id)
    cats = q.order_by(CatalogoPreco.id).all()
    itens = [catalogo_para_out(c) for c in cats]
    return ListaCatalogo(total=len(itens), itens=itens)


@router.get("/catalogo/{cat_id}", response_model=CatalogoPrecoOut)
def obter(cat_id: int, db: Session = Depends(get_db)):
    return catalogo_para_out(_get_cat(db, cat_id))


@router.post("/catalogo", response_model=CatalogoPrecoOut, status_code=201)
def criar(dados: CatalogoPrecoIn, db: Session = Depends(get_db)):
    _validar_fks(db, dados)
    cat = CatalogoPreco()
    _aplicar(cat, dados)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return catalogo_para_out(cat)


@router.put("/catalogo/{cat_id}", response_model=CatalogoPrecoOut)
def editar(cat_id: int, dados: CatalogoPrecoIn, db: Session = Depends(get_db)):
    cat = _get_cat(db, cat_id)
    _validar_fks(db, dados)
    _aplicar(cat, dados)
    db.commit()
    db.refresh(cat)
    return catalogo_para_out(cat)


@router.delete("/catalogo/{cat_id}", status_code=204)
def remover(cat_id: int, db: Session = Depends(get_db)):
    db.delete(_get_cat(db, cat_id))
    db.commit()
