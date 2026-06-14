# SisCalib — Edição em Massa no Inventário — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** No inventário, abrir a ficha em modal ao clicar na linha, selecionar múltiplos itens por checkbox e editá-los em lote numa tabela editável por item — apoiado por um endpoint de atualização parcial (PATCH).

**Architecture:** Backend ganha `PATCH /instrumentos/{id}` (atualização parcial via `InstrumentoPatch` + `exclude_unset`). Frontend ganha um componente de modal reutilizável e um helper de render de ficha compartilhado em `app.js`; o inventário ganha coluna de checkbox, barra de seleção, modal de ficha no clique e um modal de edição em lote que salva via um PATCH por item.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, SQLite, pytest, HTML/CSS/JS vanilla.

**Spec:** `docs/superpowers/specs/2026-06-14-siscalib-edicao-massa-design.md`

---

## File Structure

| Arquivo | Mudança |
|---|---|
| `backend/schemas.py` | + `InstrumentoPatch` (todos os campos opcionais) |
| `backend/routers/instrumentos.py` | + `PATCH /instrumentos/{id}` e helper `_aplicar_parcial` |
| `frontend/app.js` | + `abrirModal`/`fecharModal`, `renderFichaResumo`, `SDK.patch` |
| `frontend/siscalib.css` | + estilos de modal e barra de seleção |
| `frontend/ficha.html` | usar `renderFichaResumo` (DRY com o modal) |
| `frontend/inventario.html` | checkbox + selecionar-todos, barra de ação, modal de ficha, modal de edição em lote |
| `tests/test_api.py` | testes do PATCH |

---

## Task 1: Backend — PATCH de atualização parcial (TDD)

**Files:**
- Modify: `backend/schemas.py`
- Modify: `backend/routers/instrumentos.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Escrever os testes que falham (anexar a `tests/test_api.py`)**

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_api.py -q -k patch`
Expected: FAIL — 405 (método não permitido) ou 404 da rota inexistente.

- [ ] **Step 3: Adicionar `InstrumentoPatch` em `backend/schemas.py`**

Logo após a classe `InstrumentoIn`, adicione:
```python
class InstrumentoPatch(BaseModel):
    """Atualização parcial: todos os campos opcionais; só os enviados são aplicados."""
    equipamento: str | None = None
    familia_id: int | None = None
    tipo_id: int | None = None
    ciclo_meses: int | None = None
    status_operacional: str | None = None
    codigo_interno: str | None = None
    codigo_patrimonial: str | None = None
    serial: str | None = None
    marca: str | None = None
    modelo: str | None = None
    faixa_min: float | None = None
    faixa_max: float | None = None
    resolucao: str | None = None
    emp: str | None = None
    disciplina: str | None = None
    grandeza_id: int | None = None
    unidade_id: int | None = None
    sistema: str | None = None
    organizacao: str | None = None
    unidade_org: str | None = None
    secao: str | None = None
    bancada: str | None = None
    data_ultima_calibracao: date | None = None
    data_validade: date | None = None
    organizacao_calibradora: str | None = None
    local_calibracao: str | None = None
    certificado_ref: str | None = None
    observacoes: str | None = None
    fu: int | None = Field(None, ge=1, le=3)
    nc: int | None = Field(None, ge=1, le=3)
    ab: int | None = Field(None, ge=1, le=3)
    cm: int | None = Field(None, ge=1, le=3)
    ci: int | None = Field(None, ge=1, le=3)
```

- [ ] **Step 4: Adicionar helper e endpoint PATCH em `backend/routers/instrumentos.py`**

