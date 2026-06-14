# Registro de Calibrações — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar histórico de calibrações por instrumento (entidade `calibracao`) com laboratório em texto livre, upload de certificado PDF, resultado, e recálculo automático de validade/status do instrumento — atendendo PRD §6.2.

**Architecture:** Nova tabela `calibracao` (1 instrumento → N). Os campos `data_ultima_calibracao`/`data_validade`/`status_operacional` do instrumento passam a ser **derivados** da calibração mais recente. Motor puro novo em `backend/calibracao.py` (`adicionar_meses`, `derivar_de_calibracoes`); aplicação ao DB em `backend/servico.py`. Router `backend/routers/calibracoes.py`. Backfill dos dados importados roda no startup (módulo `backend/backfill.py`, padrão `backend/dominios.py`). UI: seção na ficha (modal) + página `calibracao.html`, ambas reusando funções compartilhadas em `app.js`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, SQLite, Pydantic v2, pytest, HTML/JS vanilla.

---

## File Structure

- **Modify** `backend/models.py` — enum `Resultado` + classe `Calibracao` + relationship em `Instrumento`.
- **Modify** `backend/calibracao.py` — helpers puros `adicionar_meses`, `derivar_de_calibracoes`, dataclass `DadosDerivados`.
- **Modify** `backend/schemas.py` — `CalibracaoIn`, `CalibracaoOut`, `ListaCalibracoes`, `RegistroCalibracaoOut`.
- **Modify** `backend/servico.py` — `calibracao_para_out`, `aplicar_derivados`, `backfill_calibracoes_origem`.
- **Create** `backend/routers/calibracoes.py` — endpoints REST.
- **Modify** `backend/main.py` — registrar o router.
- **Create** `backend/backfill.py` — runner de startup (chama `backfill_calibracoes_origem`).
- **Modify** `entrypoint.sh` — rodar `python -m backend.backfill` após dominios.
- **Create** `alembic/versions/<rev>_calibracao.py` — `create_table('calibracao')`.
- **Create** `tests/test_calibracao.py` adições (motor puro) e `tests/test_calibracoes_api.py` (API + backfill).
- **Modify** `frontend/app.js` — `renderHistoricoCalibracoes`, `renderFormCalibracao`, hook na ficha, item NAV.
- **Create** `frontend/calibracao.html` — página dedicada.

---

## Task 1: Modelo `Calibracao` + enum `Resultado`

**Files:**
- Modify: `backend/models.py`

- [ ] **Step 1: Adicionar o enum `Resultado`** logo após `class StatusOperacional` em `backend/models.py`:

```python
class Resultado(str, enum.Enum):
    APROVADO = "APROVADO"
    APROVADO_COM_RESTRICOES = "APROVADO_COM_RESTRICOES"
    REPROVADO = "REPROVADO"
```

- [ ] **Step 2: Adicionar a classe `Calibracao`** no fim de `backend/models.py` (após a classe `Instrumento`):

