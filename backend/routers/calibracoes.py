"""Endpoints de registro/histórico de calibrações."""
from __future__ import annotations
from datetime import date
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Instrumento, Calibracao, Resultado, Laboratorio, ItemContrato
from backend.servico import (instrumento_para_out, calibracao_para_out, aplicar_derivados,
                             item_consumivel, calibracao_recente_para_out)
from backend.calibracao import adicionar_meses
from backend.schemas import (CalibracaoIn, ListaCalibracoes, RegistroCalibracaoOut, CalibracaoOut,
                             InstrumentoOut, ListaCalibracoesRecentes)

router = APIRouter(prefix="/api/v1", tags=["calibracoes"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"


def _get_inst(db: Session, inst_id: int) -> Instrumento:
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    return inst


@router.get("/instrumentos/{inst_id}/calibracoes", response_model=ListaCalibracoes)
def listar(inst_id: int, db: Session = Depends(get_db)):
    _get_inst(db, inst_id)
    cals = (db.query(Calibracao)
            .filter(Calibracao.instrumento_id == inst_id)
            .order_by(Calibracao.data_calibracao.desc(), Calibracao.id.desc())
            .all())
    return ListaCalibracoes(total=len(cals), itens=[calibracao_para_out(c) for c in cals])


@router.get("/calibracoes", response_model=ListaCalibracoesRecentes)
def listar_recentes(limite: int = 100, db: Session = Depends(get_db)):
    """Lista global de calibrações (mais recentes primeiro) — landing de calibracao.html."""
    cals = (db.query(Calibracao)
            .order_by(Calibracao.data_calibracao.desc(), Calibracao.id.desc())
            .limit(limite).all())
    return ListaCalibracoesRecentes(total=len(cals),
                                    itens=[calibracao_recente_para_out(c) for c in cals])


@router.post("/instrumentos/{inst_id}/calibracoes",
             response_model=RegistroCalibracaoOut, status_code=201)
def registrar(inst_id: int, dados: CalibracaoIn, db: Session = Depends(get_db)):
    inst = _get_inst(db, inst_id)
    ciclo = inst.ciclo_meses or 12
    lab_id = dados.laboratorio_id
    custo = dados.custo
    lab_nome, lab_cnpj, lab_cgcre, lab_rbc = (
        dados.laboratorio, dados.laboratorio_cnpj, dados.numero_cgcre, dados.acreditacao_rbc)

    # Vínculo a item de contrato: só vigente; herda lab + preço do item; consome 1 unidade.
    item = None
    if dados.item_contrato_id is not None:
        item = db.get(ItemContrato, dados.item_contrato_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item de contrato não encontrado")
        if not item_consumivel(item, date.today()):
            raise HTTPException(status_code=409,
                                detail="Contrato não vigente ou sem saldo para este item")
        custo = float(item.valor_unitario) if item.valor_unitario is not None else custo
        if item.contrato is not None and item.contrato.laboratorio_id is not None:
            lab_id = item.contrato.laboratorio_id

    if lab_id is not None:
        lab = db.get(Laboratorio, lab_id)
        if not lab:
            raise HTTPException(status_code=404, detail="Laboratório não encontrado")
        lab_nome, lab_cnpj, lab_cgcre, lab_rbc = (
            lab.razao_social, lab.cnpj, lab.numero_cgcre, lab.acreditado_rbc)
    if dados.resultado == "REPROVADO":
        validade = None
    else:
        validade = adicionar_meses(dados.data_calibracao, ciclo)
    cal = Calibracao(
        instrumento_id=inst_id,
        laboratorio_id=lab_id,
        item_contrato_id=dados.item_contrato_id,
        data_calibracao=dados.data_calibracao,
        data_validade=validade,
        ciclo_meses=ciclo,
        resultado=Resultado(dados.resultado),
        laboratorio=lab_nome,
        laboratorio_cnpj=lab_cnpj,
        acreditacao_rbc=lab_rbc,
        numero_cgcre=lab_cgcre,
        numero_certificado=dados.numero_certificado,
        custo=custo,
        responsavel=dados.responsavel,
        observacoes=dados.observacoes,
        origem="MANUAL",
    )
    db.add(cal)
    if item is not None:
        item.usado += 1  # consome 1 unidade de saldo do contrato
    db.commit()
    db.refresh(cal)
    aplicar_derivados(inst, db)
    db.refresh(inst)
    return RegistroCalibracaoOut(
        instrumento=instrumento_para_out(inst, date.today()),
        calibracao=calibracao_para_out(cal),
    )


@router.post("/instrumentos/{inst_id}/calibracoes/{cal_id}/certificado",
             response_model=CalibracaoOut)
async def upload_certificado(inst_id: int, cal_id: int,
                             arquivo: UploadFile = File(...),
                             db: Session = Depends(get_db)):
    cal = db.get(Calibracao, cal_id)
    if not cal or cal.instrumento_id != inst_id:
        raise HTTPException(status_code=404, detail="Calibração não encontrada")
    if (arquivo.content_type or "") != "application/pdf":
        raise HTTPException(status_code=415, detail="Envie um PDF")
    destino_dir = UPLOAD_DIR / str(inst_id)
    destino_dir.mkdir(parents=True, exist_ok=True)
    nome = f"cert_{cal_id}.pdf"
    (destino_dir / nome).write_bytes(await arquivo.read())
    cal.certificado_path = f"uploads/{inst_id}/{nome}"
    db.commit()
    db.refresh(cal)
    return calibracao_para_out(cal)


@router.delete("/instrumentos/{inst_id}/calibracoes/{cal_id}", response_model=InstrumentoOut)
def remover(inst_id: int, cal_id: int, db: Session = Depends(get_db)):
    inst = _get_inst(db, inst_id)
    cal = db.get(Calibracao, cal_id)
    if not cal or cal.instrumento_id != inst_id:
        raise HTTPException(status_code=404, detail="Calibração não encontrada")
    if cal.item_contrato is not None and cal.item_contrato.usado > 0:
        cal.item_contrato.usado -= 1  # devolve a unidade consumida ao saldo
    db.delete(cal)
    db.commit()
    aplicar_derivados(inst, db)
    db.refresh(inst)
    return instrumento_para_out(inst, date.today())
