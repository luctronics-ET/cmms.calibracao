def _tipo_id(client):
    return client.get("/api/v1/dominios").json()["tipos"][0]["id"]


def _cria_contrato_item(client):
    c = client.post("/api/v1/contratos", json={"numero": "ATA X", "tipo": "ATA"}).json()
    client.post(f"/api/v1/contratos/{c['id']}/itens",
                json={"numero": "14", "descricao": "Cal multímetro",
                      "quantidade": 10, "valor_unitario": 50.0, "usado": 0})
    c = client.get(f"/api/v1/contratos/{c['id']}").json()
    return c["id"], c["numero"], c["itens"][0]["id"], c["itens"][0]["numero"]


def test_cria_e_lista_catalogo(client):
    tid = _tipo_id(client)
    r = client.post("/api/v1/catalogo", json={"tipo_id": tid, "fornecedor": "MQT", "preco": 165.0})
    assert r.status_code == 201
    body = client.get("/api/v1/catalogo").json()
    assert body["total"] == 1
    assert body["itens"][0]["tipo_nome"] is not None
    assert body["itens"][0]["preco"] == 165.0


def test_filtro_por_tipo(client):
    tipos = client.get("/api/v1/dominios").json()["tipos"]
    a, b = tipos[0]["id"], tipos[1]["id"]
    client.post("/api/v1/catalogo", json={"tipo_id": a, "preco": 10.0})
    client.post("/api/v1/catalogo", json={"tipo_id": b, "preco": 20.0})
    r = client.get("/api/v1/catalogo", params={"tipo_id": a})
    assert r.json()["total"] == 1
    assert r.json()["itens"][0]["tipo_id"] == a


def test_vinculo_item_popula_derivados(client):
    tid = _tipo_id(client)
    cid, cnum, item_id, item_num = _cria_contrato_item(client)
    r = client.post("/api/v1/catalogo", json={
        "tipo_id": tid, "fornecedor": "MQT", "preco": 165.0, "item_contrato_id": item_id})
    assert r.status_code == 201
    body = r.json()
    assert body["item_contrato_id"] == item_id
    assert body["item_numero"] == item_num
    assert body["contrato_id"] == cid
    assert body["contrato_numero"] == cnum


def test_tipo_inexistente_404(client):
    r = client.post("/api/v1/catalogo", json={"tipo_id": 99999, "preco": 1.0})
    assert r.status_code == 404


def test_item_contrato_inexistente_404(client):
    tid = _tipo_id(client)
    r = client.post("/api/v1/catalogo", json={"tipo_id": tid, "item_contrato_id": 99999})
    assert r.status_code == 404


def test_put_e_delete(client):
    tid = _tipo_id(client)
    cat = client.post("/api/v1/catalogo", json={"tipo_id": tid, "preco": 10.0}).json()
    r = client.put(f"/api/v1/catalogo/{cat['id']}", json={"tipo_id": tid, "preco": 99.0})
    assert r.status_code == 200 and r.json()["preco"] == 99.0
    assert client.delete(f"/api/v1/catalogo/{cat['id']}").status_code == 204
    assert client.get(f"/api/v1/catalogo/{cat['id']}").status_code == 404
