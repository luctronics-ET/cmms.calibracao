from datetime import date, timedelta


def _cria_contrato(client, **over):
    body = {"numero": "ATA MQT 129/2025", "tipo": "ATA", "fornecedor": "MQT Serviços",
            "valor_total": 1000.0}
    body.update(over)
    r = client.post("/api/v1/contratos", json=body)
    assert r.status_code == 201
    return r.json()


def _add_item(client, cid, **over):
    body = {"numero": "14", "descricao": "Calibração de multímetro",
            "quantidade": 10, "valor_unitario": 50.0, "usado": 0}
    body.update(over)
    r = client.post(f"/api/v1/contratos/{cid}/itens", json=body)
    assert r.status_code == 201
    return r.json()


def test_cria_e_lista_contrato(client):
    _cria_contrato(client)
    r = client.get("/api/v1/contratos")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["itens"][0]["numero"] == "ATA MQT 129/2025"


def test_status_vigencia(client):
    hoje = date.today()
    _cria_contrato(client, numero="Futuro", vigencia_fim=str(hoje + timedelta(days=400)))
    _cria_contrato(client, numero="Vencido", vigencia_fim=str(hoje - timedelta(days=5)))
    por = {c["numero"]: c for c in client.get("/api/v1/contratos").json()["itens"]}
    assert por["Futuro"]["status_vigencia"] == "VALIDO"
    assert por["Vencido"]["status_vigencia"] == "VENCIDO"


def test_itens_recalculam_saldo(client):
    c = _cria_contrato(client, valor_total=1000.0)
    _add_item(client, c["id"], quantidade=10, valor_unitario=50.0, usado=0)   # valor_saldo 500
    c2 = _add_item(client, c["id"], quantidade=10, valor_unitario=50.0, usado=10)  # valor_saldo 0
    assert c2["valor_saldo_total"] == 500.0
    assert c2["status_saldo"] == "OK"     # 500/1000 = 50% >= 20%


def test_saldo_baixo_e_esgotado(client):
    c = _cria_contrato(client, valor_total=1000.0)
    # um único item quase todo usado -> saldo 100 (10%) -> BAIXO
    c2 = _add_item(client, c["id"], quantidade=10, valor_unitario=100.0, usado=9)
    assert c2["valor_saldo_total"] == 100.0
    assert c2["status_saldo"] == "BAIXO"


def test_put_item_e_delete_item(client):
    c = _cria_contrato(client, valor_total=1000.0)
    item = _add_item(client, c["id"], quantidade=10, valor_unitario=50.0, usado=0)["itens"][0]
    r = client.put(f"/api/v1/contratos/{c['id']}/itens/{item['id']}",
                   json={"numero": "14", "quantidade": 10, "valor_unitario": 50.0, "usado": 10})
    assert r.status_code == 200
    assert r.json()["itens"][0]["saldo"] == 0
    r2 = client.delete(f"/api/v1/contratos/{c['id']}/itens/{item['id']}")
    assert r2.status_code == 200
    assert r2.json()["itens"] == []


def test_obter_404_e_delete_contrato(client):
    assert client.get("/api/v1/contratos/99999").status_code == 404
    c = _cria_contrato(client)
    _add_item(client, c["id"])
    assert client.delete(f"/api/v1/contratos/{c['id']}").status_code == 204
    assert client.get(f"/api/v1/contratos/{c['id']}").status_code == 404


def test_alertas_vigencia_ou_saldo(client):
    hoje = date.today()
    ok = _cria_contrato(client, numero="OK", valor_total=1000.0,
                        vigencia_fim=str(hoje + timedelta(days=400)))
    _add_item(client, ok["id"], quantidade=10, valor_unitario=100.0, usado=0)  # saldo 100% -> OK
    venc = _cria_contrato(client, numero="Vencendo", valor_total=1000.0,
                          vigencia_fim=str(hoje + timedelta(days=10)))
    _add_item(client, venc["id"], quantidade=10, valor_unitario=100.0, usado=0)
    baixo = _cria_contrato(client, numero="SaldoBaixo", valor_total=1000.0,
                           vigencia_fim=str(hoje + timedelta(days=400)))
    _add_item(client, baixo["id"], quantidade=10, valor_unitario=100.0, usado=9)  # 10% -> BAIXO
    nomes = [c["numero"] for c in client.get("/api/v1/contratos/alertas").json()]
    assert "OK" not in nomes
    assert "Vencendo" in nomes
    assert "SaldoBaixo" in nomes
