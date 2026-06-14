# Exportação + Tabela com Ordenação e Filtros Multi-seleção — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao inventário do SisCalib exportação real (CSV/XLSX/PDF) gerada no backend e uma tabela client-side ordenável por coluna com filtros multi-seleção por checkbox.

**Architecture:** O backend ganha um router de exportação (`POST /api/v1/instrumentos/export`) que recebe `{ids, formato}`, busca os instrumentos, preserva a ordem do array `ids` e gera o arquivo via funções puras (`_linhas_completas`, `_gerar_csv`, `_gerar_xlsx`, `_gerar_pdf`). O frontend muda para carregar todos os instrumentos uma vez e processar busca/ordenação/filtros no navegador; `visiveis()` é a fonte única para render e exportação.

**Tech Stack:** FastAPI + Pydantic v2 + SQLAlchemy (SQLite), `openpyxl` (XLSX), `fpdf2` (PDF); frontend HTML/JS vanilla. Testes com pytest + `fastapi.testclient`.

**Spec:** `docs/superpowers/specs/2026-06-14-siscalib-export-tabela-design.md`

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `requirements.txt` | adicionar `openpyxl`, `fpdf2` |
| `backend/schemas.py` | `ExportRequest` (ids + formato `Literal["csv","xlsx","pdf"]`) |
| `backend/routers/exportacao.py` | **novo** — endpoint `/instrumentos/export` + geradores puros csv/xlsx/pdf |
| `backend/main.py` | incluir o router de exportação |
| `frontend/app.js` | `SDK.exportar(ids, formato)` (download de blob) |
| `frontend/inventario.html` | fluxo client-side: `todos`, `visiveis()`, ordenação por cabeçalho, popovers de filtro multi-seleção, botões de export |
| `frontend/siscalib.css` | estilos de sort/funil/popover e grupo de export |
| `tests/test_api.py` | testes do endpoint de exportação |

**Ordem das colunas completas (CSV/XLSX)** — usada em todo o plano, definida uma única vez como `COLUNAS` (lista de `(chave_dict, cabeçalho_legível)`):

```
codigo_interno          → "Código interno"
codigo_patrimonial      → "Patrimônio"
serial                  → "Série"
equipamento             → "Equipamento"
marca                   → "Marca"
modelo                  → "Modelo"
familia_nome            → "Família"
tipo_nome               → "Tipo"
grandeza_nome           → "Grandeza"
unidade_simbolo         → "Unidade"
faixa                   → "Faixa"            (min … max; ver _faixa_txt)
resolucao               → "Resolução"
emp                     → "EMP"
disciplina              → "Disciplina"
sistema                 → "Sistema"
localizacao             → "Localização"      (org → unidade → seção → bancada)
status_operacional      → "Status operacional"
status                  → "Status validade"
dias_restantes          → "Dias restantes"
data_ultima_calibracao  → "Última calibração"
data_validade           → "Validade"
ciclo_meses             → "Ciclo (meses)"
igp                     → "IGP"
classe_prioridade       → "Prioridade"
observacoes             → "Observações"
```

---

## Task 1: Dependências de exportação

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Adicionar as libs ao requirements**

Acrescente ao final de `requirements.txt`:

```
openpyxl==3.1.5
fpdf2==2.8.5
```

- [ ] **Step 2: Instalar no venv local**

Run: `.venv/bin/pip install openpyxl==3.1.5 fpdf2==2.8.5`
Expected: "Successfully installed openpyxl-3.1.5 fpdf2-2.8.5 ..." (e dependências como `et-xmlfile`, `fonttools`).

- [ ] **Step 3: Confirmar import**

Run: `.venv/bin/python -c "import openpyxl, fpdf; print(openpyxl.__version__, fpdf.__version__)"`
Expected: imprime as versões sem erro.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "build: adiciona openpyxl e fpdf2 para exportação"
```

---

## Task 2: Schema `ExportRequest`

**Files:**
- Modify: `backend/schemas.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Escrever o teste de validação do formato (falha)**

Acrescente ao final de `tests/test_api.py`:

```python
def test_export_formato_invalido_422(client):
    primeiro = client.get("/api/v1/instrumentos").json()["itens"][0]["id"]
    r = client.post("/api/v1/instrumentos/export",
                    json={"ids": [primeiro], "formato": "docx"})
    assert r.status_code == 422
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_api.py::test_export_formato_invalido_422 -v`
Expected: FAIL — hoje a rota não existe, então retorna 404 (não 422). Confirma que precisamos do endpoint + schema.

