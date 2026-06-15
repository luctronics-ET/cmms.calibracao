# Gestão de Laboratórios — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cadastrar laboratórios de calibração com acreditação RBC/CGCRE, vincular calibrações a um laboratório (FK opcional + snapshot de texto), alertar acreditações a vencer — PRD §6.4.

**Architecture:** Nova tabela `laboratorio`; `Calibracao` ganha `laboratorio_id` (FK nullable). Status de acreditação reusa `calcular_status` de `backend/calibracao.py`. Router CRUD `backend/routers/laboratorios.py` + endpoints de alertas/histórico. Frontend: página `laboratorios.html`, item NAV, select no form de calibração, seção em `alertas.html`. Migração schema-only com `batch_alter_table` (SQLite).

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, SQLite, Pydantic v2, pytest, HTML/JS vanilla.

---

## File Structure

- **Modify** `backend/models.py` — classe `Laboratorio`; coluna `laboratorio_id` + relationship em `Calibracao`.
- **Modify** `backend/schemas.py` — `LaboratorioIn/Out`, `ListaLaboratorios`; `laboratorio_id` em `CalibracaoIn`/`CalibracaoOut`.
- **Modify** `backend/servico.py` — `laboratorio_para_out`; `laboratorio_id` no `calibracao_para_out`.
- **Create** `backend/routers/laboratorios.py` — CRUD + alertas + histórico.
- **Modify** `backend/routers/calibracoes.py` — snapshot do lab no `registrar`.
- **Modify** `backend/main.py` — registrar router.
- **Create** `alembic/versions/<rev>_laboratorio.py`.
- **Create** `tests/test_laboratorios_api.py`; **Modify** `tests/test_calibracoes_api.py`.
- **Create** `frontend/laboratorios.html`; **Modify** `frontend/app.js` (NAV + select), `frontend/alertas.html`.

---

## Task 1: Modelo `Laboratorio` + FK em `Calibracao`

**Files:** Modify `backend/models.py`

- [ ] **Step 1: Adicionar a classe `Laboratorio`** ao fim de `backend/models.py`:

```python
class Laboratorio(Base):
    __tablename__ = "laboratorio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    razao_social: Mapped[str] = mapped_column(String)
    cnpj: Mapped[str | None] = mapped_column(String)
    endereco: Mapped[str | None] = mapped_column(String)
    contato: Mapped[str | None] = mapped_column(String)
    telefone: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    numero_cgcre: Mapped[str | None] = mapped_column(String)
    acreditado_rbc: Mapped[bool] = mapped_column(Boolean, default=False)
    escopo: Mapped[str | None] = mapped_column(String)
    acreditacao_validade: Mapped[Date | None] = mapped_column(Date)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    observacoes: Mapped[str | None] = mapped_column(String)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 2: Adicionar a coluna FK em `Calibracao`** — dentro da classe `Calibracao`, logo após a linha `instrumento_id: Mapped[int] = mapped_column(...)`, adicionar:

```python
    laboratorio_id: Mapped[int | None] = mapped_column(
        ForeignKey("laboratorio.id", ondelete="SET NULL"), index=True
    )
```

- [ ] **Step 3: Verificar import** — `source .venv/bin/activate && python -c "import backend.models; print('ok')"`. Expected: `ok`. (`Integer, String, Date, DateTime, Boolean, ForeignKey, func` já importados.)

- [ ] **Step 4: Commit**

```bash
git add backend/models.py
git commit -m "feat: modelo Laboratorio + FK laboratorio_id em Calibracao"
```

---

## Task 2: Schemas

**Files:** Modify `backend/schemas.py`

- [ ] **Step 1: Adicionar os schemas de laboratório** ao fim de `backend/schemas.py`:

```python
class LaboratorioIn(BaseModel):
    razao_social: str
    cnpj: str | None = None
    endereco: str | None = None
    contato: str | None = None
    telefone: str | None = None
    email: str | None = None
    numero_cgcre: str | None = None
    acreditado_rbc: bool = False
    escopo: str | None = None
    acreditacao_validade: date | None = None
    ativo: bool = True
    observacoes: str | None = None