No import dos schemas, acrescente `InstrumentoPatch`:
```python
from backend.schemas import ListaInstrumentos, InstrumentoOut, InstrumentoIn, InstrumentoPatch
```
E adicione (após o endpoint `editar`, antes dos endpoints de upload):
```python
def _aplicar_parcial(inst: Instrumento, dados: InstrumentoPatch) -> None:
    payload = dados.model_dump(exclude_unset=True)
    if payload.get("disciplina"):
        payload["disciplina"] = Disciplina(payload["disciplina"].upper())
    if payload.get("status_operacional"):
        payload["status_operacional"] = StatusOperacional(payload["status_operacional"])
    for campo, valor in payload.items():
        setattr(inst, campo, valor)


@router.patch("/instrumentos/{inst_id}", response_model=InstrumentoOut)
def patch(inst_id: int, dados: InstrumentoPatch, db: Session = Depends(get_db)):
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    enviados = dados.model_dump(exclude_unset=True)
    if "codigo_patrimonial" in enviados:
        _checar_patrimonio(db, enviados["codigo_patrimonial"], ignorar_id=inst_id)
    _aplicar_parcial(inst, dados)
    db.commit()
    db.refresh(inst)
    return instrumento_para_out(inst, date.today())
```

- [ ] **Step 5: Rodar e ver passar + regressão**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS (todos — 75 anteriores + 5 novos do PATCH = 80).

- [ ] **Step 6: Commit**

```bash
git add backend/schemas.py backend/routers/instrumentos.py tests/test_api.py
git commit -m "feat: PATCH de atualização parcial de instrumento"
```

---

## Task 2: Frontend — infra de modal + SDK.patch + CSS

**Files:**
- Modify: `frontend/app.js`
- Modify: `frontend/siscalib.css`

- [ ] **Step 1: Acrescentar ao final de `frontend/app.js`**

```javascript
// ── Modal reutilizável ──────────────────────────────────────────────────────
function _escFechar(e) { if (e.key === "Escape") fecharModal(); }

function fecharModal() {
  const ov = document.getElementById("modalOv");
  if (ov) ov.remove();
  document.removeEventListener("keydown", _escFechar);
}

function abrirModal(titulo, conteudoHtml, acoesHtml) {
  fecharModal();
  const ov = document.createElement("div");
  ov.className = "modal-ov";
  ov.id = "modalOv";
  ov.innerHTML = `<div class="modal-card" role="dialog" aria-modal="true">
      <div class="modal-head"><b>${esc(titulo)}</b>
        <button class="modal-x" aria-label="Fechar">&times;</button></div>
      <div class="modal-body">${conteudoHtml}</div>
      <div class="modal-foot">${acoesHtml || ""}</div>
    </div>`;
  document.body.appendChild(ov);
  ov.addEventListener("click", e => { if (e.target === ov) fecharModal(); });
  ov.querySelector(".modal-x").onclick = fecharModal;
  document.addEventListener("keydown", _escFechar);
  return ov;
}

// ── PATCH parcial ───────────────────────────────────────────────────────────
SDK.patch = async (path, body) => {
  const r = await fetch(API + path, {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.status === 409) throw new Error("Código patrimonial já existe");
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
};

// ── Render compartilhado da ficha (página + modal) ──────────────────────────
function renderFichaResumo(i) {
  const div = i.divergencia_flag ? ' <span class="bdg amber">divergência flag×data</span>' : "";
  const igp = i.igp == null ? "" :
    ` · <span class="bdg slate">IGP ${i.igp} — ${CLASSE_LABEL[i.classe_prioridade]}</span>`;
  const status = badgeStatus(i.status) +
    (i.dias_restantes != null ? ` <span class="muted">(${i.dias_restantes} dias)</span>` : "") +
    ` <span class="bdg slate">${esc(i.status_operacional)}</span>` + div + igp;
  const linhas = [
    ["Patrimônio", i.codigo_patrimonial], ["Série", i.serial],
    ["Marca", i.marca], ["Modelo", i.modelo],
    ["Família", i.familia_nome], ["Tipo", i.tipo_nome],
    ["Grandeza", i.grandeza_nome], ["Unidade", i.unidade_simbolo],
    ["Faixa", [i.faixa_min, i.faixa_max].some(v => v != null) ? `${i.faixa_min ?? ""} … ${i.faixa_max ?? ""}` : i.faixa],
    ["Resolução", i.resolucao], ["EMP", i.emp],
    ["Disciplina", i.disciplina], ["Sistema", i.sistema],
    ["Localização", [i.organizacao, i.unidade_org, i.secao, i.bancada].filter(Boolean).join(" → ")],
    ["Ciclo (meses)", i.ciclo_meses],
    ["Última calibração", fmtData(i.data_ultima_calibracao)],
    ["Validade", fmtData(i.data_validade)],
    ["Organização calibradora", i.organizacao_calibradora],
    ["Certificado", i.certificado_ref], ["Observações", i.observacoes],
  ];
  const tabela = linhas.map(([k, v]) =>
    `<tr><th style="width:200px">${k}</th><td>${esc(v) || "—"}</td></tr>`).join("");
  const anexos =
    (i.foto_path ? `<a href="${i.foto_path}" target="_blank">Foto</a> ` : '<span class="muted">Sem foto</span> ') +
    (i.manual_path ? ` · <a href="${i.manual_path}" target="_blank">Manual (PDF)</a>` : ' · <span class="muted">Sem manual</span>');
  return `<div style="margin-bottom:12px">${status}</div>
    <div class="twrap"><table><tbody>${tabela}</tbody></table></div>
    <div style="margin-top:12px"><b>Anexos</b><div style="margin-top:6px">${anexos}</div></div>`;
}
```