- [ ] **Step 3: Adicionar o schema**

No topo de `backend/schemas.py`, troque o import para incluir `Literal`:

```python
from __future__ import annotations
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field
```

Adicione ao final do arquivo:

```python
class ExportRequest(BaseModel):
    """Pedido de exportação: ids na ordem desejada + formato do arquivo."""
    ids: list[int]
    formato: Literal["csv", "xlsx", "pdf"]
```

- [ ] **Step 4: O teste de 422 ainda falha (rota inexistente) — deixar para a Task 3**

Run: `.venv/bin/pytest tests/test_api.py::test_export_formato_invalido_422 -v`
Expected: ainda FAIL (404). A rota só nasce na Task 3; o schema sozinho não a registra. Não comite este teste ainda — ele passa a verde na Task 3.

- [ ] **Step 5: Commit (apenas o schema)**

```bash
git add backend/schemas.py
git commit -m "feat: schema ExportRequest (ids + formato literal)"
```

---

## Task 3: Endpoint + gerador CSV

**Files:**
- Create: `backend/routers/exportacao.py`
- Modify: `backend/main.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Escrever os testes de CSV + erros (falham)**

Acrescente ao final de `tests/test_api.py`:

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_api.py -k export -v`
Expected: FAIL (404 — rota não existe).

- [ ] **Step 3: Criar o router com CSV e os geradores (XLSX/PDF entram nas próximas tasks)**

Crie `backend/routers/exportacao.py`:

```python
"""Exportação do inventário (CSV/XLSX/PDF) a partir de uma lista de ids ordenada."""
from __future__ import annotations
import csv
import io
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Instrumento
from backend.servico import instrumento_para_out
from backend.schemas import ExportRequest, InstrumentoOut

router = APIRouter(prefix="/api/v1", tags=["exportacao"])

# (chave no dict de linha, cabeçalho legível) — fonte única da ordem das colunas
COLUNAS: list[tuple[str, str]] = [
    ("codigo_interno", "Código interno"),
    ("codigo_patrimonial", "Patrimônio"),
    ("serial", "Série"),
    ("equipamento", "Equipamento"),
    ("marca", "Marca"),
    ("modelo", "Modelo"),
    ("familia_nome", "Família"),
    ("tipo_nome", "Tipo"),
    ("grandeza_nome", "Grandeza"),
    ("unidade_simbolo", "Unidade"),
    ("faixa", "Faixa"),
    ("resolucao", "Resolução"),
    ("emp", "EMP"),
    ("disciplina", "Disciplina"),
    ("sistema", "Sistema"),
    ("localizacao", "Localização"),
    ("status_operacional", "Status operacional"),
    ("status", "Status validade"),
    ("dias_restantes", "Dias restantes"),
    ("data_ultima_calibracao", "Última calibração"),
    ("data_validade", "Validade"),
    ("ciclo_meses", "Ciclo (meses)"),
    ("igp", "IGP"),
    ("classe_prioridade", "Prioridade"),
    ("observacoes", "Observações"),
]

MEDIA = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def _faixa_txt(o: InstrumentoOut) -> str:
    if o.faixa_min is not None or o.faixa_max is not None:
        return f"{o.faixa_min if o.faixa_min is not None else ''} … {o.faixa_max if o.faixa_max is not None else ''}"
    return o.faixa or ""


def _localizacao_txt(o: InstrumentoOut) -> str:
    return " → ".join(p for p in [o.organizacao, o.unidade_org, o.secao, o.bancada] if p)


def _valor(o: InstrumentoOut, chave: str):
    """Valor textual de uma coluna para um instrumento (datas em ISO)."""
    if chave == "faixa":
        return _faixa_txt(o)
    if chave == "localizacao":
        return _localizacao_txt(o)
    v = getattr(o, chave)
    if isinstance(v, date):
        return v.isoformat()
    return "" if v is None else v


def _linhas_completas(instrumentos: list[InstrumentoOut]) -> list[dict]:
    """Uma linha-dict por instrumento, com as chaves de COLUNAS."""
    return [{chave: _valor(o, chave) for chave, _ in COLUNAS} for o in instrumentos]


def _gerar_csv(linhas: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([rotulo for _, rotulo in COLUNAS])
    for linha in linhas:
        w.writerow([linha[chave] for chave, _ in COLUNAS])
    # BOM para o Excel pt-BR abrir UTF-8 corretamente
    return buf.getvalue().encode("utf-8-sig")


@router.post("/instrumentos/export")
def exportar(req: ExportRequest, db: Session = Depends(get_db)):
    if not req.ids:
        raise HTTPException(status_code=400, detail="Nada a exportar")
    hoje = date.today()
    por_id = {i.id: i for i in db.query(Instrumento).filter(Instrumento.id.in_(req.ids)).all()}
    ordenados = [instrumento_para_out(por_id[i], hoje) for i in req.ids if i in por_id]
    linhas = _linhas_completas(ordenados)

    if req.formato == "csv":
        conteudo = _gerar_csv(linhas)
    elif req.formato == "xlsx":
        conteudo = _gerar_xlsx(linhas)
    else:
        conteudo = _gerar_pdf(ordenados)

    nome = f"inventario_{hoje.isoformat()}.{req.formato}"
    return Response(
        content=conteudo,
        media_type=MEDIA[req.formato],
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
```

