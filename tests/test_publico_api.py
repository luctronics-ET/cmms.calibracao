def _id_por_codigo(client, codigo):
    for i in client.get("/api/v1/instrumentos").json()["itens"]:
        if i["codigo_interno"] == codigo:
            return i["id"]
    raise AssertionError("instrumento não encontrado: " + codigo)


def test_publico_retorna_campos_curados(client):
    iid = _id_por_codigo(client, "A-1")  # fixture: validade 2020 → VENCIDO
    r = client.get(f"/api/v1/publico/instrumentos/{iid}")
    assert r.status_code == 200
    b = r.json()
    assert b["codigo_interno"] == "A-1"
    assert b["equipamento"]
    assert b["status"] == "VENCIDO"
    assert b["status_label"] == "Vencido"
    assert "status_operacional" in b


def test_publico_status_valido(client):
    iid = _id_por_codigo(client, "A-2")  # fixture: validade 2099 → VALIDO
    b = client.get(f"/api/v1/publico/instrumentos/{iid}").json()
    assert b["status"] == "VALIDO"


def test_publico_404(client):
    assert client.get("/api/v1/publico/instrumentos/99999").status_code == 404


def test_publico_nao_vaza_campos_sensiveis(client):
    iid = _id_por_codigo(client, "A-1")
    b = client.get(f"/api/v1/publico/instrumentos/{iid}").json()
    for proibido in ("custo_estimado", "custo_contratado", "observacoes",
                     "fu", "nc", "ab", "cm", "ci", "organizacao_calibradora",
                     "certificado_ref", "foto_path", "manual_path",
                     "local_calibracao", "serial", "flag_origem",
                     "divergencia_flag", "igp", "classe_prioridade"):
        assert proibido not in b, f"vazou campo sensível: {proibido}"
