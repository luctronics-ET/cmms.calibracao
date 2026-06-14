"""Seed idempotente das tabelas de domínio metrológico (taxonomia RBC/INMETRO)."""
from __future__ import annotations
from sqlalchemy.orm import Session
from backend.models import FamiliaMetrologica, UnidadeMedida, Grandeza, TipoInstrumento

# 15 grupos oficiais da RBC/INMETRO
FAMILIAS = [
    "Acústica e Vibrações",
    "Alta Frequência e Telecomunicações",
    "Dimensional",
    "Eletricidade e Magnetismo",
    "Físico-Química",
    "Força, Torque e Dureza",
    "Massa",
    "Óptica",
    "Pressão",
    "Radiações Ionizantes",
    "Temperatura e Umidade",
    "Tempo e Frequência",
    "Vazão e Velocidade de Fluidos",
    "Viscosidade",
    "Volume e Massa Específica",
]

# (nome, simbolo)
UNIDADES = [
    ("Volt", "V"), ("Ampère", "A"), ("Ohm", "Ω"), ("Hertz", "Hz"),
    ("Metro", "m"), ("Milímetro", "mm"), ("Micrômetro", "µm"),
    ("Quilograma", "kg"), ("Grama", "g"), ("Newton-metro", "N·m"),
    ("Pascal", "Pa"), ("Bar", "bar"), ("Grau Celsius", "°C"),
    ("Umidade Relativa", "%UR"), ("Litro", "L"), ("Mililitro", "mL"),
]

# (nome_grandeza, nome_familia, simbolo_unidade_padrao)
GRANDEZAS = [
    ("Tensão DC", "Eletricidade e Magnetismo", "V"),
    ("Tensão AC", "Eletricidade e Magnetismo", "V"),
    ("Corrente DC", "Eletricidade e Magnetismo", "A"),
    ("Resistência", "Eletricidade e Magnetismo", "Ω"),
    ("Frequência", "Tempo e Frequência", "Hz"),
    ("Comprimento", "Dimensional", "mm"),
    ("Massa", "Massa", "kg"),
    ("Torque", "Força, Torque e Dureza", "N·m"),
    ("Pressão", "Pressão", "Pa"),
    ("Temperatura", "Temperatura e Umidade", "°C"),
    ("Umidade", "Temperatura e Umidade", "%UR"),
    ("Volume", "Volume e Massa Específica", "L"),
]

# (nome_tipo, nome_familia | None)
TIPOS = [
    ("Multímetro", "Eletricidade e Magnetismo"),
    ("Osciloscópio", "Eletricidade e Magnetismo"),
    ("Fonte DC", "Eletricidade e Magnetismo"),
    ("Calibrador", "Eletricidade e Magnetismo"),
    ("Gerador de Funções", "Tempo e Frequência"),
    ("Paquímetro", "Dimensional"),
    ("Micrômetro", "Dimensional"),
    ("Torquímetro", "Força, Torque e Dureza"),
    ("Dinamômetro", "Força, Torque e Dureza"),
    ("Manômetro", "Pressão"),
    ("Termômetro", "Temperatura e Umidade"),
    ("Balança", "Massa"),
]


def _get_or_create(db: Session, modelo, nome: str, **extra):
    obj = db.query(modelo).filter_by(nome=nome).first()
    if obj is None:
        obj = modelo(nome=nome, **extra)
        db.add(obj)
        db.flush()
    return obj


def seed_dominios(db: Session) -> None:
    for i, nome in enumerate(FAMILIAS):
        _get_or_create(db, FamiliaMetrologica, nome, ordem=i)
    for i, (nome, simb) in enumerate(UNIDADES):
        u = _get_or_create(db, UnidadeMedida, nome, ordem=i)
        u.simbolo = simb
    fam = {f.nome: f for f in db.query(FamiliaMetrologica).all()}
    uni_por_simbolo = {u.simbolo: u for u in db.query(UnidadeMedida).all()}
    for i, (nome, fam_nome, simb) in enumerate(GRANDEZAS):
        g = _get_or_create(db, Grandeza, nome, ordem=i)
        g.familia_id = fam[fam_nome].id
        g.unidade_padrao_id = uni_por_simbolo[simb].id if simb in uni_por_simbolo else None
    for i, (nome, fam_nome) in enumerate(TIPOS):
        t = _get_or_create(db, TipoInstrumento, nome, ordem=i)
        t.familia_id = fam[fam_nome].id if fam_nome else None
    db.commit()


if __name__ == "__main__":
    from backend.db import SessionLocal
    s = SessionLocal()
    try:
        seed_dominios(s)
        print("seed concluído")
    finally:
        s.close()
