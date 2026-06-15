from datetime import date, timedelta


def _cria_lab(client, **over):
    body = {"razao_social": "Lab RBC Alfa", "cnpj": "00.000.000/0001-00",
            "numero_cgcre": "CRL-0123", "acreditado_rbc": True,
            "escopo": "VDC, IDC, Temperatura"}
    body.update(over)
    r = client.post("/api/v1/laboratorios", json=body)
    assert r.status_code == 201
    return r.json()


def test_cria_e_lista_laboratorio(client):
    _cria_lab(client)
    r = client.get("/api/v1/laboratorios")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["itens"][0]["razao_social"] == "Lab RBC Alfa"


def test_status_acreditacao_valida_vencida_a_vencer(client):
    hoje = date.today()
    _cria_lab(client, razao_social="Valida", acreditacao_validade=str(hoje + timedelta(days=400)))
    _cria_lab(client, razao_social="Vencida", acreditacao_validade=str(hoje - timedelta(days=5)))
    _cria_lab(client, razao_social="AVencer", acreditacao_validade=str(hoje + timedelta(days=20)))
    _cria_lab(client, razao_social="SemData", acreditacao_validade=None)
    por_nome = {l["razao_social"]: l for l in client.get("/api/v1/laboratorios").json()["itens"]}
    assert por_nome["Valida"]["status_acreditacao"] == "VALIDO"
    assert por_nome["Vencida"]["status_acreditacao"] == "VENCIDO"
    assert por_nome["AVencer"]["status_acreditacao"] == "A_VENCER_30"
    assert por_nome["SemData"]["status_acreditacao"] == "SEM_DATA"


def test_obter_404(client):
    assert client.get("/api/v1/laboratorios/99999").status_code == 404


def test_atualiza_laboratorio(client):
    lab = _cria_lab(client)
    r = client.put(f"/api/v1/laboratorios/{lab['id']}",
                   json={"razao_social": "Lab Renomeado", "acreditado_rbc": False})
    assert r.status_code == 200
    assert r.json()["razao_social"] == "Lab Renomeado"
    assert r.json()["acreditado_rbc"] is False


def test_alertas_so_traz_vencendo_ordenado(client):
    hoje = date.today()
    _cria_lab(client, razao_social="OK", acreditacao_validade=str(hoje + timedelta(days=400)))
    _cria_lab(client, razao_social="Venc", acreditacao_validade=str(hoje - timedelta(days=2)))
    _cria_lab(client, razao_social="Logo", acreditacao_validade=str(hoje + timedelta(days=10)))
    alertas = client.get("/api/v1/laboratorios/alertas").json()
    nomes = [a["razao_social"] for a in alertas]
    assert "OK" not in nomes
    assert nomes == ["Venc", "Logo"]  # vencido primeiro, depois a vencer


def test_registro_calibracao_com_laboratorio_id_faz_snapshot(client):
    lab = _cria_lab(client, razao_social="Lab Snap", cnpj="11.111.111/0001-11",
                    numero_cgcre="CRL-999", acreditado_rbc=True)
    iid = client.get("/api/v1/instrumentos").json()["itens"][0]["id"]
    r = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "resultado": "APROVADO",
        "laboratorio_id": lab["id"]})
    assert r.status_code == 201
    cal = r.json()["calibracao"]
    assert cal["laboratorio_id"] == lab["id"]
    assert cal["laboratorio"] == "Lab Snap"          # snapshot
    assert cal["numero_cgcre"] == "CRL-999"          # snapshot
    assert cal["acreditacao_rbc"] is True            # snapshot


def test_delete_laboratorio_zera_fk_mas_mantem_snapshot(client):
    lab = _cria_lab(client, razao_social="Lab Some")
    iid = client.get("/api/v1/instrumentos").json()["itens"][0]["id"]
    client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "resultado": "APROVADO",
        "laboratorio_id": lab["id"]})
    assert client.delete(f"/api/v1/laboratorios/{lab['id']}").status_code == 204
    cal = client.get(f"/api/v1/instrumentos/{iid}/calibracoes").json()["itens"][0]
    assert cal["laboratorio_id"] is None             # FK zerada
    assert cal["laboratorio"] == "Lab Some"          # snapshot permanece


def test_historico_por_laboratorio(client):
    lab = _cria_lab(client, razao_social="Lab Hist")
    iid = client.get("/api/v1/instrumentos").json()["itens"][0]["id"]
    client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "resultado": "APROVADO",
        "laboratorio_id": lab["id"]})
    hist = client.get(f"/api/v1/laboratorios/{lab['id']}/calibracoes").json()
    assert hist["total"] == 1
    assert hist["itens"][0]["laboratorio_id"] == lab["id"]
