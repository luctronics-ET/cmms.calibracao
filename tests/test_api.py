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


def test_busca_por_marca(client):
    r = client.get("/api/v1/instrumentos", params={"busca": "fluke"})
    assert r.json()["total"] == 1
    assert r.json()["itens"][0]["codigo_interno"] == "A-1"


def test_busca_ignora_acentos(client):
    r = client.get("/api/v1/instrumentos", params={"busca": "paquimetro"})
    assert r.json()["total"] == 1
    assert r.json()["itens"][0]["codigo_interno"] == "A-2"


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


def test_dominios_lista_familias(client):
    d = client.get("/api/v1/dominios").json()
    assert len(d["familias"]) == 15
    assert any(f["nome"] == "Eletricidade e Magnetismo" for f in d["familias"])
    assert len(d["tipos"]) > 0
    assert len(d["grandezas"]) > 0
    assert len(d["unidades"]) > 0


def test_dominios_filtra_por_familia(client):
    full = client.get("/api/v1/dominios").json()
    fam_id = next(f["id"] for f in full["familias"] if f["nome"] == "Dimensional")
    d = client.get("/api/v1/dominios", params={"familia_id": fam_id}).json()
    assert all(t["familia_id"] == fam_id for t in d["tipos"])
    assert any(t["nome"] == "Paquímetro" for t in d["tipos"])
    assert all(g["familia_id"] == fam_id for g in d["grandezas"])


def _dom(client):
    d = client.get("/api/v1/dominios").json()
    fam = next(f for f in d["familias"] if f["nome"] == "Eletricidade e Magnetismo")
    tipo = next(t for t in d["tipos"] if t["nome"] == "Multímetro")
    return fam["id"], tipo["id"]


