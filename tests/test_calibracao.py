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


# --- Testes de fronteira (off-by-one) ---

def test_fronteira_dias_7():
    # dias == 7: último dia do intervalo A_VENCER_7
    assert calcular_status(date(2026, 6, 21), "CALIBRADO", HOJE).status == StatusCalibracao.A_VENCER_7


def test_fronteira_dias_8():
    # dias == 8: primeiro dia do intervalo A_VENCER_30
    assert calcular_status(date(2026, 6, 22), "CALIBRADO", HOJE).status == StatusCalibracao.A_VENCER_30


def test_fronteira_dias_30():
    # dias == 30: último dia do intervalo A_VENCER_30
    assert calcular_status(date(2026, 7, 14), "CALIBRADO", HOJE).status == StatusCalibracao.A_VENCER_30


def test_fronteira_dias_31():
    # dias == 31: primeiro dia do intervalo A_VENCER_60
    assert calcular_status(date(2026, 7, 15), "CALIBRADO", HOJE).status == StatusCalibracao.A_VENCER_60


def test_fronteira_dias_60():
    # dias == 60: último dia do intervalo A_VENCER_60
    assert calcular_status(date(2026, 8, 13), "CALIBRADO", HOJE).status == StatusCalibracao.A_VENCER_60


def test_fronteira_dias_61():
    # dias == 61: primeiro dia do intervalo VALIDO
    assert calcular_status(date(2026, 8, 14), "CALIBRADO", HOJE).status == StatusCalibracao.VALIDO


from dataclasses import dataclass
from datetime import date
from backend.calibracao import adicionar_meses, derivar_de_calibracoes


@dataclass
class _Cal:
    id: int
    data_calibracao: date
    data_validade: date | None
    resultado: str


def test_adicionar_meses_simples():
    assert adicionar_meses(date(2026, 1, 15), 12) == date(2027, 1, 15)


def test_adicionar_meses_clamp_fim_de_mes():
    # 31/01 + 1 mês -> 28/02 (2026 não é bissexto)
    assert adicionar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_adicionar_meses_virada_de_ano():
    assert adicionar_meses(date(2026, 11, 30), 6) == date(2027, 5, 30)


def test_derivar_lista_vazia_nao_altera():
    d = derivar_de_calibracoes([])
    assert d.data_ultima_calibracao is None
    assert d.data_validade is None
    assert d.status_operacional is None


def test_derivar_um_registro_aprovado():
    cal = _Cal(1, date(2026, 1, 10), date(2027, 1, 10), "APROVADO")
    d = derivar_de_calibracoes([cal])
    assert d.data_ultima_calibracao == date(2026, 1, 10)
    assert d.data_validade == date(2027, 1, 10)
    assert d.status_operacional == "ATIVO"


def test_derivar_pega_a_mais_recente_por_data():
    velha = _Cal(1, date(2025, 1, 1), date(2026, 1, 1), "APROVADO")
    nova = _Cal(2, date(2026, 6, 1), date(2027, 6, 1), "APROVADO")
    d = derivar_de_calibracoes([velha, nova])
    assert d.data_validade == date(2027, 6, 1)


def test_derivar_desempate_por_id_quando_mesma_data():
    a = _Cal(1, date(2026, 6, 1), date(2027, 6, 1), "APROVADO")
    b = _Cal(2, date(2026, 6, 1), None, "REPROVADO")
    d = derivar_de_calibracoes([a, b])
    assert d.status_operacional == "REPROVADO"
    assert d.data_validade is None


def test_derivar_reprovado_status_e_validade_null():
    cal = _Cal(1, date(2026, 1, 10), None, "REPROVADO")
    d = derivar_de_calibracoes([cal])
    assert d.status_operacional == "REPROVADO"
    assert d.data_validade is None
