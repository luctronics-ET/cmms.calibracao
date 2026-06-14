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


from pathlib import Path

FIXTURE = ("tests/fixtures/amostra_inventario.csv", )


def _enviar(client, rota):
    data = Path("tests/fixtures/amostra_inventario.csv").read_bytes()
    return client.post(rota, files={"arquivo": ("inv.csv", data, "text/csv")})


def test_preview_nao_grava(client):
    r = _enviar(client, "/api/v1/importacao/preview")
    assert r.status_code == 200
    assert r.json()["totais"]["total_linhas"] == 5
    # nada foi inserido além do seed (3)
    assert client.get("/api/v1/instrumentos").json()["total"] == 3


def test_commit_insere(client):
    r = _enviar(client, "/api/v1/importacao/commit")
    assert r.status_code == 200
    assert r.json()["inseridos"] == 5
    assert client.get("/api/v1/instrumentos").json()["total"] == 8


def test_commit_aplica_status_baixado(client):
    _enviar(client, "/api/v1/importacao/commit")
    itens = {i["codigo_interno"]: i for i in client.get("/api/v1/instrumentos").json()["itens"]}
    assert itens["CMASM-IDM-T48-269"]["status"] == "BAIXADO"


def test_kpis(client):
    k = client.get("/api/v1/dashboard/kpis").json()
    assert k["total"] == 3
    assert k["vencidos"] == 1      # A-1
    assert k["sem_data"] == 1      # A-3
    assert k["n_sistemas"] == 2    # MK-48, F-21
    assert any(s["status"] == "VENCIDO" and s["total"] == 1 for s in k["por_status"])


def test_alertas_ordenados_excluem_validos(client):
    a = client.get("/api/v1/alertas").json()
    cods = [i["codigo_interno"] for i in a]
    assert "A-2" not in cods          # VALIDO não entra
    assert cods[0] == "A-1"           # VENCIDO primeiro


def test_alertas_csv(client):
    r = client.get("/api/v1/alertas", params={"formato": "csv"})
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "A-1" in r.text