- [ ] **Step 2: Acrescentar ao final de `frontend/siscalib.css`**

```css
.modal-ov{position:fixed;inset:0;background:rgba(0,0,0,.55);display:flex;
  align-items:center;justify-content:center;z-index:1000;padding:20px}
.modal-card{background:var(--sf);border:1px solid var(--bd);border-radius:var(--rl);
  max-width:1000px;width:100%;max-height:90vh;display:flex;flex-direction:column}
.modal-head{display:flex;justify-content:space-between;align-items:center;
  padding:14px 18px;border-bottom:1px solid var(--bd)}
.modal-x{background:none;border:none;color:var(--tx2);font-size:22px;cursor:pointer;line-height:1}
.modal-body{padding:16px 18px;overflow:auto}
.modal-foot{padding:12px 18px;border-top:1px solid var(--bd);display:flex;
  gap:8px;justify-content:flex-end;flex-wrap:wrap}
.selbar{display:flex;align-items:center;gap:10px;background:var(--sf2);
  border:1px solid var(--bd);border-radius:var(--r);padding:8px 12px;margin-bottom:10px}
th.chk,td.chk{width:34px;text-align:center}
.lote-tab td input,.lote-tab td select{width:100%;min-width:90px}
.campos-pick{display:flex;flex-wrap:wrap;gap:10px 16px;margin-bottom:6px}
.campos-pick label{display:flex;align-items:center;gap:5px;font-size:13px}
tbody tr{cursor:pointer}
```

- [ ] **Step 3: Verificar sintaxe**

Run:
```bash
cd /home/luc/DEV_ERP/xCalibracao
python3 -c "
js=open('frontend/app.js').read()
print('chaves:', js.count('{')==js.count('}'), '| abrirModal/fecharModal/renderFichaResumo/SDK.patch:',
      all(s in js for s in ['function abrirModal','function fecharModal','function renderFichaResumo','SDK.patch']))
css=open('frontend/siscalib.css').read(); print('css chaves:', css.count('{')==css.count('}'))
"
```
Expected: `True` em tudo.

- [ ] **Step 4: Commit**

```bash
git add frontend/app.js frontend/siscalib.css
git commit -m "feat: modal reutilizável, SDK.patch e render de ficha compartilhado"
```

---

## Task 3: Ficha usa o render compartilhado (DRY)

**Files:**
- Modify: `frontend/ficha.html`

- [ ] **Step 1: Substituir o `<main>` + `<script>` de `frontend/ficha.html`**

```html
<main class="main">
  <a href="inventario.html" class="muted">&larr; Inventário</a>
  <h1 id="titulo" style="margin-top:8px">Ficha do Instrumento</h1>
  <a class="btn" id="btnEditar" style="margin-bottom:12px"><i class="bi bi-pencil"></i> Editar</a>
  <div id="corpo"></div>
</main>
<script>
montarShell("");
(async () => {
  const id = new URLSearchParams(location.search).get("id");
  const i = await SDK.get("/instrumentos/" + id);
  document.getElementById("btnEditar").href = "cadastro.html?id=" + id;
  document.getElementById("titulo").textContent =
    `${i.codigo_interno || i.codigo_patrimonial || "(sem código)"} — ${i.equipamento || ""}`;
  document.getElementById("corpo").innerHTML = renderFichaResumo(i);
})();
</script>
```

