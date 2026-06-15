"""Endpoints de contratos e itens (saldo da ATA)."""
from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Contrato, ItemContrato, ContratoTipo
from backend.servico import contrato_para_out
from backend.calibracao import StatusCalibracao
from backend.schemas import ContratoIn, ContratoOut, ListaContratos, ItemContratoIn

router = APIRouter(prefix="/api/v1", tags=["contratos"])

_URGENCIA = {
    StatusCalibracao.VENCIDO.value: 0,
    StatusCalibracao.A_VENCER_7.value: 1,
    StatusCalibracao.A_VENCER_30.value: 2,
    StatusCalibracao.A_VENCER_60.value: 3,
}


def _get_contrato(db: Session, cid: int) -> Contrato:
    c = db.get(Contrato, cid)
    if not c:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    return c


def _aplicar_contrato(c: Contrato, dados: ContratoIn) -> None:
    payload = dados.model_dump()
    payload["tipo"] = ContratoTipo(payload["tipo"])
    for campo, valor in payload.items():
        setattr(c, campo, valor)


def _aplicar_item(item: ItemContrato, dados: ItemContratoIn) -> None:
    for campo, valor in dados.model_dump().items():
        setattr(item, campo, valor)


def _out(db: Session, c: Contrato) -> ContratoOut:
    db.refresh(c)
    return contrato_para_out(c, date.today())


@router.get("/contratos", response_model=ListaContratos)
def listar(db: Session = Depends(get_db)):
    hoje = date.today()
    cs = db.query(Contrato).order_by(Contrato.numero).all()
    itens = [contrato_para_out(c, hoje) for c in cs]
    return ListaContratos(total=len(itens), itens=itens)


@router.get("/contratos/alertas", response_model=list[ContratoOut])
def alertas(db: Session = Depends(get_db)):
    hoje = date.today()
    itens = [contrato_para_out(c, hoje) for c in db.query(Contrato).all()]
    itens = [c for c in itens
             if c.status_vigencia in _URGENCIA or c.status_saldo in ("BAIXO", "ESGOTADO")]
    itens.sort(key=lambda c: (_URGENCIA.get(c.status_vigencia, 9),
                              0 if c.status_saldo == "ESGOTADO" else 1,
                              c.dias_restantes if c.dias_restantes is not None else 99999))
    return itens


@router.get("/contratos/{cid}", response_model=ContratoOut)
def obter(cid: int, db: Session = Depends(get_db)):
    return contrato_para_out(_get_contrato(db, cid), date.today())


@router.post("/contratos", response_model=ContratoOut, status_code=201)
def criar(dados: ContratoIn, db: Session = Depends(get_db)):
    c = Contrato()
    _aplicar_contrato(c, dados)
    db.add(c)
    db.commit()
    return _out(db, c)


@router.put("/contratos/{cid}", response_model=ContratoOut)
def editar(cid: int, dados: ContratoIn, db: Session = Depends(get_db)):
    c = _get_contrato(db, cid)
    _aplicar_contrato(c, dados)
    db.commit()
    return _out(db, c)


@router.delete("/contratos/{cid}", status_code=204)
def remover(cid: int, db: Session = Depends(get_db)):
    c = _get_contrato(db, cid)
    db.delete(c)  # itens caem por cascade delete-orphan do ORM
    db.commit()


@router.post("/contratos/{cid}/itens", response_model=ContratoOut, status_code=201)
def criar_item(cid: int, dados: ItemContratoIn, db: Session = Depends(get_db)):
    c = _get_contrato(db, cid)
    item = ItemContrato(contrato_id=cid)
    _aplicar_item(item, dados)
    db.add(item)
    db.commit()
    return _out(db, c)


@router.put("/contratos/{cid}/itens/{item_id}", response_model=ContratoOut)
def editar_item(cid: int, item_id: int, dados: ItemContratoIn, db: Session = Depends(get_db)):
    c = _get_contrato(db, cid)
    item = db.get(ItemContrato, item_id)
    if not item or item.contrato_id != cid:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    _aplicar_item(item, dados)
    db.commit()
    return _out(db, c)


@router.delete("/contratos/{cid}/itens/{item_id}", response_model=ContratoOut)
def remover_item(cid: int, item_id: int, db: Session = Depends(get_db)):
    c = _get_contrato(db, cid)
    item = db.get(ItemContrato, item_id)
    if not item or item.contrato_id != cid:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    db.delete(item)
    db.commit()
    return _out(db, c)