> Nota: `_gerar_xlsx` e `_gerar_pdf` ainda não existem — o endpoint só será chamado com `"csv"` até a Task 4/5. Defina stubs temporários logo acima de `exportar` para o módulo importar:

```python
def _gerar_xlsx(linhas: list[dict]) -> bytes:
    raise NotImplementedError


def _gerar_pdf(instrumentos: list[InstrumentoOut]) -> bytes:
    raise NotImplementedError
```

- [ ] **Step 4: Registrar o router**

Em `backend/main.py`, troque a linha de import dos routers e a inclusão:

```python
from backend.routers import instrumentos, importacao, dashboard, dominios, exportacao
```

E logo após `app.include_router(dominios.router)`:

```python
app.include_router(exportacao.router)
```

- [ ] **Step 5: Rodar os testes de CSV + erros**

Run: `.venv/bin/pytest tests/test_api.py -k "export and not xlsx and not pdf" -v`
Expected: PASS — `test_export_csv`, `test_export_csv_preserva_ordem_dos_ids`, `test_export_ignora_ids_inexistentes`, `test_export_ids_vazio_400`, `test_export_formato_invalido_422`.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/exportacao.py backend/main.py tests/test_api.py
git commit -m "feat: endpoint de exportação com gerador CSV (ordem preservada)"
```

---

## Task 4: Gerador XLSX

**Files:**
- Modify: `backend/routers/exportacao.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Escrever o teste de XLSX (falha)**

Acrescente ao final de `tests/test_api.py`:

```python
def test_export_xlsx(client):
    import io
    import openpyxl
    itens = client.get("/api/v1/instrumentos").json()["itens"]
    ids = [i["id"] for i in itens]
    r = client.post("/api/v1/instrumentos/export", json={"ids": ids, "formato": "xlsx"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    ws = wb.active
    assert ws.cell(row=1, column=1).value == "Código interno"   # cabeçalho
    assert ws.max_row == len(ids) + 1                            # itens + cabeçalho
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_api.py::test_export_xlsx -v`
Expected: FAIL — `_gerar_xlsx` levanta `NotImplementedError` (vira 500 na resposta).

- [ ] **Step 3: Implementar `_gerar_xlsx`**

Em `backend/routers/exportacao.py`, troque o stub `_gerar_xlsx` por:

```python
def _gerar_xlsx(linhas: list[dict]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventário"
    rotulos = [rotulo for _, rotulo in COLUNAS]
    ws.append(rotulos)
    for celula in ws[1]:
        celula.font = Font(bold=True)
    for linha in linhas:
        ws.append([linha[chave] for chave, _ in COLUNAS])
    # auto-largura simples: maior conteúdo da coluna (limitado a 50)
    for idx, (chave, rotulo) in enumerate(COLUNAS, start=1):
        largura = max([len(rotulo)] + [len(str(l[chave])) for l in linhas]) + 2
        ws.column_dimensions[ws.cell(row=1, column=idx).column_letter].width = min(largura, 50)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_api.py::test_export_xlsx -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/exportacao.py tests/test_api.py
git commit -m "feat: gerador XLSX (cabeçalho em negrito + auto-largura)"
```

---

## Task 5: Gerador PDF

