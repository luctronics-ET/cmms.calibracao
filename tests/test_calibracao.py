from datetime import date
from backend.calibracao import calcular_status, StatusCalibracao

HOJE = date(2026, 6, 14)


def test_baixado_por_flag_sem_condicoes():
    r = calcular_status(date(2027, 1, 1), "SEM CONDIÇOES DE USO", HOJE)
    assert r.status == StatusCalibracao.BAIXADO
    assert r.dias_restantes is None


def test_baixado_por_flag_inativo():
    assert calcular_status(None, "inativo", HOJE).status == StatusCalibracao.BAIXADO


def test_sem_data():
    r = calcular_status(None, "CALIBRADO", HOJE)
    assert r.status == StatusCalibracao.SEM_DATA
    assert r.dias_restantes is None


def test_vencido():
    r = calcular_status(date(2026, 6, 1), "DESCALIBRADO", HOJE)
    assert r.status == StatusCalibracao.VENCIDO
    assert r.dias_restantes == -13


def test_a_vencer_7():
    assert calcular_status(date(2026, 6, 20), "CALIBRADO", HOJE).status == StatusCalibracao.A_VENCER_7


def test_a_vencer_30():
    assert calcular_status(date(2026, 7, 10), "CALIBRADO", HOJE).status == StatusCalibracao.A_VENCER_30


def test_a_vencer_60():
    assert calcular_status(date(2026, 8, 10), "CALIBRADO", HOJE).status == StatusCalibracao.A_VENCER_60


def test_valido():
    r = calcular_status(date(2027, 1, 1), "CALIBRADO", HOJE)
    assert r.status == StatusCalibracao.VALIDO
    assert r.dias_restantes == 201


def test_limite_exato_hoje_eh_a_vencer_7():
    assert calcular_status(HOJE, "CALIBRADO", HOJE).status == StatusCalibracao.A_VENCER_7


def test_divergencia_descalibrado_mas_data_valida():
    r = calcular_status(date(2027, 1, 1), "DESCALIBRADO", HOJE)
    assert r.status == StatusCalibracao.VALIDO
    assert r.divergencia_flag is True


def test_divergencia_calibrado_mas_vencido():
    r = calcular_status(date(2026, 1, 1), "CALIBRADO", HOJE)
    assert r.status == StatusCalibracao.VENCIDO
    assert r.divergencia_flag is True


def test_sem_divergencia_quando_coerente():
    assert calcular_status(date(2027, 1, 1), "CALIBRADO", HOJE).divergencia_flag is False
