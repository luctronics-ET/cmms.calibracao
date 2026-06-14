from datetime import date
from decimal import Decimal
from backend.parsing import (
    normalizar_cabecalho, parse_data, parse_moeda, parse_ciclo,
)


def test_normalizar_cabecalho_remove_espacos_e_quebras():
    assert normalizar_cabecalho("MARCA ") == "marca"
    assert normalizar_cabecalho("UNIDADE\nRANGE") == "unidade range"
    assert normalizar_cabecalho("CERTIFICADO  ") == "certificado"
    assert normalizar_cabecalho("CUSTO CONTRAT (R$)") == "custo contrat (r$)"


def test_parse_data_mm_dd_yy():
    d, aviso = parse_data("09/13/25")
    assert d == date(2025, 9, 13)
    assert aviso is None


def test_parse_data_dd_mm_quando_primeiro_maior_que_12():
    d, aviso = parse_data("26/07/24")
    assert d == date(2024, 7, 26)
    assert "DD/MM" in aviso


def test_parse_data_value_error_marcador():
    d, aviso = parse_data("#VALUE!")
    assert d is None
    assert aviso is not None


def test_parse_data_vazia():
    assert parse_data("") == (None, None)


def test_parse_data_ilegivel():
    d, aviso = parse_data("xx/yy/zz")
    assert d is None and aviso is not None


def test_parse_data_seculo():
    assert parse_data("01/01/85")[0] == date(1985, 1, 1)
    assert parse_data("01/01/24")[0] == date(2024, 1, 1)


def test_parse_moeda():
    assert parse_moeda("R$ 3,104.95") == Decimal("3104.95")
    assert parse_moeda("R$ 70.00") == Decimal("70.00")
    assert parse_moeda("") is None
    assert parse_moeda("lixo") is None


def test_parse_ciclo():
    assert parse_ciclo("12") == 12
    assert parse_ciclo("") is None
    assert parse_ciclo("abc") is None