**Files:**
- Modify: `backend/routers/exportacao.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Escrever o teste de PDF (falha)**

Acrescente ao final de `tests/test_api.py`:

```python
def test_export_pdf(client):
    itens = client.get("/api/v1/instrumentos").json()["itens"]
    ids = [i["id"] for i in itens]
    r = client.post("/api/v1/instrumentos/export", json={"ids": ids, "formato": "pdf"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/test_api.py::test_export_pdf -v`
Expected: FAIL — `_gerar_pdf` levanta `NotImplementedError`.

- [ ] **Step 3: Implementar `_gerar_pdf`**

Em `backend/routers/exportacao.py`, troque o stub `_gerar_pdf` por (relatório-resumo A4 paisagem, 6 colunas):

```python
def _gerar_pdf(instrumentos: list[InstrumentoOut]) -> bytes:
    from fpdf import FPDF
    hoje = date.today()
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "CMASM / DME - Inventario de Calibracao", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Gerado em {hoje.isoformat()} - {len(instrumentos)} item(ns)", ln=True)
    pdf.ln(2)

    # cabeçalhos e larguras (mm) do resumo
    cols = [
        ("Codigo", 45), ("Equipamento", 75), ("Sistema", 45),
        ("Validade", 30), ("Status", 40), ("IGP/Classe", 42),
    ]
    pdf.set_font("Helvetica", "B", 9)
    for titulo, larg in cols:
        pdf.cell(larg, 7, titulo, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for o in instrumentos:
        validade = o.data_validade.isoformat() if o.data_validade else "-"
        igp = f"{o.igp} / {o.classe_prioridade}" if o.igp is not None else o.classe_prioridade
        valores = [
            o.codigo_interno or o.codigo_patrimonial or "-",
            o.equipamento or "-", o.sistema or "-",
            validade, o.status, igp,
        ]
        for (titulo, larg), valor in zip(cols, valores):
            texto = str(valor)
            # trunca para caber na célula (resumo)
            while pdf.get_string_width(texto) > larg - 2 and len(texto) > 1:
                texto = texto[:-1]
            pdf.cell(larg, 6, texto, border=1)
        pdf.ln()
    saida = pdf.output()
    return bytes(saida)
```

> `fpdf2`'s `output()` retorna `bytearray`; `bytes(...)` normaliza para `Response`.

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/pytest tests/test_api.py::test_export_pdf -v`
Expected: PASS.

- [ ] **Step 5: Suite completa (regressão)**

Run: `.venv/bin/pytest -q`
Expected: PASS — os 81 testes anteriores + os novos de export (≈ 90 no total), 0 falhas.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/exportacao.py tests/test_api.py
git commit -m "feat: gerador PDF resumo (A4 paisagem, 6 colunas)"
```

---

## Task 6: Frontend — `SDK.exportar` (download de blob)

**Files:**
- Modify: `frontend/app.js`

- [ ] **Step 1: Adicionar `SDK.exportar`**

Em `frontend/app.js`, logo após o bloco `SDK.patch = async (...) => {...};` (por volta da linha 132), acrescente:

```javascript
// ── Exportação (download de arquivo) ────────────────────────────────────────
SDK.exportar = async (ids, formato) => {
  const r = await fetch(API + "/instrumentos/export", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids, formato }),
  });
  if (!r.ok) throw new Error("HTTP " + r.status);
  const blob = await r.blob();
  const cd = r.headers.get("Content-Disposition") || "";
  const m = cd.match(/filename="?([^"]+)"?/);
  const nome = m ? m[1] : `inventario.${formato}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = nome;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
};
```

- [ ] **Step 2: Verificar sintaxe do JS**

Run: `node --check frontend/app.js`
Expected: sem saída (sintaxe OK). Se `node` não estiver disponível, pule — será validado no e2e da Task 8.

- [ ] **Step 3: Commit**

```bash
git add frontend/app.js
git commit -m "feat: SDK.exportar baixa arquivo gerado no backend"
```

---

## Task 7: Frontend — tabela client-side (carga única, busca, ordenação, filtros multi-seleção, export)

**Files:**
- Modify: `frontend/inventario.html`
- Modify: `frontend/siscalib.css`

Esta task reescreve o `<script>` e a `toolbar` do inventário. A lógica de seleção/edição em lote (linhas 126-223 do arquivo atual: `STATUS_OP`, `CAMPOS_LOTE`, `INT_KEYS`, `_optsDom`, `_optsLista`, `_celula`, `abrirEdicaoLote`) é **mantida sem mudanças** e continua no final do `<script>`.

- [ ] **Step 1: Trocar a toolbar e o cabeçalho da tabela**

