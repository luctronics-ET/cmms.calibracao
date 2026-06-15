# Contratos & Saldo da ATA — Implementation Plan (sub-projeto #1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cadastrar contratos/ATAs e seus itens (quantidade, valor, consumo manual), exibir saldo por item e agregado, e alertar contratos com vigência a vencer ou saldo baixo. PRD §6.14 (parcial).

**Architecture:** Tabelas `contrato` + `item_contrato` (1→N, cascade). Motor puro `backend/contratos_calc.py` (saldo do item, status do saldo). Status de vigência reusa `calcular_status`. Router CRUD `backend/routers/contratos.py` + subendpoints de item + alertas. Frontend: página `contratos.html`, item NAV, seção em `alertas.html`. Migração schema-only.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, SQLite, Pydantic v2, pytest, HTML/JS vanilla.

---

## File Structure

- **Modify** `backend/models.py` — enum `ContratoTipo`; classes `Contrato`, `ItemContrato`.
- **Create** `backend/contratos_calc.py` — `saldo_item`, `status_saldo` (puros).
- **Modify** `backend/schemas.py` — `ContratoIn/Out`, `ItemContratoIn/Out`, `ListaContratos`.
- **Modify** `backend/servico.py` — `contrato_para_out`, `item_contrato_para_out`.
- **Create** `backend/routers/contratos.py` — CRUD + itens + alertas.
- **Modify** `backend/main.py` — registrar router.
- **Create** `alembic/versions/<rev>_contrato.py`.
- **Create** `tests/test_contratos_calc.py`, `tests/test_contratos_api.py`.
- **Create** `frontend/contratos.html`; **Modify** `frontend/app.js` (NAV), `frontend/alertas.html`.

---

## Task 1: Modelos `Contrato` + `ItemContrato`

**Files:** Modify `backend/models.py`

- [ ] **Step 1: Adicionar o enum `ContratoTipo`** após `class Resultado` (perto dos outros enums no topo):

```python
class ContratoTipo(str, enum.Enum):
    ATA = "ATA"
    CONTRATO = "CONTRATO"
    CMS = "CMS"
```

- [ ] **Step 2: Adicionar as classes** ao fim de `backend/models.py`:

```python
class Contrato(Base):
    __tablename__ = "contrato"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero: Mapped[str] = mapped_column(String)
    tipo: Mapped[ContratoTipo] = mapped_column(Enum(ContratoTipo), default=ContratoTipo.ATA)
    fornecedor: Mapped[str | None] = mapped_column(String)
    objeto: Mapped[str | None] = mapped_column(String)
    vigencia_inicio: Mapped[Date | None] = mapped_column(Date)
    vigencia_fim: Mapped[Date | None] = mapped_column(Date)
    valor_total: Mapped[float | None] = mapped_column(Numeric(14, 2))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    observacoes: Mapped[str | None] = mapped_column(String)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    itens: Mapped[list["ItemContrato"]] = relationship(
        cascade="all, delete-orphan", order_by="ItemContrato.id"
    )


class ItemContrato(Base):
    __tablename__ = "item_contrato"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contrato_id: Mapped[int] = mapped_column(
        ForeignKey("contrato.id", ondelete="CASCADE"), index=True
    )
    numero: Mapped[str | None] = mapped_column(String)
    descricao: Mapped[str | None] = mapped_column(String)
    quantidade: Mapped[int] = mapped_column(Integer, default=0)
    valor_unitario: Mapped[float | None] = mapped_column(Numeric(12, 2))
    usado: Mapped[int] = mapped_column(Integer, default=0)
    observacoes: Mapped[str | None] = mapped_column(String)
```

(Relação SEM `passive_deletes` — o ORM deleta os itens ao remover o contrato.)

- [ ] **Step 3: Verificar** — `source .venv/bin/activate && python -c "import backend.models; print('ok')"`. Expected `ok`.

- [ ] **Step 4: Commit**

```bash
git add backend/models.py
git commit -m "feat: modelos Contrato + ItemContrato"
```

---

## Task 2: Motor puro `contratos_calc.py`

**Files:** Create `backend/contratos_calc.py`; Test `tests/test_contratos_calc.py`

- [ ] **Step 1: Escrever os testes** — criar `tests/test_contratos_calc.py`:

