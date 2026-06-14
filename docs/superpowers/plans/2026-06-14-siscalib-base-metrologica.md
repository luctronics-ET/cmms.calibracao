# SisCalib — Base Metrológica + Cadastro Completo (6.1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completar o cadastro de instrumentos (PRD 6.1) com tabelas de domínio (taxonomia RBC/INMETRO), campos metrológicos, localização, estado operacional, anexos, modelo de criticidade IGP e tela de cadastro/edição — preservando os 496 registros existentes.

**Architecture:** Adiciona 4 tabelas de domínio (família/tipo/grandeza/unidade) com FK a partir de `instrumento`, novas colunas anuláveis, um motor puro `calcular_igp` (análogo ao motor de status), endpoints de domínios/criação/edição/upload e um formulário vanilla com IGP ao vivo. Migração Alembic aditiva + seed idempotente. Stack inalterado: FastAPI + SQLAlchemy/Alembic + SQLite + JS vanilla.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, SQLite, pytest, HTML/CSS/JS vanilla.

**Spec:** `docs/superpowers/specs/2026-06-14-siscalib-base-metrologica-design.md`

---

## File Structure

| Arquivo | Mudança |
|---|---|
| `backend/criticidade.py` | **novo** — motor IGP puro |
| `backend/models.py` | + 4 modelos de domínio, enum `StatusOperacional`, novas colunas + relationships em `Instrumento` |
| `backend/dominios.py` | **novo** — `seed_dominios(db)` idempotente |
| `backend/schemas.py` | `InstrumentoOut` ampliado; `InstrumentoIn`; `DominiosOut` |
| `backend/servico.py` | aplica IGP + resolve nomes de FK no output |
| `backend/routers/dominios.py` | **novo** — `GET /api/v1/dominios` |
| `backend/routers/instrumentos.py` | + POST/PUT, filtros `familia_id`/`classe_prioridade`, upload foto/manual |
| `backend/main.py` | inclui router de domínios; monta `/uploads`; seed no startup |
| `alembic/versions/*` | revisão aditiva |
| `frontend/app.js` | + `loadDominios`, `calcIgpClient`, helpers de form |
| `frontend/cadastro.html` | **novo** — form criar/editar |
| `frontend/ficha.html`, `inventario.html` | novos campos, filtros, link editar |
| `tests/test_criticidade.py`, `test_dominios.py` | **novos** |
| `tests/test_api.py`, `tests/conftest.py` | + casos de cadastro/edição/upload/domínios |

---

## Task 1: Motor IGP (TDD)

**Files:**
- Create: `backend/criticidade.py`
- Test: `tests/test_criticidade.py`

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_criticidade.py`:
```python
from backend.criticidade import calcular_igp, ClassePrioridade


def test_todas_minimas_igp_7_muito_baixa():
    r = calcular_igp(1, 1, 1, 1, 1)
    assert r.igp == 7
    assert r.classe == ClassePrioridade.MUITO_BAIXA


def test_todas_medias_igp_14_media():
    r = calcular_igp(2, 2, 2, 2, 2)
    assert r.igp == 14
    assert r.classe == ClassePrioridade.MEDIA


def test_todas_maximas_igp_21_maxima():
    r = calcular_igp(3, 3, 3, 3, 3)
    assert r.igp == 21
    assert r.classe == ClassePrioridade.MAXIMA


def test_pesos_nc_e_cm_dobram():
    # fu=1 nc=3 ab=1 cm=3 ci=1 => 1 + 6 + 1 + 6 + 1 = 15
    assert calcular_igp(1, 3, 1, 3, 1).igp == 15


def test_fronteira_10_muito_baixa():
    assert calcular_igp(2, 1, 1, 1, 3).classe == ClassePrioridade.MUITO_BAIXA  # igp 10


def test_fronteira_11_baixa():
    r = calcular_igp(1, 1, 1, 3, 1)  # igp 11
    assert r.igp == 11
    assert r.classe == ClassePrioridade.BAIXA


def test_fronteira_13_baixa():
    assert calcular_igp(3, 1, 3, 1, 3).classe == ClassePrioridade.BAIXA  # igp 13


def test_fronteira_14_media():
    assert calcular_igp(2, 2, 2, 2, 2).classe == ClassePrioridade.MEDIA  # igp 14


def test_fronteira_17_media():
    assert calcular_igp(3, 2, 3, 2, 3).classe == ClassePrioridade.MEDIA  # igp 17


def test_fronteira_18_maxima():
    r = calcular_igp(2, 3, 2, 3, 2)  # igp 18
    assert r.igp == 18
    assert r.classe == ClassePrioridade.MAXIMA


def test_qualquer_variavel_nula_nao_classificado():
    r = calcular_igp(None, 2, 2, 2, 2)
    assert r.igp is None
    assert r.classe == ClassePrioridade.NAO_CLASSIFICADO
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_criticidade.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.criticidade'`.

- [ ] **Step 3: Implementar `backend/criticidade.py`**

```python
"""Motor puro do Índice Global de Prioridade do Equipamento (IGP).

IGP = fu·1 + nc·2 + ab·1 + cm·2 + ci·1  (faixa real 7..21 quando completo).
Sem I/O, sem DB.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

LIMIAR_MAXIMA = 18
LIMIAR_MEDIA = 14
LIMIAR_BAIXA = 11


class ClassePrioridade(str, Enum):
    MAXIMA = "MAXIMA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"
    MUITO_BAIXA = "MUITO_BAIXA"
    NAO_CLASSIFICADO = "NAO_CLASSIFICADO"


@dataclass(frozen=True)
class ResultadoIGP:
    igp: int | None
    classe: ClassePrioridade


def calcular_igp(fu, nc, ab, cm, ci) -> ResultadoIGP:
    if any(v is None for v in (fu, nc, ab, cm, ci)):
        return ResultadoIGP(None, ClassePrioridade.NAO_CLASSIFICADO)
    igp = fu * 1 + nc * 2 + ab * 1 + cm * 2 + ci * 1
    if igp >= LIMIAR_MAXIMA:
        classe = ClassePrioridade.MAXIMA
    elif igp >= LIMIAR_MEDIA:
        classe = ClassePrioridade.MEDIA
    elif igp >= LIMIAR_BAIXA:
        classe = ClassePrioridade.BAIXA
    else:
        classe = ClassePrioridade.MUITO_BAIXA
    return ResultadoIGP(igp, classe)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/python -m pytest tests/test_criticidade.py -q`
Expected: PASS (11 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/criticidade.py tests/test_criticidade.py
git commit -m "feat: motor puro do IGP (criticidade/priorização)"
```

---

## Task 2: Modelos de domínio + novas colunas em Instrumento

**Files:**
- Modify: `backend/models.py`

- [ ] **Step 1: Substituir `backend/models.py` pelo conteúdo ampliado**

```python
"""ORM do SisCalib."""
from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import (
    String, Integer, Date, DateTime, Numeric, Enum, ForeignKey, Boolean, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db import Base


class Disciplina(str, enum.Enum):
    ELE = "ELE"
    MEC = "MEC"


class StatusOperacional(str, enum.Enum):
    ATIVO = "ATIVO"
    EM_CALIBRACAO = "EM_CALIBRACAO"
    EM_MANUTENCAO = "EM_MANUTENCAO"
    REPROVADO = "REPROVADO"
    BLOQUEADO = "BLOQUEADO"
    BAIXADO = "BAIXADO"


class FamiliaMetrologica(Base):
    __tablename__ = "familia_metrologica"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String, unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)


class UnidadeMedida(Base):
    __tablename__ = "unidade_medida"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String, unique=True)
    simbolo: Mapped[str | None] = mapped_column(String)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)


class Grandeza(Base):
    __tablename__ = "grandeza"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String, unique=True)
    familia_id: Mapped[int | None] = mapped_column(ForeignKey("familia_metrologica.id"))
    unidade_padrao_id: Mapped[int | None] = mapped_column(ForeignKey("unidade_medida.id"))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    familia: Mapped["FamiliaMetrologica | None"] = relationship()
    unidade_padrao: Mapped["UnidadeMedida | None"] = relationship()


