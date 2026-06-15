"""Endpoints de gestão de laboratórios de calibração."""
from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Laboratorio, Calibracao
from backend.servico import laboratorio_para_out, calibracao_para_out
from backend.calibracao import StatusCalibracao
from backend.schemas import LaboratorioIn, LaboratorioOut, ListaLaboratorios, ListaCalibracoes

router = APIRouter(prefix="/api/v1", tags=["laboratorios"])

_URGENCIA = {
    StatusCalibracao.VENCIDO.value: 0,
    StatusCalibracao.A_VENCER_7.value: 1,
    StatusCalibracao.A_VENCER_30.value: 2,
    StatusCalibracao.A_VENCER_60.value: 3,
}


def _get_lab(db: Session, lab_id: int) -> Laboratorio:
    lab = db.get(Laboratorio, lab_id)
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratório não encontrado")
    return lab


def _aplicar(lab: Laboratorio, dados: LaboratorioIn) -> None:
    for campo, valor in dados.model_dump().items():
        setattr(lab, campo, valor)


@router.get("/laboratorios", response_model=ListaLaboratorios)
def listar(db: Session = Depends(get_db)):
    hoje = date.today()
    labs = db.query(Laboratorio).order_by(Laboratorio.razao_social).all()
    itens = [laboratorio_para_out(l, hoje) for l in labs]
    return ListaLaboratorios(total=len(itens), itens=itens)


@router.get("/laboratorios/alertas", response_model=list[LaboratorioOut])
def alertas(db: Session = Depends(get_db)):
    hoje = date.today()
    itens = [laboratorio_para_out(l, hoje) for l in db.query(Laboratorio).all()]
    itens = [i for i in itens if i.status_acreditacao in _URGENCIA]
    itens.sort(key=lambda i: (_URGENCIA[i.status_acreditacao],
                              i.dias_restantes if i.dias_restantes is not None else 99999))
    return itens


@router.get("/laboratorios/{lab_id}", response_model=LaboratorioOut)
def obter(lab_id: int, db: Session = Depends(get_db)):
    return laboratorio_para_out(_get_lab(db, lab_id), date.today())


@router.post("/laboratorios", response_model=LaboratorioOut, status_code=201)
def criar(dados: LaboratorioIn, db: Session = Depends(get_db)):
    lab = Laboratorio()
    _aplicar(lab, dados)
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return laboratorio_para_out(lab, date.today())


@router.put("/laboratorios/{lab_id}", response_model=LaboratorioOut)
def editar(lab_id: int, dados: LaboratorioIn, db: Session = Depends(get_db)):
    lab = _get_lab(db, lab_id)
    _aplicar(lab, dados)
    db.commit()
    db.refresh(lab)
    return laboratorio_para_out(lab, date.today())


@router.delete("/laboratorios/{lab_id}", status_code=204)
def remover(lab_id: int, db: Session = Depends(get_db)):
    lab = _get_lab(db, lab_id)
    # zera o vínculo explicitamente (não confia no SET NULL do SQLite); snapshot texto permanece
    db.query(Calibracao).filter(Calibracao.laboratorio_id == lab_id)\
        .update({Calibracao.laboratorio_id: None})
    db.delete(lab)
    db.commit()


@router.get("/laboratorios/{lab_id}/calibracoes", response_model=ListaCalibracoes)
def historico(lab_id: int, db: Session = Depends(get_db)):
    _get_lab(db, lab_id)
    cals = (db.query(Calibracao)
            .filter(Calibracao.laboratorio_id == lab_id)
            .order_by(Calibracao.data_calibracao.desc(), Calibracao.id.desc())
            .all())
    return ListaCalibracoes(total=len(cals), itens=[calibracao_para_out(c) for c in cals])