```python
class Calibracao(Base):
    __tablename__ = "calibracao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrumento_id: Mapped[int] = mapped_column(
        ForeignKey("instrumento.id", ondelete="CASCADE"), index=True
    )
    data_calibracao: Mapped[Date] = mapped_column(Date)
    data_validade: Mapped[Date | None] = mapped_column(Date)
    ciclo_meses: Mapped[int] = mapped_column(Integer, default=12)
    resultado: Mapped[Resultado] = mapped_column(Enum(Resultado), default=Resultado.APROVADO)
    laboratorio: Mapped[str | None] = mapped_column(String)
    laboratorio_cnpj: Mapped[str | None] = mapped_column(String)
    acreditacao_rbc: Mapped[bool] = mapped_column(Boolean, default=False)
    numero_cgcre: Mapped[str | None] = mapped_column(String)
    numero_certificado: Mapped[str | None] = mapped_column(String)
    custo: Mapped[float | None] = mapped_column(Numeric(12, 2))
    responsavel: Mapped[str | None] = mapped_column(String)
    certificado_path: Mapped[str | None] = mapped_column(String)
    origem: Mapped[str] = mapped_column(String, default="MANUAL")
    observacoes: Mapped[str | None] = mapped_column(String)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 3: Adicionar a relationship em `Instrumento`** (junto às outras relationships, no fim da classe):

```python
    calibracoes: Mapped[list["Calibracao"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
```

- [ ] **Step 4: Verificar que importa** — `python -c "import backend.models"`. Expected: sem erro. (`Integer, String, Date, DateTime, Numeric, Enum, ForeignKey, Boolean, func` já estão importados no topo do arquivo.)

- [ ] **Step 5: Commit**

```bash
git add backend/models.py
git commit -m "feat: modelo Calibracao + enum Resultado"
```

---

## Task 2: Motor puro — `adicionar_meses` e `derivar_de_calibracoes`

**Files:**
- Modify: `backend/calibracao.py`
- Test: `tests/test_calibracao.py`

- [ ] **Step 1: Escrever os testes** — adicionar ao fim de `tests/test_calibracao.py`:

```python
from dataclasses import dataclass
from datetime import date
from backend.calibracao import adicionar_meses, derivar_de_calibracoes


@dataclass
class _Cal:
    id: int
    data_calibracao: date
    data_validade: date | None
    resultado: str


def test_adicionar_meses_simples():
    assert adicionar_meses(date(2026, 1, 15), 12) == date(2027, 1, 15)


def test_adicionar_meses_clamp_fim_de_mes():
    # 31/01 + 1 mês -> 28/02 (2026 não é bissexto)
    assert adicionar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_adicionar_meses_virada_de_ano():
    assert adicionar_meses(date(2026, 11, 30), 6) == date(2027, 5, 30)


def test_derivar_lista_vazia_nao_altera():
    d = derivar_de_calibracoes([])
    assert d.data_ultima_calibracao is None
    assert d.data_validade is None
    assert d.status_operacional is None


def test_derivar_um_registro_aprovado():
    cal = _Cal(1, date(2026, 1, 10), date(2027, 1, 10), "APROVADO")
    d = derivar_de_calibracoes([cal])
    assert d.data_ultima_calibracao == date(2026, 1, 10)
    assert d.data_validade == date(2027, 1, 10)
    assert d.status_operacional == "ATIVO"


def test_derivar_pega_a_mais_recente_por_data():
    velha = _Cal(1, date(2025, 1, 1), date(2026, 1, 1), "APROVADO")
    nova = _Cal(2, date(2026, 6, 1), date(2027, 6, 1), "APROVADO")
    d = derivar_de_calibracoes([velha, nova])
    assert d.data_validade == date(2027, 6, 1)


def test_derivar_desempate_por_id_quando_mesma_data():
    a = _Cal(1, date(2026, 6, 1), date(2027, 6, 1), "APROVADO")
    b = _Cal(2, date(2026, 6, 1), None, "REPROVADO")
    d = derivar_de_calibracoes([a, b])
    assert d.status_operacional == "REPROVADO"
    assert d.data_validade is None


def test_derivar_reprovado_status_e_validade_null():
    cal = _Cal(1, date(2026, 1, 10), None, "REPROVADO")
    d = derivar_de_calibracoes([cal])
    assert d.status_operacional == "REPROVADO"
    assert d.data_validade is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_calibracao.py -q`
Expected: FAIL com `ImportError: cannot import name 'adicionar_meses'`.

- [ ] **Step 3: Implementar** — adicionar ao fim de `backend/calibracao.py`:

```python
import calendar


def adicionar_meses(d: date, meses: int) -> date:
    """Soma meses a uma data, fazendo clamp do dia ao último dia do mês alvo."""
    total = d.month - 1 + meses
    ano = d.year + total // 12
    mes = total % 12 + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(d.day, ultimo_dia))


@dataclass(frozen=True)
class DadosDerivados:
    data_ultima_calibracao: date | None
    data_validade: date | None
    status_operacional: str | None  # "ATIVO" | "REPROVADO" | None (não alterar)


def derivar_de_calibracoes(calibracoes) -> DadosDerivados:
    """Deriva os campos do instrumento a partir da calibração mais recente.

    Aceita qualquer objeto com .id, .data_calibracao, .data_validade, .resultado.
    Lista vazia -> tudo None (instrumento não é alterado).
    `resultado` é comparado com a string "REPROVADO" (Resultado é str-enum).
    """
    if not calibracoes:
        return DadosDerivados(None, None, None)
    ultima = max(calibracoes, key=lambda c: (c.data_calibracao, c.id))
    status = "REPROVADO" if ultima.resultado == "REPROVADO" else "ATIVO"
    return DadosDerivados(ultima.data_calibracao, ultima.data_validade, status)
```

(`from dataclasses import dataclass` e `from datetime import date` já estão no topo de `backend/calibracao.py`.)

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_calibracao.py -q`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add backend/calibracao.py tests/test_calibracao.py
git commit -m "feat: motor puro adicionar_meses + derivar_de_calibracoes"
```

---

## Task 3: Schemas de calibração

**Files:**
- Modify: `backend/schemas.py`

- [ ] **Step 1: Adicionar os schemas** ao fim de `backend/schemas.py`:

```python
class CalibracaoIn(BaseModel):
    """Entrada de registro de calibração. validade/ciclo/status são derivados no servidor."""
    data_calibracao: date
    resultado: Literal["APROVADO", "APROVADO_COM_RESTRICOES", "REPROVADO"] = "APROVADO"
    laboratorio: str | None = None
    laboratorio_cnpj: str | None = None
    acreditacao_rbc: bool = False
    numero_cgcre: str | None = None
    numero_certificado: str | None = None
    custo: float | None = None
    responsavel: str | None = None
    observacoes: str | None = None


class CalibracaoOut(BaseModel):
    id: int
    instrumento_id: int
    data_calibracao: date
    data_validade: date | None
    ciclo_meses: int
    resultado: str
    laboratorio: str | None
    laboratorio_cnpj: str | None
    acreditacao_rbc: bool
    numero_cgcre: str | None
    numero_certificado: str | None
    custo: float | None
    responsavel: str | None
    certificado_path: str | None
    origem: str
    observacoes: str | None


class ListaCalibracoes(BaseModel):
    total: int
    itens: list[CalibracaoOut]


class RegistroCalibracaoOut(BaseModel):
    instrumento: InstrumentoOut
    calibracao: CalibracaoOut
```

(`date`, `Literal`, `BaseModel` já importados no topo.)

- [ ] **Step 2: Verificar import** — `python -c "import backend.schemas"`. Expected: sem erro.

- [ ] **Step 3: Commit**

```bash
git add backend/schemas.py
git commit -m "feat: schemas de calibracao"
```

---

## Task 4: Serviço — `calibracao_para_out` e `aplicar_derivados`

**Files:**
- Modify: `backend/servico.py`

- [ ] **Step 1: Adicionar imports** no topo de `backend/servico.py` (junto aos existentes):

```python
from sqlalchemy.orm import Session
from backend.calibracao import derivar_de_calibracoes
from backend.models import Instrumento, Calibracao, StatusOperacional, Resultado
from backend.schemas import InstrumentoOut, CalibracaoOut
```

(Substitua a linha `from backend.models import Instrumento` e `from backend.schemas import InstrumentoOut` existentes por estas — mantendo `calcular_status` e `calcular_igp` já importados.)

- [ ] **Step 2: Adicionar as funções** ao fim de `backend/servico.py`:

```python
def calibracao_para_out(cal: Calibracao) -> CalibracaoOut:
    return CalibracaoOut(
        id=cal.id,
        instrumento_id=cal.instrumento_id,
        data_calibracao=cal.data_calibracao,
        data_validade=cal.data_validade,
        ciclo_meses=cal.ciclo_meses,
        resultado=cal.resultado.value,
        laboratorio=cal.laboratorio,
        laboratorio_cnpj=cal.laboratorio_cnpj,
        acreditacao_rbc=cal.acreditacao_rbc,
        numero_cgcre=cal.numero_cgcre,
        numero_certificado=cal.numero_certificado,
        custo=float(cal.custo) if cal.custo is not None else None,
        responsavel=cal.responsavel,
        certificado_path=cal.certificado_path,
        origem=cal.origem,
        observacoes=cal.observacoes,
    )


def aplicar_derivados(inst: Instrumento, db: Session) -> None:
    """Recalcula data_ultima_calibracao/data_validade/status_operacional do instrumento
    a partir das suas calibrações e dá commit."""
    cals = db.query(Calibracao).filter(Calibracao.instrumento_id == inst.id).all()
    d = derivar_de_calibracoes(cals)
    if d.status_operacional is not None:
        inst.data_ultima_calibracao = d.data_ultima_calibracao
        inst.data_validade = d.data_validade
        inst.status_operacional = StatusOperacional(d.status_operacional)
    db.commit()
```

- [ ] **Step 3: Verificar import** — `python -c "import backend.servico"`. Expected: sem erro.

- [ ] **Step 4: Commit**

```bash
git add backend/servico.py
git commit -m "feat: servico calibracao_para_out + aplicar_derivados"
```

---

## Task 5: Router de calibrações (GET histórico + POST registrar)

**Files:**
- Create: `backend/routers/calibracoes.py`
- Modify: `backend/main.py`
- Test: `tests/test_calibracoes_api.py`

- [ ] **Step 1: Escrever os testes** — criar `tests/test_calibracoes_api.py`:

```python
from datetime import date


def _id_primeiro(client):
    return client.get("/api/v1/instrumentos").json()["itens"][0]["id"]


def test_post_calibracao_aprovada_recalcula_validade_e_status(client):
    iid = _id_primeiro(client)
    r = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "resultado": "APROVADO", "laboratorio": "RBC X",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["calibracao"]["data_validade"] == "2027-03-10"
    assert body["instrumento"]["data_validade"] == "2027-03-10"
    assert body["instrumento"]["status_operacional"] == "ATIVO"
    assert body["instrumento"]["data_ultima_calibracao"] == "2026-03-10"


def test_post_calibracao_reprovada_bloqueia(client):
    iid = _id_primeiro(client)
    r = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "resultado": "REPROVADO",
    })
    assert r.status_code == 201
    inst = r.json()["instrumento"]
    assert inst["status_operacional"] == "REPROVADO"
    assert inst["data_validade"] is None


