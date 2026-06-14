"""Aplica os motores de status e IGP sobre instrumentos do banco."""
from __future__ import annotations
from datetime import date
from sqlalchemy.orm import Session
from backend.calibracao import calcular_status, derivar_de_calibracoes
from backend.criticidade import calcular_igp
from backend.models import Instrumento, Calibracao, StatusOperacional, Resultado
from backend.schemas import InstrumentoOut, CalibracaoOut


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


def calibracao_para_out(cal: Calibracao) -> CalibracaoOut:
    return CalibracaoOut(
        id=cal.id,
        instrumento_id=cal.instrumento_id,
        data_calibracao=cal.data_calibracao,
        data_validade=cal.data_validade,
        ciclo_meses=cal.ciclo_meses,
        resultado=cal.resultado.value,
        laboratorio=cal.laboratorio,
        laboratorio_cnpj=cal.laboratorio_cnpj,
        acreditacao_rbc=cal.acreditacao_rbc,
        numero_cgcre=cal.numero_cgcre,
        numero_certificado=cal.numero_certificado,
        custo=float(cal.custo) if cal.custo is not None else None,
        responsavel=cal.responsavel,
        certificado_path=cal.certificado_path,
        origem=cal.origem,
        observacoes=cal.observacoes,
    )


def aplicar_derivados(inst: Instrumento, db: Session) -> None:
    """Recalcula data_ultima_calibracao/data_validade/status_operacional do instrumento
    a partir das suas calibrações e dá commit."""
    cals = db.query(Calibracao).filter(Calibracao.instrumento_id == inst.id).all()
    d = derivar_de_calibracoes(cals)
    if d.status_operacional is not None:
        inst.data_ultima_calibracao = d.data_ultima_calibracao
        inst.data_validade = d.data_validade
        inst.status_operacional = StatusOperacional(d.status_operacional)
    db.commit()


def backfill_calibracoes_origem(db: Session) -> int:
    """Cria 1 calibração origem='IMPORTACAO' para cada instrumento que tem
    data_ultima_calibracao mas ainda não tem nenhuma calibração. Idempotente.
    Retorna quantas calibrações foram criadas."""
    criadas = 0
    instrumentos = (db.query(Instrumento)
                    .filter(Instrumento.data_ultima_calibracao.isnot(None))
                    .all())
    for inst in instrumentos:
        existe = (db.query(Calibracao)
                  .filter(Calibracao.instrumento_id == inst.id)
                  .first())
        if existe:
            continue
        db.add(Calibracao(
            instrumento_id=inst.id,
            data_calibracao=inst.data_ultima_calibracao,
            data_validade=inst.data_validade,
            ciclo_meses=inst.ciclo_meses or 12,
            resultado=Resultado.APROVADO,
            laboratorio=inst.organizacao_calibradora,
            numero_certificado=inst.certificado_ref,
            origem="IMPORTACAO",
        ))
        criadas += 1
    db.commit()
    return criadas
