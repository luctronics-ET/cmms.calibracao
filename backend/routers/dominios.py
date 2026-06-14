"""Endpoint de tabelas de domínio para popular selects do frontend."""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import FamiliaMetrologica, UnidadeMedida, Grandeza, TipoInstrumento
from backend.schemas import DominiosOut, ItemDominio

router = APIRouter(prefix="/api/v1", tags=["dominios"])


@router.get("/dominios", response_model=DominiosOut)
def listar_dominios(db: Session = Depends(get_db), familia_id: int | None = Query(None)):
    familias = db.query(FamiliaMetrologica).filter_by(ativo=True).order_by(FamiliaMetrologica.ordem).all()
    unidades = db.query(UnidadeMedida).filter_by(ativo=True).order_by(UnidadeMedida.ordem).all()
    q_tipos = db.query(TipoInstrumento).filter_by(ativo=True)
    q_grand = db.query(Grandeza).filter_by(ativo=True)
    if familia_id is not None:
        q_tipos = q_tipos.filter_by(familia_id=familia_id)
        q_grand = q_grand.filter_by(familia_id=familia_id)
    tipos = q_tipos.order_by(TipoInstrumento.ordem).all()
    grandezas = q_grand.order_by(Grandeza.ordem).all()

    return DominiosOut(
        familias=[ItemDominio(id=f.id, nome=f.nome) for f in familias],
        unidades=[ItemDominio(id=u.id, nome=u.nome, simbolo=u.simbolo) for u in unidades],
        tipos=[ItemDominio(id=t.id, nome=t.nome, familia_id=t.familia_id) for t in tipos],
        grandezas=[ItemDominio(id=g.id, nome=g.nome, familia_id=g.familia_id,
                               unidade_padrao_id=g.unidade_padrao_id) for g in grandezas],
    )