- [ ] **Step 2: Verificar sintaxe e uso do helper**

Run:
```bash
cd /home/luc/DEV_ERP/xCalibracao
python3 -c "
h=open('frontend/ficha.html').read()
print('usa renderFichaResumo:', 'renderFichaResumo(i)' in h, '| chaves:', h.count('{')==h.count('}'))
"
```
Expected: `True` em ambos.

- [ ] **Step 3: Commit**

```bash
git add frontend/ficha.html
git commit -m "refactor: ficha usa renderFichaResumo (DRY com o modal)"
```

---

## Task 4: Inventário — checkbox, selecionar-todos, barra de seleção, modal de ficha

**Files:**
- Modify: `frontend/inventario.html`

- [ ] **Step 1: Substituir todo o conteúdo de `frontend/inventario.html`**

```html
<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SisCalib · Inventário</title>
<link rel="stylesheet" href="vendor/fonts.css">
<link rel="stylesheet" href="vendor/bootstrap-icons.min.css">
<link rel="stylesheet" href="vendor/xcmasm-govbr.css">
<link rel="stylesheet" href="siscalib.css">
</head><body class="app">
<script src="app.js"></script>
<main class="main">
  <h1>Inventário de Instrumentos</h1>
  <div class="toolbar">
    <input type="search" id="busca" placeholder="Buscar por código, série, equipamento...">
    <select id="disciplina"><option value="">Disciplina</option><option>ELE</option><option>MEC</option></select>
    <select id="sistema"><option value="">Sistema</option></select>
    <select id="status"><option value="">Status</option>
      <option value="VENCIDO">Vencido</option><option value="A_VENCER_7">A vencer 7d</option>
      <option value="A_VENCER_30">A vencer 30d</option><option value="A_VENCER_60">A vencer 60d</option>
      <option value="VALIDO">Válido</option><option value="SEM_DATA">Sem data</option>
      <option value="BAIXADO">Baixado</option></select>
    <select id="familia"><option value="">Família</option></select>
    <select id="classe"><option value="">Prioridade</option>
      <option value="MAXIMA">Máxima</option><option value="MEDIA">Média</option>
      <option value="BAIXA">Baixa</option><option value="MUITO_BAIXA">Muito baixa</option>
      <option value="NAO_CLASSIFICADO">Não classificado</option></select>
    <a class="btn" href="cadastro.html" style="margin-left:auto"><i class="bi bi-plus-lg"></i> Novo</a>
  </div>
  <div class="selbar" id="selbar" style="display:none">
    <b id="selcount">0 selecionado(s)</b>
    <button class="btn" id="btnLote"><i class="bi bi-pencil-square"></i> Editar selecionados</button>
    <button class="btn ghost" id="btnLimpar">Limpar seleção</button>
  </div>
  <div class="muted" id="cont" style="margin-bottom:8px"></div>
  <div class="twrap"><table id="tab"><thead><tr>
    <th class="chk"><input type="checkbox" id="chkAll" title="Selecionar todos"></th>
    <th>Código</th><th>Equipamento</th><th>Marca/Modelo</th><th>Disc.</th>
    <th>Sistema</th><th>Validade</th><th>Status</th></tr></thead><tbody></tbody></table></div>
</main>
<script>
montarShell("inventario.html");
let timer;
let itensAtuais = [];
const selecionados = new Set();

const busca = document.getElementById("busca"), disciplina = document.getElementById("disciplina"),
      sistema = document.getElementById("sistema"), status = document.getElementById("status"),
      familia = document.getElementById("familia"), classe = document.getElementById("classe"),
      cont = document.getElementById("cont"), chkAll = document.getElementById("chkAll"),
      selbar = document.getElementById("selbar"), selcount = document.getElementById("selcount");

function atualizarBarra() {
  selcount.textContent = `${selecionados.size} selecionado(s)`;
  selbar.style.display = selecionados.size ? "flex" : "none";
}

function renderLinhas() {
  document.querySelector("#tab tbody").innerHTML = itensAtuais.map(i => `
    <tr data-id="${i.id}">
      <td class="chk"><input type="checkbox" class="rowchk" data-id="${i.id}" ${selecionados.has(i.id) ? "checked" : ""}></td>
      <td>${esc(i.codigo_interno || i.codigo_patrimonial)}</td>
      <td>${esc(i.equipamento)}</td><td>${esc([i.marca, i.modelo].filter(Boolean).join(" "))}</td>
      <td>${esc(i.disciplina)}</td><td>${esc(i.sistema)}</td>
      <td>${fmtData(i.data_validade)}</td><td>${badgeStatus(i.status)}</td></tr>`).join("")
    || `<tr><td colspan="8" class="muted">Nada encontrado.</td></tr>`;
}

async function carregar() {
  const params = {
    busca: busca.value, disciplina: disciplina.value, sistema: sistema.value,
    status: status.value, familia_id: familia.value, classe_prioridade: classe.value,
  };
  selecionados.clear();           // trocar filtro/busca limpa seleção
  chkAll.checked = false;
  atualizarBarra();
  const r = await SDK.get("/instrumentos", params);
  itensAtuais = r.itens;
  cont.textContent = `${r.total} instrumento(s)`;
  renderLinhas();
}

// clique na linha (exceto checkbox) → modal da ficha
document.querySelector("#tab tbody").addEventListener("click", async (e) => {
  if (e.target.classList.contains("rowchk")) return;
  const tr = e.target.closest("tr[data-id]");
  if (!tr) return;
  const i = await SDK.get("/instrumentos/" + tr.dataset.id);
  abrirModal(`${i.codigo_interno || i.codigo_patrimonial || ""} — ${i.equipamento || ""}`,
    renderFichaResumo(i),
    `<a class="btn ghost" href="ficha.html?id=${i.id}">Ficha completa</a>
     <a class="btn" href="cadastro.html?id=${i.id}">Editar</a>`);
});

// checkbox por linha
document.querySelector("#tab tbody").addEventListener("change", (e) => {
  if (!e.target.classList.contains("rowchk")) return;
  const id = parseInt(e.target.dataset.id);
  if (e.target.checked) selecionados.add(id); else selecionados.delete(id);
  atualizarBarra();
});

chkAll.onchange = () => {
  if (chkAll.checked) itensAtuais.forEach(i => selecionados.add(i.id));
  else selecionados.clear();
  renderLinhas();
  atualizarBarra();
};

document.getElementById("btnLimpar").onclick = () => {
  selecionados.clear(); chkAll.checked = false; renderLinhas(); atualizarBarra();
};

document.getElementById("btnLote").onclick = () => abrirEdicaoLote();

[disciplina, sistema, status, familia, classe].forEach(e => e.onchange = carregar);
busca.oninput = () => { clearTimeout(timer); timer = setTimeout(carregar, 250); };

(async () => {
  const r = await SDK.get("/instrumentos");
  [...new Set(r.itens.map(i => i.sistema).filter(Boolean))].sort()
    .forEach(s => sistema.add(new Option(s, s)));
  window._dominios = await SDK.get("/dominios");
  window._dominios.familias.forEach(f => familia.add(new Option(f.nome, f.id)));
  carregar();
})();

// abrirEdicaoLote() é definida na Task 5 (script adicional)
function abrirEdicaoLote() { alert("Edição em lote — implementada na próxima etapa."); }
</script>
</body></html>
```