class LaboratorioOut(BaseModel):
    id: int
    razao_social: str
    cnpj: str | None
    endereco: str | None
    contato: str | None
    telefone: str | None
    email: str | None
    numero_cgcre: str | None
    acreditado_rbc: bool
    escopo: str | None
    acreditacao_validade: date | None
    ativo: bool
    observacoes: str | None
    # derivados
    status_acreditacao: str
    dias_restantes: int | None


class ListaLaboratorios(BaseModel):
    total: int
    itens: list[LaboratorioOut]
```

- [ ] **Step 2: Adicionar `laboratorio_id` ao `CalibracaoIn`** — na classe `CalibracaoIn`, após `data_calibracao: date`, adicionar:

```python
    laboratorio_id: int | None = None
```

- [ ] **Step 3: Adicionar `laboratorio_id` ao `CalibracaoOut`** — na classe `CalibracaoOut`, após `instrumento_id: int`, adicionar:

```python
    laboratorio_id: int | None
```

- [ ] **Step 4: Verificar** — `python -c "import backend.schemas; print('ok')"`. Expected `ok`.

- [ ] **Step 5: Commit**

```bash
git add backend/schemas.py
git commit -m "feat: schemas de laboratorio + laboratorio_id na calibracao"
```

---

## Task 3: Serviço — `laboratorio_para_out` + `laboratorio_id` no `calibracao_para_out`

**Files:** Modify `backend/servico.py`

- [ ] **Step 1: Atualizar imports** — em `backend/servico.py`, ajustar os imports de models e schemas para incluir `Laboratorio` e os schemas de laboratório. As linhas atuais são:

```python
from backend.models import Instrumento, Calibracao, StatusOperacional, Resultado
from backend.schemas import InstrumentoOut, CalibracaoOut
```
Trocar por:
```python
from backend.models import Instrumento, Calibracao, Laboratorio, StatusOperacional, Resultado
from backend.schemas import InstrumentoOut, CalibracaoOut, LaboratorioOut
```

- [ ] **Step 2: Adicionar `laboratorio_id` no `calibracao_para_out`** — na função `calibracao_para_out`, adicionar `laboratorio_id=cal.laboratorio_id,` logo após `instrumento_id=cal.instrumento_id,`.

- [ ] **Step 3: Adicionar `laboratorio_para_out`** ao fim de `backend/servico.py`:

```python
def laboratorio_para_out(lab: Laboratorio, hoje: date) -> LaboratorioOut:
    st = calcular_status(lab.acreditacao_validade, None, hoje)
    return LaboratorioOut(
        id=lab.id,
        razao_social=lab.razao_social,
        cnpj=lab.cnpj,
        endereco=lab.endereco,
        contato=lab.contato,
        telefone=lab.telefone,
        email=lab.email,
        numero_cgcre=lab.numero_cgcre,
        acreditado_rbc=lab.acreditado_rbc,
        escopo=lab.escopo,
        acreditacao_validade=lab.acreditacao_validade,
        ativo=lab.ativo,
        observacoes=lab.observacoes,
        status_acreditacao=st.status.value,
        dias_restantes=st.dias_restantes,
    )
```

(`calcular_status` e `date` já estão importados no topo de `servico.py`.)

- [ ] **Step 4: Verificar** — `python -c "import backend.servico; print('ok')"`. Expected `ok`.

- [ ] **Step 5: Commit**

```bash
git add backend/servico.py
git commit -m "feat: laboratorio_para_out (status acreditacao) + laboratorio_id no calibracao_para_out"
```

---

## Task 4: Router de laboratórios (CRUD + alertas + histórico)

**Files:** Create `backend/routers/laboratorios.py`; Modify `backend/main.py`; Test `tests/test_laboratorios_api.py`

- [ ] **Step 1: Escrever os testes** — criar `tests/test_laboratorios_api.py`:

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `source .venv/bin/activate && python -m pytest tests/test_laboratorios_api.py -q`
Expected: FAIL (404/erro — rotas não existem).

- [ ] **Step 3: Criar o router** `backend/routers/laboratorios.py`:

```python
"""Endpoints de gestão de laboratórios de calibração."""
from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Laboratorio, Calibracao
from backend.servico import laboratorio_para_out, calibracao_para_out
from backend.calibracao import StatusCalibracao
from backend.schemas import LaboratorioIn, LaboratorioOut, ListaLaboratorios, ListaCalibracoes

