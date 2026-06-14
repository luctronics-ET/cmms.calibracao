from backend.criticidade import calcular_igp, ClassePrioridade


def test_todas_minimas_igp_7_muito_baixa():
    r = calcular_igp(1, 1, 1, 1, 1)
    assert r.igp == 7
    assert r.classe == ClassePrioridade.MUITO_BAIXA


def test_todas_medias_igp_14_media():
    r = calcular_igp(2, 2, 2, 2, 2)
    assert r.igp == 14
    assert r.classe == ClassePrioridade.MEDIA


def test_todas_maximas_igp_21_maxima():
    r = calcular_igp(3, 3, 3, 3, 3)
    assert r.igp == 21
    assert r.classe == ClassePrioridade.MAXIMA


def test_pesos_nc_e_cm_dobram():
    # fu=1 nc=3 ab=1 cm=3 ci=1 => 1 + 6 + 1 + 6 + 1 = 15
    assert calcular_igp(1, 3, 1, 3, 1).igp == 15


def test_fronteira_10_muito_baixa():
    assert calcular_igp(2, 1, 1, 1, 3).classe == ClassePrioridade.MUITO_BAIXA  # igp 10


def test_fronteira_11_baixa():
    r = calcular_igp(1, 1, 1, 3, 1)  # igp 11
    assert r.igp == 11
    assert r.classe == ClassePrioridade.BAIXA


def test_fronteira_13_baixa():
    assert calcular_igp(3, 1, 3, 1, 3).classe == ClassePrioridade.BAIXA  # igp 13


def test_fronteira_14_media():
    assert calcular_igp(2, 2, 2, 2, 2).classe == ClassePrioridade.MEDIA  # igp 14


def test_fronteira_17_media():
    assert calcular_igp(3, 2, 3, 2, 3).classe == ClassePrioridade.MEDIA  # igp 17


def test_fronteira_18_maxima():
    r = calcular_igp(2, 3, 2, 3, 2)  # igp 18
    assert r.igp == 18
    assert r.classe == ClassePrioridade.MAXIMA


def test_qualquer_variavel_nula_nao_classificado():
    r = calcular_igp(None, 2, 2, 2, 2)
    assert r.igp is None
    assert r.classe == ClassePrioridade.NAO_CLASSIFICADO