class TipoInstrumento(Base):
    __tablename__ = "tipo_instrumento"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String, unique=True)
    familia_id: Mapped[int | None] = mapped_column(ForeignKey("familia_metrologica.id"))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    familia: Mapped["FamiliaMetrologica | None"] = relationship()


class Instrumento(Base):
    __tablename__ = "instrumento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_interno: Mapped[str | None] = mapped_column(String, index=True)
    codigo_patrimonial: Mapped[str | None] = mapped_column(String, index=True)
    serial: Mapped[str | None] = mapped_column(String, index=True)
    equipamento: Mapped[str | None] = mapped_column(String)
    marca: Mapped[str | None] = mapped_column(String)
    modelo: Mapped[str | None] = mapped_column(String)
    # especificação técnica
    faixa: Mapped[str | None] = mapped_column(String)            # legado (texto livre)
    unidade_faixa: Mapped[str | None] = mapped_column(String)    # legado
    faixa_min: Mapped[float | None] = mapped_column(Numeric(18, 6))
    faixa_max: Mapped[float | None] = mapped_column(Numeric(18, 6))
    resolucao: Mapped[str | None] = mapped_column(String)
    emp: Mapped[str | None] = mapped_column(String)
    # classificação
    disciplina: Mapped[Disciplina | None] = mapped_column(Enum(Disciplina))
    familia_id: Mapped[int | None] = mapped_column(ForeignKey("familia_metrologica.id"))
    tipo_id: Mapped[int | None] = mapped_column(ForeignKey("tipo_instrumento.id"))
    grandeza_id: Mapped[int | None] = mapped_column(ForeignKey("grandeza.id"))
    unidade_id: Mapped[int | None] = mapped_column(ForeignKey("unidade_medida.id"))
    # localização
    sistema: Mapped[str | None] = mapped_column(String, index=True)
    organizacao: Mapped[str | None] = mapped_column(String)
    unidade_org: Mapped[str | None] = mapped_column(String)
    secao: Mapped[str | None] = mapped_column(String)
    bancada: Mapped[str | None] = mapped_column(String)
    # calibração
    ciclo_meses: Mapped[int] = mapped_column(Integer, default=12)
    data_ultima_calibracao: Mapped[Date | None] = mapped_column(Date)
    data_validade: Mapped[Date | None] = mapped_column(Date)
    flag_origem: Mapped[str | None] = mapped_column(String)
    organizacao_calibradora: Mapped[str | None] = mapped_column(String)
    local_calibracao: Mapped[str | None] = mapped_column(String)
    custo_estimado: Mapped[float | None] = mapped_column(Numeric(12, 2))
    custo_contratado: Mapped[float | None] = mapped_column(Numeric(12, 2))
    certificado_ref: Mapped[str | None] = mapped_column(String)
    # estado operacional
    status_operacional: Mapped[StatusOperacional] = mapped_column(
        Enum(StatusOperacional), default=StatusOperacional.ATIVO
    )
    # anexos
    foto_path: Mapped[str | None] = mapped_column(String)
    manual_path: Mapped[str | None] = mapped_column(String)
    # criticidade IGP (1..3, anuláveis)
    fu: Mapped[int | None] = mapped_column(Integer)
    nc: Mapped[int | None] = mapped_column(Integer)
    ab: Mapped[int | None] = mapped_column(Integer)
    cm: Mapped[int | None] = mapped_column(Integer)
    ci: Mapped[int | None] = mapped_column(Integer)
    # observações / auditoria
    observacoes: Mapped[str | None] = mapped_column(String)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    # relationships (lazy)
    familia: Mapped["FamiliaMetrologica | None"] = relationship()
    tipo: Mapped["TipoInstrumento | None"] = relationship()
    grandeza: Mapped["Grandeza | None"] = relationship()
    unidade: Mapped["UnidadeMedida | None"] = relationship()
```

- [ ] **Step 2: Verificar import e que o metadata registra as tabelas**

Run:
```bash
.venv/bin/python -c "from backend import models; print(sorted(models.Base.metadata.tables.keys()))"
```
Expected: lista incluindo `familia_metrologica`, `grandeza`, `instrumento`, `tipo_instrumento`, `unidade_medida`.

- [ ] **Step 3: Commit**

```bash
git add backend/models.py
git commit -m "feat: modelos de domínio metrológico + novas colunas em instrumento"
```

---

## Task 3: Migração Alembic aditiva

**Files:**
- Create: `alembic/versions/<hash>_base_metrologica.py` (autogenerada)

- [ ] **Step 1: Gerar a migração**

Run (a partir de `/home/luc/DEV_ERP/xCalibracao`):
```bash
.venv/bin/alembic revision --autogenerate -m "base metrologica"
```
Expected: novo arquivo em `alembic/versions/` com `op.create_table` para as 4 tabelas de domínio e `op.add_column` para cada coluna nova de `instrumento`.

- [ ] **Step 2: Adicionar índice único parcial em `codigo_patrimonial`**

Edite a migração gerada: dentro de `upgrade()`, ao final, adicione:
```python
    op.create_index(
        "uq_instrumento_codigo_patrimonial",
        "instrumento",
        ["codigo_patrimonial"],
        unique=True,
        sqlite_where=sa.text("codigo_patrimonial IS NOT NULL"),
    )
```
E em `downgrade()`, no início:
```python
    op.drop_index("uq_instrumento_codigo_patrimonial", table_name="instrumento")