def test_calibracao_mais_recente_prevalece(client):
    iid = _id_primeiro(client)
    client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2025-01-01", "resultado": "APROVADO"})
    client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-01-01", "resultado": "APROVADO"})
    inst = client.get(f"/api/v1/instrumentos/{iid}").json()
    assert inst["data_validade"] == "2027-01-01"


def test_get_historico_ordenado_desc(client):
    iid = _id_primeiro(client)
    client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2024-01-01", "resultado": "APROVADO"})
    client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-01-01", "resultado": "APROVADO"})
    r = client.get(f"/api/v1/instrumentos/{iid}/calibracoes")
    assert r.status_code == 200
    itens = r.json()["itens"]
    assert itens[0]["data_calibracao"] == "2026-01-01"
    assert itens[1]["data_calibracao"] == "2024-01-01"


def test_post_calibracao_instrumento_inexistente_404(client):
    r = client.post("/api/v1/instrumentos/99999/calibracoes", json={
        "data_calibracao": "2026-03-10", "resultado": "APROVADO"})
    assert r.status_code == 404
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_calibracoes_api.py -q`
Expected: FAIL (404 em todas — rota não existe).

- [ ] **Step 3: Criar o router** `backend/routers/calibracoes.py`:

```python
"""Endpoints de registro/histórico de calibrações."""
from __future__ import annotations
from datetime import date
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Instrumento, Calibracao, Resultado
from backend.servico import instrumento_para_out, calibracao_para_out, aplicar_derivados
from backend.calibracao import adicionar_meses
from backend.schemas import CalibracaoIn, ListaCalibracoes, RegistroCalibracaoOut, CalibracaoOut