Em `frontend/inventario.html`, substitua o bloco da `toolbar` (linhas 12-27, do `<div class="toolbar">` até o `</div>` que fecha antes de `selbar`) por:

```html
  <div class="toolbar">
    <input type="search" id="busca" placeholder="Buscar por código, série, equipamento...">
    <a class="btn" href="cadastro.html"><i class="bi bi-plus-lg"></i> Novo</a>
    <div class="export-grp" style="margin-left:auto">
      <span class="muted">Exportar:</span>
      <button class="btn ghost" data-exp="csv">CSV</button>
      <button class="btn ghost" data-exp="xlsx">XLSX</button>
      <button class="btn ghost" data-exp="pdf">PDF</button>
    </div>
  </div>
```

Em seguida, substitua o `<thead>` (linhas 34-37, do `<div class="twrap">` até `</thead>`) por cabeçalhos com `data-col` (ordenáveis) e `data-filtro` (filtráveis):

```html
  <div class="twrap"><table id="tab"><thead><tr>
    <th class="chk"><input type="checkbox" id="chkAll" title="Selecionar todos"></th>
    <th data-col="codigo">Código</th>
    <th data-col="equipamento">Equipamento</th>
    <th data-col="marcamodelo">Marca/Modelo</th>
    <th data-col="disciplina" data-filtro="disciplina">Disc.</th>
    <th data-col="sistema" data-filtro="sistema">Sistema</th>
    <th data-col="data_validade">Validade</th>
    <th data-col="status" data-filtro="status">Status</th>
  </tr></thead><tbody></tbody></table></div>
```

> Família e Prioridade não são colunas visíveis da tabela, mas o spec pede filtro por elas. Para manter a tabela enxuta, os filtros de **Família** e **Prioridade** ficam como dois funis extra na toolbar (Step 3 cria os popovers a partir de `data-filtro`; aqui adicionamos dois cabeçalhos lógicos). Adicione, ainda dentro da `toolbar` e antes do grupo de export, dois botões de funil avulsos:

```html
    <button class="funil-extra btn ghost" data-filtro="familia"><i class="bi bi-funnel"></i> Família</button>
    <button class="funil-extra btn ghost" data-filtro="classe"><i class="bi bi-funnel"></i> Prioridade</button>
```

(insira essas duas linhas logo após o `<a ... >Novo</a>`).

- [ ] **Step 2: Reescrever o topo do `<script>` — estado e `visiveis()`**

Em `frontend/inventario.html`, substitua o trecho do `<script>` que vai de `montarShell("inventario.html");` (linha 40) até o fim do bloco IIFE `})();` (linha 124) por:

