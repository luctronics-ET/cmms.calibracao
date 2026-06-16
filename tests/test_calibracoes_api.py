from datetime import date


def _id_primeiro(client):
    return client.get("/api/v1/instrumentos").json()["itens"][0]["id"]


def test_post_calibracao_aprovada_recalcula_validade_e_status(client):
    iid = _id_primeiro(client)
    r = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "resultado": "APROVADO", "laboratorio": "RBC X",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["calibracao"]["data_validade"] == "2027-03-10"
    assert body["instrumento"]["data_validade"] == "2027-03-10"
    assert body["instrumento"]["status_operacional"] == "ATIVO"
    assert body["instrumento"]["data_ultima_calibracao"] == "2026-03-10"


def test_post_calibracao_reprovada_bloqueia(client):
    iid = _id_primeiro(client)
    r = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "resultado": "REPROVADO",
    })
    assert r.status_code == 201
    inst = r.json()["instrumento"]
    assert inst["status_operacional"] == "REPROVADO"
    assert inst["data_validade"] is None


def test_calibracao_mais_recente_prevalece(client):
    iid = _id_primeiro(client)
    client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2025-01-01", "resultado": "APROVADO"})
    client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-01-01", "resultado": "APROVADO"})
    inst = client.get(f"/api/v1/instrumentos/{iid}").json()
    assert inst["data_validade"] == "2027-01-01"


def test_get_historico_ordenado_desc(client):
    iid = _id_primeiro(client)
    client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2024-01-01", "resultado": "APROVADO"})
    client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-01-01", "resultado": "APROVADO"})
    r = client.get(f"/api/v1/instrumentos/{iid}/calibracoes")
    assert r.status_code == 200
    itens = r.json()["itens"]
    assert itens[0]["data_calibracao"] == "2026-01-01"
    assert itens[1]["data_calibracao"] == "2024-01-01"


def test_post_calibracao_instrumento_inexistente_404(client):
    r = client.post("/api/v1/instrumentos/99999/calibracoes", json={
        "data_calibracao": "2026-03-10", "resultado": "APROVADO"})
    assert r.status_code == 404


def _cria_cal(client):
    iid = _id_primeiro(client)
    cal = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "resultado": "APROVADO"}).json()["calibracao"]
    return iid, cal["id"]


def test_upload_certificado_pdf(client):
    iid, cid = _cria_cal(client)
    r = client.post(
        f"/api/v1/instrumentos/{iid}/calibracoes/{cid}/certificado",
        files={"arquivo": ("cert.pdf", b"%PDF-1.4 x", "application/pdf")},
    )
    assert r.status_code == 200
    assert r.json()["certificado_path"].endswith(f"cert_{cid}.pdf")


def test_upload_certificado_rejeita_nao_pdf(client):
    iid, cid = _cria_cal(client)
    r = client.post(
        f"/api/v1/instrumentos/{iid}/calibracoes/{cid}/certificado",
        files={"arquivo": ("x.png", b"\x89PNG", "image/png")},
    )
    assert r.status_code == 415


def test_upload_certificado_calibracao_inexistente_404(client):
    iid = _id_primeiro(client)
    r = client.post(
        f"/api/v1/instrumentos/{iid}/calibracoes/99999/certificado",
        files={"arquivo": ("cert.pdf", b"%PDF", "application/pdf")},
    )
    assert r.status_code == 404


def test_delete_calibracao_recalcula(client):
    iid = _id_primeiro(client)
    client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2025-01-01", "resultado": "APROVADO"})
    nova = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-01-01", "resultado": "APROVADO"}).json()["calibracao"]
    # apaga a mais recente -> validade volta a refletir a de 2025
    r = client.delete(f"/api/v1/instrumentos/{iid}/calibracoes/{nova['id']}")
    assert r.status_code == 200
    assert r.json()["data_validade"] == "2026-01-01"


