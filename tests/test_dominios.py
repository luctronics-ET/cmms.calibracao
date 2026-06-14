from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base
from backend import models
from backend.dominios import seed_dominios


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'d.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_seed_cria_15_familias(tmp_path):
    db = _session(tmp_path)
    seed_dominios(db)
    assert db.query(models.FamiliaMetrologica).count() == 15


def test_seed_cria_unidades_grandezas_tipos(tmp_path):
    db = _session(tmp_path)
    seed_dominios(db)
    assert db.query(models.UnidadeMedida).count() > 0
    assert db.query(models.Grandeza).count() > 0
    assert db.query(models.TipoInstrumento).count() > 0


def test_seed_idempotente(tmp_path):
    db = _session(tmp_path)
    seed_dominios(db)
    n1 = db.query(models.FamiliaMetrologica).count()
    seed_dominios(db)  # roda de novo
    n2 = db.query(models.FamiliaMetrologica).count()
    assert n1 == n2 == 15


def test_grandeza_ligada_a_familia(tmp_path):
    db = _session(tmp_path)
    seed_dominios(db)
    g = db.query(models.Grandeza).filter_by(nome="Tensão DC").first()
    assert g is not None
    assert g.familia is not None
    assert g.familia.nome == "Eletricidade e Magnetismo"
