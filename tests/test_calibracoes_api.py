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