def test_criar_instrumento(client):
    fam_id, tipo_id = _dom(client)
    payload = {"equipamento": "FONTE DC", "familia_id": fam_id, "tipo_id": tipo_id,
               "ciclo_meses": 12, "status_operacional": "ATIVO",
               "codigo_patrimonial": "PAT-100", "fu": 3, "nc": 3, "ab": 2, "cm": 3, "ci": 2}
    r = client.post("/api/v1/instrumentos", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["equipamento"] == "FONTE DC"
    assert body["familia_nome"] == "Eletricidade e Magnetismo"
    assert body["igp"] == 3 + 6 + 2 + 6 + 2  # 19
    assert body["classe_prioridade"] == "MAXIMA"


def test_criar_sem_obrigatorio_falha(client):
    r = client.post("/api/v1/instrumentos", json={"familia_id": 1, "tipo_id": 1})
    assert r.status_code == 422  # falta equipamento


def test_patrimonio_duplicado_409(client):
    fam_id, tipo_id = _dom(client)
    p = {"equipamento": "X", "familia_id": fam_id, "tipo_id": tipo_id, "codigo_patrimonial": "DUP-1"}
    assert client.post("/api/v1/instrumentos", json=p).status_code == 201
    r2 = client.post("/api/v1/instrumentos", json={**p, "equipamento": "Y"})
    assert r2.status_code == 409


def test_editar_instrumento(client):
    primeiro = client.get("/api/v1/instrumentos").json()["itens"][0]
    fam_id, tipo_id = _dom(client)
    r = client.put(f"/api/v1/instrumentos/{primeiro['id']}",
                   json={"equipamento": "EDITADO", "familia_id": fam_id, "tipo_id": tipo_id,
                         "ciclo_meses": 24, "status_operacional": "EM_MANUTENCAO"})
    assert r.status_code == 200
    assert r.json()["equipamento"] == "EDITADO"
    assert r.json()["status_operacional"] == "EM_MANUTENCAO"
    assert r.json()["ciclo_meses"] == 24


def test_editar_inexistente_404(client):
    fam_id, tipo_id = _dom(client)
    r = client.put("/api/v1/instrumentos/99999",
                   json={"equipamento": "Z", "familia_id": fam_id, "tipo_id": tipo_id})
    assert r.status_code == 404


def test_filtro_classe_prioridade(client):
    fam_id, tipo_id = _dom(client)
    client.post("/api/v1/instrumentos", json={"equipamento": "CRIT", "familia_id": fam_id,
                "tipo_id": tipo_id, "fu": 3, "nc": 3, "ab": 3, "cm": 3, "ci": 3})  # igp 21
    r = client.get("/api/v1/instrumentos", params={"classe_prioridade": "MAXIMA"})
    assert r.json()["total"] >= 1
    assert all(i["classe_prioridade"] == "MAXIMA" for i in r.json()["itens"])


def _criar_basico(client):
    fam_id, tipo_id = _dom(client)
    return client.post("/api/v1/instrumentos", json={
        "equipamento": "UP", "familia_id": fam_id, "tipo_id": tipo_id}).json()["id"]


def test_upload_foto_aceita_imagem(client):
    iid = _criar_basico(client)
    r = client.post(f"/api/v1/instrumentos/{iid}/foto",
                    files={"arquivo": ("f.png", b"\x89PNG\r\n", "image/png")})
    assert r.status_code == 200
    assert r.json()["foto_path"] and r.json()["foto_path"].endswith(".png")


def test_upload_foto_rejeita_nao_imagem(client):
    iid = _criar_basico(client)
    r = client.post(f"/api/v1/instrumentos/{iid}/foto",
                    files={"arquivo": ("f.txt", b"abc", "text/plain")})
    assert r.status_code == 415


def test_upload_manual_aceita_pdf(client):
    iid = _criar_basico(client)
    r = client.post(f"/api/v1/instrumentos/{iid}/manual",
                    files={"arquivo": ("m.pdf", b"%PDF-1.4", "application/pdf")})
    assert r.status_code == 200
    assert r.json()["manual_path"].endswith(".pdf")


def test_upload_manual_rejeita_nao_pdf(client):
    iid = _criar_basico(client)
    r = client.post(f"/api/v1/instrumentos/{iid}/manual",
                    files={"arquivo": ("m.png", b"\x89PNG", "image/png")})
    assert r.status_code == 415


def test_patch_altera_so_o_campo_enviado(client):
    fam_id, tipo_id = _dom(client)
    iid = client.post("/api/v1/instrumentos", json={
        "equipamento": "ORIG", "familia_id": fam_id, "tipo_id": tipo_id,
        "ciclo_meses": 24, "marca": "Fluke"}).json()["id"]
    r = client.patch(f"/api/v1/instrumentos/{iid}", json={"secao": "Bancada 3"})
    assert r.status_code == 200
    body = r.json()
    assert body["secao"] == "Bancada 3"
    # preservados:
    assert body["equipamento"] == "ORIG"
    assert body["ciclo_meses"] == 24
    assert body["marca"] == "Fluke"


def test_patch_recalcula_igp(client):
    fam_id, tipo_id = _dom(client)
    iid = client.post("/api/v1/instrumentos", json={
        "equipamento": "X", "familia_id": fam_id, "tipo_id": tipo_id}).json()["id"]
    r = client.patch(f"/api/v1/instrumentos/{iid}",
                     json={"fu": 3, "nc": 3, "ab": 2, "cm": 3, "ci": 2})
    assert r.json()["igp"] == 19
    assert r.json()["classe_prioridade"] == "MAXIMA"


def test_patch_inexistente_404(client):
    assert client.patch("/api/v1/instrumentos/99999", json={"secao": "z"}).status_code == 404


def test_patch_patrimonio_duplicado_409(client):
    fam_id, tipo_id = _dom(client)
    client.post("/api/v1/instrumentos", json={"equipamento": "A", "familia_id": fam_id,
                "tipo_id": tipo_id, "codigo_patrimonial": "PX-1"})
    iid = client.post("/api/v1/instrumentos", json={"equipamento": "B", "familia_id": fam_id,
                      "tipo_id": tipo_id}).json()["id"]
    r = client.patch(f"/api/v1/instrumentos/{iid}", json={"codigo_patrimonial": "PX-1"})
    assert r.status_code == 409


def test_patch_corpo_parcial_sem_obrigatorios_ok(client):
    fam_id, tipo_id = _dom(client)
    iid = client.post("/api/v1/instrumentos", json={"equipamento": "Y", "familia_id": fam_id,
                      "tipo_id": tipo_id}).json()["id"]
    # corpo só com status — não exige equipamento/familia/tipo
    r = client.patch(f"/api/v1/instrumentos/{iid}", json={"status_operacional": "EM_MANUTENCAO"})
    assert r.status_code == 200
    assert r.json()["status_operacional"] == "EM_MANUTENCAO"
    assert r.json()["equipamento"] == "Y"


def test_patch_status_null_nao_quebra(client):
    fam_id, tipo_id = _dom(client)
    iid = client.post("/api/v1/instrumentos", json={"equipamento": "S", "familia_id": fam_id,
                      "tipo_id": tipo_id, "status_operacional": "EM_MANUTENCAO"}).json()["id"]
    r = client.patch(f"/api/v1/instrumentos/{iid}", json={"status_operacional": None, "secao": "B1"})
    assert r.status_code == 200
    assert r.json()["status_operacional"] == "EM_MANUTENCAO"   # preservado, não nulo
    assert r.json()["secao"] == "B1"


def test_export_formato_invalido_422(client):
    primeiro = client.get("/api/v1/instrumentos").json()["itens"][0]["id"]
    r = client.post("/api/v1/instrumentos/export",
                    json={"ids": [primeiro], "formato": "docx"})
    assert r.status_code == 422


def test_export_csv(client):
    itens = client.get("/api/v1/instrumentos").json()["itens"]
    ids = [i["id"] for i in itens]
    r = client.post("/api/v1/instrumentos/export", json={"ids": ids, "formato": "csv"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    texto = r.content.decode("utf-8-sig")
    assert "Código interno" in texto          # cabeçalho legível
    assert "A-1" in texto and "A-2" in texto and "A-3" in texto


def test_export_csv_preserva_ordem_dos_ids(client):
    itens = {i["codigo_interno"]: i for i in client.get("/api/v1/instrumentos").json()["itens"]}
    ids = [itens["A-3"]["id"], itens["A-1"]["id"], itens["A-2"]["id"]]
    r = client.post("/api/v1/instrumentos/export", json={"ids": ids, "formato": "csv"})
    linhas = r.content.decode("utf-8-sig").splitlines()
    # linha 0 = cabeçalho; depois os códigos na ordem dos ids
    assert linhas[1].startswith("A-3")
    assert linhas[2].startswith("A-1")
    assert linhas[3].startswith("A-2")


def test_export_ignora_ids_inexistentes(client):
    primeiro = client.get("/api/v1/instrumentos").json()["itens"][0]["id"]
    r = client.post("/api/v1/instrumentos/export",
                    json={"ids": [primeiro, 99999], "formato": "csv"})
    assert r.status_code == 200
    linhas = r.content.decode("utf-8-sig").splitlines()
    assert len(linhas) == 2     # cabeçalho + 1 item válido


def test_export_ids_vazio_400(client):
    r = client.post("/api/v1/instrumentos/export", json={"ids": [], "formato": "csv"})
    assert r.status_code == 400
