# Catálogo de Preços — Implementation Plan (sub-projeto #2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cadastrar opções de preço de calibração por tipo de instrumento (fornecedor × contrato), com preço próprio e vínculo opcional a um item de contrato, e semear os dados reais da ATA 129/2025. PRD §6.14/§6.15 (parcial).

**Architecture:** Tabela `catalogo_preco` (FK tipo_id + FK item_contrato_id opcional). Router CRUD `backend/routers/catalogo.py`. Seed de startup `backend/seed_ata.py` (contrato ATA + itens + catálogo, matching de tipo por substring normalizado). Frontend: página `catalogo.html` + item NAV. Migração schema-only.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, SQLite, Pydantic v2, pytest, HTML/JS vanilla.

---

## File Structure

- **Modify** `backend/models.py` — classe `CatalogoPreco`.
- **Modify** `backend/schemas.py` — `CatalogoPrecoIn/Out`, `ListaCatalogo`.
- **Modify** `backend/servico.py` — `catalogo_para_out`.
- **Create** `backend/routers/catalogo.py` — CRUD + filtro por tipo.
- **Modify** `backend/main.py` — registrar router.
- **Create** `backend/seed_ata.py` — seed idempotente (dados do protótipo) + runner.
- **Modify** `entrypoint.sh` — rodar `python -m backend.seed_ata` após backfill.
- **Create** `alembic/versions/<rev>_catalogo_preco.py`.
- **Create** `tests/test_catalogo_api.py`, `tests/test_seed_ata.py`.
- **Create** `frontend/catalogo.html`; **Modify** `frontend/app.js` (NAV).

---

## Task 1: Modelo `CatalogoPreco`

**Files:** Modify `backend/models.py`

- [ ] **Step 1: Adicionar a classe** ao fim de `backend/models.py`:

```python
class CatalogoPreco(Base):
    __tablename__ = "catalogo_preco"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo_id: Mapped[int] = mapped_column(
        ForeignKey("tipo_instrumento.id"), index=True
    )
    fornecedor: Mapped[str | None] = mapped_column(String)
    preco: Mapped[float | None] = mapped_column(Numeric(12, 2))
    item_contrato_id: Mapped[int | None] = mapped_column(
        ForeignKey("item_contrato.id", ondelete="SET NULL"), index=True
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    observacoes: Mapped[str | None] = mapped_column(String)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    tipo: Mapped["TipoInstrumento | None"] = relationship()
    item_contrato: Mapped["ItemContrato | None"] = relationship()
```

- [ ] **Step 2: Verificar** — `source .venv/bin/activate && python -c "import backend.models; print('ok')"`. Expected `ok`.

- [ ] **Step 3: Commit**

```bash
git add backend/models.py
git commit -m "feat: modelo CatalogoPreco"
```

---

## Task 2: Schemas

**Files:** Modify `backend/schemas.py`

- [ ] **Step 1: Adicionar** ao fim de `backend/schemas.py`:

```python
class CatalogoPrecoIn(BaseModel):
    tipo_id: int
    fornecedor: str | None = None
    preco: float | None = None
    item_contrato_id: int | None = None
    ativo: bool = True
    observacoes: str | None = None


class CatalogoPrecoOut(BaseModel):
    id: int
    tipo_id: int
    fornecedor: str | None
    preco: float | None
    item_contrato_id: int | None
    ativo: bool
    observacoes: str | None
    # derivados
    tipo_nome: str | None
    item_numero: str | None
    contrato_id: int | None
    contrato_numero: str | None


class ListaCatalogo(BaseModel):
    total: int
    itens: list[CatalogoPrecoOut]
```

- [ ] **Step 2: Verificar** — `python -c "import backend.schemas; print('ok')"`. Expected `ok`.

- [ ] **Step 3: Commit**

```bash
git add backend/schemas.py
git commit -m "feat: schemas de catalogo_preco"
```

---

## Task 3: Serviço — `catalogo_para_out`

**Files:** Modify `backend/servico.py`

- [ ] **Step 1: Atualizar imports** — em `backend/servico.py`, adicionar `CatalogoPreco` ao import de models e `CatalogoPrecoOut` ao import de schemas (mesclar com as linhas existentes).

- [ ] **Step 2: Adicionar** ao fim de `backend/servico.py`:

