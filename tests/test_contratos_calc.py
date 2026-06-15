from backend.contratos_calc import saldo_item, status_saldo


def test_saldo_item_basico():
    saldo, valor_saldo = saldo_item(quantidade=10, usado=3, valor_unitario=100.0)
    assert saldo == 7
    assert valor_saldo == 700.0


def test_saldo_item_clamp_em_zero():
    saldo, valor_saldo = saldo_item(quantidade=2, usado=5, valor_unitario=50.0)
    assert saldo == -3            # saldo pode ser negativo (overuse)
    assert valor_saldo == 0.0     # mas valor_saldo nunca é negativo


def test_saldo_item_sem_valor_unitario():
    saldo, valor_saldo = saldo_item(quantidade=10, usado=0, valor_unitario=None)
    assert saldo == 10
    assert valor_saldo == 0.0


def test_status_saldo_ok_baixo_esgotado():
    assert status_saldo(valor_saldo_total=800.0, valor_total=1000.0) == "OK"       # 80%
    assert status_saldo(valor_saldo_total=150.0, valor_total=1000.0) == "BAIXO"    # 15%
    assert status_saldo(valor_saldo_total=0.0, valor_total=1000.0) == "ESGOTADO"
    assert status_saldo(valor_saldo_total=-10.0, valor_total=1000.0) == "ESGOTADO"


def test_status_saldo_sem_valor_total():
    assert status_saldo(valor_saldo_total=500.0, valor_total=None) == "OK"
    assert status_saldo(valor_saldo_total=500.0, valor_total=0.0) == "OK"
    # sem base monetária, total zero NÃO é "esgotado" — não há como classificar
    assert status_saldo(valor_saldo_total=0.0, valor_total=None) == "OK"
