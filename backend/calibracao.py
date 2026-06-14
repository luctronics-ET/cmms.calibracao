"""Motor puro de status/validade de calibração. Sem I/O, sem DB."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from enum import Enum

LIMIAR_7 = 7
LIMIAR_30 = 30
LIMIAR_60 = 60


class StatusCalibracao(str, Enum):
    VALIDO = "VALIDO"
    A_VENCER_60 = "A_VENCER_60"
    A_VENCER_30 = "A_VENCER_30"
    A_VENCER_7 = "A_VENCER_7"
    VENCIDO = "VENCIDO"
    SEM_DATA = "SEM_DATA"
    BAIXADO = "BAIXADO"


@dataclass(frozen=True)
class ResultadoStatus:
    status: StatusCalibracao
    dias_restantes: int | None
    divergencia_flag: bool


def _categoria_flag(flag: str | None) -> str | None:
    """Normaliza o texto bruto da coluna de status do CSV."""
    if not flag:
        return None
    t = flag.strip().upper()
    if t.startswith("SEM CONDI") or t == "INATIVO":
        return "BAIXADO"
    if t.startswith("DESCAL"):
        return "DESCALIBRADO"
    if t.startswith("CALIBRAD"):
        return "CALIBRADO"
    return None


def calcular_status(
    data_validade: date | None, flag_origem: str | None, hoje: date
) -> ResultadoStatus:
    cat = _categoria_flag(flag_origem)

    if cat == "BAIXADO":
        return ResultadoStatus(StatusCalibracao.BAIXADO, None, False)

    if data_validade is None:
        return ResultadoStatus(StatusCalibracao.SEM_DATA, None, False)

    dias = (data_validade - hoje).days
    # dias == 0 significa "vence hoje, ainda válido" — cai em A_VENCER_7
    if dias < 0:
        status = StatusCalibracao.VENCIDO
    elif dias <= LIMIAR_7:
        status = StatusCalibracao.A_VENCER_7
    elif dias <= LIMIAR_30:
        status = StatusCalibracao.A_VENCER_30
    elif dias <= LIMIAR_60:
        status = StatusCalibracao.A_VENCER_60
    else:
        status = StatusCalibracao.VALIDO

    divergencia = (
        (cat == "DESCALIBRADO" and status != StatusCalibracao.VENCIDO)
        or (cat == "CALIBRADO" and status == StatusCalibracao.VENCIDO)
    )
    return ResultadoStatus(status, dias, divergencia)


import calendar


def adicionar_meses(d: date, meses: int) -> date:
    """Soma meses a uma data, fazendo clamp do dia ao último dia do mês alvo."""
    total = d.month - 1 + meses
    ano = d.year + total // 12
    mes = total % 12 + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(d.day, ultimo_dia))


@dataclass(frozen=True)
class DadosDerivados:
    data_ultima_calibracao: date | None
    data_validade: date | None
    status_operacional: str | None  # "ATIVO" | "REPROVADO" | None (não alterar)


def derivar_de_calibracoes(calibracoes) -> DadosDerivados:
    """Deriva os campos do instrumento a partir da calibração mais recente.

    Aceita qualquer objeto com .id, .data_calibracao, .data_validade, .resultado.
    Lista vazia -> tudo None (instrumento não é alterado).
    `resultado` é comparado com a string "REPROVADO" (Resultado é str-enum).
    """
    if not calibracoes:
        return DadosDerivados(None, None, None)
    ultima = max(calibracoes, key=lambda c: (c.data_calibracao, c.id))
    status = "REPROVADO" if ultima.resultado == "REPROVADO" else "ATIVO"
    return DadosDerivados(ultima.data_calibracao, ultima.data_validade, status)