```python
from backend.contratos_calc import saldo_item, status_saldo


def test_saldo_item_basico():
    saldo, valor_saldo = saldo_item(quantidade=10, usado=3, valor_unitario=100.0)
    assert saldo == 7
    assert valor_saldo == 700.0


def test_saldo_item_clamp_em_zero():
    saldo, valor_saldo = saldo_item(quantidade=2, usado=5, valor_unitario=50.0)
    assert saldo == -3            # saldo pode ser negativo (overuse)
    assert valor_saldo == 0.0     # mas valor_saldo nunca é negativo


def test_saldo_item_sem_valor_unitario():
    saldo, valor_saldo = saldo_item(quantidade=10, usado=0, valor_unitario=None)
    assert saldo == 10
    assert valor_saldo == 0.0


def test_status_saldo_ok_baixo_esgotado():
    assert status_saldo(valor_saldo_total=800.0, valor_total=1000.0) == "OK"       # 80%
    assert status_saldo(valor_saldo_total=150.0, valor_total=1000.0) == "BAIXO"    # 15%
    assert status_saldo(valor_saldo_total=0.0, valor_total=1000.0) == "ESGOTADO"
    assert status_saldo(valor_saldo_total=-10.0, valor_total=1000.0) == "ESGOTADO"


def test_status_saldo_sem_valor_total():
    assert status_saldo(valor_saldo_total=500.0, valor_total=None) == "OK"
    assert status_saldo(valor_saldo_total=500.0, valor_total=0.0) == "OK"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_contratos_calc.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implementar** — criar `backend/contratos_calc.py`:

```python
"""Motor puro de saldo de contrato/ATA. Sem I/O, sem DB."""
from __future__ import annotations

LIMIAR_SALDO_BAIXO = 0.20


def saldo_item(quantidade: int, usado: int, valor_unitario: float | None) -> tuple[int, float]:
    """Retorna (saldo, valor_saldo). saldo = quantidade - usado (pode ser negativo);
    valor_saldo = max(saldo, 0) * valor_unitario (0 se sem valor unitário)."""
    saldo = (quantidade or 0) - (usado or 0)
    if valor_unitario is None:
        return saldo, 0.0
    return saldo, max(saldo, 0) * float(valor_unitario)


def status_saldo(valor_saldo_total: float, valor_total: float | None) -> str:
    """OK / BAIXO / ESGOTADO. Sem valor_total definido (None/0) -> OK."""
    if valor_saldo_total <= 0:
        return "ESGOTADO"
    if not valor_total:
        return "OK"
    if valor_saldo_total / valor_total < LIMIAR_SALDO_BAIXO:
        return "BAIXO"
    return "OK"
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_contratos_calc.py -q`
Expected: PASS (5).

- [ ] **Step 5: Commit**

```bash
git add backend/contratos_calc.py tests/test_contratos_calc.py
git commit -m "feat: motor puro de saldo de contrato (saldo_item + status_saldo)"
```

---

## Task 3: Schemas

**Files:** Modify `backend/schemas.py`

- [ ] **Step 1: Adicionar os schemas** ao fim de `backend/schemas.py`:

```python
class ItemContratoIn(BaseModel):
    numero: str | None = None
    descricao: str | None = None
    quantidade: int = 0
    valor_unitario: float | None = None
    usado: int = 0
    observacoes: str | None = None


class ItemContratoOut(BaseModel):
    id: int
    contrato_id: int
    numero: str | None
    descricao: str | None
    quantidade: int
    valor_unitario: float | None
    usado: int
    observacoes: str | None
    # derivados
    saldo: int
    valor_saldo: float


class ContratoIn(BaseModel):
    numero: str
    tipo: Literal["ATA", "CONTRATO", "CMS"] = "ATA"
    fornecedor: str | None = None
    objeto: str | None = None
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    valor_total: float | None = None
    ativo: bool = True
    observacoes: str | None = None


class ContratoOut(BaseModel):
    id: int
    numero: str
    tipo: str
    fornecedor: str | None
    objeto: str | None
    vigencia_inicio: date | None
    vigencia_fim: date | None
    valor_total: float | None
    ativo: bool
    observacoes: str | None
    itens: list[ItemContratoOut]
    # derivados
    status_vigencia: str
    dias_restantes: int | None
    valor_saldo_total: float
    saldo_percent: float | None
    status_saldo: str


