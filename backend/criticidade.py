"""Motor puro do Índice Global de Prioridade do Equipamento (IGP).

IGP = fu·1 + nc·2 + ab·1 + cm·2 + ci·1  (faixa real 7..21 quando completo).
Sem I/O, sem DB.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

LIMIAR_MAXIMA = 18
LIMIAR_MEDIA = 14
LIMIAR_BAIXA = 11


class ClassePrioridade(str, Enum):
    MAXIMA = "MAXIMA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"
    MUITO_BAIXA = "MUITO_BAIXA"
    NAO_CLASSIFICADO = "NAO_CLASSIFICADO"


@dataclass(frozen=True)
class ResultadoIGP:
    igp: int | None
    classe: ClassePrioridade


def calcular_igp(fu, nc, ab, cm, ci) -> ResultadoIGP:
    if any(v is None for v in (fu, nc, ab, cm, ci)):
        return ResultadoIGP(None, ClassePrioridade.NAO_CLASSIFICADO)
    igp = fu * 1 + nc * 2 + ab * 1 + cm * 2 + ci * 1
    if igp >= LIMIAR_MAXIMA:
        classe = ClassePrioridade.MAXIMA
    elif igp >= LIMIAR_MEDIA:
        classe = ClassePrioridade.MEDIA
    elif igp >= LIMIAR_BAIXA:
        classe = ClassePrioridade.BAIXA
    else:
        classe = ClassePrioridade.MUITO_BAIXA
    return ResultadoIGP(igp, classe)
