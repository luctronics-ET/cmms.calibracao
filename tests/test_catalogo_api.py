from datetime import date, timedelta


def _lab_contrato_item(client, dias_fim=400, quantidade=10, usado=0, valor=50.0):
    lab = client.post("/api/v1/laboratorios", json={"razao_social": "Lab Cat"}).json()
    fim = str(date.today() + timedelta(days=dias_fim))
    c = client.post("/api/v1/contratos", json={
        "numero": "ATA C", "tipo": "ATA", "laboratorio_id": lab["id"],
        "valor_total": 1000.0, "vigencia_fim": fim}).json()
    client.post(f"/api/v1/contratos/{c['id']}/itens", json={
        "numero": "14", "descricao": "CALIBRAÇÃO DE MULTÍMETRO",
        "quantidade": quantidade, "valor_unitario": valor, "usado": usado})
    return lab, client.get(f"/api/v1/contratos/{c['id']}").json()


def test_catalogo_deriva_dos_itens_de_contrato(client):
    lab, c = _lab_contrato_item(client, quantidade=10, usado=3, valor=50.0)
    r = client.get("/api/v1/catalogo")
    assert r.status_code == 200
    itens = r.json()["itens"]
    assert len(itens) == 1
    linha = itens[0]
    assert linha["laboratorio"] == "Lab Cat"
    assert linha["contrato_numero"] == "ATA C"
    assert linha["descricao"] == "CALIBRAÇÃO DE MULTÍMETRO"
    assert linha["preco"] == 50.0
    assert linha["saldo"] == 7          # 10 - 3
    assert linha["valor_saldo"] == 350.0
    assert linha["vigente"] is True


def test_catalogo_filtra_por_laboratorio(client):
    lab_a, _ = _lab_contrato_item(client)
    # cria outro lab+contrato+item
    lab_b = client.post("/api/v1/laboratorios", json={"razao_social": "Lab B"}).json()
    cb = client.post("/api/v1/contratos", json={
        "numero": "ATA B", "tipo": "ATA", "laboratorio_id": lab_b["id"]}).json()
    client.post(f"/api/v1/contratos/{cb['id']}/itens", json={
        "numero": "1", "descricao": "X", "quantidade": 1, "valor_unitario": 10.0})
    r = client.get("/api/v1/catalogo", params={"laboratorio_id": lab_a["id"]})
    itens = r.json()["itens"]
    assert all(i["laboratorio"] == "Lab Cat" for i in itens)
    assert len(itens) == 1


def test_catalogo_apenas_vigentes(client):
    # contrato vencido -> item não vigente
    _lab_contrato_item(client, dias_fim=-5)
    assert client.get("/api/v1/catalogo").json()["total"] == 1
    assert client.get("/api/v1/catalogo", params={"apenas_vigentes": True}).json()["total"] == 0
