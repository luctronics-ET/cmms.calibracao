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