- [ ] **Step 2: Verificar sintaxe e elementos**

Run:
```bash
cd /home/luc/DEV_ERP/xCalibracao
python3 -c "
h=open('frontend/inventario.html').read()
print('chaves:', h.count('{')==h.count('}'),
      '| chkAll:', 'id=\"chkAll\"' in h, '| selbar:', 'id=\"selbar\"' in h,
      '| modal no clique:', 'renderFichaResumo(i)' in h,
      '| carregar única:', h.count('async function carregar')==1)
"
```
Expected: `True` em tudo; `carregar` única.

- [ ] **Step 3: Commit**

```bash
git add frontend/inventario.html
git commit -m "feat: inventário com checkbox, selecionar-todos, barra de seleção e ficha em modal"
```

---

## Task 5: Inventário — modal de edição em lote (tabela editável por item)

**Files:**
- Modify: `frontend/inventario.html`

- [ ] **Step 1: Substituir a função placeholder `abrirEdicaoLote()` pelo código real**

Localize no final do `<script>` de `frontend/inventario.html` a linha:
```javascript
function abrirEdicaoLote() { alert("Edição em lote — implementada na próxima etapa."); }
```
e substitua-a por:
```javascript
// ── Edição em lote ──────────────────────────────────────────────────────────
const STATUS_OP = ["ATIVO", "EM_CALIBRACAO", "EM_MANUTENCAO", "REPROVADO", "BLOQUEADO", "BAIXADO"];
const CAMPOS_LOTE = [
  { key: "codigo_patrimonial", label: "Patrimônio", tipo: "text" },
  { key: "familia_id", label: "Família", tipo: "dom", dom: "familias" },
  { key: "tipo_id", label: "Tipo", tipo: "dom", dom: "tipos" },
  { key: "grandeza_id", label: "Grandeza", tipo: "dom", dom: "grandezas" },
  { key: "unidade_id", label: "Unidade", tipo: "dom", dom: "unidades" },
  { key: "status_operacional", label: "Status oper.", tipo: "opcoes", opcoes: STATUS_OP },
  { key: "ciclo_meses", label: "Ciclo (m)", tipo: "num" },
  { key: "secao", label: "Seção", tipo: "text" },
  { key: "bancada", label: "Bancada", tipo: "text" },
  { key: "fu", label: "FU", tipo: "igp" }, { key: "nc", label: "NC", tipo: "igp" },
  { key: "ab", label: "AB", tipo: "igp" }, { key: "cm", label: "CM", tipo: "igp" },
  { key: "ci", label: "CI", tipo: "igp" },
];
const INT_KEYS = ["familia_id", "tipo_id", "grandeza_id", "unidade_id", "ciclo_meses", "fu", "nc", "ab", "cm", "ci"];

function _optsDom(domKey, valor) {
  const itens = window._dominios[domKey] || [];
  return `<option value="">—</option>` + itens.map(o =>
    `<option value="${o.id}" ${o.id == valor ? "selected" : ""}>${esc(o.simbolo ? `${o.nome} (${o.simbolo})` : o.nome)}</option>`).join("");
}
function _optsLista(lista, valor) {
  return `<option value="">—</option>` + lista.map(o =>
    `<option ${o == valor ? "selected" : ""}>${o}</option>`).join("");
}

function _celula(campo, item) {
  const v = item[campo.key];
  const at = `data-id="${item.id}" data-key="${campo.key}"`;
  if (campo.tipo === "dom") return `<select ${at}>${_optsDom(campo.dom, v)}</select>`;
  if (campo.tipo === "opcoes") return `<select ${at}>${_optsLista(campo.opcoes, v)}</select>`;
  if (campo.tipo === "num") return `<input ${at} type="number" value="${v ?? ""}">`;
  if (campo.tipo === "igp") return `<input ${at} type="number" min="1" max="3" value="${v ?? ""}">`;
  return `<input ${at} type="text" value="${esc(v) ?? ""}">`;
}

function abrirEdicaoLote() {
  const sel = itensAtuais.filter(i => selecionados.has(i.id));
  if (!sel.length) return;
  const picks = CAMPOS_LOTE.map(c =>
    `<label><input type="checkbox" class="pickcampo" value="${c.key}"> ${c.label}</label>`).join("");
  abrirModal(`Editar ${sel.length} item(ns)`,
    `<div><b>1. Campos a editar</b>
       <div class="campos-pick" id="picker">${picks}</div></div>
     <div id="loteArea"></div>`,
    `<button class="btn" id="btnSalvarLote">Salvar tudo</button>
     <button class="btn ghost" onclick="fecharModal()">Cancelar</button>
     <span id="loteMsg" class="muted"></span>`);

  const area = document.getElementById("loteArea");
  function montarTabela() {
    const escolhidos = [...document.querySelectorAll(".pickcampo:checked")]
      .map(c => CAMPOS_LOTE.find(x => x.key === c.value));
    if (!escolhidos.length) { area.innerHTML = `<p class="muted" style="margin-top:10px">Escolha ao menos um campo.</p>`; return; }
    const ths = escolhidos.map(c =>
      `<th>${c.label} <button type="button" class="btn ghost" style="padding:1px 6px" data-fill="${c.key}" title="Preencher coluna">↓</button></th>`).join("");
    const rows = sel.map(i => `<tr><td>${esc(i.codigo_interno || i.codigo_patrimonial)}</td>
      <td>${esc(i.equipamento)}</td>${escolhidos.map(c => `<td>${_celula(c, i)}</td>`).join("")}</tr>`).join("");
    area.innerHTML = `<div class="twrap" style="margin-top:10px"><table class="lote-tab">
      <thead><tr><th>Código</th><th>Equipamento</th>${ths}</tr></thead><tbody>${rows}</tbody></table></div>`;
    area.querySelectorAll("[data-fill]").forEach(b => b.onclick = () => {
      const key = b.dataset.fill;
      const campos = [...area.querySelectorAll(`[data-key="${key}"]`)];
      if (!campos.length) return;
      const val = campos[0].value;
      campos.forEach(c => c.value = val);
    });
  }
  document.getElementById("picker").addEventListener("change", montarTabela);

  document.getElementById("btnSalvarLote").onclick = async () => {
    const escolhidos = [...document.querySelectorAll(".pickcampo:checked")].map(c => c.value);
    if (!escolhidos.length) return alert("Escolha ao menos um campo.");
    const msg = document.getElementById("loteMsg");
    const erros = [];
    let n = 0;
    for (const item of sel) {
      const body = {};
      escolhidos.forEach(key => {
        const el = area.querySelector(`[data-key="${key}"][data-id="${item.id}"]`);
        if (!el) return;
        const raw = el.value.trim();
        if (raw === "") return;                       // vazio = não altera
        body[key] = INT_KEYS.includes(key) ? parseInt(raw) : raw;
      });
      n++;
      msg.textContent = `salvando ${n}/${sel.length}...`;
      if (Object.keys(body).length === 0) continue;
      try { await SDK.patch("/instrumentos/" + item.id, body); }
      catch (e) { erros.push(`${item.codigo_interno || item.id}: ${e.message}`); }
    }
    if (erros.length) { msg.innerHTML = `<span class="sev-erro">${esc(erros.join(" | "))}</span>`; }
    else { fecharModal(); }
    await carregar();
  };
}
```