router = APIRouter(prefix="/api/v1", tags=["laboratorios"])

_URGENCIA = {
    StatusCalibracao.VENCIDO.value: 0,
    StatusCalibracao.A_VENCER_7.value: 1,
    StatusCalibracao.A_VENCER_30.value: 2,
    StatusCalibracao.A_VENCER_60.value: 3,
}


def _get_lab(db: Session, lab_id: int) -> Laboratorio:
    lab = db.get(Laboratorio, lab_id)
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratório não encontrado")
    return lab


def _aplicar(lab: Laboratorio, dados: LaboratorioIn) -> None:
    for campo, valor in dados.model_dump().items():
        setattr(lab, campo, valor)


@router.get("/laboratorios", response_model=ListaLaboratorios)
def listar(db: Session = Depends(get_db)):
    hoje = date.today()
    labs = db.query(Laboratorio).order_by(Laboratorio.razao_social).all()
    itens = [laboratorio_para_out(l, hoje) for l in labs]
    return ListaLaboratorios(total=len(itens), itens=itens)


@router.get("/laboratorios/alertas", response_model=list[LaboratorioOut])
def alertas(db: Session = Depends(get_db)):
    hoje = date.today()
    itens = [laboratorio_para_out(l, hoje) for l in db.query(Laboratorio).all()]
    itens = [i for i in itens if i.status_acreditacao in _URGENCIA]
    itens.sort(key=lambda i: (_URGENCIA[i.status_acreditacao],
                              i.dias_restantes if i.dias_restantes is not None else 99999))
    return itens


@router.get("/laboratorios/{lab_id}", response_model=LaboratorioOut)
def obter(lab_id: int, db: Session = Depends(get_db)):
    return laboratorio_para_out(_get_lab(db, lab_id), date.today())


@router.post("/laboratorios", response_model=LaboratorioOut, status_code=201)
def criar(dados: LaboratorioIn, db: Session = Depends(get_db)):
    lab = Laboratorio()
    _aplicar(lab, dados)
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return laboratorio_para_out(lab, date.today())


@router.put("/laboratorios/{lab_id}", response_model=LaboratorioOut)
def editar(lab_id: int, dados: LaboratorioIn, db: Session = Depends(get_db)):
    lab = _get_lab(db, lab_id)
    _aplicar(lab, dados)
    db.commit()
    db.refresh(lab)
    return laboratorio_para_out(lab, date.today())


@router.delete("/laboratorios/{lab_id}", status_code=204)
def remover(lab_id: int, db: Session = Depends(get_db)):
    lab = _get_lab(db, lab_id)
    # zera o vínculo explicitamente (não confia no SET NULL do SQLite); snapshot texto permanece
    db.query(Calibracao).filter(Calibracao.laboratorio_id == lab_id)\
        .update({Calibracao.laboratorio_id: None})
    db.delete(lab)
    db.commit()


@router.get("/laboratorios/{lab_id}/calibracoes", response_model=ListaCalibracoes)
def historico(lab_id: int, db: Session = Depends(get_db)):
    _get_lab(db, lab_id)
    cals = (db.query(Calibracao)
            .filter(Calibracao.laboratorio_id == lab_id)
            .order_by(Calibracao.data_calibracao.desc(), Calibracao.id.desc())
            .all())
    return ListaCalibracoes(total=len(cals), itens=[calibracao_para_out(c) for c in cals])