```python
def catalogo_para_out(cat: CatalogoPreco) -> CatalogoPrecoOut:
    item = cat.item_contrato
    contrato = item.contrato if item is not None else None
    return CatalogoPrecoOut(
        id=cat.id,
        tipo_id=cat.tipo_id,
        fornecedor=cat.fornecedor,
        preco=float(cat.preco) if cat.preco is not None else None,
        item_contrato_id=cat.item_contrato_id,
        ativo=cat.ativo,
        observacoes=cat.observacoes,
        tipo_nome=cat.tipo.nome if cat.tipo is not None else None,
        item_numero=item.numero if item is not None else None,
        contrato_id=contrato.id if contrato is not None else None,
        contrato_numero=contrato.numero if contrato is not None else None,
    )
```

> Nota: `ItemContrato` não tem hoje uma relationship `contrato`. Adicione-a em `backend/models.py`
> na classe `ItemContrato` (junto aos outros campos):
> `contrato: Mapped["Contrato | None"] = relationship()`
> (faça isso neste task; é necessário para `item.contrato` acima. Verifique se já não existe.)

- [ ] **Step 3: Verificar** — `python -c "import backend.servico; print('ok')"`. Expected `ok`.

- [ ] **Step 4: Commit**

```bash
git add backend/servico.py backend/models.py
git commit -m "feat: catalogo_para_out + relationship ItemContrato.contrato"
```

---

## Task 4: Router de catálogo

**Files:** Create `backend/routers/catalogo.py`; Modify `backend/main.py`; Test `tests/test_catalogo_api.py`

- [ ] **Step 1: Escrever os testes** — criar `tests/test_catalogo_api.py`:

```python
def _tipo_id(client):
    return client.get("/api/v1/dominios").json()["tipos"][0]["id"]


def _cria_contrato_item(client):
    c = client.post("/api/v1/contratos", json={"numero": "ATA X", "tipo": "ATA"}).json()
    client.post(f"/api/v1/contratos/{c['id']}/itens",
                json={"numero": "14", "descricao": "Cal multímetro",
                      "quantidade": 10, "valor_unitario": 50.0, "usado": 0})
    c = client.get(f"/api/v1/contratos/{c['id']}").json()
    return c["id"], c["numero"], c["itens"][0]["id"], c["itens"][0]["numero"]


def test_cria_e_lista_catalogo(client):
    tid = _tipo_id(client)
    r = client.post("/api/v1/catalogo", json={"tipo_id": tid, "fornecedor": "MQT", "preco": 165.0})
    assert r.status_code == 201
    body = client.get("/api/v1/catalogo").json()
    assert body["total"] == 1
    assert body["itens"][0]["tipo_nome"] is not None
    assert body["itens"][0]["preco"] == 165.0


def test_filtro_por_tipo(client):
    tipos = client.get("/api/v1/dominios").json()["tipos"]
    a, b = tipos[0]["id"], tipos[1]["id"]
    client.post("/api/v1/catalogo", json={"tipo_id": a, "preco": 10.0})
    client.post("/api/v1/catalogo", json={"tipo_id": b, "preco": 20.0})
    r = client.get("/api/v1/catalogo", params={"tipo_id": a})
    assert r.json()["total"] == 1
    assert r.json()["itens"][0]["tipo_id"] == a


def test_vinculo_item_popula_derivados(client):
    tid = _tipo_id(client)
    cid, cnum, item_id, item_num = _cria_contrato_item(client)
    r = client.post("/api/v1/catalogo", json={
        "tipo_id": tid, "fornecedor": "MQT", "preco": 165.0, "item_contrato_id": item_id})
    assert r.status_code == 201
    body = r.json()
    assert body["item_contrato_id"] == item_id
    assert body["item_numero"] == item_num
    assert body["contrato_id"] == cid
    assert body["contrato_numero"] == cnum


def test_tipo_inexistente_404(client):
    r = client.post("/api/v1/catalogo", json={"tipo_id": 99999, "preco": 1.0})
    assert r.status_code == 404


def test_item_contrato_inexistente_404(client):
    tid = _tipo_id(client)
    r = client.post("/api/v1/catalogo", json={"tipo_id": tid, "item_contrato_id": 99999})
    assert r.status_code == 404


def test_put_e_delete(client):
    tid = _tipo_id(client)
    cat = client.post("/api/v1/catalogo", json={"tipo_id": tid, "preco": 10.0}).json()
    r = client.put(f"/api/v1/catalogo/{cat['id']}", json={"tipo_id": tid, "preco": 99.0})
    assert r.status_code == 200 and r.json()["preco"] == 99.0
    assert client.delete(f"/api/v1/catalogo/{cat['id']}").status_code == 204
    assert client.get(f"/api/v1/catalogo/{cat['id']}").status_code == 404
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_catalogo_api.py -q`
Expected: FAIL (rotas não existem).

