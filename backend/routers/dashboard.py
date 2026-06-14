"""Endpoints de dashboard e alertas."""
from __future__ import annotations
import csv
import io
from collections import Counter
from datetime import date
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Instrumento
from backend.servico import instrumento_para_out

router = APIRouter(prefix="/api/v1", tags=["dashboard"])

LABEL = {
    "VENCIDO": "Vencidos", "A_VENCER_7": "A vencer (7d)",
    "A_VENCER_30": "A vencer (30d)", "A_VENCER_60": "A vencer (60d)",
    "VALIDO": "Válidos", "SEM_DATA": "Sem data", "BAIXADO": "Baixados",
}
URGENCIA = {"VENCIDO": 0, "A_VENCER_7": 1, "A_VENCER_30": 2,
            "A_VENCER_60": 3, "SEM_DATA": 4}


def _todos(db, hoje):
    return [instrumento_para_out(i, hoje) for i in db.query(Instrumento).all()]


@router.get("/dashboard/kpis")
def kpis(db: Session = Depends(get_db)):
    hoje = date.today()
    itens = _todos(db, hoje)
    cont = Counter(i.status for i in itens)
    a_vencer_30 = cont.get("A_VENCER_7", 0) + cont.get("A_VENCER_30", 0)
    return {
        "total": len(itens),
        "vencidos": cont.get("VENCIDO", 0),
        "a_vencer_30": a_vencer_30,
        "sem_data": cont.get("SEM_DATA", 0),
        "n_sistemas": len({i.sistema for i in itens if i.sistema}),
        "por_status": [{"status": s, "label": LABEL.get(s, s), "total": cont[s]}
                       for s in cont],
    }


@router.get("/alertas")
def alertas(
    db: Session = Depends(get_db),
    disciplina: str | None = Query(None),
    sistema: str | None = Query(None),
    formato: str | None = Query(None),
):
    hoje = date.today()
    itens = [i for i in _todos(db, hoje) if i.status in URGENCIA]
    if disciplina:
        itens = [i for i in itens if i.disciplina == disciplina.upper()]
    if sistema:
        itens = [i for i in itens if (i.sistema or "") == sistema]
    itens.sort(key=lambda i: (URGENCIA[i.status],
                              i.dias_restantes if i.dias_restantes is not None else 99999))

    if formato == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["codigo_interno", "equipamento", "sistema", "disciplina",
                    "data_validade", "status", "dias_restantes"])
        for i in itens:
            w.writerow([i.codigo_interno, i.equipamento, i.sistema, i.disciplina,
                        i.data_validade, i.status, i.dias_restantes])
        return Response(content=buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=alertas.csv"})

    return [i.model_dump() for i in itens]
