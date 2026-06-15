"""Motor puro de saldo de contrato/ATA. Sem I/O, sem DB."""
from __future__ import annotations

LIMIAR_SALDO_BAIXO = 0.20


def saldo_item(quantidade: int, usado: int, valor_unitario: float | None) -> tuple[int, float]:
    """Retorna (saldo, valor_saldo). saldo = quantidade - usado (pode ser negativo);
    valor_saldo = max(saldo, 0) * valor_unitario (0 se sem valor unitário)."""
    saldo = (quantidade or 0) - (usado or 0)
    if valor_unitario is None:
        return saldo, 0.0
    return saldo, max(saldo, 0) * float(valor_unitario)


def status_saldo(valor_saldo_total: float, valor_total: float | None) -> str:
    """OK / BAIXO / ESGOTADO. Sem valor_total definido (None/0) -> OK
    (sem base monetária não dá para classificar saldo)."""
    if not valor_total:
        return "OK"
    if valor_saldo_total <= 0:
        return "ESGOTADO"
    if valor_saldo_total / valor_total < LIMIAR_SALDO_BAIXO:
        return "BAIXO"
    return "OK"