```javascript
montarShell("inventario.html");
let timer;
let todos = [];                       // lista completa carregada uma vez
let itensAtuais = [];                 // = visiveis(); fonte do render e do export
const selecionados = new Set();
const filtrosCol = {};                // { coluna: Set(valores) }
let ordenacao = { coluna: null, dir: null };  // dir: "asc" | "desc"

const busca = document.getElementById("busca"),
      cont = document.getElementById("cont"),
      chkAll = document.getElementById("chkAll"),
      selbar = document.getElementById("selbar"),
      selcount = document.getElementById("selcount");

// valor de uma coluna para filtro/ordenação/exibição
function valorCol(i, col) {
  switch (col) {
    case "codigo": return i.codigo_interno || i.codigo_patrimonial || "";
    case "marcamodelo": return [i.marca, i.modelo].filter(Boolean).join(" ");
    case "familia": return i.familia_nome || "";
    case "classe": return i.classe_prioridade || "";
    default: return i[col] == null ? "" : i[col];
  }
}

const semAcento = s => s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();

// ordem de urgência para a coluna status
const ORDEM_STATUS = ["VENCIDO", "A_VENCER_7", "A_VENCER_30", "A_VENCER_60",
                      "VALIDO", "SEM_DATA", "BAIXADO"];

function cmp(a, b, col) {
  if (col === "data_validade") {
    const x = a.data_validade || "9999-99-99", y = b.data_validade || "9999-99-99";
    return x < y ? -1 : x > y ? 1 : 0;
  }
  if (col === "status") {
    return ORDEM_STATUS.indexOf(a.status) - ORDEM_STATUS.indexOf(b.status);
  }
  const x = semAcento(String(valorCol(a, col))), y = semAcento(String(valorCol(b, col)));
  return x < y ? -1 : x > y ? 1 : 0;
}

// fonte única: aplica busca → filtros → ordenação sobre `todos`
function visiveis() {
  let r = todos;
  if (busca.value.trim()) {
    const b = semAcento(busca.value);
    r = r.filter(i => semAcento([i.codigo_interno, i.serial, i.equipamento, i.modelo, i.marca]
      .filter(Boolean).join(" ")).includes(b));
  }
  for (const [col, sel] of Object.entries(filtrosCol)) {
    if (sel && sel.size) r = r.filter(i => sel.has(String(valorCol(i, col))));
  }
  if (ordenacao.coluna) {
    const sinal = ordenacao.dir === "desc" ? -1 : 1;
    r = [...r].sort((a, b) => sinal * cmp(a, b, ordenacao.coluna));
  }
  return r;
}

function indicadorSort(col) {
  if (ordenacao.coluna !== col) return "";
  return ordenacao.dir === "asc" ? " ▲" : ordenacao.dir === "desc" ? " ▼" : "";
}

function atualizarCabecalhos() {
  document.querySelectorAll("#tab thead th[data-col]").forEach(th => {
    const col = th.dataset.col;
    const base = th.dataset.label || (th.dataset.label = th.textContent.trim());
    const funil = th.dataset.filtro
      ? ` <i class="bi bi-funnel${filtrosCol[th.dataset.filtro]?.size ? "-fill ativo" : ""}" data-filtro="${th.dataset.filtro}"></i>`
      : "";
    th.innerHTML = base + indicadorSort(col) + funil;
  });
  document.querySelectorAll(".funil-extra").forEach(b => {
    const f = b.dataset.filtro;
    b.classList.toggle("ativo", !!filtrosCol[f]?.size);
  });
}

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

// recomputa visiveis(), atualiza contagem/cabeçalhos e re-renderiza
function refrescar() {
  itensAtuais = visiveis();
  cont.textContent = `${itensAtuais.length} de ${todos.length} instrumento(s)`;
  atualizarCabecalhos();
  renderLinhas();
}

// qualquer mudança de busca/filtro/ordenação limpa a seleção
function mudouVisao() {
  selecionados.clear();
  chkAll.checked = false;
  atualizarBarra();
  refrescar();
}

// recarrega do backend (após edições) preservando filtros/ordenação
async function recarregar() {
  const r = await SDK.get("/instrumentos");
  todos = r.itens;
  refrescar();
}
```

- [ ] **Step 3: Adicionar handlers de ordenação, filtro (popover) e export + o IIFE de inicialização**

Logo após o bloco do Step 2 (ainda dentro do `<script>`, antes do bloco `// ── Edição em lote ──` que permanece intacto), insira:

