import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base, get_db
from backend import models
from backend.main import app


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'t.db'}",
                           connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    db.add_all([
        models.Instrumento(codigo_interno="A-1", equipamento="MULTÍMETRO",
                           marca="Fluke",
                           disciplina=models.Disciplina.ELE, sistema="MK-48",
                           ciclo_meses=12, data_validade=date(2020, 1, 1),
                           flag_origem="DESCALIBRADO"),
        models.Instrumento(codigo_interno="A-2", equipamento="PAQUÍMETRO",
                           disciplina=models.Disciplina.MEC, sistema="F-21",
                           ciclo_meses=12, data_validade=date(2099, 1, 1),
                           flag_origem="CALIBRADO"),
        models.Instrumento(codigo_interno="A-3", equipamento="TORQUÍMETRO",
                           disciplina=models.Disciplina.MEC, sistema="MK-48",
                           ciclo_meses=12, data_validade=None,
                           flag_origem=""),
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
