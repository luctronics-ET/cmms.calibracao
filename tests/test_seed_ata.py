from backend.db import Base, get_db
from backend import models
from backend.dominios import seed_dominios
from backend.seed_ata import seed_ata


def _db(client):
    # reaproveita a sessão de teste via dependency override do conftest
    gen = __import__("backend.main", fromlist=["app"]).app.dependency_overrides[get_db]()
    return next(gen)


def test_seed_idempotente_e_matching(client):
    db = _db(client)
    seed_dominios(db)  # garante tipos do domínio (Multímetro, Paquímetro, etc.)
    r1 = seed_ata(db)
    # contrato + 22 itens criados
    assert r1["contrato"] == 1
    assert r1["itens"] == 22
    # ao menos os tipos óbvios casaram (Multímetro, Paquímetro, Torquímetro, ...)
    assert r1["catalogo"] >= 5
    contrato = db.query(models.Contrato).filter_by(numero="ATA MQT 129/2025").first()
    assert contrato is not None
    assert db.query(models.ItemContrato).filter_by(contrato_id=contrato.id).count() == 22
    n_cat = db.query(models.CatalogoPreco).count()
    assert n_cat == r1["catalogo"]
    # alguma entrada de catálogo está vinculada a um item de contrato
    assert db.query(models.CatalogoPreco).filter(
        models.CatalogoPreco.item_contrato_id.isnot(None)).count() >= 1

    # idempotência: rodar de novo não duplica
    r2 = seed_ata(db)
    assert r2["contrato"] == 0
    assert r2["itens"] == 0
    assert r2["catalogo"] == 0
    assert db.query(models.ItemContrato).filter_by(contrato_id=contrato.id).count() == 22
    assert db.query(models.CatalogoPreco).count() == n_cat
    db.close()
