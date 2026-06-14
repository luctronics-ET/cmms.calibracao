import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base, get_db
from backend import models
from backend.dominios import seed_dominios
from backend.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path/'t.db'}",
                           connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    import backend.routers.instrumentos as _instr_mod
    monkeypatch.setattr(_instr_mod, "UPLOAD_DIR", tmp_path / "uploads")
    import backend.routers.calibracoes as _cal_mod
    monkeypatch.setattr(_cal_mod, "UPLOAD_DIR", tmp_path / "uploads")

    db = TestingSession()
    seed_dominios(db)
    fam = db.query(models.FamiliaMetrologica).filter_by(nome="Eletricidade e Magnetismo").first()
    fam_mec = db.query(models.FamiliaMetrologica).filter_by(nome="Dimensional").first()
    tipo = db.query(models.TipoInstrumento).filter_by(nome="Multímetro").first()
    tipo_paq = db.query(models.TipoInstrumento).filter_by(nome="Paquímetro").first()
    db.add_all([
        models.Instrumento(codigo_interno="A-1", equipamento="MULTÍMETRO", marca="Fluke",
                           disciplina=models.Disciplina.ELE, sistema="MK-48",
                           familia_id=fam.id, tipo_id=tipo.id, ciclo_meses=12,
                           data_validade=date(2020, 1, 1), flag_origem="DESCALIBRADO"),
        models.Instrumento(codigo_interno="A-2", equipamento="PAQUÍMETRO",
                           disciplina=models.Disciplina.MEC, sistema="F-21",
                           familia_id=fam_mec.id, tipo_id=tipo_paq.id, ciclo_meses=12,
                           data_validade=date(2099, 1, 1), flag_origem="CALIBRADO"),
        models.Instrumento(codigo_interno="A-3", equipamento="TORQUÍMETRO",
                           disciplina=models.Disciplina.MEC, sistema="MK-48",
                           ciclo_meses=12, data_validade=None, flag_origem=""),
    ])
    db.commit()
    db.close()

    def _override():
        d = TestingSession()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()
