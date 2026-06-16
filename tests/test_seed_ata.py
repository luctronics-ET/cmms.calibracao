from backend.db import get_db
from backend import models
from backend.dominios import seed_dominios
from backend.seed_ata import seed_ata


def _db(client):
    # reaproveita a sessão de teste via dependency override do conftest
    gen = __import__("backend.main", fromlist=["app"]).app.dependency_overrides[get_db]()
    return next(gen)


def test_seed_cria_lab_contrato_itens(client):
    db = _db(client)
    seed_dominios(db)
    r1 = seed_ata(db)
    assert r1["contrato"] == 1
    assert r1["itens"] == 22
    contrato = db.query(models.Contrato).filter_by(numero="ATA MQT 129/2025").first()
    assert contrato is not None
    # fornecedor do contrato = laboratório (FK), não texto
    assert contrato.laboratorio is not None
    assert contrato.laboratorio.razao_social == "MQT Serviços Metrológicos Ltda"
    assert db.query(models.ItemContrato).filter_by(contrato_id=contrato.id).count() == 22
    db.close()


def test_seed_idempotente(client):
    db = _db(client)
    seed_dominios(db)
    seed_ata(db)
    n_lab = db.query(models.Laboratorio).count()
    r2 = seed_ata(db)
    assert r2["contrato"] == 0
    assert r2["itens"] == 0
    contrato = db.query(models.Contrato).filter_by(numero="ATA MQT 129/2025").first()
    assert db.query(models.ItemContrato).filter_by(contrato_id=contrato.id).count() == 22
    assert db.query(models.Laboratorio).count() == n_lab  # não duplica o lab
    db.close()