def test_delete_unica_calibracao_limpa_datas(client):
    iid = _id_primeiro(client)
    cal = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "resultado": "APROVADO"}).json()["calibracao"]
    r = client.delete(f"/api/v1/instrumentos/{iid}/calibracoes/{cal['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["data_validade"] is None
    assert body["data_ultima_calibracao"] is None


def test_post_calibracao_aprovado_com_restricoes_tem_validade(client):
    iid = _id_primeiro(client)
    r = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "resultado": "APROVADO_COM_RESTRICOES",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["calibracao"]["data_validade"] == "2027-03-10"
    assert body["instrumento"]["status_operacional"] == "ATIVO"


def test_delete_calibracao_inexistente_404(client):
    iid = _id_primeiro(client)
    r = client.delete(f"/api/v1/instrumentos/{iid}/calibracoes/99999")
    assert r.status_code == 404


def test_backfill_cria_calibracao_origem_e_e_idempotente(client):
    # A fixture cria A-1 com data_validade=2020-01-01 e sem data_ultima_calibracao.
    # Damos a um instrumento uma data_ultima_calibracao para o backfill agir.
    from backend.db import get_db
    from backend import models, servico
    from backend.main import app
    from datetime import date as _date

    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    inst = db.query(models.Instrumento).filter_by(codigo_interno="A-2").first()
    inst.data_ultima_calibracao = _date(2026, 1, 5)
    inst.organizacao_calibradora = "Lab Origem"
    db.commit()

    n1 = servico.backfill_calibracoes_origem(db)
    assert n1 == 1
    cals = db.query(models.Calibracao).filter_by(instrumento_id=inst.id).all()
    assert len(cals) == 1
    assert cals[0].origem == "IMPORTACAO"
    assert cals[0].laboratorio == "Lab Origem"
    assert cals[0].resultado == models.Resultado.APROVADO

    # idempotente: rodar de novo não cria outra
    n2 = servico.backfill_calibracoes_origem(db)
    assert n2 == 0
    assert db.query(models.Calibracao).filter_by(instrumento_id=inst.id).count() == 1
    db.close()


# ── D: vínculo calibração ↔ item de contrato ────────────────────────────────
from datetime import timedelta


def _contrato_item_vigente(client, quantidade=10, valor=50.0, usado=0, dias_fim=400):
    lab = client.post("/api/v1/laboratorios", json={"razao_social": "Lab MQT"}).json()
    fim = str(date.today() + timedelta(days=dias_fim))
    c = client.post("/api/v1/contratos", json={
        "numero": "ATA D", "tipo": "ATA", "laboratorio_id": lab["id"],
        "valor_total": 1000.0, "vigencia_fim": fim}).json()
    client.post(f"/api/v1/contratos/{c['id']}/itens", json={
        "numero": "1", "descricao": "Cal", "quantidade": quantidade,
        "valor_unitario": valor, "usado": usado})
    c = client.get(f"/api/v1/contratos/{c['id']}").json()
    return lab, c, c["itens"][0]


def test_calibracao_vinculada_consome_saldo_e_herda_preco_lab(client):
    iid = _id_primeiro(client)
    lab, c, item = _contrato_item_vigente(client, valor=77.0, usado=0)
    r = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "item_contrato_id": item["id"]})
    assert r.status_code == 201
    cal = r.json()["calibracao"]
    assert cal["custo"] == 77.0                     # preço do item
    assert cal["laboratorio_id"] == lab["id"]       # lab herdado do contrato
    assert cal["item_contrato_id"] == item["id"]
    assert cal["contrato_numero"] == c["numero"]
    # saldo consumido: usado passou de 0 -> 1
    c2 = client.get(f"/api/v1/contratos/{c['id']}").json()
    assert c2["itens"][0]["usado"] == 1


def test_calibracao_contrato_vencido_bloqueia(client):
    iid = _id_primeiro(client)
    _, c, item = _contrato_item_vigente(client, dias_fim=-5)  # vencido
    r = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "item_contrato_id": item["id"]})
    assert r.status_code == 409


def test_calibracao_item_esgotado_bloqueia(client):
    iid = _id_primeiro(client)
    _, c, item = _contrato_item_vigente(client, quantidade=1, usado=1)  # sem saldo
    r = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "item_contrato_id": item["id"]})
    assert r.status_code == 409


def test_calibracao_item_inexistente_404(client):
    iid = _id_primeiro(client)
    r = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "item_contrato_id": 99999})
    assert r.status_code == 404


def test_delete_calibracao_vinculada_devolve_saldo(client):
    iid = _id_primeiro(client)
    _, c, item = _contrato_item_vigente(client, usado=0)
    cal = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "item_contrato_id": item["id"]}).json()["calibracao"]
    assert client.get(f"/api/v1/contratos/{c['id']}").json()["itens"][0]["usado"] == 1
    client.delete(f"/api/v1/instrumentos/{iid}/calibracoes/{cal['id']}")
    assert client.get(f"/api/v1/contratos/{c['id']}").json()["itens"][0]["usado"] == 0


def test_lista_calibracoes_recentes(client):
    iid = _id_primeiro(client)
    client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-05-01", "laboratorio": "RBC Z"})
    r = client.get("/api/v1/calibracoes")
    assert r.status_code == 200
    b = r.json()
    assert b["total"] >= 1
    assert b["itens"][0]["instrumento_id"] == iid
    assert "instrumento_codigo" in b["itens"][0]
