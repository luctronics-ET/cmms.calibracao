# Etiquetas com QR Code — Implementation Plan (PRD §6.6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ficha pública por instrumento (sem login) + etiquetas imprimíveis (individual/lote) com QR Code apontando para essa ficha, gerado client-side.

**Architecture:** Endpoint público curado `GET /api/v1/publico/instrumentos/{id}`. Páginas estáticas `publica.html` (ficha pública) e `etiquetas.html` (grade imprimível com QR via lib JS vendorizada MIT). Integração no inventário (botão Etiquetas) e na ficha (Gerar etiqueta). Sem mudança de schema.

**Tech Stack:** FastAPI, Pydantic v2, pytest, HTML/JS vanilla, lib QR vendorizada (MIT), CSS @media print.

---

## File Structure

- **Modify** `backend/schemas.py` — `InstrumentoPublicoOut`.
- **Modify** `backend/servico.py` — `instrumento_publico_para_out`.
- **Create** `backend/routers/publico.py` — endpoint público.
- **Modify** `backend/main.py` — registrar router.
- **Create** `tests/test_publico_api.py`.
- **Add (vendorizar)** `frontend/vendor/qrcode-generator.min.js` + `frontend/vendor/qrcode-generator.LICENSE`.
- **Create** `frontend/publica.html`, `frontend/etiquetas.html`.
- **Modify** `frontend/inventario.html` (botão Etiquetas), `frontend/app.js` (botão "Gerar etiqueta" na ficha/modal — via renderFichaResumo + montar*).

---

## Task 1: Endpoint público (schema + serviço + router + testes)

**Files:** Modify `backend/schemas.py`, `backend/servico.py`, `backend/main.py`; Create `backend/routers/publico.py`, `tests/test_publico_api.py`

- [ ] **Step 1: Schema** — adicionar ao fim de `backend/schemas.py`:

```python
class InstrumentoPublicoOut(BaseModel):
    id: int
    codigo_interno: str | None
    codigo_patrimonial: str | None
    equipamento: str | None
    marca: str | None
    modelo: str | None
    tipo_nome: str | None
    secao: str | None
    sistema: str | None
    status: str
    status_label: str
    status_operacional: str
    data_ultima_calibracao: date | None
    data_validade: date | None
    dias_restantes: int | None
```

- [ ] **Step 2: Serviço** — em `backend/servico.py`:
  a. adicionar `InstrumentoPublicoOut` ao import de schemas (mesclar com a linha existente).
  b. importar o mapa de labels: no topo, `from backend.calibracao import calcular_status` já existe; adicionar uma constante local de labels OU reutilizar. Adicionar ao fim do arquivo:

```python
_STATUS_LABEL_PUB = {
    "VALIDO": "Válido", "A_VENCER_60": "A vencer (60d)", "A_VENCER_30": "A vencer (30d)",
    "A_VENCER_7": "A vencer (7d)", "VENCIDO": "Vencido", "SEM_DATA": "Sem data", "BAIXADO": "Baixado",
}


def instrumento_publico_para_out(inst, hoje: date) -> InstrumentoPublicoOut:
    st = calcular_status(inst.data_validade, inst.flag_origem, hoje)
    return InstrumentoPublicoOut(
        id=inst.id,
        codigo_interno=inst.codigo_interno,
        codigo_patrimonial=inst.codigo_patrimonial,
        equipamento=inst.equipamento,
        marca=inst.marca,
        modelo=inst.modelo,
        tipo_nome=inst.tipo.nome if inst.tipo is not None else None,
        secao=inst.secao,
        sistema=inst.sistema,
        status=st.status.value,
        status_label=_STATUS_LABEL_PUB.get(st.status.value, st.status.value),
        status_operacional=inst.status_operacional.value,
        data_ultima_calibracao=inst.data_ultima_calibracao,
        data_validade=inst.data_validade,
        dias_restantes=st.dias_restantes,
    )
```

(`Instrumento` já está importado em servico.py; `date` também.)

- [ ] **Step 3: Escrever os testes** — criar `tests/test_publico_api.py`:

```python
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
                     "fu", "nc", "ab", "cm", "ci", "organizacao_calibradora"):
        assert proibido not in b, f"vazou campo sensível: {proibido}"
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `source .venv/bin/activate && python -m pytest tests/test_publico_api.py -q`
Expected: FAIL (rota não existe).

- [ ] **Step 5: Criar o router** `backend/routers/publico.py`:

```python
"""Endpoint público (sem login) — ficha resumida do instrumento p/ QR Code."""
from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Instrumento
from backend.servico import instrumento_publico_para_out
from backend.schemas import InstrumentoPublicoOut