- [ ] **Step 3: Criar o router** `backend/routers/catalogo.py`:

```python
"""Endpoints do catálogo de preços de calibração."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import CatalogoPreco, TipoInstrumento, ItemContrato
from backend.servico import catalogo_para_out
from backend.schemas import CatalogoPrecoIn, CatalogoPrecoOut, ListaCatalogo

router = APIRouter(prefix="/api/v1", tags=["catalogo"])


def _get_cat(db: Session, cat_id: int) -> CatalogoPreco:
    cat = db.get(CatalogoPreco, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Item de catálogo não encontrado")
    return cat


def _validar_fks(db: Session, dados: CatalogoPrecoIn) -> None:
    if not db.get(TipoInstrumento, dados.tipo_id):
        raise HTTPException(status_code=404, detail="Tipo de instrumento não encontrado")
    if dados.item_contrato_id is not None and not db.get(ItemContrato, dados.item_contrato_id):
        raise HTTPException(status_code=404, detail="Item de contrato não encontrado")


def _aplicar(cat: CatalogoPreco, dados: CatalogoPrecoIn) -> None:
    for campo, valor in dados.model_dump().items():
        setattr(cat, campo, valor)


@router.get("/catalogo", response_model=ListaCatalogo)
def listar(db: Session = Depends(get_db), tipo_id: int | None = Query(None)):
    q = db.query(CatalogoPreco)
    if tipo_id is not None:
        q = q.filter(CatalogoPreco.tipo_id == tipo_id)
    cats = q.order_by(CatalogoPreco.id).all()
    itens = [catalogo_para_out(c) for c in cats]
    return ListaCatalogo(total=len(itens), itens=itens)


@router.get("/catalogo/{cat_id}", response_model=CatalogoPrecoOut)
def obter(cat_id: int, db: Session = Depends(get_db)):
    return catalogo_para_out(_get_cat(db, cat_id))


@router.post("/catalogo", response_model=CatalogoPrecoOut, status_code=201)
def criar(dados: CatalogoPrecoIn, db: Session = Depends(get_db)):
    _validar_fks(db, dados)
    cat = CatalogoPreco()
    _aplicar(cat, dados)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return catalogo_para_out(cat)


@router.put("/catalogo/{cat_id}", response_model=CatalogoPrecoOut)
def editar(cat_id: int, dados: CatalogoPrecoIn, db: Session = Depends(get_db)):
    cat = _get_cat(db, cat_id)
    _validar_fks(db, dados)
    _aplicar(cat, dados)
    db.commit()
    db.refresh(cat)
    return catalogo_para_out(cat)


@router.delete("/catalogo/{cat_id}", status_code=204)
def remover(cat_id: int, db: Session = Depends(get_db)):
    db.delete(_get_cat(db, cat_id))
    db.commit()
```

- [ ] **Step 4: Registrar no app** — em `backend/main.py`, adicionar `catalogo` ao import `from backend.routers import ...` e `app.include_router(catalogo.router)`.

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_catalogo_api.py -q`
Expected: PASS (6).

- [ ] **Step 6: Commit**

```bash
git add backend/routers/catalogo.py backend/main.py tests/test_catalogo_api.py
git commit -m "feat: router de catalogo de precos (CRUD + filtro por tipo)"
```

---

## Task 5: Seed dos dados reais (ATA 129/2025)

**Files:** Create `backend/seed_ata.py`; Modify `entrypoint.sh`; Test `tests/test_seed_ata.py`

> Os dados de origem estão em `.reference_readonly/calibracao_erp.html` (arquivo do próprio
> projeto): `CATALOG_DEFAULT` (linhas 1699–1908, 28 tipos), `ATA_ITEMS_SEED` (1909–2063, 22
> itens `{item, desc, quant, valor, usado, saldo}`), `ATA_INFO` (2064–2073). LEIA esses ranges
> e transcreva os dados para constantes Python no topo de `backend/seed_ata.py`
> (`_ATA_ITENS = [...]`, `_CATALOG = {...}`, `_ATA = {...}`). Transcreva fielmente os números.

- [ ] **Step 1: Escrever o teste** — criar `tests/test_seed_ata.py`:

```python
from backend.db import Base, get_db
from backend import models
from backend.dominios import seed_dominios
from backend.seed_ata import seed_ata