class ListaContratos(BaseModel):
    total: int
    itens: list[ContratoOut]
```

- [ ] **Step 2: Verificar** — `python -c "import backend.schemas; print('ok')"`. Expected `ok`.

- [ ] **Step 3: Commit**

```bash
git add backend/schemas.py
git commit -m "feat: schemas de contrato e item_contrato"
```

---

## Task 4: Serviço — serializadores

**Files:** Modify `backend/servico.py`

- [ ] **Step 1: Atualizar imports** — em `backend/servico.py`, adicionar ao import de models `Contrato, ItemContrato` e ao import de schemas `ContratoOut, ItemContratoOut`. Importar o motor:

```python
from backend.contratos_calc import saldo_item, status_saldo
```
(adicionar essa linha junto aos outros imports do topo; `calcular_status` já está importado.)

- [ ] **Step 2: Adicionar os serializadores** ao fim de `backend/servico.py`:

```python
def item_contrato_para_out(item: ItemContrato) -> ItemContratoOut:
    saldo, valor_saldo = saldo_item(item.quantidade, item.usado,
                                    float(item.valor_unitario) if item.valor_unitario is not None else None)
    return ItemContratoOut(
        id=item.id,
        contrato_id=item.contrato_id,
        numero=item.numero,
        descricao=item.descricao,
        quantidade=item.quantidade,
        valor_unitario=float(item.valor_unitario) if item.valor_unitario is not None else None,
        usado=item.usado,
        observacoes=item.observacoes,
        saldo=saldo,
        valor_saldo=valor_saldo,
    )


def contrato_para_out(contrato: Contrato, hoje: date) -> ContratoOut:
    itens = [item_contrato_para_out(i) for i in contrato.itens]
    valor_saldo_total = sum(i.valor_saldo for i in itens)
    vt = float(contrato.valor_total) if contrato.valor_total is not None else None
    st = calcular_status(contrato.vigencia_fim, None, hoje)
    saldo_percent = (valor_saldo_total / vt) if vt else None
    return ContratoOut(
        id=contrato.id,
        numero=contrato.numero,
        tipo=contrato.tipo.value,
        fornecedor=contrato.fornecedor,
        objeto=contrato.objeto,
        vigencia_inicio=contrato.vigencia_inicio,
        vigencia_fim=contrato.vigencia_fim,
        valor_total=vt,
        ativo=contrato.ativo,
        observacoes=contrato.observacoes,
        itens=itens,
        status_vigencia=st.status.value,
        dias_restantes=st.dias_restantes,
        valor_saldo_total=valor_saldo_total,
        saldo_percent=saldo_percent,
        status_saldo=status_saldo(valor_saldo_total, vt),
    )
```

- [ ] **Step 3: Verificar** — `python -c "import backend.servico; print('ok')"`. Expected `ok`.

- [ ] **Step 4: Commit**

```bash
git add backend/servico.py
git commit -m "feat: serializadores contrato_para_out + item_contrato_para_out"
```

---

## Task 5: Router de contratos (CRUD + itens + alertas)

**Files:** Create `backend/routers/contratos.py`; Modify `backend/main.py`; Test `tests/test_contratos_api.py`

- [ ] **Step 1: Escrever os testes** — criar `tests/test_contratos_api.py`:

```python
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
```

> Nota: no `test_itens_recalculam_saldo`, dois itens de saldo 500 + 0 = `valor_saldo_total` 500; 500/1000 = 50% → na verdade **OK**, não BAIXO. CORRIJA a asserção ao implementar se necessário: o esperado correto é `status_saldo == "OK"`. (Deixe o teste refletindo a regra: <20% = BAIXO.) Ajuste a última linha do teste para `assert c2["status_saldo"] == "OK"`.

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_contratos_api.py -q`
Expected: FAIL (rotas não existem).

- [ ] **Step 3: Criar o router** `backend/routers/contratos.py`:

