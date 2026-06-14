def test_lista_instrumentos(client):
    r = client.get("/api/v1/instrumentos")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert {i["codigo_interno"] for i in body["itens"]} == {"A-1", "A-2", "A-3"}


def test_status_derivado(client):
    itens = {i["codigo_interno"]: i for i in client.get("/api/v1/instrumentos").json()["itens"]}
    assert itens["A-1"]["status"] == "VENCIDO"
    assert itens["A-2"]["status"] == "VALIDO"
    assert itens["A-3"]["status"] == "SEM_DATA"


def test_filtro_por_disciplina(client):
    r = client.get("/api/v1/instrumentos", params={"disciplina": "MEC"})
    assert r.json()["total"] == 2


def test_filtro_por_status(client):
    r = client.get("/api/v1/instrumentos", params={"status": "VENCIDO"})
    assert r.json()["total"] == 1
    assert r.json()["itens"][0]["codigo_interno"] == "A-1"


def test_busca_por_codigo(client):
    r = client.get("/api/v1/instrumentos", params={"busca": "A-2"})
    assert r.json()["total"] == 1


def test_get_um(client):
    primeiro = client.get("/api/v1/instrumentos").json()["itens"][0]["id"]
    r = client.get(f"/api/v1/instrumentos/{primeiro}")
    assert r.status_code == 200
    assert r.json()["id"] == primeiro


def test_get_inexistente_404(client):
    assert client.get("/api/v1/instrumentos/99999").status_code == 404