```
(Confirme que `import sqlalchemy as sa` já está no topo do arquivo — o template do Alembic inclui.)

- [ ] **Step 3: Aplicar a migração from-scratch e verificar**

Run:
```bash
rm -f /tmp/sc_meta.db
SISCALIB_DB_URL="sqlite:////tmp/sc_meta.db" .venv/bin/alembic upgrade head
SISCALIB_DB_URL="sqlite:////tmp/sc_meta.db" .venv/bin/python -c "
import sqlite3
c = sqlite3.connect('/tmp/sc_meta.db')
print('tabelas:', sorted(r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")))
print('colunas instrumento:', sorted(r[1] for r in c.execute('PRAGMA table_info(instrumento)')))
print('indices:', sorted(r[1] for r in c.execute('PRAGMA index_list(instrumento)')))
"
```
Expected: tabelas incluem as 4 de domínio; colunas incluem `codigo_patrimonial`, `familia_id`, `tipo_id`, `grandeza_id`, `unidade_id`, `faixa_min`, `faixa_max`, `resolucao`, `emp`, `organizacao`, `unidade_org`, `secao`, `bancada`, `status_operacional`, `foto_path`, `manual_path`, `fu`, `nc`, `ab`, `cm`, `ci`; índices incluem `uq_instrumento_codigo_patrimonial`.

- [ ] **Step 4: Aplicar também no banco de dev existente (preserva os 496)**

Run:
```bash
.venv/bin/alembic upgrade head
.venv/bin/python -c "import sqlite3; print('instrumentos:', sqlite3.connect('data/siscalib.db').execute('SELECT count(*) FROM instrumento').fetchone()[0])"
```
Expected: a migração aplica sem erro; a contagem de instrumentos permanece (não zera).

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/
git commit -m "feat: migração aditiva da base metrológica + índice único de patrimônio"
```

---

## Task 4: Seed idempotente dos domínios (TDD)

**Files:**
- Create: `backend/dominios.py`
- Test: `tests/test_dominios.py`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_dominios.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base
from backend import models
from backend.dominios import seed_dominios


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'d.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_seed_cria_15_familias(tmp_path):
    db = _session(tmp_path)
    seed_dominios(db)
    assert db.query(models.FamiliaMetrologica).count() == 15


def test_seed_cria_unidades_grandezas_tipos(tmp_path):
    db = _session(tmp_path)
    seed_dominios(db)
    assert db.query(models.UnidadeMedida).count() > 0
    assert db.query(models.Grandeza).count() > 0
    assert db.query(models.TipoInstrumento).count() > 0


def test_seed_idempotente(tmp_path):
    db = _session(tmp_path)
    seed_dominios(db)
    n1 = db.query(models.FamiliaMetrologica).count()
    seed_dominios(db)  # roda de novo
    n2 = db.query(models.FamiliaMetrologica).count()
    assert n1 == n2 == 15


def test_grandeza_ligada_a_familia(tmp_path):
    db = _session(tmp_path)
    seed_dominios(db)
    g = db.query(models.Grandeza).filter_by(nome="Tensão DC").first()
    assert g is not None
    assert g.familia is not None
    assert g.familia.nome == "Eletricidade e Magnetismo"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_dominios.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.dominios'`.

- [ ] **Step 3: Implementar `backend/dominios.py`**

```python
"""Seed idempotente das tabelas de domínio metrológico (taxonomia RBC/INMETRO)."""
from __future__ import annotations
from sqlalchemy.orm import Session
from backend.models import FamiliaMetrologica, UnidadeMedida, Grandeza, TipoInstrumento

# 15 grupos oficiais da RBC/INMETRO
FAMILIAS = [
    "Acústica e Vibrações",
    "Alta Frequência e Telecomunicações",
    "Dimensional",
    "Eletricidade e Magnetismo",
    "Físico-Química",
    "Força, Torque e Dureza",
    "Massa",
    "Óptica",
    "Pressão",
    "Radiações Ionizantes",
    "Temperatura e Umidade",
    "Tempo e Frequência",
    "Vazão e Velocidade de Fluidos",
    "Viscosidade",
    "Volume e Massa Específica",
]

# (nome, simbolo)
UNIDADES = [
    ("Volt", "V"), ("Ampère", "A"), ("Ohm", "Ω"), ("Hertz", "Hz"),
    ("Metro", "m"), ("Milímetro", "mm"), ("Micrômetro", "µm"),
    ("Quilograma", "kg"), ("Grama", "g"), ("Newton-metro", "N·m"),
    ("Pascal", "Pa"), ("Bar", "bar"), ("Grau Celsius", "°C"),
    ("Umidade Relativa", "%UR"), ("Litro", "L"), ("Mililitro", "mL"),
]

# (nome_grandeza, nome_familia, simbolo_unidade_padrao)
GRANDEZAS = [
    ("Tensão DC", "Eletricidade e Magnetismo", "V"),
    ("Tensão AC", "Eletricidade e Magnetismo", "V"),
    ("Corrente DC", "Eletricidade e Magnetismo", "A"),
    ("Resistência", "Eletricidade e Magnetismo", "Ω"),
    ("Frequência", "Tempo e Frequência", "Hz"),
    ("Comprimento", "Dimensional", "mm"),
    ("Massa", "Massa", "kg"),
    ("Torque", "Força, Torque e Dureza", "N·m"),
    ("Pressão", "Pressão", "Pa"),
    ("Temperatura", "Temperatura e Umidade", "°C"),
    ("Umidade", "Temperatura e Umidade", "%UR"),
    ("Volume", "Volume e Massa Específica", "L"),
]

# (nome_tipo, nome_familia | None)
TIPOS = [
    ("Multímetro", "Eletricidade e Magnetismo"),
    ("Osciloscópio", "Eletricidade e Magnetismo"),
    ("Fonte DC", "Eletricidade e Magnetismo"),
    ("Calibrador", "Eletricidade e Magnetismo"),
    ("Gerador de Funções", "Tempo e Frequência"),
    ("Paquímetro", "Dimensional"),
    ("Micrômetro", "Dimensional"),
    ("Torquímetro", "Força, Torque e Dureza"),
    ("Dinamômetro", "Força, Torque e Dureza"),
    ("Manômetro", "Pressão"),
    ("Termômetro", "Temperatura e Umidade"),
    ("Balança", "Massa"),
]


def _get_or_create(db: Session, modelo, nome: str, **extra):
    obj = db.query(modelo).filter_by(nome=nome).first()
    if obj is None:
        obj = modelo(nome=nome, **extra)
        db.add(obj)
        db.flush()
    return obj


def seed_dominios(db: Session) -> None:
    for i, nome in enumerate(FAMILIAS):
        _get_or_create(db, FamiliaMetrologica, nome, ordem=i)
    for i, (nome, simb) in enumerate(UNIDADES):
        u = _get_or_create(db, UnidadeMedida, nome, ordem=i)
        u.simbolo = simb
    fam = {f.nome: f for f in db.query(FamiliaMetrologica).all()}
    uni_por_simbolo = {u.simbolo: u for u in db.query(UnidadeMedida).all()}
    for i, (nome, fam_nome, simb) in enumerate(GRANDEZAS):
        g = _get_or_create(db, Grandeza, nome, ordem=i)
        g.familia_id = fam[fam_nome].id
        g.unidade_padrao_id = uni_por_simbolo[simb].id if simb in uni_por_simbolo else None
    for i, (nome, fam_nome) in enumerate(TIPOS):
        t = _get_or_create(db, TipoInstrumento, nome, ordem=i)
        t.familia_id = fam[fam_nome].id if fam_nome else None
    db.commit()


if __name__ == "__main__":
    from backend.db import SessionLocal
    s = SessionLocal()
    try:
        seed_dominios(s)
        print("seed concluído")
    finally:
        s.close()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/python -m pytest tests/test_dominios.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Rodar o seed no banco de dev**

Run: `.venv/bin/python -m backend.dominios && .venv/bin/python -c "from backend.db import SessionLocal; from backend import models; s=SessionLocal(); print('familias:', s.query(models.FamiliaMetrologica).count())"`
Expected: `seed concluído` e `familias: 15`.

- [ ] **Step 6: Commit**

```bash
git add backend/dominios.py tests/test_dominios.py
git commit -m "feat: seed idempotente dos domínios (15 famílias RBC + grandezas/unidades/tipos)"
```

---

## Task 5: Schemas ampliados + serviço com IGP e nomes de FK

**Files:**
- Modify: `backend/schemas.py`
- Modify: `backend/servico.py`

- [ ] **Step 1: Substituir `backend/schemas.py`**

```python
"""Modelos de entrada/saída da API."""
from __future__ import annotations
from datetime import date
from pydantic import BaseModel, Field


class InstrumentoOut(BaseModel):
    id: int
    codigo_interno: str | None
    codigo_patrimonial: str | None
    serial: str | None
    equipamento: str | None
    marca: str | None
    modelo: str | None
    faixa: str | None
    unidade_faixa: str | None
    faixa_min: float | None
    faixa_max: float | None
    resolucao: str | None
    emp: str | None
    disciplina: str | None
    familia_id: int | None
    familia_nome: str | None
    tipo_id: int | None
    tipo_nome: str | None
    grandeza_id: int | None
    grandeza_nome: str | None
    unidade_id: int | None
    unidade_simbolo: str | None
    sistema: str | None
    organizacao: str | None
    unidade_org: str | None
    secao: str | None
    bancada: str | None
    ciclo_meses: int
    data_ultima_calibracao: date | None
    data_validade: date | None
    flag_origem: str | None
    organizacao_calibradora: str | None
    local_calibracao: str | None
    custo_estimado: float | None
    custo_contratado: float | None
    certificado_ref: str | None
    status_operacional: str
    foto_path: str | None
    manual_path: str | None
    fu: int | None
    nc: int | None
    ab: int | None
    cm: int | None
    ci: int | None
    observacoes: str | None
    # derivados
    status: str
    dias_restantes: int | None
    divergencia_flag: bool
    igp: int | None
    classe_prioridade: str


class InstrumentoIn(BaseModel):
    """Entrada de criação/edição."""
    equipamento: str
    familia_id: int
    tipo_id: int
    ciclo_meses: int = 12
    status_operacional: str = "ATIVO"
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


class ProblemaImport(BaseModel):
    severidade: str
    campo: str
    mensagem: str


class TotaisImport(BaseModel):
    total_linhas: int
    validas: int
    com_aviso: int
    com_erro: int


class LinhaPreview(BaseModel):
    numero: int
    dados: dict
    problemas: list[ProblemaImport]


class PreviewResposta(BaseModel):
    totais: TotaisImport
    linhas: list[LinhaPreview]


class CommitResposta(BaseModel):
    inseridos: int
    ignorados: int


class ListaInstrumentos(BaseModel):
    total: int
    itens: list[InstrumentoOut]


class ItemDominio(BaseModel):
    id: int
    nome: str
    simbolo: str | None = None
    familia_id: int | None = None
    unidade_padrao_id: int | None = None


class DominiosOut(BaseModel):
    familias: list[ItemDominio]
    tipos: list[ItemDominio]
    grandezas: list[ItemDominio]
    unidades: list[ItemDominio]
```

- [ ] **Step 2: Substituir `backend/servico.py`**

```python
"""Aplica os motores de status e IGP sobre instrumentos do banco."""
from __future__ import annotations
from datetime import date
from backend.calibracao import calcular_status
from backend.criticidade import calcular_igp
from backend.models import Instrumento
from backend.schemas import InstrumentoOut


def instrumento_para_out(inst: Instrumento, hoje: date) -> InstrumentoOut:
    st = calcular_status(inst.data_validade, inst.flag_origem, hoje)
    ig = calcular_igp(inst.fu, inst.nc, inst.ab, inst.cm, inst.ci)
    return InstrumentoOut(
        id=inst.id,
        codigo_interno=inst.codigo_interno,
        codigo_patrimonial=inst.codigo_patrimonial,
        serial=inst.serial,
        equipamento=inst.equipamento,
        marca=inst.marca,
        modelo=inst.modelo,
        faixa=inst.faixa,
        unidade_faixa=inst.unidade_faixa,
        faixa_min=float(inst.faixa_min) if inst.faixa_min is not None else None,
        faixa_max=float(inst.faixa_max) if inst.faixa_max is not None else None,
        resolucao=inst.resolucao,
        emp=inst.emp,
        disciplina=inst.disciplina.value if inst.disciplina else None,
        familia_id=inst.familia_id,
        familia_nome=inst.familia.nome if inst.familia else None,
        tipo_id=inst.tipo_id,
        tipo_nome=inst.tipo.nome if inst.tipo else None,
        grandeza_id=inst.grandeza_id,
        grandeza_nome=inst.grandeza.nome if inst.grandeza else None,
        unidade_id=inst.unidade_id,
        unidade_simbolo=inst.unidade.simbolo if inst.unidade else None,
        sistema=inst.sistema,
        organizacao=inst.organizacao,
        unidade_org=inst.unidade_org,
        secao=inst.secao,
        bancada=inst.bancada,
        ciclo_meses=inst.ciclo_meses,
        data_ultima_calibracao=inst.data_ultima_calibracao,
        data_validade=inst.data_validade,
        flag_origem=inst.flag_origem,
        organizacao_calibradora=inst.organizacao_calibradora,
        local_calibracao=inst.local_calibracao,
        custo_estimado=float(inst.custo_estimado) if inst.custo_estimado is not None else None,
        custo_contratado=float(inst.custo_contratado) if inst.custo_contratado is not None else None,
        certificado_ref=inst.certificado_ref,
        status_operacional=inst.status_operacional.value,
        foto_path=inst.foto_path,
        manual_path=inst.manual_path,
        fu=inst.fu, nc=inst.nc, ab=inst.ab, cm=inst.cm, ci=inst.ci,
        observacoes=inst.observacoes,
        status=st.status.value,
        dias_restantes=st.dias_restantes,
        divergencia_flag=st.divergencia_flag,
        igp=ig.igp,
        classe_prioridade=ig.classe.value,
    )
```

- [ ] **Step 3: Verificar import e regressão**

Run: `.venv/bin/python -c "import backend.schemas, backend.servico"` then `.venv/bin/python -m pytest tests/ -q`
Expected: import ok; **a suíte pode ter falhas** em `tests/test_api.py` porque o seed/conftest ainda não cria os domínios e os instrumentos do seed não têm `status_operacional`. Anote quais falham — serão corrigidas na Task 7 (conftest). Se as únicas falhas forem em `test_api.py` por causa de `status_operacional`/domínios, prossiga; os testes de `test_calibracao`, `test_parsing`, `test_importacao`, `test_criticidade`, `test_dominios` devem passar.

> Nota: `status_operacional` tem default no modelo, então instrumentos do seed existente recebem ATIVO; o `InstrumentoOut` exige `status` e `classe_prioridade` (sempre presentes via motores). A regressão deve passar mesmo assim. Se algo quebrar por FK não-resolvida, é porque o seed do conftest não roda domínios — será ajustado na Task 7.

- [ ] **Step 4: Commit**

```bash
git add backend/schemas.py backend/servico.py
git commit -m "feat: schemas ampliados (cadastro + IGP) e serviço com nomes de FK"
```

---

## Task 6: Router de domínios (TDD)

**Files:**
- Create: `backend/routers/dominios.py`
- Modify: `backend/main.py`
- Modify: `tests/conftest.py` (seed de domínios na fixture)
- Test: `tests/test_api.py` (anexar)

- [ ] **Step 1: Atualizar `tests/conftest.py` para semear domínios e usar status_operacional**

Substitua o corpo da fixture `client` por (mantém os 3 instrumentos, agora com família/tipo e status):
```python
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base, get_db
from backend import models
from backend.dominios import seed_dominios
from backend.main import app


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'t.db'}",
                           connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    seed_dominios(db)
    fam = db.query(models.FamiliaMetrologica).filter_by(nome="Eletricidade e Magnetismo").first()
    fam_mec = db.query(models.FamiliaMetrologica).filter_by(nome="Dimensional").first()
    tipo = db.query(models.TipoInstrumento).filter_by(nome="Multímetro").first()
    tipo_paq = db.query(models.TipoInstrumento).filter_by(nome="Paquímetro").first()
    db.add_all([
        models.Instrumento(codigo_interno="A-1", equipamento="MULTÍMETRO", marca="Fluke",
                           disciplina=models.Disciplina.ELE, sistema="MK-48",
                           familia_id=fam.id, tipo_id=tipo.id, ciclo_meses=12,
                           data_validade=date(2020, 1, 1), flag_origem="DESCALIBRADO"),
        models.Instrumento(codigo_interno="A-2", equipamento="PAQUÍMETRO",
                           disciplina=models.Disciplina.MEC, sistema="F-21",
                           familia_id=fam_mec.id, tipo_id=tipo_paq.id, ciclo_meses=12,
                           data_validade=date(2099, 1, 1), flag_origem="CALIBRADO"),
        models.Instrumento(codigo_interno="A-3", equipamento="TORQUÍMETRO",
                           disciplina=models.Disciplina.MEC, sistema="MK-48",
                           ciclo_meses=12, data_validade=None, flag_origem=""),
    ])
    db.commit()
    db.close()

    def _override():
        d = TestingSession()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Escrever os testes que falham (anexar a `tests/test_api.py`)**

```python
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
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_api.py -q -k dominios`
Expected: FAIL — 404 (rota inexistente).

- [ ] **Step 4: Implementar `backend/routers/dominios.py`**

```python
"""Endpoint de tabelas de domínio para popular selects do frontend."""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import FamiliaMetrologica, UnidadeMedida, Grandeza, TipoInstrumento
from backend.schemas import DominiosOut, ItemDominio

router = APIRouter(prefix="/api/v1", tags=["dominios"])


@router.get("/dominios", response_model=DominiosOut)
def listar_dominios(db: Session = Depends(get_db), familia_id: int | None = Query(None)):
    familias = db.query(FamiliaMetrologica).filter_by(ativo=True).order_by(FamiliaMetrologica.ordem).all()
    unidades = db.query(UnidadeMedida).filter_by(ativo=True).order_by(UnidadeMedida.ordem).all()
    q_tipos = db.query(TipoInstrumento).filter_by(ativo=True)
    q_grand = db.query(Grandeza).filter_by(ativo=True)
    if familia_id is not None:
        q_tipos = q_tipos.filter_by(familia_id=familia_id)
        q_grand = q_grand.filter_by(familia_id=familia_id)
    tipos = q_tipos.order_by(TipoInstrumento.ordem).all()
    grandezas = q_grand.order_by(Grandeza.ordem).all()

    def fam(o): return {"id": o.id, "nome": o.nome}
    return DominiosOut(
        familias=[ItemDominio(id=f.id, nome=f.nome) for f in familias],
        unidades=[ItemDominio(id=u.id, nome=u.nome, simbolo=u.simbolo) for u in unidades],
        tipos=[ItemDominio(id=t.id, nome=t.nome, familia_id=t.familia_id) for t in tipos],
        grandezas=[ItemDominio(id=g.id, nome=g.nome, familia_id=g.familia_id,
                               unidade_padrao_id=g.unidade_padrao_id) for g in grandezas],
    )
```

- [ ] **Step 5: Incluir o router e seed no startup em `backend/main.py`**

Substitua `backend/main.py` por:
```python
"""App FastAPI do SisCalib."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.routers import instrumentos, importacao, dashboard, dominios

app = FastAPI(title="SisCalib", version="0.2.0")
app.include_router(instrumentos.router)
app.include_router(importacao.router)
app.include_router(dashboard.router)
app.include_router(dominios.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


DATA = Path(__file__).resolve().parent.parent / "data"
UPLOADS = DATA / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS)), name="uploads")

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
```
> O mount `/uploads` é registrado ANTES do mount `/` para ter precedência.

- [ ] **Step 6: Rodar e ver passar + regressão**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS (todos, incluindo os 48 anteriores + os novos de domínios). Se algum teste antigo do dashboard/alertas falhar por causa do `status_operacional`, verifique — não deveria, pois há default.

- [ ] **Step 7: Commit**

```bash
git add backend/routers/dominios.py backend/main.py tests/conftest.py tests/test_api.py
git commit -m "feat: GET /dominios, mount /uploads e seed nos testes"
```

---

## Task 7: Criar e editar instrumento (POST/PUT) + filtros novos (TDD)

**Files:**
- Modify: `backend/routers/instrumentos.py`
- Test: `tests/test_api.py` (anexar)

- [ ] **Step 1: Escrever os testes que falham (anexar a `tests/test_api.py`)**

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_api.py -q -k "criar or editar or patrimonio or classe"`
Expected: FAIL — 404/405 (rotas inexistentes).

- [ ] **Step 3: Substituir `backend/routers/instrumentos.py`**

```python
"""Endpoints de inventário (listar, obter, criar, editar)."""
from __future__ import annotations
import unicodedata
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Instrumento, Disciplina, StatusOperacional
from backend.servico import instrumento_para_out
from backend.schemas import ListaInstrumentos, InstrumentoOut, InstrumentoIn

router = APIRouter(prefix="/api/v1", tags=["instrumentos"])


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


@router.get("/instrumentos", response_model=ListaInstrumentos)
def listar(
    db: Session = Depends(get_db),
    busca: str | None = Query(None),
    disciplina: str | None = Query(None),
    sistema: str | None = Query(None),
    status: str | None = Query(None),
    familia_id: int | None = Query(None),
    classe_prioridade: str | None = Query(None),
):
    hoje = date.today()
    itens = [instrumento_para_out(i, hoje) for i in db.query(Instrumento).all()]

    if busca:
        b = _sem_acento(busca)
        itens = [i for i in itens if b in _sem_acento(" ".join(
            filter(None, [i.codigo_interno, i.serial, i.equipamento, i.modelo, i.marca])))]
    if disciplina:
        itens = [i for i in itens if i.disciplina == disciplina.upper()]
    if sistema:
        itens = [i for i in itens if (i.sistema or "") == sistema]
    if status:
        itens = [i for i in itens if i.status == status.upper()]
    if familia_id is not None:
        itens = [i for i in itens if i.familia_id == familia_id]
    if classe_prioridade:
        itens = [i for i in itens if i.classe_prioridade == classe_prioridade.upper()]

    itens.sort(key=lambda i: (i.codigo_interno or "").lower())
    return ListaInstrumentos(total=len(itens), itens=itens)


@router.get("/instrumentos/{inst_id}", response_model=InstrumentoOut)
def obter(inst_id: int, db: Session = Depends(get_db)):
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    return instrumento_para_out(inst, date.today())


def _aplicar(inst: Instrumento, dados: InstrumentoIn) -> None:
    payload = dados.model_dump(exclude_unset=False)
    if payload.get("disciplina"):
        payload["disciplina"] = Disciplina(payload["disciplina"].upper())
    payload["status_operacional"] = StatusOperacional(payload["status_operacional"])
    for campo, valor in payload.items():
        setattr(inst, campo, valor)


def _checar_patrimonio(db: Session, codigo: str | None, ignorar_id: int | None = None) -> None:
    if not codigo:
        return
    q = db.query(Instrumento).filter(Instrumento.codigo_patrimonial == codigo)
    if ignorar_id is not None:
        q = q.filter(Instrumento.id != ignorar_id)
    if q.first():
        raise HTTPException(status_code=409, detail="Código patrimonial já existe")


@router.post("/instrumentos", response_model=InstrumentoOut, status_code=201)
def criar(dados: InstrumentoIn, db: Session = Depends(get_db)):
    _checar_patrimonio(db, dados.codigo_patrimonial)
    inst = Instrumento()
    _aplicar(inst, dados)
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return instrumento_para_out(inst, date.today())


@router.put("/instrumentos/{inst_id}", response_model=InstrumentoOut)
def editar(inst_id: int, dados: InstrumentoIn, db: Session = Depends(get_db)):
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    _checar_patrimonio(db, dados.codigo_patrimonial, ignorar_id=inst_id)
    _aplicar(inst, dados)
    db.commit()
    db.refresh(inst)
    return instrumento_para_out(inst, date.today())
```

- [ ] **Step 4: Rodar e ver passar + regressão**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add backend/routers/instrumentos.py tests/test_api.py
git commit -m "feat: criar/editar instrumento + filtros familia/classe_prioridade"
```

---

## Task 8: Upload de foto e manual (TDD)

**Files:**
- Modify: `backend/routers/instrumentos.py`
- Test: `tests/test_api.py` (anexar)

- [ ] **Step 1: Escrever os testes que falham (anexar a `tests/test_api.py`)**

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_api.py -q -k upload`
Expected: FAIL — 404.

- [ ] **Step 3: Adicionar os endpoints de upload em `backend/routers/instrumentos.py`**

Adicione os imports no topo (junto aos existentes):
```python
from pathlib import Path
from fastapi import UploadFile, File
```
E ao final do arquivo:
```python
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"


def _salvar(inst_id: int, sufixo: str, conteudo: bytes, ext: str) -> str:
    destino_dir = UPLOAD_DIR / str(inst_id)
    destino_dir.mkdir(parents=True, exist_ok=True)
    nome = f"{sufixo}{ext}"
    (destino_dir / nome).write_bytes(conteudo)
    return f"uploads/{inst_id}/{nome}"


@router.post("/instrumentos/{inst_id}/foto", response_model=InstrumentoOut)
async def upload_foto(inst_id: int, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    if not (arquivo.content_type or "").startswith("image/"):
        raise HTTPException(status_code=415, detail="Envie um arquivo de imagem")
    ext = Path(arquivo.filename or "").suffix.lower() or ".img"
    inst.foto_path = _salvar(inst_id, "foto", await arquivo.read(), ext)
    db.commit()
    db.refresh(inst)
    return instrumento_para_out(inst, date.today())


@router.post("/instrumentos/{inst_id}/manual", response_model=InstrumentoOut)
async def upload_manual(inst_id: int, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    if (arquivo.content_type or "") != "application/pdf":
        raise HTTPException(status_code=415, detail="Envie um PDF")
    inst.manual_path = _salvar(inst_id, "manual", await arquivo.read(), ".pdf")
    db.commit()
    db.refresh(inst)
    return instrumento_para_out(inst, date.today())
```

- [ ] **Step 4: Rodar e ver passar + regressão**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add backend/routers/instrumentos.py tests/test_api.py
git commit -m "feat: upload de foto (imagem) e manual (PDF) por instrumento"
```

---

## Task 9: Frontend — helpers (app.js) + página de cadastro/edição

**Files:**
- Modify: `frontend/app.js`
- Create: `frontend/cadastro.html`

- [ ] **Step 1: Acrescentar helpers ao final de `frontend/app.js`**

```javascript
// ── Domínios e IGP (cadastro) ───────────────────────────────────────────────
SDK.post = async (path, body) => {
  const r = await fetch(API + path, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.status === 409) throw new Error("Código patrimonial já existe");
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
};
SDK.put = async (path, body) => {
  const r = await fetch(API + path, {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.status === 409) throw new Error("Código patrimonial já existe");
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
};

const CLASSE_LABEL = {
  MAXIMA: "Prioridade máxima", MEDIA: "Média", BAIXA: "Baixa",
  MUITO_BAIXA: "Muito baixa", NAO_CLASSIFICADO: "Não classificado",
};

// Espelha backend/criticidade.py
function calcIgpClient(fu, nc, ab, cm, ci) {
  const v = [fu, nc, ab, cm, ci];
  if (v.some(x => !x)) return { igp: null, classe: "NAO_CLASSIFICADO" };
  const igp = fu * 1 + nc * 2 + ab * 1 + cm * 2 + ci * 1;
  let classe = "MUITO_BAIXA";
  if (igp >= 18) classe = "MAXIMA";
  else if (igp >= 14) classe = "MEDIA";
  else if (igp >= 11) classe = "BAIXA";
  return { igp, classe };
}
```

- [ ] **Step 2: Criar `frontend/cadastro.html`**

```html
<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SisCalib · Cadastro</title>
<link rel="stylesheet" href="vendor/fonts.css">
<link rel="stylesheet" href="vendor/bootstrap-icons.min.css">
<link rel="stylesheet" href="vendor/xcmasm-govbr.css">
<link rel="stylesheet" href="siscalib.css">
<style>
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.fld{display:flex;flex-direction:column;gap:4px;margin-bottom:10px}
.fld label{font-size:12px;color:var(--tx2)}
fieldset{border:1px solid var(--bd);border-radius:var(--rl);padding:14px 16px;margin-bottom:14px}
legend{padding:0 6px;font-weight:600;color:var(--tx2);font-size:12px;text-transform:uppercase}
.req label::after{content:" *";color:var(--red)}
.igp-box{font-size:15px;font-weight:600;margin-top:8px}
</style>
</head><body class="app">
<script src="app.js"></script>
<main class="main">
  <a href="inventario.html" class="muted">&larr; Inventário</a>
  <h1 id="titulo" style="margin-top:8px">Novo Instrumento</h1>
  <form id="form">
    <fieldset><legend>Identificação</legend>
      <div class="grid2">
        <div class="fld req"><label>Equipamento</label><input name="equipamento" required></div>
        <div class="fld"><label>Código patrimonial</label><input name="codigo_patrimonial"></div>
        <div class="fld"><label>Código interno</label><input name="codigo_interno"></div>
        <div class="fld"><label>Número de série</label><input name="serial"></div>
        <div class="fld"><label>Marca</label><input name="marca"></div>
        <div class="fld"><label>Modelo</label><input name="modelo"></div>
      </div>
    </fieldset>
    <fieldset><legend>Classificação</legend>
      <div class="grid2">
        <div class="fld req"><label>Família metrológica</label><select name="familia_id" required></select></div>
        <div class="fld req"><label>Tipo</label><select name="tipo_id" required></select></div>
        <div class="fld"><label>Grandeza principal</label><select name="grandeza_id"><option value="">—</option></select></div>
        <div class="fld"><label>Unidade SI</label><select name="unidade_id"><option value="">—</option></select></div>
        <div class="fld"><label>Disciplina</label><select name="disciplina"><option value="">—</option><option>ELE</option><option>MEC</option></select></div>
      </div>
    </fieldset>
    <fieldset><legend>Especificação técnica</legend>
      <div class="grid2">
        <div class="fld"><label>Faixa mínima</label><input name="faixa_min" type="number" step="any"></div>
        <div class="fld"><label>Faixa máxima</label><input name="faixa_max" type="number" step="any"></div>
        <div class="fld"><label>Resolução</label><input name="resolucao" placeholder="0,01 mm"></div>
        <div class="fld"><label>EMP / exatidão</label><input name="emp" placeholder="±(0,5% + 2d)"></div>
        <div class="fld req"><label>Periodicidade (meses)</label><input name="ciclo_meses" type="number" value="12" required></div>
      </div>
    </fieldset>
    <fieldset><legend>Localização e estado</legend>
      <div class="grid2">
        <div class="fld"><label>Organização</label><input name="organizacao"></div>
        <div class="fld"><label>Unidade</label><input name="unidade_org"></div>
        <div class="fld"><label>Seção</label><input name="secao"></div>
        <div class="fld"><label>Bancada</label><input name="bancada"></div>
        <div class="fld"><label>Sistema</label><input name="sistema"></div>
        <div class="fld req"><label>Status operacional</label><select name="status_operacional" required>
          <option>ATIVO</option><option>EM_CALIBRACAO</option><option>EM_MANUTENCAO</option>
          <option>REPROVADO</option><option>BLOQUEADO</option><option>BAIXADO</option></select></div>
      </div>
    </fieldset>
    <fieldset><legend>Criticidade (IGP)</legend>
      <div class="grid2">
        <div class="fld"><label>Frequência de uso (FU)</label><select name="fu" class="igp"><option value="">—</option><option value="1">1 — esporádico</option><option value="2">2 — regular</option><option value="3">3 — diário</option></select></div>
        <div class="fld"><label>Necessidade crítica (NC)</label><select name="nc" class="igp"><option value="">—</option><option value="1">1 — baixo impacto</option><option value="2">2 — importante</option><option value="3">3 — crítico</option></select></div>
        <div class="fld"><label>Abundância/redundância (AB)</label><select name="ab" class="igp"><option value="">—</option><option value="1">1 — alta redundância</option><option value="2">2 — média</option><option value="3">3 — única</option></select></div>
        <div class="fld"><label>Criticidade metrológica (CM)</label><select name="cm" class="igp"><option value="">—</option><option value="1">1 — tolerância alta</option><option value="2">2 — moderada</option><option value="3">3 — baixa tolerância</option></select></div>
        <div class="fld"><label>Custo de indisponibilidade (CI)</label><select name="ci" class="igp"><option value="">—</option><option value="1">1 — mínimo</option><option value="2">2 — moderado</option><option value="3">3 — afeta operação</option></select></div>
      </div>
      <div class="igp-box" id="igpBox">IGP: — · <span class="muted">preencha as 5 variáveis</span></div>
    </fieldset>
    <div class="fld"><label>Observações</label><textarea name="observacoes" rows="2"></textarea></div>
    <button class="btn" type="submit">Salvar</button>
    <a class="btn ghost" href="inventario.html">Cancelar</a>
    <span id="erro" class="sev-erro" style="margin-left:10px"></span>
  </form>
</main>
<script>
montarShell("");
const form = document.getElementById("form");
const params = new URLSearchParams(location.search);
const editId = params.get("id");

function setSelect(sel, itens, valueKey, labelFn, keep) {
  const atual = keep ? sel.value : "";
  const head = sel.querySelector('option[value=""]') ? '<option value="">—</option>' : "";
  sel.innerHTML = head + itens.map(i => `<option value="${i[valueKey]}">${esc(labelFn(i))}</option>`).join("");
  if (atual) sel.value = atual;
}

async function carregarDominios(familiaId) {
  const d = await SDK.get("/dominios", familiaId ? { familia_id: familiaId } : null);
  if (!familiaId) setSelect(form.familia_id, d.familias, "id", i => i.nome);
  setSelect(form.tipo_id, d.tipos, "id", i => i.nome);
  setSelect(form.grandeza_id, d.grandezas, "id", i => i.nome);
  setSelect(form.unidade_id, d.unidades, "id", i => `${i.nome} (${i.simbolo || ""})`);
  return d;
}

function atualizarIgp() {
  const g = n => { const v = form[n].value; return v ? parseInt(v) : null; };
  const r = calcIgpClient(g("fu"), g("nc"), g("ab"), g("cm"), g("ci"));
  document.getElementById("igpBox").innerHTML = r.igp == null
    ? 'IGP: — · <span class="muted">preencha as 5 variáveis</span>'
    : `IGP: <b>${r.igp}</b> · ${CLASSE_LABEL[r.classe]}`;
}

(async () => {
  await carregarDominios(null);
  form.familia_id.onchange = () => carregarDominios(form.familia_id.value);
  form.querySelectorAll(".igp").forEach(s => s.onchange = atualizarIgp);

  if (editId) {
    document.getElementById("titulo").textContent = "Editar Instrumento";
    const i = await SDK.get("/instrumentos/" + editId);
    if (i.familia_id) { form.familia_id.value = i.familia_id; await carregarDominios(i.familia_id); }
    for (const [k, v] of Object.entries(i)) {
      if (form[k] && v !== null && v !== undefined) form[k].value = v;
    }
    form.status_operacional.value = i.status_operacional || "ATIVO";
    atualizarIgp();
  }
})();

form.onsubmit = async (e) => {
  e.preventDefault();
  document.getElementById("erro").textContent = "";
  const fd = new FormData(form);
  const body = {};
  for (const [k, v] of fd.entries()) {
    if (v === "") continue;
    body[k] = ["familia_id","tipo_id","grandeza_id","unidade_id","ciclo_meses","fu","nc","ab","cm","ci"].includes(k)
      ? parseInt(v) : (["faixa_min","faixa_max"].includes(k) ? parseFloat(v) : v);
  }
  try {
    const saved = editId ? await SDK.put("/instrumentos/" + editId, body)
                         : await SDK.post("/instrumentos", body);
    location.href = "ficha.html?id=" + saved.id;
  } catch (err) {
    document.getElementById("erro").textContent = err.message;
  }
};
</script></body></html>
```

- [ ] **Step 3: Verificar sintaxe e referências**

Run:
```bash
cd /home/luc/DEV_ERP/xCalibracao
python3 - <<'PY'
js=open('frontend/app.js').read()
print("app.js chaves:", js.count('{')==js.count('}'), "| SDK.post/put/calcIgpClient:",
      all(s in js for s in ["SDK.post","SDK.put","calcIgpClient"]))
html=open('frontend/cadastro.html').read()
print("cadastro refs app.js:", "app.js" in html, "| tem form:", 'id="form"' in html)
PY
```
Expected: tudo `True`.

- [ ] **Step 4: Commit**

```bash
git add frontend/app.js frontend/cadastro.html
git commit -m "feat: página de cadastro/edição com domínios encadeados e IGP ao vivo"
```

---

## Task 10: Frontend — ficha ampliada + filtros no inventário

**Files:**
- Modify: `frontend/ficha.html`
- Modify: `frontend/inventario.html`

- [ ] **Step 1: Substituir o `<script>` de `frontend/ficha.html`** (mantém o `<head>`/markup; adiciona campos novos, IGP, anexos e botão Editar)

Substitua o bloco `<main>...</main>` e o `<script>` por:
```html
<main class="main">
  <a href="inventario.html" class="muted">&larr; Inventário</a>
  <h1 id="titulo" style="margin-top:8px">Ficha do Instrumento</h1>
  <div id="status" style="margin-bottom:14px"></div>
  <a class="btn" id="btnEditar"><i class="bi bi-pencil"></i> Editar</a>
  <div class="card" style="margin-top:14px"><table><tbody id="campos"></tbody></table></div>
  <div id="anexos" class="card"></div>
</main>
<script>
montarShell("");
(async () => {
  const id = new URLSearchParams(location.search).get("id");
  const i = await SDK.get("/instrumentos/" + id);
  document.getElementById("btnEditar").href = "cadastro.html?id=" + id;
  document.getElementById("titulo").textContent =
    `${i.codigo_interno || i.codigo_patrimonial || "(sem código)"} — ${i.equipamento || ""}`;
  const classeLbl = { MAXIMA:"Prioridade máxima", MEDIA:"Média", BAIXA:"Baixa",
    MUITO_BAIXA:"Muito baixa", NAO_CLASSIFICADO:"Não classificado" };
  const div = i.divergencia_flag ? ' <span class="bdg amber">divergência flag×data</span>' : "";
  const igp = i.igp == null ? "" :
    ` · <span class="bdg slate">IGP ${i.igp} — ${classeLbl[i.classe_prioridade]}</span>`;
  document.getElementById("status").innerHTML = badgeStatus(i.status) +
    (i.dias_restantes != null ? ` <span class="muted">(${i.dias_restantes} dias)</span>` : "") +
    ` <span class="bdg slate">${i.status_operacional}</span>` + div + igp;
  const linhas = [
    ["Patrimônio", i.codigo_patrimonial], ["Série", i.serial],
    ["Marca", i.marca], ["Modelo", i.modelo],
    ["Família", i.familia_nome], ["Tipo", i.tipo_nome],
    ["Grandeza", i.grandeza_nome], ["Unidade", i.unidade_simbolo],
    ["Faixa", [i.faixa_min, i.faixa_max].some(v=>v!=null) ? `${i.faixa_min ?? ""} … ${i.faixa_max ?? ""}` : i.faixa],
    ["Resolução", i.resolucao], ["EMP", i.emp],
    ["Disciplina", i.disciplina], ["Sistema", i.sistema],
    ["Localização", [i.organizacao, i.unidade_org, i.secao, i.bancada].filter(Boolean).join(" → ")],
    ["Ciclo (meses)", i.ciclo_meses],
    ["Última calibração", fmtData(i.data_ultima_calibracao)],
    ["Validade", fmtData(i.data_validade)],
    ["Organização calibradora", i.organizacao_calibradora],
    ["Certificado", i.certificado_ref], ["Observações", i.observacoes],
  ];
  document.getElementById("campos").innerHTML = linhas.map(([k, v]) =>
    `<tr><th style="width:200px">${k}</th><td>${esc(v) || "—"}</td></tr>`).join("");
  document.getElementById("anexos").innerHTML =
    `<b>Anexos</b><div style="margin-top:8px">` +
    (i.foto_path ? `<a href="${i.foto_path}" target="_blank">Foto</a> ` : '<span class="muted">Sem foto</span> ') +
    (i.manual_path ? ` · <a href="${i.manual_path}" target="_blank">Manual (PDF)</a>` : ' · <span class="muted">Sem manual</span>') +
    `</div>`;
})();
</script>
```

- [ ] **Step 2: Atualizar `frontend/inventario.html` — adicionar filtros de família e classe**

Na `<div class="toolbar">`, após o select `#sistema`, adicione dois selects:
```html
    <select id="familia"><option value="">Família</option></select>
    <select id="classe"><option value="">Prioridade</option>
      <option value="MAXIMA">Máxima</option><option value="MEDIA">Média</option>
      <option value="BAIXA">Baixa</option><option value="MUITO_BAIXA">Muito baixa</option>
      <option value="NAO_CLASSIFICADO">Não classificado</option></select>
    <a class="btn" href="cadastro.html" style="margin-left:auto"><i class="bi bi-plus-lg"></i> Novo</a>
```
E no `<script>`, atualize `carregar()` e a inicialização. Substitua a função `carregar` e o bloco de init final por:
```javascript
async function carregar() {
  const params = {
    busca: busca.value, disciplina: disciplina.value, sistema: sistema.value,
    status: status.value, familia_id: familia.value, classe_prioridade: classe.value,
  };
  const r = await SDK.get("/instrumentos", params);
  cont.textContent = `${r.total} instrumento(s)`;
  document.querySelector("#tab tbody").innerHTML = r.itens.map(i => `
    <tr><td><a href="ficha.html?id=${i.id}">${esc(i.codigo_interno || i.codigo_patrimonial)}</a></td>
    <td>${esc(i.equipamento)}</td><td>${esc([i.marca, i.modelo].filter(Boolean).join(" "))}</td>
    <td>${esc(i.disciplina)}</td><td>${esc(i.sistema)}</td>
    <td>${fmtData(i.data_validade)}</td><td>${badgeStatus(i.status)}</td></tr>`).join("")
    || `<tr><td colspan="7" class="muted">Nada encontrado.</td></tr>`;
}
const busca = document.getElementById("busca"), disciplina = document.getElementById("disciplina"),
      sistema = document.getElementById("sistema"), status = document.getElementById("status"),
      familia = document.getElementById("familia"), classe = document.getElementById("classe"),
      cont = document.getElementById("cont");
[disciplina, sistema, status, familia, classe].forEach(e => e.onchange = carregar);
busca.oninput = () => { clearTimeout(timer); timer = setTimeout(carregar, 250); };
(async () => {
  const r = await SDK.get("/instrumentos");
  [...new Set(r.itens.map(i => i.sistema).filter(Boolean))].sort()
    .forEach(s => sistema.add(new Option(s, s)));
  const d = await SDK.get("/dominios");
  d.familias.forEach(f => familia.add(new Option(f.nome, f.id)));
  carregar();
})();
```
> Remova a versão antiga de `carregar()` e do bloco de init para não duplicar (`let timer;` no topo do script permanece).

- [ ] **Step 3: Verificar sintaxe**

Run:
```bash
cd /home/luc/DEV_ERP/xCalibracao
python3 - <<'PY'
for f in ["frontend/ficha.html","frontend/inventario.html"]:
    h=open(f).read()
    print(f, "| chaves <script> balanceadas:", h.count('{')==h.count('}'),
          "| sem dupla def carregar:", h.count("async function carregar")<=1)
PY
```
Expected: `True` em ambos; `carregar` definida uma única vez no inventário.

- [ ] **Step 4: Commit**

```bash
git add frontend/ficha.html frontend/inventario.html
git commit -m "feat: ficha ampliada (campos metrológicos + IGP + anexos) e filtros no inventário"
```

---

## Task 11: Verificação end-to-end + entrypoint + Docker

**Files:**
- Modify: `entrypoint.sh`
- Modify: `README.md`

- [ ] **Step 1: Atualizar `entrypoint.sh` para semear domínios após migrar**

```bash
#!/bin/sh
set -e
alembic upgrade head
python -m backend.dominios
exec uvicorn backend.main:app --host 0.0.0.0 --port 8080
```

- [ ] **Step 2: Acrescentar nota ao `README.md`** (após a seção "Importar o inventário")

```markdown
## Cadastro metrológico
- Os domínios (famílias RBC/INMETRO, tipos, grandezas, unidades) são semeados no startup
  (`python -m backend.dominios`, idempotente).
- Use **Novo** no Inventário (ou **Editar** na ficha) para preencher: classificação, faixa,
  resolução/EMP, localização, estado operacional, anexos (foto/PDF) e o IGP (5 variáveis 1–3).
- O **IGP** (Índice Global de Prioridade) é calculado automaticamente: faixas 18–21 máxima,
  14–17 média, 11–13 baixa, 7–10 muito baixa.
```

- [ ] **Step 3: Rodar a suíte completa**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS (todos — fatia anterior + novos).

- [ ] **Step 4: Build e verificação end-to-end no Docker**

Run:
```bash
cd /home/luc/DEV_ERP/xCalibracao
docker build -t siscalib:latest .
docker rm -f siscalib 2>/dev/null
docker run -d --name siscalib -p 8080:8080 -v siscalib_data:/data siscalib:latest
sleep 5
echo "health:"; curl -s localhost:8080/api/v1/health; echo
echo "dominios (familias):"; curl -s localhost:8080/api/v1/dominios | python3 -c "import sys,json; print(len(json.load(sys.stdin)['familias']),'familias')"
echo "criar instrumento:"; curl -s -X POST localhost:8080/api/v1/instrumentos -H "Content-Type: application/json" -d '{"equipamento":"TESTE E2E","familia_id":4,"tipo_id":1,"ciclo_meses":12,"status_operacional":"ATIVO","fu":3,"nc":3,"ab":2,"cm":3,"ci":2}' | python3 -c "import sys,json; o=json.load(sys.stdin); print('id',o['id'],'igp',o['igp'],o['classe_prioridade'],o['familia_nome'])"
echo "paginas:"; for p in cadastro.html ficha.html inventario.html; do echo "$p -> $(curl -s -o /dev/null -w '%{http_code}' localhost:8080/$p)"; done
```
Expected: health ok; 15 famílias; criação retorna `igp 19 MAXIMA Eletricidade e Magnetismo` (familia_id=4 é "Eletricidade e Magnetismo" pela ordem do seed; ajuste o id se o seed numerar diferente — confira via `/api/v1/dominios`); páginas 200. Os 496 instrumentos do volume permanecem.

- [ ] **Step 5: Parar o container de teste**

Run: `docker rm -f siscalib`

- [ ] **Step 6: Commit**

```bash
git add entrypoint.sh README.md
git commit -m "feat: seed de domínios no entrypoint + doc do cadastro metrológico"
```

---

## Self-Review (autor do plano)

**Cobertura do spec:**
- §2 tabelas de domínio + seed → Tasks 2, 4. ✓
- §3 novas colunas + status_operacional + anexos → Tasks 2, 3. ✓
- §4 motor IGP (faixas 7–21) → Task 1; aplicado no output → Task 5. ✓
- §5 migração aditiva + índice único parcial → Task 3; GET /dominios → Task 6; POST/PUT + obrigatórios + 409 + filtros → Task 7; upload foto/manual + /uploads → Tasks 6, 8; cadastro.html + ficha + inventário → Tasks 9, 10. ✓
- §6 testes (IGP fronteiras, domínios idempotente, criar/editar/409, upload tipos, regressão) → Tasks 1,4,7,8,11. ✓

**Placeholder scan:** sem TBD/TODO; todo passo de código mostra o código. O ajuste do `familia_id=4` no e2e (Task 11) é verificável via `/dominios`, não um placeholder.

**Consistência de tipos/nomes:** `calcular_igp`/`ClassePrioridade`/`ResultadoIGP` (Task 1) usados em `servico.py` (Task 5); `InstrumentoIn`/`InstrumentoOut`/`DominiosOut`/`ItemDominio` (Task 5) usados em routers (6,7) e frontend (9,10); valores de `classe_prioridade` (MAXIMA/MEDIA/BAIXA/MUITO_BAIXA/NAO_CLASSIFICADO) idênticos em `criticidade.py`, `app.js` (`calcIgpClient`/`CLASSE_LABEL`) e nos selects de `inventario.html`; `status_operacional` enum idêntico em `models.py`, schema (string) e selects do `cadastro.html`. ✓

**Risco conhecido:** o `familia_id`/`tipo_id` concretos dependem da ordem do seed; os testes resolvem por nome via `/dominios` (não por id fixo), e o e2e instrui a conferir via `/dominios`. ✓