```python
"""Endpoints de contratos e itens (saldo da ATA)."""
from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Contrato, ItemContrato, ContratoTipo
from backend.servico import contrato_para_out
from backend.calibracao import StatusCalibracao
from backend.schemas import ContratoIn, ContratoOut, ListaContratos, ItemContratoIn

router = APIRouter(prefix="/api/v1", tags=["contratos"])

_URGENCIA = {
    StatusCalibracao.VENCIDO.value: 0,
    StatusCalibracao.A_VENCER_7.value: 1,
    StatusCalibracao.A_VENCER_30.value: 2,
    StatusCalibracao.A_VENCER_60.value: 3,
}


def _get_contrato(db: Session, cid: int) -> Contrato:
    c = db.get(Contrato, cid)
    if not c:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    return c


def _aplicar_contrato(c: Contrato, dados: ContratoIn) -> None:
    payload = dados.model_dump()
    payload["tipo"] = ContratoTipo(payload["tipo"])
    for campo, valor in payload.items():
        setattr(c, campo, valor)


def _aplicar_item(item: ItemContrato, dados: ItemContratoIn) -> None:
    for campo, valor in dados.model_dump().items():
        setattr(item, campo, valor)


def _out(db: Session, c: Contrato) -> ContratoOut:
    db.refresh(c)
    return contrato_para_out(c, date.today())


@router.get("/contratos", response_model=ListaContratos)
def listar(db: Session = Depends(get_db)):
    hoje = date.today()
    cs = db.query(Contrato).order_by(Contrato.numero).all()
    itens = [contrato_para_out(c, hoje) for c in cs]
    return ListaContratos(total=len(itens), itens=itens)


@router.get("/contratos/alertas", response_model=list[ContratoOut])
def alertas(db: Session = Depends(get_db)):
    hoje = date.today()
    itens = [contrato_para_out(c, hoje) for c in db.query(Contrato).all()]
    itens = [c for c in itens
             if c.status_vigencia in _URGENCIA or c.status_saldo in ("BAIXO", "ESGOTADO")]
    itens.sort(key=lambda c: (_URGENCIA.get(c.status_vigencia, 9),
                              0 if c.status_saldo == "ESGOTADO" else 1))
    return itens


@router.get("/contratos/{cid}", response_model=ContratoOut)
def obter(cid: int, db: Session = Depends(get_db)):
    return contrato_para_out(_get_contrato(db, cid), date.today())


@router.post("/contratos", response_model=ContratoOut, status_code=201)
def criar(dados: ContratoIn, db: Session = Depends(get_db)):
    c = Contrato()
    _aplicar_contrato(c, dados)
    db.add(c)
    db.commit()
    return _out(db, c)


@router.put("/contratos/{cid}", response_model=ContratoOut)
def editar(cid: int, dados: ContratoIn, db: Session = Depends(get_db)):
    c = _get_contrato(db, cid)
    _aplicar_contrato(c, dados)
    db.commit()
    return _out(db, c)


@router.delete("/contratos/{cid}", status_code=204)
def remover(cid: int, db: Session = Depends(get_db)):
    c = _get_contrato(db, cid)
    db.delete(c)  # itens caem por cascade delete-orphan do ORM
    db.commit()


@router.post("/contratos/{cid}/itens", response_model=ContratoOut, status_code=201)
def criar_item(cid: int, dados: ItemContratoIn, db: Session = Depends(get_db)):
    c = _get_contrato(db, cid)
    item = ItemContrato(contrato_id=cid)
    _aplicar_item(item, dados)
    db.add(item)
    db.commit()
    return _out(db, c)


@router.put("/contratos/{cid}/itens/{item_id}", response_model=ContratoOut)
def editar_item(cid: int, item_id: int, dados: ItemContratoIn, db: Session = Depends(get_db)):
    c = _get_contrato(db, cid)
    item = db.get(ItemContrato, item_id)
    if not item or item.contrato_id != cid:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    _aplicar_item(item, dados)
    db.commit()
    return _out(db, c)


@router.delete("/contratos/{cid}/itens/{item_id}", response_model=ContratoOut)
def remover_item(cid: int, item_id: int, db: Session = Depends(get_db)):
    c = _get_contrato(db, cid)
    item = db.get(ItemContrato, item_id)
    if not item or item.contrato_id != cid:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    db.delete(item)
    db.commit()
    return _out(db, c)
```