- [ ] **Step 2: Verificar sintaxe e ausência de placeholder**

Run:
```bash
cd /home/luc/DEV_ERP/xCalibracao
python3 -c "
h=open('frontend/inventario.html').read()
print('chaves:', h.count('{')==h.count('}'),
      '| sem placeholder alert:', 'implementada na próxima etapa' not in h,
      '| usa SDK.patch:', 'SDK.patch(' in h,
      '| CAMPOS_LOTE:', 'CAMPOS_LOTE' in h)
"
```
Expected: `True` em tudo.

- [ ] **Step 3: Commit**

```bash
git add frontend/inventario.html
git commit -m "feat: modal de edição em lote (tabela editável por item) com PATCH"
```

---

## Task 6: Verificação end-to-end + rebuild

**Files:** nenhum (verificação)

- [ ] **Step 1: Rodar a suíte completa**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS (80).

- [ ] **Step 2: Rebuild da imagem e subir o container (mantém volume)**

Run:
```bash
cd /home/luc/DEV_ERP/xCalibracao
docker build -q -t siscalib:latest .
docker rm -f siscalib 2>/dev/null
docker run -d --name siscalib -p 8080:8080 -v siscalib_data:/data siscalib:latest
sleep 5
curl -s localhost:8080/api/v1/health; echo
```
Expected: `{"status":"ok"}`.