def _db(client):
    # reaproveita a sessão de teste via dependency override do conftest
    gen = __import__("backend.main", fromlist=["app"]).app.dependency_overrides[get_db]()
    return next(gen)


def test_seed_idempotente_e_matching(client):
    db = _db(client)
    seed_dominios(db)  # garante tipos do domínio (Multímetro, Paquímetro, etc.)
    r1 = seed_ata(db)
    # contrato + 22 itens criados
    assert r1["contrato"] == 1
    assert r1["itens"] == 22
    # ao menos os tipos óbvios casaram (Multímetro, Paquímetro, Torquímetro, ...)
    assert r1["catalogo"] >= 5
    contrato = db.query(models.Contrato).filter_by(numero="ATA MQT 129/2025").first()
    assert contrato is not None
    assert db.query(models.ItemContrato).filter_by(contrato_id=contrato.id).count() == 22
    n_cat = db.query(models.CatalogoPreco).count()
    assert n_cat == r1["catalogo"]
    # alguma entrada de catálogo está vinculada a um item de contrato
    assert db.query(models.CatalogoPreco).filter(
        models.CatalogoPreco.item_contrato_id.isnot(None)).count() >= 1

    # idempotência: rodar de novo não duplica
    r2 = seed_ata(db)
    assert r2["contrato"] == 0
    assert r2["itens"] == 0
    assert r2["catalogo"] == 0
    assert db.query(models.ItemContrato).filter_by(contrato_id=contrato.id).count() == 22
    assert db.query(models.CatalogoPreco).count() == n_cat
    db.close()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_seed_ata.py -q`
Expected: FAIL (ImportError: seed_ata).

- [ ] **Step 3: Implementar** — criar `backend/seed_ata.py`. Estrutura (preencha `_ATA_ITENS`/`_CATALOG`/`_ATA` lendo o arquivo de referência conforme a nota acima):

```python
"""Seed idempotente da ATA 129/2025 (contrato + itens + catálogo). Roda no startup."""
from __future__ import annotations
import unicodedata
from backend.db import SessionLocal
from backend.models import (
    Contrato, ItemContrato, CatalogoPreco, TipoInstrumento, ContratoTipo,
)

_ATA = {"numero": "ATA MQT 129/2025", "fornecedor": "MQT Serviços Metrológicos Ltda",
        "teto": 112114.00}

# Transcrito de .reference_readonly/calibracao_erp.html (ATA_ITEMS_SEED, linhas 1909-2063):
_ATA_ITENS = [
    {"item": 1, "desc": "CALIBRAÇÃO DE ALICATE AMPERÍMETRO", "quant": 2, "valor": 240.0, "usado": 0},
    # ... transcreva os 22 itens (item, desc, quant, valor, usado) ...
]

