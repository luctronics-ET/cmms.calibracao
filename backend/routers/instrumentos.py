"""Endpoints de inventário (listar, obter, criar, editar)."""
from __future__ import annotations
import unicodedata
from datetime import date
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Instrumento, Disciplina, StatusOperacional
from backend.servico import instrumento_para_out
from backend.schemas import ListaInstrumentos, InstrumentoOut, InstrumentoIn

router = APIRouter(prefix="/api/v1", tags=["instrumentos"])


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


@router.get("/instrumentos", response_model=ListaInstrumentos)
def listar(
    db: Session = Depends(get_db),
    busca: str | None = Query(None),
    disciplina: str | None = Query(None),
    sistema: str | None = Query(None),
    status: str | None = Query(None),
    familia_id: int | None = Query(None),
    classe_prioridade: str | None = Query(None),
):
    hoje = date.today()
    itens = [instrumento_para_out(i, hoje) for i in db.query(Instrumento).all()]

    if busca:
        b = _sem_acento(busca)
        itens = [i for i in itens if b in _sem_acento(" ".join(
            filter(None, [i.codigo_interno, i.serial, i.equipamento, i.modelo, i.marca])))]
    if disciplina:
        itens = [i for i in itens if i.disciplina == disciplina.upper()]
    if sistema:
        itens = [i for i in itens if (i.sistema or "") == sistema]
    if status:
        itens = [i for i in itens if i.status == status.upper()]
    if familia_id is not None:
        itens = [i for i in itens if i.familia_id == familia_id]
    if classe_prioridade:
        itens = [i for i in itens if i.classe_prioridade == classe_prioridade.upper()]

    itens.sort(key=lambda i: (i.codigo_interno or "").lower())
    return ListaInstrumentos(total=len(itens), itens=itens)


@router.get("/instrumentos/{inst_id}", response_model=InstrumentoOut)
def obter(inst_id: int, db: Session = Depends(get_db)):
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    return instrumento_para_out(inst, date.today())


def _aplicar(inst: Instrumento, dados: InstrumentoIn) -> None:
    payload = dados.model_dump(exclude_unset=False)
    if payload.get("disciplina"):
        payload["disciplina"] = Disciplina(payload["disciplina"].upper())
    payload["status_operacional"] = StatusOperacional(payload["status_operacional"])
    for campo, valor in payload.items():
        setattr(inst, campo, valor)


def _checar_patrimonio(db: Session, codigo: str | None, ignorar_id: int | None = None) -> None:
    if not codigo:
        return
    q = db.query(Instrumento).filter(Instrumento.codigo_patrimonial == codigo)
    if ignorar_id is not None:
        q = q.filter(Instrumento.id != ignorar_id)
    if q.first():
        raise HTTPException(status_code=409, detail="Código patrimonial já existe")


@router.post("/instrumentos", response_model=InstrumentoOut, status_code=201)
def criar(dados: InstrumentoIn, db: Session = Depends(get_db)):
    _checar_patrimonio(db, dados.codigo_patrimonial)
    inst = Instrumento()
    _aplicar(inst, dados)
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return instrumento_para_out(inst, date.today())


@router.put("/instrumentos/{inst_id}", response_model=InstrumentoOut)
def editar(inst_id: int, dados: InstrumentoIn, db: Session = Depends(get_db)):
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    _checar_patrimonio(db, dados.codigo_patrimonial, ignorar_id=inst_id)
    _aplicar(inst, dados)
    db.commit()
    db.refresh(inst)
    return instrumento_para_out(inst, date.today())


UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"


def _salvar(inst_id: int, sufixo: str, conteudo: bytes, ext: str) -> str:
    destino_dir = UPLOAD_DIR / str(inst_id)
    destino_dir.mkdir(parents=True, exist_ok=True)
    nome = f"{sufixo}{ext}"
    (destino_dir / nome).write_bytes(conteudo)
    return f"uploads/{inst_id}/{nome}"


@router.post("/instrumentos/{inst_id}/foto", response_model=InstrumentoOut)
async def upload_foto(inst_id: int, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    if not (arquivo.content_type or "").startswith("image/"):
        raise HTTPException(status_code=415, detail="Envie um arquivo de imagem")
    ext = Path(arquivo.filename or "").suffix.lower() or ".img"
    inst.foto_path = _salvar(inst_id, "foto", await arquivo.read(), ext)
    db.commit()
    db.refresh(inst)
    return instrumento_para_out(inst, date.today())


@router.post("/instrumentos/{inst_id}/manual", response_model=InstrumentoOut)
async def upload_manual(inst_id: int, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    if (arquivo.content_type or "") != "application/pdf":
        raise HTTPException(status_code=415, detail="Envie um PDF")
    inst.manual_path = _salvar(inst_id, "manual", await arquivo.read(), ".pdf")
    db.commit()
    db.refresh(inst)
    return instrumento_para_out(inst, date.today())