```javascript
// ── Ordenação por clique no cabeçalho ───────────────────────────────────────
document.querySelector("#tab thead").addEventListener("click", (e) => {
  if (e.target.closest(".bi-funnel, .bi-funnel-fill")) return;  // funil tem handler próprio
  const th = e.target.closest("th[data-col]");
  if (!th) return;
  const col = th.dataset.col;
  if (ordenacao.coluna !== col) ordenacao = { coluna: col, dir: "asc" };
  else if (ordenacao.dir === "asc") ordenacao.dir = "desc";
  else ordenacao = { coluna: null, dir: null };   // 3º clique: sem ordem
  mudouVisao();
});

// ── Popover de filtro multi-seleção ─────────────────────────────────────────
function fecharPopover() {
  document.getElementById("filtroPop")?.remove();
  document.removeEventListener("click", _foraPop, true);
}
function _foraPop(e) {
  const pop = document.getElementById("filtroPop");
  if (pop && !pop.contains(e.target) && !e.target.closest("[data-filtro]")) fecharPopover();
}
function abrirPopover(col, ancora) {
  fecharPopover();
  const valores = [...new Set(todos.map(i => String(valorCol(i, col))).filter(v => v !== ""))].sort();
  const sel = filtrosCol[col] || new Set();
  const itens = valores.map(v =>
    `<label><input type="checkbox" value="${esc(v)}" ${sel.has(v) ? "checked" : ""}> ${esc(v)}</label>`).join("");
  const pop = document.createElement("div");
  pop.id = "filtroPop";
  pop.className = "filtro-pop";
  pop.innerHTML = `<div class="filtro-acts">
      <button type="button" data-act="all">Marcar todos</button>
      <button type="button" data-act="none">Limpar</button></div>
    <div class="filtro-itens">${itens || '<span class="muted">Sem valores</span>'}</div>`;
  document.body.appendChild(pop);
  const r = ancora.getBoundingClientRect();
  pop.style.top = (r.bottom + window.scrollY + 4) + "px";
  pop.style.left = (r.left + window.scrollX) + "px";

  pop.addEventListener("change", () => {
    const marcados = [...pop.querySelectorAll("input:checked")].map(c => c.value);
    if (marcados.length) filtrosCol[col] = new Set(marcados);
    else delete filtrosCol[col];
    mudouVisao();
  });
  pop.querySelector('[data-act="all"]').onclick = () => {
    pop.querySelectorAll("input").forEach(c => c.checked = true);
    pop.dispatchEvent(new Event("change"));
  };
  pop.querySelector('[data-act="none"]').onclick = () => {
    pop.querySelectorAll("input").forEach(c => c.checked = false);
    pop.dispatchEvent(new Event("change"));
  };
  setTimeout(() => document.addEventListener("click", _foraPop, true), 0);
}
document.addEventListener("keydown", e => { if (e.key === "Escape") fecharPopover(); });

// abre o popover a partir de qualquer elemento com data-filtro (funil no th ou na toolbar)
document.addEventListener("click", (e) => {
  const alvo = e.target.closest("[data-filtro]");
  if (!alvo) return;
  e.stopPropagation();
  abrirPopover(alvo.dataset.filtro, alvo);
});

// ── Export ──────────────────────────────────────────────────────────────────
document.querySelector(".export-grp").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-exp]");
  if (!btn) return;
  const ids = itensAtuais.map(i => i.id);
  if (!ids.length) { alert("Nada a exportar."); return; }
  const orig = btn.textContent;
  btn.disabled = true; btn.textContent = "gerando…";
  try { await SDK.exportar(ids, btn.dataset.exp); }
  catch (err) { alert("Falha ao exportar: " + err.message); }
  finally { btn.disabled = false; btn.textContent = orig; }
});

// busca reaproveita o debounce, mas filtra client-side
busca.oninput = () => { clearTimeout(timer); timer = setTimeout(mudouVisao, 200); };

// inicialização: carrega tudo uma vez
(async () => {
  window._dominios = await SDK.get("/dominios");
  await recarregar();
})();
```

- [ ] **Step 4: Atualizar os pontos da edição em lote que falavam com o backend**

Na função `abrirEdicaoLote` (bloco mantido), a última linha do `btnSalvarLote.onclick` chama `await carregar();`. Substitua essa chamada por `await recarregar();` (a função `carregar` foi removida).

Run: `grep -n "carregar()" frontend/inventario.html`
Expected: nenhuma ocorrência de `carregar()` sozinho (apenas `recarregar()`). Se aparecer `carregar()`, troque por `recarregar()`.

- [ ] **Step 5: Adicionar estilos de sort/funil/popover/export**

Acrescente ao final de `frontend/siscalib.css`:

```css
#tab thead th[data-col]{cursor:pointer;user-select:none}
#tab thead th[data-col]:hover{color:var(--tx)}
.bi-funnel,.bi-funnel-fill{cursor:pointer;margin-left:4px;font-size:11px}
.bi-funnel-fill.ativo,.funil-extra.ativo{color:var(--blue);border-color:var(--blue)}
.export-grp{display:flex;align-items:center;gap:6px}
.filtro-pop{position:absolute;z-index:1100;background:var(--sf);border:1px solid var(--bd2);
  border-radius:var(--r);padding:8px;min-width:180px;max-height:320px;overflow:auto;
  box-shadow:0 8px 24px rgba(0,0,0,.5)}
.filtro-acts{display:flex;gap:8px;margin-bottom:6px}
.filtro-acts button{background:var(--sf2);border:1px solid var(--bd);color:var(--tx2);
  font-size:11px;padding:3px 8px;border-radius:var(--r);cursor:pointer}
.filtro-itens{display:flex;flex-direction:column;gap:4px}
.filtro-itens label{display:flex;align-items:center;gap:6px;font-size:13px;cursor:pointer;
  text-transform:none;letter-spacing:0;color:var(--tx)}
```

- [ ] **Step 6: Verificação estática**