```

> Nota: a rota `/laboratorios/alertas` é declarada ANTES de `/laboratorios/{lab_id}` de propósito (precedência de path).

- [ ] **Step 4: Registrar no app** — em `backend/main.py`, adicionar `laboratorios` ao import `from backend.routers import ...` e `app.include_router(laboratorios.router)` após os demais includes.

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_laboratorios_api.py -q`
Expected: PASS (6).

- [ ] **Step 6: Commit**

```bash
git add backend/routers/laboratorios.py backend/main.py tests/test_laboratorios_api.py
git commit -m "feat: router de laboratorios (CRUD + alertas + historico)"
```

---

## Task 5: Snapshot do laboratório no registro de calibração

**Files:** Modify `backend/routers/calibracoes.py`; Test `tests/test_laboratorios_api.py` (DELETE→null e snapshot) + `tests/test_calibracoes_api.py`

- [ ] **Step 1: Escrever os testes** — adicionar ao fim de `tests/test_laboratorios_api.py`:

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_laboratorios_api.py -k "snapshot or zera or historico" -q`
Expected: FAIL (snapshot não acontece; `laboratorio_id` não é gravado).

- [ ] **Step 3: Implementar o snapshot** — em `backend/routers/calibracoes.py`:

  a. Adicionar `Laboratorio` ao import de models: trocar
     `from backend.models import Instrumento, Calibracao, Resultado`
     por `from backend.models import Instrumento, Calibracao, Resultado, Laboratorio`.

  b. Na função `registrar`, logo após `ciclo = inst.ciclo_meses or 12`, e antes de construir `cal`, resolver os campos do laboratório:

```python
    lab_id = dados.laboratorio_id
    lab_nome, lab_cnpj, lab_cgcre, lab_rbc = (
        dados.laboratorio, dados.laboratorio_cnpj, dados.numero_cgcre, dados.acreditacao_rbc)
    if lab_id is not None:
        lab = db.get(Laboratorio, lab_id)
        if not lab:
            raise HTTPException(status_code=404, detail="Laboratório não encontrado")
        lab_nome, lab_cnpj, lab_cgcre, lab_rbc = (
            lab.razao_social, lab.cnpj, lab.numero_cgcre, lab.acreditado_rbc)
```

  c. No construtor `Calibracao(...)`, trocar as 4 linhas de laboratório pelos valores resolvidos e incluir a FK:

```python
        laboratorio_id=lab_id,
        laboratorio=lab_nome,
        laboratorio_cnpj=lab_cnpj,
        acreditacao_rbc=lab_rbc,
        numero_cgcre=lab_cgcre,