router = APIRouter(prefix="/api/v1/publico", tags=["publico"])


@router.get("/instrumentos/{inst_id}", response_model=InstrumentoPublicoOut)
def ficha_publica(inst_id: int, db: Session = Depends(get_db)):
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    return instrumento_publico_para_out(inst, date.today())
```

- [ ] **Step 6: Registrar** — em `backend/main.py`, adicionar `publico` ao import `from backend.routers import ...` e `app.include_router(publico.router)`.

- [ ] **Step 7: Rodar e ver passar**

Run: `python -m pytest tests/test_publico_api.py -q`
Expected: PASS (4).

- [ ] **Step 8: Commit**

```bash
git add backend/schemas.py backend/servico.py backend/routers/publico.py backend/main.py tests/test_publico_api.py
git commit -m "feat: endpoint publico /publico/instrumentos/{id} (ficha resumida p/ QR)"
```

---

## Task 2: Vendorizar a lib de QR

**Files:** Create `frontend/vendor/qrcode-generator.min.js`, `frontend/vendor/qrcode-generator.LICENSE`

- [ ] **Step 1: Obter a lib via npm pack** (registry acessível neste ambiente). NÃO escreva o código da lib à mão — baixe o arquivo real:

```bash
cd /tmp && npm pack qrcode-generator 2>/dev/null && tar -xzf qrcode-generator-*.tgz
ls package/   # deve conter qrcode.js (e/ou dist), README, LICENSE
```

- [ ] **Step 2: Copiar para vendor/** — copie o arquivo JS principal (ex.: `package/qrcode.js`) para `frontend/vendor/qrcode-generator.min.js` e a licença (`package/LICENSE`) para `frontend/vendor/qrcode-generator.LICENSE`:

```bash
cp /tmp/package/qrcode.js /home/luc/DEV_ERP/xCalibracao/frontend/vendor/qrcode-generator.min.js
cp /tmp/package/LICENSE /home/luc/DEV_ERP/xCalibracao/frontend/vendor/qrcode-generator.LICENSE
rm -rf /tmp/package /tmp/qrcode-generator-*.tgz
```

> A lib `qrcode-generator` (Kazuhiko Arase, MIT) expõe um global `qrcode`. API documentada no
> README dela (leia o README do pacote): `var qr = qrcode(typeNumber, errorCorrectionLevel)` →
> `qr.addData(texto); qr.make();` → `qr.createSvgTag({cellSize, margin})` (string SVG) ou
> `qr.createImgTag(cellSize, margin)` ou `qr.createDataURL(cellSize, margin)`. Use `typeNumber=0`
> (auto) e `errorCorrectionLevel='M'`. CONFIRME a API real lendo o README baixado antes de usar.

- [ ] **Step 3: Verificar** — confirme que `frontend/vendor/qrcode-generator.min.js` define o global `qrcode` (grep por `function qrcode` ou `var qrcode`). Se o pacote `qrcode-generator` não estiver disponível ou a API divergir, use outra lib QR **MIT/BSD pura-JS** equivalente (ex.: `qrcodejs`), vendorizando do mesmo modo e ajustando a chamada no Task 4 — reporte qual usou. Se não houver rede, é BLOCKED — reporte.

- [ ] **Step 4: Commit**

```bash
git add frontend/vendor/qrcode-generator.min.js frontend/vendor/qrcode-generator.LICENSE
git commit -m "chore: vendoriza lib de QR (qrcode-generator, MIT)"
```

---

## Task 3: Página pública `publica.html`

**Files:** Create `frontend/publica.html`

> Layout standalone (SEM sidebar, NÃO chama `montarShell`). Antes de criar, leia `frontend/ficha.html`
> (estrutura `<head>`/vendor) e `frontend/app.js` (`SDK.get`, `badgeStatus`, `fmtData`, `esc`, e o init
> de tema no topo — ele roda sozinho ao carregar `app.js`).

- [ ] **Step 1: Criar `frontend/publica.html`**:
  - `<head>` com os mesmos `vendor/fonts.css`, `vendor/bootstrap-icons.min.css`,
    `vendor/xcmasm-govbr.css`, `siscalib.css`, viewport mobile.
  - `<body class="app">` mas SEM `montarShell`. Um `<main class="main">` com largura máxima
    (~520px, centralizado) contendo um card.
  - Carrega `app.js` (aplica tema automaticamente; usaremos só os helpers).
  - JS: lê `?id=`, faz `SDK.get("/publico/instrumentos/"+id)`; em 404 (erro) mostra "Instrumento não
    encontrado". Renderiza: logo MB + título com `codigo_interno` (grande) e `codigo_patrimonial`,
    `equipamento`; `badgeStatus(status)` + "Validade: `fmtData(data_validade)`"; "Última calibração:
    `fmtData(...)`"; tipo/marca/modelo; localização (`secao` · `sistema`); `status_operacional`.
    Use `esc()` em tudo.
  - Cabeçalho discreto "SisCalib · consulta pública" e nota "Sem login — leitura por QR".

- [ ] **Step 2: Verificação (browser)**

Run: `source .venv/bin/activate && uvicorn backend.main:app --port 8051 &` (aguarde ~2s).
- `curl -s -o /dev/null -w "%{http_code}" localhost:8051/publica.html` → 200.
- Pegue um id real (`curl -s localhost:8051/api/v1/instrumentos | head -c 200`) e abra
  `localhost:8051/publica.html?id=<id>` no navegador (Playwright) → confirma código, status badge,
  validade; abra `?id=99999` → "Instrumento não encontrado". 0 erros de console (favicon ok). Kill server.

- [ ] **Step 3: Commit**

```bash
git add frontend/publica.html
git commit -m "feat: ficha publica do instrumento (publica.html, sem login)"
```

---

## Task 4: Página de etiquetas `etiquetas.html`

**Files:** Create `frontend/etiquetas.html`

> Standalone (sem sidebar). Usa a lib vendorizada do Task 2. Antes de criar, confirme a API real
> da lib (README baixado) e leia `frontend/app.js` (`SDK.get`, `fmtData`, `esc`, `badgeStatus`).

- [ ] **Step 1: Criar `frontend/etiquetas.html`**:
  - `<head>`: vendor CSS + `siscalib.css` + `<script src="vendor/qrcode-generator.min.js"></script>`
    + estilos de etiqueta e `@media print`.
  - **Toolbar** (classe `.naoimprime`): botões "Imprimir / Salvar PDF" (`window.print()`) e
    "← Inventário" (`inventario.html`). Título "Etiquetas".
  - Container `.etiquetas` (grade). JS: lê `?ids=` (split por vírgula, filtra inteiros). Para cada id:
    `SDK.get("/publico/instrumentos/"+id)`; em erro, card "Instrumento {id} não encontrado".
  - Card de etiqueta (~70×40mm via CSS): código interno (grande, monospace) + patrimonial pequeno,
    equipamento (truncado), `badgeStatus(status)` + "Val: `fmtData(data_validade)`", e o **QR**
    (≈90px) codificando `${location.origin}/publica.html?id=${id}`. Gera o QR com a lib:
    `const qr = qrcode(0,'M'); qr.addData(url); qr.make(); divQr.innerHTML = qr.createSvgTag({cellSize:3, margin:0});`
    (AJUSTE conforme a API confirmada no Task 2).
  - CSS `@media print`: `.naoimprime{display:none}`; remove qualquer sidebar; grade com
    `page-break-inside:avoid` por etiqueta; fundo branco e texto preto nas etiquetas (independe do
    tema) para impressão limpa.
  - `esc()` em todo texto de usuário.

- [ ] **Step 2: Verificação (browser — o ponto-chave)**

Run: `uvicorn backend.main:app --port 8052 &` (aguarde ~2s). `node --check` não se aplica (HTML).
- Abra `localhost:8052/etiquetas.html?ids=<id1>,<id2>` (use ids reais) no Playwright:
  - confirma que renderiza 1 card por id, cada um com um `<svg>` (ou `<img>`) de QR não-vazio
    (`document.querySelectorAll('.etiquetas svg, .etiquetas img').length === <n ids>`).
  - confirma que o conteúdo do QR é a URL correta: a lib não expõe isso facilmente, então valide
    indiretamente — o card deve conter um `data-url` igual a `…/publica.html?id=<id>` (adicione esse
    `data-url` no card para teste/inspeção).
  - `?ids=99999` → card "não encontrado", sem quebrar.
  - chame `window.print()` via evaluate e confirme que não lança erro (não precisa concluir o diálogo).
  - 0 erros de console além de favicon. Kill server + limpe artefatos.

- [ ] **Step 3: Commit**

```bash
git add frontend/etiquetas.html
git commit -m "feat: pagina de etiquetas imprimiveis com QR (individual e em lote)"
```

---

## Task 5: Integração no inventário e na ficha

**Files:** Modify `frontend/inventario.html`, `frontend/app.js`

- [ ] **Step 1: Botão "Etiquetas" no inventário** — em `frontend/inventario.html`, na toolbar
  (perto do `.export-grp`), adicionar um botão `id="btnEtiquetas"`. No JS, ao clicar: monta a lista de
  ids = se `selecionados.size` então os selecionados na ordem de `itensAtuais`, senão
  `itensAtuais.map(i => i.id)`; se vazio → `alert("Nada para etiquetar.")`; senão
  `location.href = "etiquetas.html?ids=" + ids.join(",")`. (Espelhe a fonte de ids do export, que usa
  `itensAtuais` — ver o handler `.export-grp` existente.)

```javascript
// exemplo do handler:
document.getElementById("btnEtiquetas").addEventListener("click", () => {
  const base = selecionados.size ? itensAtuais.filter(i => selecionados.has(i.id)) : itensAtuais;
  const ids = base.map(i => i.id);
  if (!ids.length) { alert("Nada para etiquetar."); return; }
  location.href = "etiquetas.html?ids=" + ids.join(",");
});
```

- [ ] **Step 2: Botão "Gerar etiqueta" na ficha/modal** — em `frontend/app.js`, em `renderFichaResumo`,
  adicionar na seção Anexos (ou logo abaixo do status) um link/botão
  `<a class="btn ghost" href="etiquetas.html?ids=${i.id}" target="_blank">Gerar etiqueta</a>`.
  (Como `renderFichaResumo` retorna string, basta inserir o `<a>` no HTML — não precisa de handler.)
  A `ficha.html` standalone também ganha o botão automaticamente por usar `renderFichaResumo`.

- [ ] **Step 3: Verificação (browser)**

Run: `uvicorn backend.main:app --port 8053 &` (aguarde ~2s).
- Inventário: clicar "Etiquetas" sem seleção → abre `etiquetas.html` com todos os visíveis; selecionar
  2 linhas e clicar → abre com os 2 ids.
- Abrir a ficha de um instrumento (modal) → botão "Gerar etiqueta" abre `etiquetas.html?ids=<id>`.
- 0 erros de console. Kill server + limpe artefatos.

- [ ] **Step 4: Commit**

```bash
git add frontend/inventario.html frontend/app.js
git commit -m "feat: botao Etiquetas no inventario + Gerar etiqueta na ficha"
```

---

## Task 6: PRD + verificação final

**Files:** Modify `PRD-SisCalib.md`

- [ ] **Step 1: Atualizar PRD** — no §0 (tabela de status) trocar "Página pública por seção ⬜ Pendente"
  por uma linha nova? Não — manter. Adicionar linha "Etiquetas com QR Code (6.6) ✅ Entregue" com nota
  (ficha pública `publica.html` + endpoint `/publico/instrumentos/{id}`; `etiquetas.html` com QR
  client-side, individual/lote, impressão pelo navegador). No §6.6, marcar `[x]` todos os itens
  (geração de etiqueta; QR p/ ficha pública sem login; impressão individual/lote; critério de aceite).
  No roadmap Fase 1, marcar `[x]` "Etiquetas com QR Code".

- [ ] **Step 2: Suíte + import**

Run: `python -m pytest -q` → todos passam (141 + 4 novos). `python -c "import backend.main"` → ok.

- [ ] **Step 3: Commit**

```bash
git add PRD-SisCalib.md
git commit -m "docs: marca Etiquetas com QR Code (6.6) como entregue no PRD"
```

---

## Verificação final (antes do merge)

- [ ] `python -m pytest -q` → todos passam (141 + 4 novos).
- [ ] `python -c "import backend.main"` → app sobe.
- [ ] Lib QR vendorizada presente com LICENSE; `etiquetas.html` referencia o arquivo local (sem CDN).
- [ ] Smoke manual: `publica.html?id=N` mostra status; `etiquetas.html?ids=...` renderiza QR(s) e imprime;
  botão Etiquetas (inventário) e Gerar etiqueta (ficha) funcionam.
- [ ] Usar `superpowers:finishing-a-development-branch` para `feat/etiquetas-qr`.
