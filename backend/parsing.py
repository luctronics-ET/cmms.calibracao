"""Helpers puros de normalização de texto do CSV legado."""
from __future__ import annotations
import re
from datetime import date
from decimal import Decimal, InvalidOperation


def normalizar_cabecalho(nome: str) -> str:
    """lowercase, colapsa espaços/quebras de linha, remove bordas."""
    return re.sub(r"\s+", " ", (nome or "").replace("\n", " ")).strip().lower()


def _expandir_ano(aa: int) -> int:
    if aa >= 100:
        return aa
    return 2000 + aa if aa <= 69 else 1900 + aa


def parse_data(texto: str) -> tuple[date | None, str | None]:
    """Devolve (date, aviso). Lida com MM/DD/YY e DD/MM/YY ambíguos do legado."""
    t = (texto or "").strip()
    if not t:
        return (None, None)
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", t)
    if not m:
        return (None, f"data ilegível: {t!r}")
    a, b, c = int(m.group(1)), int(m.group(2)), _expandir_ano(int(m.group(3)))
    aviso = None
    if a > 12 and b <= 12:
        dia, mes = a, b
        aviso = "data interpretada como DD/MM"
    elif a <= 12:
        mes, dia = a, b
    else:
        return (None, f"data ambígua/ilegível: {t!r}")
    try:
        return (date(c, mes, dia), aviso)
    except ValueError:
        return (None, f"data inválida: {t!r}")


def parse_moeda(texto: str) -> Decimal | None:
    t = (texto or "").strip()
    if not t:
        return None
    limpo = t.replace("R$", "").replace(" ", "").replace(",", "")
    try:
        return Decimal(limpo)
    except (InvalidOperation, ValueError):
        return None


def parse_ciclo(texto: str) -> int | None:
    t = (texto or "").strip()
    try:
        return int(t)
    except (ValueError, TypeError):
        return None