```
(ou seja: `laboratorio=dados.laboratorio` → `laboratorio=lab_nome`, etc., e adicionar `laboratorio_id=lab_id`.)

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_laboratorios_api.py -q`
Expected: PASS (todos). Depois `python -m pytest tests/test_calibracoes_api.py -q` — os testes existentes (sem `laboratorio_id`) continuam passando, pois `lab_id` é None e o comportamento texto-livre é preservado.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/calibracoes.py tests/test_laboratorios_api.py
git commit -m "feat: snapshot do laboratorio no registro de calibracao"
```

---

## Task 6: Migração Alembic

**Files:** Create `alembic/versions/<rev>_laboratorio.py`

- [ ] **Step 1: Gerar a migração**

Run: `SISCALIB_DB_URL="sqlite:////tmp/lab.db" alembic revision -m "laboratorio"`
Confirme que `down_revision = 'ba250c7eb571'` (head atual). Se não, ajuste.

- [ ] **Step 2: Escrever `upgrade()`/`downgrade()`** no arquivo gerado:

```python
def upgrade() -> None:
    op.create_table(
        'laboratorio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('razao_social', sa.String(), nullable=False),
        sa.Column('cnpj', sa.String(), nullable=True),
        sa.Column('endereco', sa.String(), nullable=True),
        sa.Column('contato', sa.String(), nullable=True),
        sa.Column('telefone', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('numero_cgcre', sa.String(), nullable=True),
        sa.Column('acreditado_rbc', sa.Boolean(), nullable=False),
        sa.Column('escopo', sa.String(), nullable=True),
        sa.Column('acreditacao_validade', sa.Date(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('observacoes', sa.String(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('calibracao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('laboratorio_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_calibracao_laboratorio', 'laboratorio',
            ['laboratorio_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('ix_calibracao_laboratorio_id', ['laboratorio_id'])


def downgrade() -> None:
    with op.batch_alter_table('calibracao', schema=None) as batch_op:
        batch_op.drop_index('ix_calibracao_laboratorio_id')
        batch_op.drop_constraint('fk_calibracao_laboratorio', type_='foreignkey')
        batch_op.drop_column('laboratorio_id')
    op.drop_table('laboratorio')
```

- [ ] **Step 3: Aplicar num banco limpo**

Run: `rm -f /tmp/lab.db && SISCALIB_DB_URL="sqlite:////tmp/lab.db" alembic upgrade head`
Expected: aplica todas as revisões até `laboratorio` sem erro. Depois `rm -f /tmp/lab.db`.

- [ ] **Step 4: Suíte completa**

Run: `python -m pytest -q`
Expected: PASS (todos — 110 + ~9 novos).

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/
git commit -m "feat: migracao da tabela laboratorio + FK em calibracao"
```

---

## Task 7: Frontend — página `laboratorios.html` + NAV

**Files:** Create `frontend/laboratorios.html`; Modify `frontend/app.js`

> UI: verificação manual. Antes de editar, leia `frontend/app.js` (`montarShell`, `NAV`, `abrirModal`, `SDK`), `frontend/cadastro.html` e `frontend/calibracao.html` para espelhar o padrão.

- [ ] **Step 1: Item NAV** — em `frontend/app.js`, no array `NAV`, adicionar após a entrada de Calibrações:

```javascript
  ["laboratorios.html", "building", "Laboratórios"],
```

- [ ] **Step 2: Criar `frontend/laboratorios.html`** espelhando o skeleton de `calibracao.html` (mesmo `<head>`, vendor CSS, `montarShell("laboratorios.html")`, `app.js`). Conteúdo:
  - `<h1>Laboratórios</h1>` + botão "Novo laboratório".
  - Tabela (`.twrap` + `table`) carregada de `GET /api/v1/laboratorios`: colunas Razão social · CNPJ · CGCRE · Acreditação (validade `fmtData` + `badgeStatus(status_acreditacao)`) · Escopo · Ações.
  - Ações por linha: "Editar" (abre modal com form preenchido) e "Excluir" (confirm → `SDK.del('/laboratorios/'+id)` → recarrega).
  - Form (em modal via `abrirModal`, ou inline) com todos os campos de `LaboratorioIn`: razao_social (obrigatório), cnpj, endereco, contato, telefone, email, numero_cgcre, acreditado_rbc (checkbox), escopo (textarea), acreditacao_validade (date), ativo (checkbox), observacoes (textarea). Salvar: `POST /laboratorios` (novo) ou `PUT /laboratorios/{id}` (edição) → fecha modal → recarrega tabela.
  - Usar `esc()` em todo valor de usuário injetado via innerHTML.

- [ ] **Step 3: Verificação manual**

Run: `source .venv/bin/activate && uvicorn backend.main:app --port 8021 &` (aguarde ~2s).
- `node --check frontend/app.js` → sem erro.
- `curl -s -o /dev/null -w "%{http_code}" localhost:8021/laboratorios.html` → 200.
- Criar um lab: `curl -s -X POST localhost:8021/api/v1/laboratorios -H 'Content-Type: application/json' -d '{"razao_social":"Lab Teste","numero_cgcre":"CRL-1","acreditacao_validade":"2027-01-01"}'`.
- No navegador (`localhost:8021/laboratorios.html`): confirmar que o lab aparece com badge "Válido", abrir Editar, salvar, e Excluir. Kill o server (`kill %1`).

- [ ] **Step 4: Commit**

```bash
git add frontend/laboratorios.html frontend/app.js
git commit -m "feat: pagina de laboratorios (CRUD) + item NAV"
```

---

## Task 8: Frontend — select de lab no form de calibração + seção em alertas

**Files:** Modify `frontend/app.js`, `frontend/alertas.html`

- [ ] **Step 1: Select de laboratório no `renderFormCalibracao`** — em `frontend/app.js`, dentro de `renderFormCalibracao`, adicionar no topo do form um `<select id="calibLab">` com uma opção vazia ("— laboratório (opcional) —") e as opções carregadas de `GET /api/v1/laboratorios` (value = id, label = razão social). No submit: se um lab estiver selecionado, incluir `laboratorio_id: Number(valor)` no corpo do POST; o campo texto `laboratorio` permanece como fallback para quando nenhum lab é escolhido. (Carregue a lista de labs de forma assíncrona ao montar o form; trate lista vazia exibindo só a opção vazia.)

- [ ] **Step 2: Seção "Acreditações a vencer" em `alertas.html`** — adicionar abaixo da tabela de instrumentos uma nova seção/card que faz `SDK.get('/laboratorios/alertas')` e renderiza uma tabela: Laboratório · CGCRE · Validade (`fmtData`) · Status (`badgeStatus(status_acreditacao)`). Se vazia, mostrar "Nenhuma acreditação a vencer." Seguir o estilo das outras tabelas da página. Usar `esc()` nos valores.

- [ ] **Step 3: Verificação manual**

Run: `uvicorn backend.main:app --port 8022 &` (aguarde ~2s). Com um lab criado (via curl) e um instrumento existente:
- Abrir a ficha de um instrumento → seção Calibrações → "Registrar calibração": o select de laboratório aparece e lista o lab; registrar escolhendo o lab; confirmar (via `GET /instrumentos/{id}/calibracoes` ou na UI) que a calibração ficou vinculada e com o texto preenchido.
- Criar um lab com `acreditacao_validade` próxima/passada e abrir `alertas.html`: a seção "Acreditações a vencer" lista o lab com badge. Kill o server.

- [ ] **Step 4: Commit**

```bash
git add frontend/app.js frontend/alertas.html
git commit -m "feat: select de laboratorio na calibracao + secao de acreditacoes em alertas"
```

---

## Task 9: PRD + verificação final

**Files:** Modify `PRD-SisCalib.md`

- [ ] **Step 1: Marcar 6.4 como entregue** — no §0 (tabela de status) trocar "Gestão de laboratórios (6.4) ⬜ Pendente" por ✅ Entregue com nota (entidade `laboratorio`, CRUD, acreditação CGCRE + alerta, FK opcional na calibração com snapshot). No roadmap da Fase 1, trocar `[ ] Gestão de laboratórios externos...` por `[x]`. No §6.4, marcar os itens implementados com `[x]` (cadastro, acreditação CGCRE, alerta de vencimento, histórico por laboratório).

- [ ] **Step 2: Suíte completa**

Run: `python -m pytest -q` → todos passam. `python -c "import backend.main"` → ok.

- [ ] **Step 3: Commit**

```bash
git add PRD-SisCalib.md
git commit -m "docs: marca Gestao de Laboratorios (6.4) como entregue no PRD"
```

---

## Verificação final (antes do merge)

- [ ] `python -m pytest -q` → todos passam (110 + ~9 novos).
- [ ] `python -c "import backend.main"` → app sobe.
- [ ] Migração aplica limpa em banco novo.
- [ ] Smoke manual: CRUD de laboratório, badge de acreditação, select na calibração com snapshot, seção de alertas.
- [ ] Usar `superpowers:finishing-a-development-branch` para `feat/gestao-laboratorios`.
