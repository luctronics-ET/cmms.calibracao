"""Aplica os motores de status e IGP sobre instrumentos do banco."""
from __future__ import annotations
from datetime import date
from backend.calibracao import calcular_status
from backend.criticidade import calcular_igp
from backend.models import Instrumento
from backend.schemas import InstrumentoOut


def instrumento_para_out(inst: Instrumento, hoje: date) -> InstrumentoOut:
    st = calcular_status(inst.data_validade, inst.flag_origem, hoje)
    ig = calcular_igp(inst.fu, inst.nc, inst.ab, inst.cm, inst.ci)
    return InstrumentoOut(
        id=inst.id,
        codigo_interno=inst.codigo_interno,
        codigo_patrimonial=inst.codigo_patrimonial,
        serial=inst.serial,
        equipamento=inst.equipamento,
        marca=inst.marca,
        modelo=inst.modelo,
        faixa=inst.faixa,
        unidade_faixa=inst.unidade_faixa,
        faixa_min=float(inst.faixa_min) if inst.faixa_min is not None else None,
        faixa_max=float(inst.faixa_max) if inst.faixa_max is not None else None,
        resolucao=inst.resolucao,
        emp=inst.emp,
        disciplina=inst.disciplina.value if inst.disciplina else None,
        familia_id=inst.familia_id,
        familia_nome=inst.familia.nome if inst.familia else None,
        tipo_id=inst.tipo_id,
        tipo_nome=inst.tipo.nome if inst.tipo else None,
        grandeza_id=inst.grandeza_id,
        grandeza_nome=inst.grandeza.nome if inst.grandeza else None,
        unidade_id=inst.unidade_id,
        unidade_simbolo=inst.unidade.simbolo if inst.unidade else None,
        sistema=inst.sistema,
        organizacao=inst.organizacao,
        unidade_org=inst.unidade_org,
        secao=inst.secao,
        bancada=inst.bancada,
        ciclo_meses=inst.ciclo_meses,
        data_ultima_calibracao=inst.data_ultima_calibracao,
        data_validade=inst.data_validade,
        flag_origem=inst.flag_origem,
        organizacao_calibradora=inst.organizacao_calibradora,
        local_calibracao=inst.local_calibracao,
        custo_estimado=float(inst.custo_estimado) if inst.custo_estimado is not None else None,
        custo_contratado=float(inst.custo_contratado) if inst.custo_contratado is not None else None,
        certificado_ref=inst.certificado_ref,
        status_operacional=inst.status_operacional.value,
        foto_path=inst.foto_path,
        manual_path=inst.manual_path,
        fu=inst.fu, nc=inst.nc, ab=inst.ab, cm=inst.cm, ci=inst.ci,
        observacoes=inst.observacoes,
        status=st.status.value,
        dias_restantes=st.dias_restantes,
        divergencia_flag=st.divergencia_flag,
        igp=ig.igp,
        classe_prioridade=ig.classe.value,
    )