- [ ] **Step 3: E2E do PATCH (API) sobre dados reais**

Run:
```bash
ID=$(curl -s "localhost:8080/api/v1/instrumentos" | python3 -c "import sys,json; print(json.load(sys.stdin)['itens'][0]['id'])")
echo "id alvo: $ID"
echo "antes:"; curl -s localhost:8080/api/v1/instrumentos/$ID | python3 -c "import sys,json; o=json.load(sys.stdin); print('equip',o['equipamento'],'| secao',o['secao'],'| igp',o['igp'])"
curl -s -X PATCH localhost:8080/api/v1/instrumentos/$ID -H "Content-Type: application/json" -d '{"secao":"Bancada Teste","fu":3,"nc":3,"ab":2,"cm":3,"ci":2}' >/dev/null
echo "depois:"; curl -s localhost:8080/api/v1/instrumentos/$ID | python3 -c "import sys,json; o=json.load(sys.stdin); print('equip',o['equipamento'],'| secao',o['secao'],'| igp',o['igp'],o['classe_prioridade'])"
```
Expected: `equipamento` inalterado; `secao` vira "Bancada Teste"; `igp` 19 / MAXIMA. (Confirma PATCH parcial preservando o resto.)

- [ ] **Step 4: Páginas servidas**

Run: `for p in inventario.html ficha.html cadastro.html; do echo "$p -> $(curl -s -o /dev/null -w '%{http_code}' localhost:8080/$p)"; done`
Expected: todas 200.

