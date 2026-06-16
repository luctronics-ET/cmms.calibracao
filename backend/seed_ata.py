"""Seed idempotente da ATA 129/2025 (laboratório + contrato + itens). Roda no startup."""
from __future__ import annotations
from backend.db import SessionLocal
from backend.models import (
    Contrato, ItemContrato, ContratoTipo, Laboratorio,
)

_ATA = {"numero": "ATA MQT 129/2025", "fornecedor": "MQT Serviços Metrológicos Ltda",
        "teto": 112114.00}

# Transcrito de .reference_readonly/calibracao_erp.html (ATA_ITEMS_SEED, linhas 1909-2063):
_ATA_ITENS = [
    {"item": 1, "desc": "CALIBRAÇÃO DE ALICATE AMPERÍMETRO", "quant": 2, "valor": 240.0, "usado": 0},
    {"item": 5, "desc": "CALIBRAÇÃO DE CONTADOR", "quant": 26, "valor": 450.0, "usado": 11},
    {"item": 7, "desc": "CALIBRAÇÃO DE DIFFERENTIAL PROBE", "quant": 2, "valor": 322.0, "usado": 1},
    {"item": 9, "desc": "CALIBRAÇÃO DE FONTE DC", "quant": 28, "valor": 180.0, "usado": 9},
    {"item": 10, "desc": "CALIBRAÇÃO DE FONTE DC PROPRIETÁRIA (AMETEK)", "quant": 2, "valor": 350.0, "usado": 0},
    {"item": 11, "desc": "CALIBRAÇÃO DE GERADOR DE FUNÇÕES", "quant": 32, "valor": 410.0, "usado": 5},
    {"item": 13, "desc": "CALIBRAÇÃO DE MEGÔHMETRO", "quant": 12, "valor": 260.0, "usado": 6},
    {"item": 14, "desc": "CALIBRAÇÃO DE MULTÍMETRO", "quant": 74, "valor": 165.0, "usado": 36},
    {"item": 17, "desc": "CALIBRAÇÃO DE OHMÍMETRO", "quant": 12, "valor": 456.0, "usado": 5},
    {"item": 18, "desc": "CALIBRAÇÃO DE OSCILOSCÓPIO", "quant": 16, "valor": 475.0, "usado": 7},
    {"item": 23, "desc": "CALIBRAÇÃO DE DINAMÔMETRO", "quant": 10, "valor": 240.0, "usado": 5},
    {"item": 24, "desc": "CALIBRAÇÃO DE DINAMÔMETRO DIGITAL", "quant": 6, "valor": 228.0, "usado": 3},
    {"item": 26, "desc": "CALIBRAÇÃO DE MANÔMETRO ANALÓGICO", "quant": 66, "valor": 65.0, "usado": 32},
    {"item": 27, "desc": "CALIBRAÇÃO DE MANÔMETRO ANALÓGICO BACS (ÁGUA SALGADA)", "quant": 2, "valor": 140.0, "usado": 1},
    {"item": 28, "desc": "CALIBRAÇÃO DE MANÔMETRO DIGITAL", "quant": 6, "valor": 70.0, "usado": 3},
    {"item": 29, "desc": "CALIBRAÇÃO DE MANOVACUÔMETRO ANALÓGICO", "quant": 2, "valor": 133.0, "usado": 1},
    {"item": 30, "desc": "CALIBRAÇÃO DE MEDIDOR DE FLUXO / VÁLVULA DE ALÍVIO", "quant": 6, "valor": 199.0, "usado": 5},
    {"item": 31, "desc": "CALIBRAÇÃO DE MICROMETRO DE PROFUNDIDADE", "quant": 46, "valor": 85.0, "usado": 23},
    {"item": 32, "desc": "CALIBRAÇÃO DE NÍVEL LINEAR DE PRECISÃO", "quant": 2, "valor": 80.0, "usado": 1},
    {"item": 33, "desc": "CALIBRAÇÃO DE PAQUÍMETRO", "quant": 24, "valor": 45.0, "usado": 12},
    {"item": 34, "desc": "CALIBRAÇÃO DE TERMÔMETRO", "quant": 4, "valor": 65.0, "usado": 3},
    {"item": 35, "desc": "CALIBRAÇÃO DE TORQUÍMETRO", "quant": 520, "valor": 70.0, "usado": 264},
]



def seed_ata(db) -> dict:
    contagem = {"contrato": 0, "itens": 0}

    # fornecedor do contrato = laboratório (get-or-create por razão social)
    lab = db.query(Laboratorio).filter_by(razao_social=_ATA["fornecedor"]).first()
    if lab is None:
        lab = Laboratorio(razao_social=_ATA["fornecedor"], ativo=True)
        db.add(lab)
        db.flush()

    contrato = db.query(Contrato).filter_by(numero=_ATA["numero"]).first()
    if contrato is None:
        contrato = Contrato(numero=_ATA["numero"], tipo=ContratoTipo.ATA,
                            laboratorio_id=lab.id, valor_total=_ATA["teto"], ativo=True)
        db.add(contrato)
        db.flush()
        contagem["contrato"] = 1
    elif contrato.laboratorio_id is None:
        contrato.laboratorio_id = lab.id

    itens_por_numero = {i.numero: i for i in
                        db.query(ItemContrato).filter_by(contrato_id=contrato.id).all()}
    for it in _ATA_ITENS:
        num = str(it["item"])
        if num in itens_por_numero:
            continue
        novo = ItemContrato(contrato_id=contrato.id, numero=num, descricao=it["desc"],
                            quantidade=it["quant"], valor_unitario=it["valor"], usado=it["usado"])
        db.add(novo)
        db.flush()
        itens_por_numero[num] = novo
        contagem["itens"] += 1

    # catálogo não é mais semeado: virou visão derivada dos itens de contrato.
    db.commit()
    return contagem


def main() -> None:
    db = SessionLocal()
    try:
        r = seed_ata(db)
        print(f"seed_ata: contrato={r['contrato']} itens={r['itens']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
