"""Aplica o motor de status sobre instrumentos do banco."""
from __future__ import annotations
from datetime import date
from backend.calibracao import calcular_status
from backend.models import Instrumento
from backend.schemas import InstrumentoOut


def instrumento_para_out(inst: Instrumento, hoje: date) -> InstrumentoOut:
    r = calcular_status(inst.data_validade, inst.flag_origem, hoje)
    return InstrumentoOut(
        id=inst.id,
        codigo_interno=inst.codigo_interno,
        serial=inst.serial,
        equipamento=inst.equipamento,
        marca=inst.marca,
        modelo=inst.modelo,
        faixa=inst.faixa,
        unidade_faixa=inst.unidade_faixa,
        disciplina=inst.disciplina.value if inst.disciplina else None,
        sistema=inst.sistema,
        ciclo_meses=inst.ciclo_meses,
        data_ultima_calibracao=inst.data_ultima_calibracao,
        data_validade=inst.data_validade,
        flag_origem=inst.flag_origem,
        organizacao_calibradora=inst.organizacao_calibradora,
        local_calibracao=inst.local_calibracao,
        custo_estimado=float(inst.custo_estimado) if inst.custo_estimado is not None else None,
        custo_contratado=float(inst.custo_contratado) if inst.custo_contratado is not None else None,
        certificado_ref=inst.certificado_ref,
        observacoes=inst.observacoes,
        status=r.status.value,
        dias_restantes=r.dias_restantes,
        divergencia_flag=r.divergencia_flag,
    )