- [ ] **Step 5: Verificação visual (manual)**

Abrir `http://localhost:8080/inventario.html`: clicar numa linha abre o modal da ficha; marcar 2-3 checkboxes mostra a barra "N selecionado(s)"; "Editar selecionados" abre o modal; escolher campos (ex.: Status oper. + Ciclo) monta a tabela; "↓" preenche a coluna; "Salvar tudo" persiste e recarrega. (Esta etapa é manual; reporte como pendente de confirmação visual do usuário.)

- [ ] **Step 6: Parar o container de teste**

Run: `docker rm -f siscalib`

- [ ] **Step 7: Commit (caso algum ajuste tenha sido necessário)**

Se nada mudou no código (só verificação), não há commit. Se houve ajuste, commitar com mensagem descritiva.

---

## Self-Review (autor do plano)

**Cobertura do spec:**
- §2 modal reutilizável + ficha em modal → Tasks 2, 3, 4. ✓
- §3 multi-seleção (checkbox, selecionar-todos, barra, filtro limpa seleção) → Task 4. ✓
- §4 modal de edição em lote (passo 1 campos → passo 2 tabela editável; "preencher coluna"; selects sem cascata; salvar = PATCH por item, erros por linha) → Task 5. ✓
- §5 PATCH parcial + InstrumentoPatch + SDK.patch → Tasks 1, 2. ✓
- §7 testes (PATCH parcial/IGP/404/409/parcial-sem-obrigatórios; regressão) → Task 1; e2e → Task 6. ✓

**Placeholder scan:** a função `abrirEdicaoLote()` placeholder da Task 4 é **substituída** pelo código real na Task 5 (Step 1) — explicitado e verificado por grep. Sem TBD/TODO remanescentes.

**Consistência de tipos/nomes:** `InstrumentoPatch` (Task 1) usado no PATCH; `SDK.patch`/`abrirModal`/`fecharModal`/`renderFichaResumo` (Task 2) usados em Tasks 3,4,5; `window._dominios` carregado na Task 4 e consumido por `_optsDom` na Task 5; `itensAtuais`/`selecionados` definidos na Task 4 e usados na Task 5; chaves de `CAMPOS_LOTE` (familia_id, status_operacional, fu… ) batem com `InstrumentoPatch` e com os nomes de campo de `InstrumentoOut`. ✓

**Risco conhecido:** verificação visual (Task 6 Step 5) é manual — não automatizável aqui; reportada como pendência de confirmação do usuário.