# Transcrito de CATALOG_DEFAULT (linhas 1699-1908): { "TIPO": [ {forn, preco, item, tipo}, ... ] }
_CATALOG = {
    "TORQUÍMETRO": [{"forn": "MQT Serviços", "preco": 70.0, "item": "35", "tipo": "ata"}],
    # ... transcreva os 28 tipos com suas opções (use "item": None quando for "—") ...
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().replace(" ", "")


def _match_tipo(db, chave: str, tipos: list[TipoInstrumento]) -> TipoInstrumento | None:
    """Acha o TipoInstrumento cujo nome normalizado esteja CONTIDO na chave do catálogo.
    Em empate, o nome de domínio mais longo vence."""
    alvo = _norm(chave)
    candidatos = [t for t in tipos if _norm(t.nome) and _norm(t.nome) in alvo]
    if not candidatos:
        return None
    return max(candidatos, key=lambda t: len(_norm(t.nome)))


def seed_ata(db) -> dict:
    contagem = {"contrato": 0, "itens": 0, "catalogo": 0, "tipos_nao_casados": []}

    contrato = db.query(Contrato).filter_by(numero=_ATA["numero"]).first()
    if contrato is None:
        contrato = Contrato(numero=_ATA["numero"], tipo=ContratoTipo.ATA,
                            fornecedor=_ATA["fornecedor"], valor_total=_ATA["teto"], ativo=True)
        db.add(contrato)
        db.flush()
        contagem["contrato"] = 1

    itens_por_numero = {i.numero: i for i in
                        db.query(ItemContrato).filter_by(contrato_id=contrato.id).all()}
    for it in _ATA_ITENS:
        num = str(it["item"])
        if num in itens_por_numero:
            continue
        novo = ItemContrato(contrato_id=contrato.id, numero=num, descricao=it["desc"],
                            quantidade=it["quant"], valor_unitario=it["valor"], usado=it["usado"])
        db.add(novo)
        db.flush()
        itens_por_numero[num] = novo
        contagem["itens"] += 1

    tipos = db.query(TipoInstrumento).all()
    existentes = {(c.tipo_id, c.fornecedor, c.item_contrato_id)
                  for c in db.query(CatalogoPreco).all()}
    nao_casados = set()
    for chave, opcoes in _CATALOG.items():
        tipo = _match_tipo(db, chave, tipos)
        if tipo is None:
            nao_casados.add(chave)
            continue
        for o in opcoes:
            item_id = None
            if o.get("item"):
                item = itens_por_numero.get(str(o["item"]))
                item_id = item.id if item else None
            chave_unica = (tipo.id, o.get("forn"), item_id)
            if chave_unica in existentes:
                continue
            db.add(CatalogoPreco(tipo_id=tipo.id, fornecedor=o.get("forn"),
                                 preco=o.get("preco"), item_contrato_id=item_id, ativo=True))
            existentes.add(chave_unica)
            contagem["catalogo"] += 1

    contagem["tipos_nao_casados"] = sorted(nao_casados)
    db.commit()
    return contagem


def main() -> None:
    db = SessionLocal()
    try:
        r = seed_ata(db)
        print(f"seed_ata: contrato={r['contrato']} itens={r['itens']} "
              f"catalogo={r['catalogo']} nao_casados={len(r['tipos_nao_casados'])}")
        if r["tipos_nao_casados"]:
            print("  tipos sem match no domínio:", ", ".join(r["tipos_nao_casados"]))
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_seed_ata.py -q`
Expected: PASS. (Se `r1["catalogo"] >= 5` falhar, confira a transcrição de `_CATALOG` e a
normalização — os tipos óbvios "MULTÍMETRO/PAQUÍMETRO/TORQUÍMETRO/OSCILOSCÓPIO/FONTE DC/
GERADOR DE FUNÇÕES/TERMÔMETRO/DINAMÔMETRO" devem casar com o domínio.)

- [ ] **Step 5: Adicionar ao entrypoint** — em `entrypoint.sh`, após `python -m backend.backfill`:

```sh
python -m backend.seed_ata
```

- [ ] **Step 6: Commit**

```bash
git add backend/seed_ata.py entrypoint.sh tests/test_seed_ata.py
git commit -m "feat: seed idempotente da ATA 129/2025 (contrato + itens + catalogo)"
```

---

## Task 6: Migração Alembic

**Files:** Create `alembic/versions/<rev>_catalogo_preco.py`

- [ ] **Step 1: Gerar**

Run: `SISCALIB_DB_URL="sqlite:////tmp/cat.db" alembic revision -m "catalogo_preco"`
Confirme `down_revision = '2dae72dfab3d'`.

- [ ] **Step 2: Escrever `upgrade()`/`downgrade()`**:

```python
def upgrade() -> None:
    op.create_table(
        'catalogo_preco',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tipo_id', sa.Integer(), nullable=False),
        sa.Column('fornecedor', sa.String(), nullable=True),
        sa.Column('preco', sa.Numeric(12, 2), nullable=True),
        sa.Column('item_contrato_id', sa.Integer(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('observacoes', sa.String(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['tipo_id'], ['tipo_instrumento.id']),
        sa.ForeignKeyConstraint(['item_contrato_id'], ['item_contrato.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_catalogo_preco_tipo_id', 'catalogo_preco', ['tipo_id'])
    op.create_index('ix_catalogo_preco_item_contrato_id', 'catalogo_preco', ['item_contrato_id'])


def downgrade() -> None:
    op.drop_index('ix_catalogo_preco_item_contrato_id', table_name='catalogo_preco')
    op.drop_index('ix_catalogo_preco_tipo_id', table_name='catalogo_preco')
    op.drop_table('catalogo_preco')
```

- [ ] **Step 3: Aplicar em banco limpo**

Run: `rm -f /tmp/cat.db && SISCALIB_DB_URL="sqlite:////tmp/cat.db" alembic upgrade head`
Expected: aplica até `catalogo_preco` sem erro. Depois `rm -f /tmp/cat.db`.

- [ ] **Step 4: Suíte completa**

Run: `python -m pytest -q`
Expected: PASS (132 + ~8 novos).

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/
git commit -m "feat: migracao da tabela catalogo_preco"
```

---

## Task 7: Frontend — `catalogo.html` + NAV

**Files:** Create `frontend/catalogo.html`; Modify `frontend/app.js`

> UI: verificação manual/browser. Antes de editar, leia `frontend/app.js` (`SDK`, `montarShell`,
> `NAV`, `abrirModal`, `esc`, `badgeStatus`), `frontend/contratos.html` (padrão lista+modal +
> `money()`) e `frontend/siscalib.css`.

- [ ] **Step 1: Item NAV** — em `frontend/app.js`, no array `NAV`, após a entrada de Contratos:

```javascript
  ["catalogo.html", "tags", "Catálogo"],
```

- [ ] **Step 2: Criar `frontend/catalogo.html`** espelhando `contratos.html`:
  - `<h1>Catálogo de Preços</h1>` + filtro por tipo (`<select>` carregado de `GET /dominios` `.tipos`, opção "Todos") + botão "Novo preço".
  - Tabela de `GET /catalogo` (com `?tipo_id=` quando filtrado): Tipo (`tipo_nome`) · Fornecedor · Preço (`money(preco)`) · Contrato/Item (`contrato_numero ? contrato_numero + ' · item ' + item_numero : '—'`) · Ativo (Sim/Não) · Ações (Editar, Excluir).
  - "Novo"/"Editar" → modal (`abrirModal`): tipo_id (select de `/dominios` tipos, obrigatório), fornecedor, preco (number step=any), item_contrato_id (select OPCIONAL: opção vazia "— sem vínculo —" + opções achatando os itens de `GET /contratos` no formato `"{c.numero} · item {it.numero} — {it.descricao}"`, value = it.id), ativo (checkbox, default checked), observacoes (textarea). Editar pré-preenche tudo (PUT é replace). Salvar → POST/PUT → recarrega.
  - "Excluir" → confirm → `SDK.del('/catalogo/'+id)` → recarrega.
  - `money()` helper local; `esc()` em todo valor de usuário.

- [ ] **Step 3: Verificação (browser)**

Run: `source .venv/bin/activate && uvicorn backend.main:app --port 8041 &` (aguarde ~2s; rode `python -m backend.seed_ata` antes para ter dados, ou crie manualmente). `node --check frontend/app.js` → ok. `curl -s -o /dev/null -w "%{http_code}" localhost:8041/catalogo.html` → 200.
- Se houver Playwright MCP: abrir catalogo.html → ver a lista (com os preços semeados se rodou o seed) → filtrar por tipo → "Novo preço" criar uma entrada com vínculo a um item de contrato e confirmar que a coluna Contrato/Item mostra "ATA MQT 129/2025 · item N" → editar → excluir. Console só favicon 404. Kill server + limpar artefatos.

- [ ] **Step 4: Commit**

```bash
git add frontend/catalogo.html frontend/app.js
git commit -m "feat: pagina de catalogo de precos + item NAV"
```

---

## Task 8: PRD + verificação final

**Files:** Modify `PRD-SisCalib.md`

- [ ] **Step 1: Atualizar PRD** — no §0 (tabela de status) adicionar linha "Catálogo de Preços (6.14/6.15, base de custos) ✅ Entregue" com nota (tabela `catalogo_preco`, preço por tipo × fornecedor com vínculo opcional a item de contrato; seed da ATA 129/2025). No §6.14, marcar `[x]` o que se aplica (estimativa de custo baseada em contratos — base criada).

- [ ] **Step 2: Suíte + import**

Run: `python -m pytest -q` → todos passam. `python -c "import backend.main"` → ok.

- [ ] **Step 3: Commit**

```bash
git add PRD-SisCalib.md
git commit -m "docs: marca Catalogo de Precos no PRD (base de custos 6.14/6.15)"
```

---

## Verificação final (antes do merge)

- [ ] `python -m pytest -q` → todos passam (132 + ~8 novos).
- [ ] `python -c "import backend.main"` → app sobe.
- [ ] Migração aplica limpa em banco novo.
- [ ] `python -m backend.seed_ata` roda idempotente (2× → segunda não cria nada) e loga os tipos não-casados.
- [ ] Smoke manual: CRUD catálogo, filtro por tipo, vínculo a item de contrato, dados semeados visíveis.
- [ ] Usar `superpowers:finishing-a-development-branch` para `feat/catalogo-precos`.