router = APIRouter(prefix="/api/v1", tags=["calibracoes"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"


def _get_inst(db: Session, inst_id: int) -> Instrumento:
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    return inst


@router.get("/instrumentos/{inst_id}/calibracoes", response_model=ListaCalibracoes)
def listar(inst_id: int, db: Session = Depends(get_db)):
    _get_inst(db, inst_id)
    cals = (db.query(Calibracao)
            .filter(Calibracao.instrumento_id == inst_id)
            .order_by(Calibracao.data_calibracao.desc(), Calibracao.id.desc())
            .all())
    return ListaCalibracoes(total=len(cals), itens=[calibracao_para_out(c) for c in cals])


@router.post("/instrumentos/{inst_id}/calibracoes",
             response_model=RegistroCalibracaoOut, status_code=201)
def registrar(inst_id: int, dados: CalibracaoIn, db: Session = Depends(get_db)):
    inst = _get_inst(db, inst_id)
    ciclo = inst.ciclo_meses or 12
    if dados.resultado == "REPROVADO":
        validade = None
    else:
        validade = adicionar_meses(dados.data_calibracao, ciclo)
    cal = Calibracao(
        instrumento_id=inst_id,
        data_calibracao=dados.data_calibracao,
        data_validade=validade,
        ciclo_meses=ciclo,
        resultado=Resultado(dados.resultado),
        laboratorio=dados.laboratorio,
        laboratorio_cnpj=dados.laboratorio_cnpj,
        acreditacao_rbc=dados.acreditacao_rbc,
        numero_cgcre=dados.numero_cgcre,
        numero_certificado=dados.numero_certificado,
        custo=dados.custo,
        responsavel=dados.responsavel,
        observacoes=dados.observacoes,
        origem="MANUAL",
    )
    db.add(cal)
    db.commit()
    db.refresh(cal)
    aplicar_derivados(inst, db)
    db.refresh(inst)
    return RegistroCalibracaoOut(
        instrumento=instrumento_para_out(inst, date.today()),
        calibracao=calibracao_para_out(cal),
    )
```

- [ ] **Step 4: Registrar no app** — em `backend/main.py`, atualizar o import e o include:

```python
from backend.routers import instrumentos, importacao, dashboard, dominios, exportacao, calibracoes
```
e adicionar após `app.include_router(exportacao.router)`:
```python
app.include_router(calibracoes.router)
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_calibracoes_api.py -q`
Expected: PASS (5).

- [ ] **Step 6: Commit**

```bash
git add backend/routers/calibracoes.py backend/main.py tests/test_calibracoes_api.py
git commit -m "feat: router de calibracoes (GET historico + POST registrar)"
```

---

## Task 6: Upload de certificado PDF

**Files:**
- Modify: `backend/routers/calibracoes.py`
- Test: `tests/test_calibracoes_api.py`

- [ ] **Step 1: Adicionar testes** ao fim de `tests/test_calibracoes_api.py`:

```python
def _cria_cal(client):
    iid = _id_primeiro(client)
    cal = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-03-10", "resultado": "APROVADO"}).json()["calibracao"]
    return iid, cal["id"]


def test_upload_certificado_pdf(client):
    iid, cid = _cria_cal(client)
    r = client.post(
        f"/api/v1/instrumentos/{iid}/calibracoes/{cid}/certificado",
        files={"arquivo": ("cert.pdf", b"%PDF-1.4 x", "application/pdf")},
    )
    assert r.status_code == 200
    assert r.json()["certificado_path"].endswith(f"cert_{cid}.pdf")


def test_upload_certificado_rejeita_nao_pdf(client):
    iid, cid = _cria_cal(client)
    r = client.post(
        f"/api/v1/instrumentos/{iid}/calibracoes/{cid}/certificado",
        files={"arquivo": ("x.png", b"\x89PNG", "image/png")},
    )
    assert r.status_code == 415


def test_upload_certificado_calibracao_inexistente_404(client):
    iid = _id_primeiro(client)
    r = client.post(
        f"/api/v1/instrumentos/{iid}/calibracoes/99999/certificado",
        files={"arquivo": ("cert.pdf", b"%PDF", "application/pdf")},
    )
    assert r.status_code == 404
```

- [ ] **Step 2: Adicionar a fixture de UPLOAD_DIR ao conftest** — em `tests/conftest.py`, logo após o `monkeypatch.setattr(_instr_mod, "UPLOAD_DIR", ...)` existente, adicionar:

```python
    import backend.routers.calibracoes as _cal_mod
    monkeypatch.setattr(_cal_mod, "UPLOAD_DIR", tmp_path / "uploads")
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `python -m pytest tests/test_calibracoes_api.py -k certificado -q`
Expected: FAIL (404/405 — rota não existe).

- [ ] **Step 4: Implementar o endpoint** — adicionar ao fim de `backend/routers/calibracoes.py`:

```python
@router.post("/instrumentos/{inst_id}/calibracoes/{cal_id}/certificado",
             response_model=CalibracaoOut)
async def upload_certificado(inst_id: int, cal_id: int,
                             arquivo: UploadFile = File(...),
                             db: Session = Depends(get_db)):
    cal = db.get(Calibracao, cal_id)
    if not cal or cal.instrumento_id != inst_id:
        raise HTTPException(status_code=404, detail="Calibração não encontrada")
    if (arquivo.content_type or "") != "application/pdf":
        raise HTTPException(status_code=415, detail="Envie um PDF")
    destino_dir = UPLOAD_DIR / str(inst_id)
    destino_dir.mkdir(parents=True, exist_ok=True)
    nome = f"cert_{cal_id}.pdf"
    (destino_dir / nome).write_bytes(await arquivo.read())
    cal.certificado_path = f"uploads/{inst_id}/{nome}"
    db.commit()
    db.refresh(cal)
    return calibracao_para_out(cal)
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_calibracoes_api.py -q`
Expected: PASS (todos).

- [ ] **Step 6: Commit**

```bash
git add backend/routers/calibracoes.py tests/test_calibracoes_api.py tests/conftest.py
git commit -m "feat: upload de certificado PDF da calibracao"
```

---

## Task 7: DELETE de calibração (recalcula derivados)

**Files:**
- Modify: `backend/routers/calibracoes.py`
- Test: `tests/test_calibracoes_api.py`

- [ ] **Step 1: Adicionar teste** ao fim de `tests/test_calibracoes_api.py`:

```python
def test_delete_calibracao_recalcula(client):
    iid = _id_primeiro(client)
    client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2025-01-01", "resultado": "APROVADO"})
    nova = client.post(f"/api/v1/instrumentos/{iid}/calibracoes", json={
        "data_calibracao": "2026-01-01", "resultado": "APROVADO"}).json()["calibracao"]
    # apaga a mais recente -> validade volta a refletir a de 2025
    r = client.delete(f"/api/v1/instrumentos/{iid}/calibracoes/{nova['id']}")
    assert r.status_code == 200
    assert r.json()["data_validade"] == "2026-01-01"


def test_delete_calibracao_inexistente_404(client):
    iid = _id_primeiro(client)
    r = client.delete(f"/api/v1/instrumentos/{iid}/calibracoes/99999")
    assert r.status_code == 404
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_calibracoes_api.py -k delete -q`
Expected: FAIL (405/404 — rota não existe).

- [ ] **Step 3: Implementar** — adicionar ao fim de `backend/routers/calibracoes.py`:

```python
from backend.schemas import InstrumentoOut  # adicionar ao bloco de imports do topo


@router.delete("/instrumentos/{inst_id}/calibracoes/{cal_id}", response_model=InstrumentoOut)
def remover(inst_id: int, cal_id: int, db: Session = Depends(get_db)):
    inst = _get_inst(db, inst_id)
    cal = db.get(Calibracao, cal_id)
    if not cal or cal.instrumento_id != inst_id:
        raise HTTPException(status_code=404, detail="Calibração não encontrada")
    db.delete(cal)
    db.commit()
    aplicar_derivados(inst, db)
    db.refresh(inst)
    return instrumento_para_out(inst, date.today())
```

> Nota: mova o `InstrumentoOut` para o import existente do topo (`from backend.schemas import CalibracaoIn, ListaCalibracoes, RegistroCalibracaoOut, CalibracaoOut, InstrumentoOut`) em vez de importar no meio do arquivo.

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_calibracoes_api.py -q`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add backend/routers/calibracoes.py tests/test_calibracoes_api.py
git commit -m "feat: DELETE de calibracao com recalculo dos derivados"
```

---

## Task 8: Backfill dos dados importados

**Files:**
- Modify: `backend/servico.py`
- Create: `backend/backfill.py`
- Modify: `entrypoint.sh`
- Test: `tests/test_calibracoes_api.py`

- [ ] **Step 1: Escrever o teste** ao fim de `tests/test_calibracoes_api.py`:

```python
def test_backfill_cria_calibracao_origem_e_e_idempotente(client):
    # A fixture cria A-1 com data_validade=2020-01-01 e sem data_ultima_calibracao.
    # Damos a um instrumento uma data_ultima_calibracao para o backfill agir.
    from backend.db import get_db
    from backend import models, servico
    from backend.main import app
    from datetime import date as _date

    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    inst = db.query(models.Instrumento).filter_by(codigo_interno="A-2").first()
    inst.data_ultima_calibracao = _date(2026, 1, 5)
    inst.organizacao_calibradora = "Lab Origem"
    db.commit()

    n1 = servico.backfill_calibracoes_origem(db)
    assert n1 == 1
    cals = db.query(models.Calibracao).filter_by(instrumento_id=inst.id).all()
    assert len(cals) == 1
    assert cals[0].origem == "IMPORTACAO"
    assert cals[0].laboratorio == "Lab Origem"
    assert cals[0].resultado == models.Resultado.APROVADO

    # idempotente: rodar de novo não cria outra
    n2 = servico.backfill_calibracoes_origem(db)
    assert n2 == 0
    assert db.query(models.Calibracao).filter_by(instrumento_id=inst.id).count() == 1
    db.close()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_calibracoes_api.py -k backfill -q`
Expected: FAIL com `AttributeError: module 'backend.servico' has no attribute 'backfill_calibracoes_origem'`.

- [ ] **Step 3: Implementar** — adicionar ao fim de `backend/servico.py`:

```python
def backfill_calibracoes_origem(db: Session) -> int:
    """Cria 1 calibração origem='IMPORTACAO' para cada instrumento que tem
    data_ultima_calibracao mas ainda não tem nenhuma calibração. Idempotente.
    Retorna quantas calibrações foram criadas."""
    criadas = 0
    instrumentos = (db.query(Instrumento)
                    .filter(Instrumento.data_ultima_calibracao.isnot(None))
                    .all())
    for inst in instrumentos:
        existe = (db.query(Calibracao)
                  .filter(Calibracao.instrumento_id == inst.id)
                  .first())
        if existe:
            continue
        db.add(Calibracao(
            instrumento_id=inst.id,
            data_calibracao=inst.data_ultima_calibracao,
            data_validade=inst.data_validade,
            ciclo_meses=inst.ciclo_meses or 12,
            resultado=Resultado.APROVADO,
            laboratorio=inst.organizacao_calibradora,
            numero_certificado=inst.certificado_ref,
            origem="IMPORTACAO",
        ))
        criadas += 1
    db.commit()
    return criadas
```

- [ ] **Step 4: Criar o runner** `backend/backfill.py`:

```python
"""Backfill de calibrações de origem — roda no startup (após dominios)."""
from __future__ import annotations
from backend.db import SessionLocal
from backend.servico import backfill_calibracoes_origem


def main() -> None:
    db = SessionLocal()
    try:
        n = backfill_calibracoes_origem(db)
        print(f"backfill_calibracoes: {n} calibração(ões) de origem criada(s)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

> Antes de implementar, confirme o nome do sessionmaker em `backend/db.py` (`grep -n "sessionmaker\|SessionLocal\|Session" backend/db.py`). Se for diferente de `SessionLocal`, ajuste o import. Espelhe o que `backend/dominios.py` faz no seu `if __name__ == "__main__"`.

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_calibracoes_api.py -k backfill -q`
Expected: PASS.

- [ ] **Step 6: Adicionar ao entrypoint** — em `entrypoint.sh`, após `python -m backend.dominios`:

```sh
python -m backend.backfill
```

- [ ] **Step 7: Commit**

```bash
git add backend/servico.py backend/backfill.py entrypoint.sh tests/test_calibracoes_api.py
git commit -m "feat: backfill de calibracoes de origem no startup"
```

---

## Task 9: Migração Alembic (cria tabela `calibracao`)

**Files:**
- Create: `alembic/versions/<rev>_calibracao.py`

- [ ] **Step 1: Gerar a migração vazia** (não dependa de autogenerate sobre o volume dev vazio):

Run: `alembic revision -m "calibracao"`
Expected: cria um arquivo em `alembic/versions/`. Anote o `revision` gerado e confirme que `down_revision = 'c00a5e8ec52e'` (head atual). Se não estiver, edite para `c00a5e8ec52e`.

- [ ] **Step 2: Escrever o `upgrade()`/`downgrade()`** no arquivo gerado:

```python
def upgrade() -> None:
    op.create_table(
        'calibracao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('instrumento_id', sa.Integer(), nullable=False),
        sa.Column('data_calibracao', sa.Date(), nullable=False),
        sa.Column('data_validade', sa.Date(), nullable=True),
        sa.Column('ciclo_meses', sa.Integer(), nullable=False),
        sa.Column('resultado',
                  sa.Enum('APROVADO', 'APROVADO_COM_RESTRICOES', 'REPROVADO', name='resultado'),
                  nullable=False),
        sa.Column('laboratorio', sa.String(), nullable=True),
        sa.Column('laboratorio_cnpj', sa.String(), nullable=True),
        sa.Column('acreditacao_rbc', sa.Boolean(), nullable=False),
        sa.Column('numero_cgcre', sa.String(), nullable=True),
        sa.Column('numero_certificado', sa.String(), nullable=True),
        sa.Column('custo', sa.Numeric(12, 2), nullable=True),
        sa.Column('responsavel', sa.String(), nullable=True),
        sa.Column('certificado_path', sa.String(), nullable=True),
        sa.Column('origem', sa.String(), nullable=False),
        sa.Column('observacoes', sa.String(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['instrumento_id'], ['instrumento.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_calibracao_instrumento_id', 'calibracao', ['instrumento_id'])


def downgrade() -> None:
    op.drop_index('ix_calibracao_instrumento_id', table_name='calibracao')
    op.drop_table('calibracao')
```

- [ ] **Step 3: Aplicar a migração num banco limpo de teste**

Run: `rm -f /tmp/mig.db && DATABASE_URL="sqlite:////tmp/mig.db" alembic upgrade head`
Expected: termina sem erro; menciona revisão `calibracao`.
(Se o projeto não usa `DATABASE_URL`, confira como `alembic.ini`/`env.py` define a URL e use o mesmo mecanismo. Não rode contra `data/siscalib.db` se ele tiver dados que você não quer tocar — use um arquivo temporário.)

- [ ] **Step 4: Rodar a suíte inteira** (garante que models + create_all dos testes seguem coerentes)

Run: `python -m pytest -q`
Expected: PASS (todos — 89 anteriores + os novos).

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/
git commit -m "feat: migracao da tabela calibracao"
```

---

## Task 10: Frontend — histórico + form na ficha (modal)

**Files:**
- Modify: `frontend/app.js`

> Estes passos são de UI; a verificação é manual no navegador. Antes de editar, leia `frontend/app.js` para localizar `abrirModal`, `renderFichaResumo` e o objeto de NAV, e siga o estilo existente (fetch helpers, classes CSS de `siscalib.css`).

- [ ] **Step 1: Adicionar `renderHistoricoCalibracoes(instId, container)`** em `app.js` — faz `GET /api/v1/instrumentos/{instId}/calibracoes` e injeta uma tabela com colunas: Data · Validade · Resultado · Laboratório · Certificado (link 📎 para `/{certificado_path}` quando houver) · Ação (botão Excluir → `DELETE` → re-render). Use os mesmos helpers de fetch já usados no arquivo.

- [ ] **Step 2: Adicionar `renderFormCalibracao(instId, onSaved)`** em `app.js` — monta um form com campos: `data_calibracao` (date, obrigatório), `resultado` (select: APROVADO / APROVADO_COM_RESTRICOES / REPROVADO), `laboratorio`, `numero_certificado`, `custo`, `responsavel`, `observacoes`, e um input file (PDF) opcional. Ao submeter: `POST /api/v1/instrumentos/{instId}/calibracoes` com JSON; se houver arquivo, em seguida `POST .../{cal_id}/certificado` (multipart). Depois chama `onSaved()`.

- [ ] **Step 3: Plugar na ficha** — em `renderFichaResumo` (ou onde o modal monta o conteúdo), adicionar uma seção "Calibrações" que chama `renderHistoricoCalibracoes` e um botão "Registrar calibração" que revela `renderFormCalibracao(instId, () => { recarregar histórico; recarregar a linha do inventário })`. O `onSaved` deve atualizar `todos`/`visiveis()` para refletir a nova validade/status na tabela (re-fetch do instrumento ou da lista).

- [ ] **Step 4: Verificação manual**

Run: `uvicorn backend.main:app --reload` (com um banco que tenha ao menos 1 instrumento; em dev, importe via tela ou crie um).
Abrir `http://localhost:8000/inventario.html`, clicar numa linha, conferir a seção Calibrações: registrar uma calibração APROVADA → validade aparece e some o "vencido"; registrar REPROVADA → status vira REPROVADO; anexar PDF → link 📎 abre o arquivo; excluir a mais recente → validade recua.

- [ ] **Step 5: Commit**

```bash
git add frontend/app.js
git commit -m "feat: secao de calibracoes na ficha (historico + form + upload)"
```

---

## Task 11: Frontend — página dedicada `calibracao.html`

**Files:**
- Create: `frontend/calibracao.html`
- Modify: `frontend/app.js` (item de NAV)

- [ ] **Step 1: Criar `frontend/calibracao.html`** espelhando a estrutura de `frontend/cadastro.html` (mesmo `<head>`, vendor CSS, layout/sidebar). Conteúdo principal: um seletor de instrumento no topo (campo de busca que lista instrumentos via `GET /api/v1/instrumentos?busca=`), e ao escolher um, renderiza no corpo `renderFormCalibracao(instId, ...)` + `renderHistoricoCalibracoes(instId, ...)` (reuso das funções do Task 10). Carregue `app.js`.

- [ ] **Step 2: Adicionar item na NAV** — no objeto/sidebar de navegação em `app.js`, adicionar entrada "Calibrações" apontando para `calibracao.html`, seguindo exatamente o padrão dos itens existentes (ícone bootstrap-icons, rótulo, href).

- [ ] **Step 3: Verificação manual**

Abrir `http://localhost:8000/calibracao.html`, buscar um instrumento, registrar uma calibração em série para dois instrumentos diferentes, conferir que o histórico atualiza e que a NAV destaca a página atual como nas demais.

- [ ] **Step 4: Commit**

```bash
git add frontend/calibracao.html frontend/app.js
git commit -m "feat: pagina dedicada de registro de calibracoes + item NAV"
```

---

## Task 12: Atualizar PRD §0 (status) + memória do projeto

**Files:**
- Modify: `PRD-SisCalib.md`

- [ ] **Step 1: Marcar 6.2 como entregue** no §0 (Status de Implementação) e na §6.2 / roadmap Fase 1: trocar o item "Registro de calibrações" de ⬜/`[ ]` para ✅/`[x]`, citando a entidade `calibracao`, backfill e upload de certificado.

- [ ] **Step 2: Rodar a suíte completa** uma última vez

Run: `python -m pytest -q`
Expected: PASS (todos).

- [ ] **Step 3: Commit**

```bash
git add PRD-SisCalib.md
git commit -m "docs: marca Registro de Calibracoes (6.2) como entregue no PRD"
```

---

## Verificação final (antes do merge)

- [ ] `python -m pytest -q` → todos passam (89 + ~16 novos).
- [ ] `python -c "import backend.main"` → sem erro (app sobe).
- [ ] Migração aplica limpa em banco novo (`alembic upgrade head`).
- [ ] Smoke manual da ficha e da página `calibracao.html`.
- [ ] Usar `superpowers:finishing-a-development-branch` para decidir merge/PR de `feat/registro-calibracoes`.
