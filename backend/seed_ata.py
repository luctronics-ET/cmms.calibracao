"""Seed idempotente da ATA 129/2025 (contrato + itens + catálogo). Roda no startup."""
from __future__ import annotations
import unicodedata
from backend.db import SessionLocal
from backend.models import (
    Contrato, ItemContrato, CatalogoPreco, TipoInstrumento, ContratoTipo,
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

# Transcrito de CATALOG_DEFAULT (linhas 1699-1908): { "TIPO": [ {forn, preco, item, tipo}, ... ] }
_CATALOG = {
    "TORQUÍMETRO": [{"forn": "MQT Serviços", "preco": 70.0, "item": "35", "tipo": "ata"}],
    "MULTÍMETRO": [
        {"forn": "MQT Serviços", "preco": 165.0, "item": "14", "tipo": "ata"},
        {"forn": "CMS (interno)", "preco": 243.67, "item": None, "tipo": "interno"},
    ],
    "MANÔMETRO ANALÓGICO": [{"forn": "MQT Serviços", "preco": 65.0, "item": "26", "tipo": "ata"}],
    "MANÔMETRO ANALÓGICO  BACS": [{"forn": "MQT Serviços", "preco": 140.0, "item": "27", "tipo": "ata"}],
    "MICROMETRO DE PROFUNDIDADE": [{"forn": "MQT Serviços", "preco": 85.0, "item": "31", "tipo": "ata"}],
    "PAQUÍMETRO": [{"forn": "MQT Serviços", "preco": 45.0, "item": "33", "tipo": "ata"}],
    "CONTADOR": [{"forn": "MQT Serviços", "preco": 450.0, "item": "5", "tipo": "ata"}],
    "FONTE DC": [
        {"forn": "MQT Serviços", "preco": 180.0, "item": "9", "tipo": "ata"},
        {"forn": "MQT (AMETEK propr.)", "preco": 350.0, "item": "10", "tipo": "ata"},
    ],
    "OSCILOSCÓPIO": [{"forn": "MQT Serviços", "preco": 475.0, "item": "18", "tipo": "ata"}],
    "MEGÔHMETRO": [{"forn": "MQT Serviços", "preco": 260.0, "item": "13", "tipo": "ata"}],
    "GERADOR DE FUNÇÕES": [{"forn": "MQT Serviços", "preco": 410.0, "item": "11", "tipo": "ata"}],
    "OHMÍMETRO": [{"forn": "MQT Serviços", "preco": 456.0, "item": "17", "tipo": "ata"}],
    "DINAMÔMETRO": [{"forn": "MQT Serviços", "preco": 240.0, "item": "23", "tipo": "ata"}],
    "DINAMÔMETRO DIGITAL": [{"forn": "MQT Serviços", "preco": 228.0, "item": "24", "tipo": "ata"}],
    "MANÔMETRO DIGITAL": [{"forn": "MQT Serviços", "preco": 70.0, "item": "28", "tipo": "ata"}],
    "MANOVACUÔMETRO ANALÓGICO": [{"forn": "MQT Serviços", "preco": 133.0, "item": "29", "tipo": "ata"}],
    "MEDIDOR DE FLUXO / VALVULA DE ALIVIO": [{"forn": "MQT Serviços", "preco": 199.0, "item": "30", "tipo": "ata"}],
    "VÁLVULA DE ALÍVIO": [{"forn": "MQT Serviços", "preco": 199.0, "item": "30", "tipo": "ata"}],
    "NÍVEL LINEAR DE PRECISÃO": [{"forn": "MQT Serviços", "preco": 80.0, "item": "32", "tipo": "ata"}],
    "TERMÔMETRO": [{"forn": "MQT Serviços", "preco": 65.0, "item": "34", "tipo": "ata"}],
    "TERMÔMETRO DIGITAL": [{"forn": "MQT Serviços", "preco": 65.0, "item": "34", "tipo": "ata"}],
    "DIFFERENTIAL PROBE": [{"forn": "MQT Serviços", "preco": 322.0, "item": "7", "tipo": "ata"}],
    "ALICATE AMPERÍMETRO": [{"forn": "MQT Serviços", "preco": 240.0, "item": "1", "tipo": "ata"}],
    "IGNITER CIRCUIT TEST": [{"forn": "CMS (interno)", "preco": 483.5, "item": None, "tipo": "interno"}],
    "GROUND STRAP TESTER": [{"forn": "CMS (interno)", "preco": 322.24, "item": None, "tipo": "interno"}],
    "ANALISADOR DE SEGURANÇA": [{"forn": "CMS (interno)", "preco": 967.01, "item": None, "tipo": "interno"}],
    "ANALISADOR DE ESPECTRO": [{"forn": "CMASM (interno)", "preco": 1450.51, "item": None, "tipo": "interno"}],
    "BALANÇA DIGITAL": [{"forn": "Visomes", "preco": 320.0, "item": None, "tipo": "ata"}],
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().replace(" ", "")


def _match_tipo(db, chave: str, tipos: list[TipoInstrumento]) -> TipoInstrumento | None:
    """Acha o TipoInstrumento cujo nome normalizado esteja CONTIDO na chave do catálogo.
    Em empate, o nome de domínio mais longo vence."""
    alvo = _norm(chave)
    candidatos = [t for t in tipos if _norm(t.nome) and _norm(t.nome) in alvo]
    if not candidatos:
        return None
    return max(candidatos, key=lambda t: len(_norm(t.nome)))


def seed_ata(db) -> dict:
    contagem = {"contrato": 0, "itens": 0, "catalogo": 0, "tipos_nao_casados": []}

    contrato = db.query(Contrato).filter_by(numero=_ATA["numero"]).first()
    if contrato is None:
        contrato = Contrato(numero=_ATA["numero"], tipo=ContratoTipo.ATA,
                            fornecedor=_ATA["fornecedor"], valor_total=_ATA["teto"], ativo=True)
        db.add(contrato)
        db.flush()
        contagem["contrato"] = 1

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

    tipos = db.query(TipoInstrumento).all()
    existentes = {(c.tipo_id, c.fornecedor, c.item_contrato_id)
                  for c in db.query(CatalogoPreco).all()}
    nao_casados = set()
    for chave, opcoes in _CATALOG.items():
        tipo = _match_tipo(db, chave, tipos)
        if tipo is None:
            nao_casados.add(chave)
            continue
        for o in opcoes:
            item_id = None
            if o.get("item"):
                item = itens_por_numero.get(str(o["item"]))
                item_id = item.id if item else None
            chave_unica = (tipo.id, o.get("forn"), item_id)
            if chave_unica in existentes:
                continue
            db.add(CatalogoPreco(tipo_id=tipo.id, fornecedor=o.get("forn"),
                                 preco=o.get("preco"), item_contrato_id=item_id, ativo=True))
            existentes.add(chave_unica)
            contagem["catalogo"] += 1

    contagem["tipos_nao_casados"] = sorted(nao_casados)
    db.commit()
    return contagem


def main() -> None:
    db = SessionLocal()
    try:
        r = seed_ata(db)
        print(f"seed_ata: contrato={r['contrato']} itens={r['itens']} "
              f"catalogo={r['catalogo']} nao_casados={len(r['tipos_nao_casados'])}")
        if r["tipos_nao_casados"]:
            print("  tipos sem match no domínio:", ", ".join(r["tipos_nao_casados"]))
    finally:
        db.close()


if __name__ == "__main__":
    main()