Run: `grep -n "disciplina\b\|getElementById(\"sistema\")\|getElementById(\"classe\")\|itensAtuais = r.itens" frontend/inventario.html`
Expected: nenhuma referência aos selects antigos (`disciplina`, `sistema`, `status`, `familia`, `classe` como elementos) nem a `r.itens` fora de `recarregar`. As únicas referências a `disciplina`/`sistema`/`status` devem ser nomes de coluna/strings.

- [ ] **Step 7: Commit**

```bash
git add frontend/inventario.html frontend/siscalib.css
git commit -m "feat: inventário client-side com ordenação, filtros multi-seleção e export"
```

---

## Task 8: Verificação ponta-a-ponta

**Files:** nenhuma alteração de código (validação).

- [ ] **Step 1: Suite de testes completa**

Run: `.venv/bin/pytest -q`
Expected: todos passam (81 antigos + ~7 de export), 0 falhas.

- [ ] **Step 2: Subir o app e exercitar o inventário no navegador**

Use a skill `superpowers:webapp-testing` (Playwright) OU rode o app manualmente:

Run (background): `.venv/bin/uvicorn backend.main:app --port 8080`

> Atenção: o `data/siscalib.db` local fica vazio em dev — os ~498 instrumentos estão no volume Docker `siscalib_data`. Para um teste com dados, ou rode via Docker, ou importe a amostra/CSV antes. Para validar a UI bastam alguns registros.

Verifique no navegador (`http://localhost:8080/inventario.html`):
- a tabela carrega; clicar num cabeçalho ordena (▲ → ▼ → sem ordem);
- o funil em Disc./Sistema/Status e os botões Família/Prioridade abrem popover com checkboxes; marcar filtra; o funil fica destacado; Esc/clique-fora fecha;
- busca filtra sem recarregar a página;
- selecionar linhas e mudar filtro limpa a seleção;
- editar em lote ainda funciona e a tabela atualiza após salvar;
- os botões CSV/XLSX/PDF baixam `inventario_<data>.<ext>`; abrir o CSV (UTF-8/acentos OK), o XLSX (cabeçalho em negrito) e o PDF (resumo paisagem).

- [ ] **Step 3: Encerrar o servidor**

Pare o processo do uvicorn (TaskStop / Ctrl-C).

- [ ] **Step 4: Verificação anti-mentira**

Use a skill `superpowers:verification-before-completion`: confirme que `pytest -q` passou (cole a linha final) e que os três downloads abriram corretamente antes de declarar concluído.

---

## Self-Review

**Spec coverage:**
- Exportar CSV/XLSX/PDF no backend, ordem = `ids` → Tasks 3/4/5. ✓
- `ExportRequest` (ids + formato Literal) → Task 2. ✓
- Validações: ids vazio 400, formato inválido 422, ids inexistentes ignorados → Tasks 2/3. ✓
- Colunas completas (CSV/XLSX) e resumo PDF → `COLUNAS` (Task 3), `_gerar_pdf` (Task 5). ✓
- CSV UTF-8 com BOM → Task 3 (`utf-8-sig`). ✓
- Deps openpyxl + fpdf2 → Task 1. ✓
- Tabela client-side: `todos`, `filtrosCol`, `ordenacao`, `busca`, `selecionados`, `visiveis()` → Task 7. ✓
- Ordenação por coluna com ▲/▼, regras de data/status → Task 7 (`cmp`, `indicadorSort`). ✓
- Filtros multi-seleção (Disciplina, Sistema, Status, Família, Prioridade), E entre colunas / OU dentro, marcar-todos/limpar, fecha fora/Esc → Task 7. ✓
- Remoção dos dropdowns antigos → Task 7 Step 1. ✓
- Mudança de visão limpa seleção → Task 7 (`mudouVisao`). ✓
- `SDK.exportar`, "gerando…", nada a exportar → Tasks 6/7. ✓
- Testes do endpoint + regressão → Tasks 3/4/5/8. ✓

**Placeholder scan:** sem TBD/TODO; todo passo com código tem o código completo. ✓

**Type consistency:** `ExportRequest{ids, formato}`, `COLUNAS` (chave,rotulo), `_linhas_completas`/`_gerar_csv`/`_gerar_xlsx`/`_gerar_pdf`, `MEDIA`; no front `visiveis()`/`refrescar()`/`recarregar()`/`mudouVisao()`/`valorCol()`/`filtrosCol`/`ordenacao` usados de forma consistente entre os steps. `carregar()` antigo removido e substituído por `recarregar()` (Task 7 Step 4). ✓