- [ ] **Step 4: Registrar no app** — em `backend/main.py`, adicionar `contratos` ao import `from backend.routers import ...` e `app.include_router(contratos.router)`.

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_contratos_api.py -q`
Expected: PASS (todos — confirme que ajustou a asserção do `test_itens_recalculam_saldo` para `"OK"` conforme a nota do Step 1).

- [ ] **Step 6: Commit**

```bash
git add backend/routers/contratos.py backend/main.py tests/test_contratos_api.py
git commit -m "feat: router de contratos (CRUD + itens + alertas)"
```

---

## Task 6: Migração Alembic

**Files:** Create `alembic/versions/<rev>_contrato.py`

- [ ] **Step 1: Gerar**

Run: `SISCALIB_DB_URL="sqlite:////tmp/ct.db" alembic revision -m "contrato"`
Confirme `down_revision = 'a5e01e43b2d8'`.

- [ ] **Step 2: Escrever `upgrade()`/`downgrade()`**:

```python
def upgrade() -> None:
    op.create_table(
        'contrato',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('numero', sa.String(), nullable=False),
        sa.Column('tipo', sa.Enum('ATA', 'CONTRATO', 'CMS', name='contratotipo'), nullable=False),
        sa.Column('fornecedor', sa.String(), nullable=True),
        sa.Column('objeto', sa.String(), nullable=True),
        sa.Column('vigencia_inicio', sa.Date(), nullable=True),
        sa.Column('vigencia_fim', sa.Date(), nullable=True),
        sa.Column('valor_total', sa.Numeric(14, 2), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('observacoes', sa.String(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'item_contrato',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contrato_id', sa.Integer(), nullable=False),
        sa.Column('numero', sa.String(), nullable=True),
        sa.Column('descricao', sa.String(), nullable=True),
        sa.Column('quantidade', sa.Integer(), nullable=False),
        sa.Column('valor_unitario', sa.Numeric(12, 2), nullable=True),
        sa.Column('usado', sa.Integer(), nullable=False),
        sa.Column('observacoes', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['contrato_id'], ['contrato.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_item_contrato_contrato_id', 'item_contrato', ['contrato_id'])


def downgrade() -> None:
    op.drop_index('ix_item_contrato_contrato_id', table_name='item_contrato')
    op.drop_table('item_contrato')
    op.drop_table('contrato')
```

- [ ] **Step 3: Aplicar em banco limpo**

Run: `rm -f /tmp/ct.db && SISCALIB_DB_URL="sqlite:////tmp/ct.db" alembic upgrade head`
Expected: aplica até `contrato` sem erro. Depois `rm -f /tmp/ct.db`.

- [ ] **Step 4: Suíte completa**

Run: `python -m pytest -q`
Expected: PASS (118 + ~12 novos).

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/
git commit -m "feat: migracao das tabelas contrato + item_contrato"
```

---

## Task 7: Frontend — `contratos.html` + NAV

**Files:** Create `frontend/contratos.html`; Modify `frontend/app.js`

> UI: verificação manual/browser. Antes de editar, leia `frontend/app.js` (`SDK`, `montarShell`, `NAV`, `abrirModal`, `esc`, `fmtData`, `badgeStatus`), `frontend/laboratorios.html` (padrão de lista+modal CRUD) e `frontend/siscalib.css`.

- [ ] **Step 1: Item NAV** — em `frontend/app.js`, no array `NAV`, após a entrada de Laboratórios:

```javascript
  ["contratos.html", "file-earmark-text", "Contratos"],
```

- [ ] **Step 2: Badges de saldo** — em `frontend/siscalib.css`, garantir classes para o status de saldo reusando as cores existentes. Adicionar ao fim:

```css
.bdg.saldo-OK{background:var(--green-bg);color:var(--green)}
.bdg.saldo-BAIXO{background:var(--amber-bg);color:var(--amber)}
.bdg.saldo-ESGOTADO{background:var(--red-bg);color:var(--red)}
```

- [ ] **Step 3: Criar `frontend/contratos.html`** espelhando `laboratorios.html`:
  - `<h1>Contratos & Saldo da ATA</h1>` + botão "Novo contrato".
  - Tabela de `GET /contratos`: Número · Tipo · Fornecedor · Vigência (`fmtData(vigencia_fim)` + `badgeStatus(status_vigencia)`) · Valor total · Saldo (`valor_saldo_total` formatado em R$ + `<span class="bdg saldo-${status_saldo}">${status_saldo}</span>`) · Ações (Abrir, Editar, Excluir).
  - "Novo"/"Editar" → modal (`abrirModal`) com campos de `ContratoIn`: numero (obrigatório), tipo (select ATA/CONTRATO/CMS), fornecedor, objeto, vigencia_inicio (date), vigencia_fim (date), valor_total (number), ativo (checkbox), observacoes (textarea). Salvar → `POST`/`PUT` → recarrega.
  - "Abrir" → modal de detalhe: dados do contrato + **tabela de itens** (`GET /contratos/{id}` traz `itens`): item nº · descrição · quant · valor unit (R$) · usado · saldo · valor saldo (R$). Botão "Adicionar item" e por linha Editar/Excluir item. Cada operação chama `POST/PUT/DELETE /contratos/{id}/itens[/{item_id}]` (retorna o ContratoOut atualizado) → re-renderiza o detalhe.
  - "Excluir" contrato → confirm → `SDK.del('/contratos/'+id)` → recarrega lista.
  - Helper local `money(n)` → `"R$ " + Number(n||0).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2})`.
  - `esc()` em todo valor de usuário.

- [ ] **Step 4: Verificação (browser)**

Run: `source .venv/bin/activate && uvicorn backend.main:app --port 8031 &` (aguarde ~2s).
- `node --check frontend/app.js` → ok. `curl -s -o /dev/null -w "%{http_code}" localhost:8031/contratos.html` → 200.
- Criar contrato + 2 itens via UI; abrir detalhe; conferir saldo/valor_saldo e badge; editar um item (mudar `usado`) e ver o saldo recalcular; excluir item; excluir contrato. Se tiver Playwright MCP, dirija o fluxo e cheque o console (só favicon 404 aceitável). Kill o server e limpe artefatos.

- [ ] **Step 5: Commit**

```bash
git add frontend/contratos.html frontend/app.js frontend/siscalib.css
git commit -m "feat: pagina de contratos (CRUD + itens/saldo) + item NAV"
```

---

## Task 8: Frontend — seção em `alertas.html` + PRD

**Files:** Modify `frontend/alertas.html`, `PRD-SisCalib.md`

- [ ] **Step 1: Seção "Contratos a vencer / saldo baixo"** — em `frontend/alertas.html`, abaixo da seção de instrumentos (e da de acreditações, se presente), adicionar um card que faz `SDK.get('/contratos/alertas')` e renderiza uma tabela: Número · Fornecedor · Vigência (`fmtData` + `badgeStatus(status_vigencia)`) · Saldo (`status_saldo` badge). Vazia → "Nenhum contrato a vencer ou com saldo baixo." `esc()` nos valores.

- [ ] **Step 2: Verificação** — subir o app, criar um contrato com vigência próxima e outro com saldo baixo, abrir `alertas.html` e confirmar que aparecem na nova seção.

- [ ] **Step 3: Atualizar PRD** — em `PRD-SisCalib.md` §0 (tabela de status), adicionar uma linha "Contratos & Saldo da ATA (6.14, parcial) ✅ Entregue" com nota (entidades `contrato`/`item_contrato`, saldo derivado, alertas de vigência/saldo; consumo manual — automático virá com os Lotes). No §6.14, marcar `[x]` os itens entregues (cadastro de contratos/ARPs; alerta de vencimento/saldo baixo).

- [ ] **Step 4: Suíte + commit**

Run: `python -m pytest -q` → todos passam. `python -c "import backend.main"` → ok.
```bash
git add frontend/alertas.html PRD-SisCalib.md
git commit -m "feat: secao de contratos em alertas + PRD (6.14 parcial)"
```

---

## Verificação final (antes do merge)

- [ ] `python -m pytest -q` → todos passam (118 + ~12 novos).
- [ ] `python -c "import backend.main"` → app sobe.
- [ ] Migração aplica limpa em banco novo.
- [ ] Smoke manual: CRUD contrato + itens, saldo recalcula, badges, seção de alertas.
- [ ] Usar `superpowers:finishing-a-development-branch` para `feat/contratos-saldo-ata`.
