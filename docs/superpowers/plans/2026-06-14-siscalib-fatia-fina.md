# SisCalib — Fatia Fina Vertical — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar um app standalone rodando de ponta a ponta que importa o CSV real de inventário (~496 instrumentos), calcula status/validade automaticamente e mostra inventário, painel de alertas e dashboard.

**Architecture:** Container único FastAPI (Python 3.12) servindo API REST `/api/v1` + HTML/JS vanilla estático. Persistência SQLite via SQLAlchemy 2.0 + Alembic. Status de calibração nunca é gravado — é derivado por uma função pura a cada request. Frontend reaproveita a camada visual do cmasm.erp (fontes, bootstrap-icons, govbr CSS, tokens de cor) com render próprio enxuto.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, SQLite, pytest, httpx (TestClient), HTML/CSS/JS vanilla, Docker.

**Spec de referência:** `docs/superpowers/specs/2026-06-14-siscalib-fatia-fina-design.md`

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `requirements.txt` | Dependências Python |
| `backend/__init__.py` | Marca pacote |
| `backend/db.py` | Engine SQLAlchemy, `SessionLocal`, `Base`, dependency `get_db` |
| `backend/calibracao.py` | **Motor puro** de status/validade (sem I/O, sem DB) |
| `backend/parsing.py` | Helpers puros texto→valor (cabeçalho, datas, moeda, ciclo) |
| `backend/models.py` | ORM `Instrumento`, enum `Disciplina` |
| `backend/importacao.py` | `processar_csv` (parse + validação dry-run, sem DB) |
| `backend/schemas.py` | Modelos Pydantic de entrada/saída da API |
| `backend/servico.py` | Monta `InstrumentoOut` aplicando o motor; lista com status |
| `backend/routers/instrumentos.py` | `GET /instrumentos`, `GET /instrumentos/{id}` |
| `backend/routers/importacao.py` | `POST /importacao/preview`, `POST /importacao/commit` |
| `backend/routers/dashboard.py` | `GET /dashboard/kpis`, `GET /alertas` |
| `backend/main.py` | App FastAPI: inclui routers, monta estáticos |
| `alembic/`, `alembic.ini` | Migrações versionadas |
| `frontend/vendor/` | Assets COPIADOS do cmasm.erp (fontes, ícones, govbr) |
| `frontend/siscalib.css` | CSS próprio (shell, cards, tabela) com tokens do cmasm.erp |
| `frontend/app.js` | SDK HTTP + helpers de render + init por página |
| `frontend/index.html` | Dashboard |
| `frontend/inventario.html` | Tabela com busca/filtros |
| `frontend/alertas.html` | Painel de alertas + export CSV |
| `frontend/importar.html` | Upload + relatório dry-run |
| `frontend/ficha.html` | Ficha read-only |
| `tests/fixtures/amostra_inventario.csv` | Amostra real do CSV para testes |
| `tests/test_calibracao.py` | Testes do motor |
| `tests/test_parsing.py` | Testes dos helpers |
| `tests/test_importacao.py` | Testes do importador |
| `tests/test_api.py` | Smoke tests dos endpoints |
| `Dockerfile`, `entrypoint.sh` | Build + start (migra e sobe uvicorn) |
| `README.md` | Como rodar, importar e fazer backup |

> Módulos `parsing.py` e `servico.py` são decomposições auxiliares (não citadas no spec) para manter cada arquivo focado e testável — consistente com o princípio de arquivos pequenos.

---

## Task 1: Scaffolding e dependências

**Files:**
- Create: `requirements.txt`
- Create: `backend/__init__.py`
- Create: `backend/db.py`

- [ ] **Step 1: Criar `requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.34
alembic==1.13.2
pydantic==2.7.4
python-multipart==0.0.9
pytest==8.3.2
httpx==0.27.2
```

- [ ] **Step 2: Criar ambiente e instalar**

Run:
```bash
cd /home/luc/DEV_ERP/xCalibracao
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
echo ".venv/" >> .gitignore
echo "data/*.db" >> .gitignore
```
Expected: instala sem erro.

- [ ] **Step 3: Criar `backend/__init__.py`**

```python
```
(arquivo vazio)

- [ ] **Step 4: Criar `backend/db.py`**

```python
"""Configuração do banco SQLite via SQLAlchemy 2.0."""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATA_DIR = Path(os.getenv("SISCALIB_DATA", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_URL = os.getenv("SISCALIB_DB_URL", f"sqlite:///{DATA_DIR / 'siscalib.db'}")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Verificar import**

Run: `.venv/bin/python -c "import backend.db; print('ok', backend.db.DB_URL)"`
Expected: imprime `ok sqlite:///data/siscalib.db`.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt backend/ .gitignore
git commit -m "chore: scaffolding do backend (deps + db.py)"
```

---

## Task 2: Motor de status/validade (TDD)

**Files:**
- Create: `backend/calibracao.py`
- Test: `tests/test_calibracao.py`

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_calibracao.py`:
```python
from datetime import date
from backend.calibracao import calcular_status, StatusCalibracao

HOJE = date(2026, 6, 14)


def test_baixado_por_flag_sem_condicoes():
    r = calcular_status(date(2027, 1, 1), "SEM CONDIÇOES DE USO", HOJE)
    assert r.status == StatusCalibracao.BAIXADO
    assert r.dias_restantes is None


def test_baixado_por_flag_inativo():
    assert calcular_status(None, "inativo", HOJE).status == StatusCalibracao.BAIXADO


def test_sem_data():
    r = calcular_status(None, "CALIBRADO", HOJE)
    assert r.status == StatusCalibracao.SEM_DATA
    assert r.dias_restantes is None


def test_vencido():
    r = calcular_status(date(2026, 6, 1), "DESCALIBRADO", HOJE)
    assert r.status == StatusCalibracao.VENCIDO
    assert r.dias_restantes == -13


def test_a_vencer_7():
    assert calcular_status(date(2026, 6, 20), "CALIBRADO", HOJE).status == StatusCalibracao.A_VENCER_7


def test_a_vencer_30():
    assert calcular_status(date(2026, 7, 10), "CALIBRADO", HOJE).status == StatusCalibracao.A_VENCER_30


def test_a_vencer_60():
    assert calcular_status(date(2026, 8, 10), "CALIBRADO", HOJE).status == StatusCalibracao.A_VENCER_60


def test_valido():
    r = calcular_status(date(2027, 1, 1), "CALIBRADO", HOJE)
    assert r.status == StatusCalibracao.VALIDO
    assert r.dias_restantes == 201


def test_limite_exato_hoje_eh_a_vencer_7():
    assert calcular_status(HOJE, "CALIBRADO", HOJE).status == StatusCalibracao.A_VENCER_7


def test_divergencia_descalibrado_mas_data_valida():
    r = calcular_status(date(2027, 1, 1), "DESCALIBRADO", HOJE)
    assert r.status == StatusCalibracao.VALIDO
    assert r.divergencia_flag is True


def test_divergencia_calibrado_mas_vencido():
    r = calcular_status(date(2026, 1, 1), "CALIBRADO", HOJE)
    assert r.status == StatusCalibracao.VENCIDO
    assert r.divergencia_flag is True


def test_sem_divergencia_quando_coerente():
    assert calcular_status(date(2027, 1, 1), "CALIBRADO", HOJE).divergencia_flag is False
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_calibracao.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.calibracao'`.

- [ ] **Step 3: Implementar `backend/calibracao.py`**

```python
"""Motor puro de status/validade de calibração. Sem I/O, sem DB."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from enum import Enum

LIMIAR_7 = 7
LIMIAR_30 = 30
LIMIAR_60 = 60


class StatusCalibracao(str, Enum):
    VALIDO = "VALIDO"
    A_VENCER_60 = "A_VENCER_60"
    A_VENCER_30 = "A_VENCER_30"
    A_VENCER_7 = "A_VENCER_7"
    VENCIDO = "VENCIDO"
    SEM_DATA = "SEM_DATA"
    BAIXADO = "BAIXADO"


@dataclass(frozen=True)
class ResultadoStatus:
    status: StatusCalibracao
    dias_restantes: int | None
    divergencia_flag: bool


def _categoria_flag(flag: str | None) -> str | None:
    """Normaliza o texto bruto da coluna de status do CSV."""
    if not flag:
        return None
    t = flag.strip().upper()
    if t.startswith("SEM CONDI") or t == "INATIVO":
        return "BAIXADO"
    if t.startswith("DESCAL"):
        return "DESCALIBRADO"
    if t.startswith("CALIBRAD"):
        return "CALIBRADO"
    return None


def calcular_status(
    data_validade: date | None, flag_origem: str | None, hoje: date
) -> ResultadoStatus:
    cat = _categoria_flag(flag_origem)

    if cat == "BAIXADO":
        return ResultadoStatus(StatusCalibracao.BAIXADO, None, False)

    if data_validade is None:
        return ResultadoStatus(StatusCalibracao.SEM_DATA, None, False)

    dias = (data_validade - hoje).days
    if dias < 0:
        status = StatusCalibracao.VENCIDO
    elif dias <= LIMIAR_7:
        status = StatusCalibracao.A_VENCER_7
    elif dias <= LIMIAR_30:
        status = StatusCalibracao.A_VENCER_30
    elif dias <= LIMIAR_60:
        status = StatusCalibracao.A_VENCER_60
    else:
        status = StatusCalibracao.VALIDO

    divergencia = (
        (cat == "DESCALIBRADO" and status != StatusCalibracao.VENCIDO)
        or (cat == "CALIBRADO" and status == StatusCalibracao.VENCIDO)
    )
    return ResultadoStatus(status, dias, divergencia)
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_calibracao.py -q`
Expected: PASS (12 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/calibracao.py tests/test_calibracao.py
git commit -m "feat: motor puro de status/validade de calibração"
```

---

## Task 3: Helpers de parsing (TDD)

**Files:**
- Create: `backend/parsing.py`
- Test: `tests/test_parsing.py`

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_parsing.py`:
```python
from datetime import date
from decimal import Decimal
from backend.parsing import (
    normalizar_cabecalho, parse_data, parse_moeda, parse_ciclo,
)


def test_normalizar_cabecalho_remove_espacos_e_quebras():
    assert normalizar_cabecalho("MARCA ") == "marca"
    assert normalizar_cabecalho("UNIDADE\nRANGE") == "unidade range"
    assert normalizar_cabecalho("CERTIFICADO  ") == "certificado"
    assert normalizar_cabecalho("CUSTO CONTRAT (R$)") == "custo contrat (r$)"


def test_parse_data_mm_dd_yy():
    d, aviso = parse_data("09/13/25")
    assert d == date(2025, 9, 13)
    assert aviso is None


def test_parse_data_dd_mm_quando_primeiro_maior_que_12():
    d, aviso = parse_data("26/07/24")
    assert d == date(2024, 7, 26)
    assert "DD/MM" in aviso


def test_parse_data_value_error_marcador():
    d, aviso = parse_data("#VALUE!")
    assert d is None
    assert aviso is not None


def test_parse_data_vazia():
    assert parse_data("") == (None, None)


def test_parse_data_ilegivel():
    d, aviso = parse_data("xx/yy/zz")
    assert d is None and aviso is not None


def test_parse_data_seculo():
    assert parse_data("01/01/85")[0] == date(1985, 1, 1)
    assert parse_data("01/01/24")[0] == date(2024, 1, 1)


def test_parse_moeda():
    assert parse_moeda("R$ 3,104.95") == Decimal("3104.95")
    assert parse_moeda("R$ 70.00") == Decimal("70.00")
    assert parse_moeda("") is None
    assert parse_moeda("lixo") is None


def test_parse_ciclo():
    assert parse_ciclo("12") == 12
    assert parse_ciclo("") is None
    assert parse_ciclo("abc") is None
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_parsing.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.parsing'`.

- [ ] **Step 3: Implementar `backend/parsing.py`**

```python
"""Helpers puros de normalização de texto do CSV legado."""
from __future__ import annotations
import re
from datetime import date
from decimal import Decimal, InvalidOperation


def normalizar_cabecalho(nome: str) -> str:
    """lowercase, colapsa espaços/quebras de linha, remove bordas."""
    return re.sub(r"\s+", " ", (nome or "").replace("\n", " ")).strip().lower()


def _expandir_ano(aa: int) -> int:
    if aa >= 100:
        return aa
    return 2000 + aa if aa <= 69 else 1900 + aa


def parse_data(texto: str) -> tuple[date | None, str | None]:
    """Devolve (date, aviso). Lida com MM/DD/YY e DD/MM/YY ambíguos do legado."""
    t = (texto or "").strip()
    if not t:
        return (None, None)
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", t)
    if not m:
        return (None, f"data ilegível: {t!r}")
    a, b, c = int(m.group(1)), int(m.group(2)), _expandir_ano(int(m.group(3)))
    aviso = None
    if a > 12 and b <= 12:
        dia, mes = a, b
        aviso = "data interpretada como DD/MM"
    elif a <= 12:
        mes, dia = a, b
    else:
        return (None, f"data ambígua/ilegível: {t!r}")
    try:
        return (date(c, mes, dia), aviso)
    except ValueError:
        return (None, f"data inválida: {t!r}")


def parse_moeda(texto: str) -> Decimal | None:
    t = (texto or "").strip()
    if not t:
        return None
    limpo = t.replace("R$", "").replace(" ", "").replace(",", "")
    try:
        return Decimal(limpo)
    except (InvalidOperation, ValueError):
        return None


def parse_ciclo(texto: str) -> int | None:
    t = (texto or "").strip()
    try:
        return int(t)
    except (ValueError, TypeError):
        return None
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_parsing.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/parsing.py tests/test_parsing.py
git commit -m "feat: helpers de parsing do CSV legado (datas, moeda, cabeçalho)"
```

---

## Task 4: Modelo ORM e migração Alembic

**Files:**
- Create: `backend/models.py`
- Create: `alembic.ini`, `alembic/env.py` (via `alembic init`)

- [ ] **Step 1: Criar `backend/models.py`**

```python
"""ORM do SisCalib (fatia fina: apenas Instrumento)."""
from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import String, Integer, Date, DateTime, Numeric, Enum, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.db import Base


class Disciplina(str, enum.Enum):
    ELE = "ELE"
    MEC = "MEC"


class Instrumento(Base):
    __tablename__ = "instrumento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_interno: Mapped[str | None] = mapped_column(String, index=True)
    serial: Mapped[str | None] = mapped_column(String, index=True)
    equipamento: Mapped[str | None] = mapped_column(String)
    marca: Mapped[str | None] = mapped_column(String)
    modelo: Mapped[str | None] = mapped_column(String)
    faixa: Mapped[str | None] = mapped_column(String)
    unidade_faixa: Mapped[str | None] = mapped_column(String)
    disciplina: Mapped[Disciplina | None] = mapped_column(Enum(Disciplina))
    sistema: Mapped[str | None] = mapped_column(String, index=True)
    ciclo_meses: Mapped[int] = mapped_column(Integer, default=12)
    data_ultima_calibracao: Mapped[Date | None] = mapped_column(Date)
    data_validade: Mapped[Date | None] = mapped_column(Date)
    flag_origem: Mapped[str | None] = mapped_column(String)
    organizacao_calibradora: Mapped[str | None] = mapped_column(String)
    local_calibracao: Mapped[str | None] = mapped_column(String)
    custo_estimado: Mapped[float | None] = mapped_column(Numeric(12, 2))
    custo_contratado: Mapped[float | None] = mapped_column(Numeric(12, 2))
    certificado_ref: Mapped[str | None] = mapped_column(String)
    observacoes: Mapped[str | None] = mapped_column(String)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 2: Inicializar Alembic**

Run: `.venv/bin/alembic init alembic`
Expected: cria `alembic/` e `alembic.ini`.

- [ ] **Step 3: Configurar `alembic/env.py`**

Substituir o miolo de configuração de `target_metadata` e URL. No topo do `env.py`, após os imports existentes, adicionar:
```python
import os, sys
sys.path.insert(0, os.getcwd())
from backend.db import Base, DB_URL
from backend import models  # noqa: F401  (registra as tabelas)
target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", DB_URL)
```
E garantir que a linha `target_metadata = None` original seja removida/substituída pela acima.

- [ ] **Step 4: Gerar a migração inicial**

Run: `.venv/bin/alembic revision --autogenerate -m "instrumento"`
Expected: cria arquivo em `alembic/versions/` com `op.create_table('instrumento', ...)` contendo as colunas do Step 1 (verifique a presença de `codigo_interno`, `data_validade`, `flag_origem`, `ciclo_meses`).

- [ ] **Step 5: Aplicar a migração**

Run: `.venv/bin/alembic upgrade head && .venv/bin/python -c "import sqlite3; print([r[1] for r in sqlite3.connect('data/siscalib.db').execute('PRAGMA table_info(instrumento)')])"`
Expected: lista de colunas incluindo `codigo_interno`, `serial`, `data_validade`, `flag_origem`, `ciclo_meses`.

- [ ] **Step 6: Commit**

```bash
git add backend/models.py alembic.ini alembic/
git commit -m "feat: modelo Instrumento + migração Alembic inicial"
```

---

## Task 5: Importador `processar_csv` (TDD com fixture real)

**Files:**
- Create: `tests/fixtures/amostra_inventario.csv`
- Create: `backend/importacao.py`
- Test: `tests/test_importacao.py`

- [ ] **Step 1: Criar a fixture com dados reais**

`tests/fixtures/amostra_inventario.csv` (conteúdo exato — preserva o `\n` dentro de "UNIDADE\nRANGE" e os casos difíceis):
```
ELE/MEC,EQUIPAMENTO,MARCA ,MODELO,RANGE,"UNIDADE
RANGE",COD INTERNO,SERIAL,DIVISÃO,PS,ENTRADA OF ET,SAÍDA/CAL,RETORNO CAL,ULTIMA CALIBRAÇÃO,CICLO CALIBRAÇÃO,PRÓXIMA CALIBRAÇÃO,VALIDADE CALIBRAÇÃO,CERTIFICADO  ,SITUAÇÃO,COMENTÁRIOS,CUSTO ESTIMADO,CUSTO CONTRAT (R$),PAGAMENTO,LOCAL CALIBRAÇÃO,item,CERTIFICADO 
ELE ,ANALISADOR DE ESPECTRO,ROHDE&SCHWARZ,FSL18,,,MAN-EXO-ATENA-004,102412,EXOCET,CMS 004/2025,08/21/24,08/22/24,09/16/24,09/13/24,12,09/13/25,DESCALIBRADO,certificado nº 2142090/2024,CMS,EM CALIBRACAO,"R$ 3,104.95","R$ 1,450.51",,CMS,,R101809Z/DEZ/2025 
MEC,TORQUÍMETRO ,FALCOM,40 – 200 Nm S315 DA,265.0,Nm,MAN-EXO-MEC-015,S315DA,EXOCET,MQT LT2 / 2026,07/15/24,08/20/24,11/10/25,11/06/25,12,11/06/26,CALIBRADO,222199/24,CMASM,,R$ 100.00,R$ 70.00,,MQT 129/2025,35,
MEC,TORQUÍMETRO ,,STURTEVANT RICHMONT (CAL-36) 2-36 lbs,4.0,Nm,CMASM-IDM-T46-054,104-A,MK-46,,07/15/24,08/20/24,08/12/24,26/07/24,12,#VALUE!,#VALUE!,SEM ETIQUETE/219018/24,CMASM,,R$ 100.00,R$ 70.00,,MQT 129/2025,,
MEC,TORQUÍMETRO ,CMKP,1 - 4 dNm ,0.4,Nm,MAN-EXO-MEC-001,,EXOCET,MQT LT2 / 2026,,,,,12,01/01/24,DESCALIBRADO,0835/2022,CMASM,,R$ 100.00,R$ 70.00,,MQT 129/2025,35,
MEC,DINAMÔMETRO DIGITAL,,"SCALE, DIGITAL READOUT 2500 LB",1134,Kg ,CMASM-IDM-T48-269,8115,MK-48,,12/15/25,12/15/25,01/23/26,01/23/26,12,01/23/27,SEM CONDIÇOES DE USO,,,NOVO PREGÃO,R$ 228.00,R$ 228.00,,MQT 129/2025,,
,,,,,,,,,,,,,,,,,,,,,,,,,
```
> A última linha é vazia (deve ser ignorada). A 4ª linha de dados tem `#VALUE!` nas duas colunas de data/validade (gera avisos). A 5ª tem flag "SEM CONDIÇOES DE USO" (vira BAIXADO).

- [ ] **Step 2: Escrever os testes que falham**

`tests/test_importacao.py`:
```python
from datetime import date
from pathlib import Path
from backend.importacao import processar_csv

FIXTURE = Path("tests/fixtures/amostra_inventario.csv").read_bytes()


def _proc():
    return processar_csv(FIXTURE)


def test_ignora_linha_vazia():
    res = _proc()
    # 5 linhas de dados úteis (a 6ª é vazia)
    assert res["totais"]["total_linhas"] == 5


def test_mapeia_campos_por_conteudo():
    linha = _proc()["linhas"][0]["dados"]
    assert linha["equipamento"] == "ANALISADOR DE ESPECTRO"
    assert linha["disciplina"] == "ELE"
    assert linha["sistema"] == "EXOCET"
    assert linha["organizacao_calibradora"] == "CMS"        # SITUAÇÃO -> org
    assert linha["flag_origem"] == "DESCALIBRADO"           # VALIDADE -> flag
    assert linha["data_validade"] == date(2025, 9, 13)      # PRÓXIMA -> validade
    assert linha["data_ultima_calibracao"] == date(2024, 9, 13)
    assert linha["ciclo_meses"] == 12
    assert str(linha["custo_estimado"]) == "3104.95"


def test_marca_value_gera_aviso():
    linha = next(l for l in _proc()["linhas"]
                 if l["dados"]["codigo_interno"] == "CMASM-IDM-T46-054")
    assert linha["dados"]["data_validade"] is None
    assert any(p["severidade"] == "aviso" for p in linha["problemas"])


def test_sem_serial_nao_eh_erro():
    linha = next(l for l in _proc()["linhas"]
                 if l["dados"]["codigo_interno"] == "MAN-EXO-MEC-001")
    assert all(p["severidade"] != "erro" for p in linha["problemas"])


def test_totais_somam():
    t = _proc()["totais"]
    assert t["validas"] + t["com_erro"] == t["total_linhas"]
```

- [ ] **Step 3: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_importacao.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.importacao'`.

- [ ] **Step 4: Implementar `backend/importacao.py`**

```python
"""Parser + validação dry-run do CSV legado. Não toca no banco."""
from __future__ import annotations
import csv
import io
from backend.parsing import (
    normalizar_cabecalho, parse_data, parse_moeda, parse_ciclo,
)

# cabeçalho normalizado -> campo do modelo
MAPA_COLUNAS = {
    "ele/mec": "disciplina",
    "equipamento": "equipamento",
    "marca": "marca",
    "modelo": "modelo",
    "range": "faixa",
    "unidade range": "unidade_faixa",
    "cod interno": "codigo_interno",
    "serial": "serial",
    "divisão": "sistema",
    "ciclo calibração": "ciclo_meses",
    "ultima calibração": "data_ultima_calibracao",
    "última calibração": "data_ultima_calibracao",
    "próxima calibração": "data_validade",
    "validade calibração": "flag_origem",
    "situação": "organizacao_calibradora",
    "local calibração": "local_calibracao",
    "custo estimado": "custo_estimado",
    "custo contrat (r$)": "custo_contratado",
    "certificado": "certificado_ref",
    "comentários": "observacoes",
}
CAMPOS_DATA = {"data_ultima_calibracao", "data_validade"}
CAMPOS_MOEDA = {"custo_estimado", "custo_contratado"}


def _decodificar(conteudo: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return conteudo.decode(enc)
        except UnicodeDecodeError:
            continue
    return conteudo.decode("utf-8", errors="replace")


def _mapa_indices(cabecalho: list[str]) -> dict[str, int]:
    """campo -> índice da coluna. Para campos repetidos (certificado), fica o 1º."""
    indices: dict[str, int] = {}
    for i, bruto in enumerate(cabecalho):
        campo = MAPA_COLUNAS.get(normalizar_cabecalho(bruto))
        if campo and campo not in indices:
            indices[campo] = i
    return indices


def processar_csv(conteudo: bytes) -> dict:
    texto = _decodificar(conteudo)
    leitor = list(csv.reader(io.StringIO(texto)))
    if not leitor:
        return {"totais": {"total_linhas": 0, "validas": 0, "com_aviso": 0, "com_erro": 0}, "linhas": []}

    indices = _mapa_indices(leitor[0])
    linhas_saida = []
    validas = com_aviso = com_erro = 0

    for numero, bruto in enumerate(leitor[1:], start=2):
        if not any(c.strip() for c in bruto):
            continue  # linha totalmente vazia

        dados: dict = {}
        problemas: list[dict] = []

        for campo, i in indices.items():
            valor = bruto[i].strip() if i < len(bruto) else ""
            if campo in CAMPOS_DATA:
                d, aviso = parse_data(valor)
                dados[campo] = d
                if aviso:
                    problemas.append({"severidade": "aviso", "campo": campo, "mensagem": aviso})
            elif campo in CAMPOS_MOEDA:
                dados[campo] = parse_moeda(valor)
            elif campo == "ciclo_meses":
                c = parse_ciclo(valor)
                if c is None:
                    dados[campo] = 12
                    problemas.append({"severidade": "aviso", "campo": campo,
                                      "mensagem": "ciclo ausente; assumido 12 meses"})
                else:
                    dados[campo] = c
            elif campo == "disciplina":
                v = valor.upper()
                dados[campo] = v if v in ("ELE", "MEC") else None
            else:
                dados[campo] = valor or None

        # validação de severidade
        if not dados.get("equipamento") and not dados.get("codigo_interno"):
            problemas.append({"severidade": "erro", "campo": "linha",
                              "mensagem": "linha sem equipamento e sem código interno"})

        # divergência flag x data
        flag = (dados.get("flag_origem") or "").upper()
        val = dados.get("data_validade")
        if flag.startswith("DESCAL") and val is not None:
            from datetime import date as _d  # comparação informativa apenas
            problemas.append({"severidade": "aviso", "campo": "flag_origem",
                              "mensagem": "marcado DESCALIBRADO mas possui data de validade"})

        tem_erro = any(p["severidade"] == "erro" for p in problemas)
        tem_aviso = any(p["severidade"] == "aviso" for p in problemas)
        if tem_erro:
            com_erro += 1
        else:
            validas += 1
            if tem_aviso:
                com_aviso += 1

        linhas_saida.append({"numero": numero, "dados": dados, "problemas": problemas})

    total = len(linhas_saida)
    return {
        "totais": {"total_linhas": total, "validas": validas,
                   "com_aviso": com_aviso, "com_erro": com_erro},
        "linhas": linhas_saida,
    }
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_importacao.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/importacao.py tests/test_importacao.py tests/fixtures/
git commit -m "feat: importador dry-run do CSV legado com validação por severidade"
```

---

## Task 6: Schemas Pydantic e serviço de status

**Files:**
- Create: `backend/schemas.py`
- Create: `backend/servico.py`
- Test: adicionar a `tests/test_importacao.py` (reuso) — não necessário; cobre-se via API na Task 9.

- [ ] **Step 1: Criar `backend/schemas.py`**

```python
"""Modelos de entrada/saída da API."""
from __future__ import annotations
from datetime import date
from pydantic import BaseModel


class InstrumentoOut(BaseModel):
    id: int
    codigo_interno: str | None
    serial: str | None
    equipamento: str | None
    marca: str | None
    modelo: str | None
    faixa: str | None
    unidade_faixa: str | None
    disciplina: str | None
    sistema: str | None
    ciclo_meses: int
    data_ultima_calibracao: date | None
    data_validade: date | None
    flag_origem: str | None
    organizacao_calibradora: str | None
    local_calibracao: str | None
    custo_estimado: float | None
    custo_contratado: float | None
    certificado_ref: str | None
    observacoes: str | None
    # derivados
    status: str
    dias_restantes: int | None
    divergencia_flag: bool


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
```

- [ ] **Step 2: Criar `backend/servico.py`**

```python
"""Aplica o motor de status sobre instrumentos do banco."""
from __future__ import annotations
from datetime import date
from backend.calibracao import calcular_status
from backend.models import Instrumento
from backend.schemas import InstrumentoOut


def instrumento_para_out(inst: Instrumento, hoje: date) -> InstrumentoOut:
    r = calcular_status(inst.data_validade, inst.flag_origem, hoje)
    return InstrumentoOut(
        id=inst.id,
        codigo_interno=inst.codigo_interno,
        serial=inst.serial,
        equipamento=inst.equipamento,
        marca=inst.marca,
        modelo=inst.modelo,
        faixa=inst.faixa,
        unidade_faixa=inst.unidade_faixa,
        disciplina=inst.disciplina.value if inst.disciplina else None,
        sistema=inst.sistema,
        ciclo_meses=inst.ciclo_meses,
        data_ultima_calibracao=inst.data_ultima_calibracao,
        data_validade=inst.data_validade,
        flag_origem=inst.flag_origem,
        organizacao_calibradora=inst.organizacao_calibradora,
        local_calibracao=inst.local_calibracao,
        custo_estimado=float(inst.custo_estimado) if inst.custo_estimado is not None else None,
        custo_contratado=float(inst.custo_contratado) if inst.custo_contratado is not None else None,
        certificado_ref=inst.certificado_ref,
        observacoes=inst.observacoes,
        status=r.status.value,
        dias_restantes=r.dias_restantes,
        divergencia_flag=r.divergencia_flag,
    )
```

- [ ] **Step 3: Verificar import**

Run: `.venv/bin/python -c "import backend.schemas, backend.servico; print('ok')"`
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add backend/schemas.py backend/servico.py
git commit -m "feat: schemas da API e serviço de aplicação de status"
```

---

## Task 7: Router de instrumentos (TDD via TestClient)

**Files:**
- Create: `backend/routers/__init__.py` (vazio)
- Create: `backend/routers/instrumentos.py`
- Create: `backend/main.py` (versão inicial, expandida na Task 10)
- Create: `tests/conftest.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Criar `tests/conftest.py` (DB isolado em memória + seed)**

```python
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base, get_db
from backend import models
from backend.main import app


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'t.db'}",
                           connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    db.add_all([
        models.Instrumento(codigo_interno="A-1", equipamento="MULTÍMETRO",
                           disciplina=models.Disciplina.ELE, sistema="MK-48",
                           ciclo_meses=12, data_validade=date(2020, 1, 1),
                           flag_origem="DESCALIBRADO"),
        models.Instrumento(codigo_interno="A-2", equipamento="PAQUÍMETRO",
                           disciplina=models.Disciplina.MEC, sistema="F-21",
                           ciclo_meses=12, data_validade=date(2099, 1, 1),
                           flag_origem="CALIBRADO"),
        models.Instrumento(codigo_interno="A-3", equipamento="TORQUÍMETRO",
                           disciplina=models.Disciplina.MEC, sistema="MK-48",
                           ciclo_meses=12, data_validade=None,
                           flag_origem=""),
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

- [ ] **Step 2: Escrever os testes que falham**

`tests/test_api.py`:
```python
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


def test_get_um(client):
    primeiro = client.get("/api/v1/instrumentos").json()["itens"][0]["id"]
    r = client.get(f"/api/v1/instrumentos/{primeiro}")
    assert r.status_code == 200
    assert r.json()["id"] == primeiro


def test_get_inexistente_404(client):
    assert client.get("/api/v1/instrumentos/99999").status_code == 404
```

- [ ] **Step 3: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_api.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.main'`.

- [ ] **Step 4: Criar `backend/routers/__init__.py`** (vazio)

```python
```

- [ ] **Step 5: Implementar `backend/routers/instrumentos.py`**

```python
"""Endpoints de inventário."""
from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Instrumento
from backend.servico import instrumento_para_out
from backend.schemas import ListaInstrumentos, InstrumentoOut

router = APIRouter(prefix="/api/v1", tags=["instrumentos"])


@router.get("/instrumentos", response_model=ListaInstrumentos)
def listar(
    db: Session = Depends(get_db),
    busca: str | None = Query(None),
    disciplina: str | None = Query(None),
    sistema: str | None = Query(None),
    status: str | None = Query(None),
):
    hoje = date.today()
    itens = [instrumento_para_out(i, hoje) for i in db.query(Instrumento).all()]

    if busca:
        b = busca.lower()
        itens = [i for i in itens if b in " ".join(
            filter(None, [i.codigo_interno, i.serial, i.equipamento, i.modelo])).lower()]
    if disciplina:
        itens = [i for i in itens if i.disciplina == disciplina.upper()]
    if sistema:
        itens = [i for i in itens if (i.sistema or "") == sistema]
    if status:
        itens = [i for i in itens if i.status == status.upper()]

    itens.sort(key=lambda i: (i.codigo_interno or "").lower())
    return ListaInstrumentos(total=len(itens), itens=itens)


@router.get("/instrumentos/{inst_id}", response_model=InstrumentoOut)
def obter(inst_id: int, db: Session = Depends(get_db)):
    inst = db.get(Instrumento, inst_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instrumento não encontrado")
    return instrumento_para_out(inst, date.today())
```

- [ ] **Step 6: Criar `backend/main.py` (inicial)**

```python
"""App FastAPI do SisCalib."""
from fastapi import FastAPI
from backend.routers import instrumentos

app = FastAPI(title="SisCalib", version="0.1.0")
app.include_router(instrumentos.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_api.py -q`
Expected: PASS (7 passed).

- [ ] **Step 8: Commit**

```bash
git add backend/routers/ backend/main.py tests/conftest.py tests/test_api.py
git commit -m "feat: API de inventário (lista/busca/filtro/detalhe) com status derivado"
```

---

## Task 8: Router de importação (preview/commit)

**Files:**
- Create: `backend/routers/importacao.py`
- Modify: `backend/main.py` (incluir router)
- Test: adicionar testes a `tests/test_api.py`

- [ ] **Step 1: Escrever os testes que falham (anexar a `tests/test_api.py`)**

```python
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
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_api.py -q -k "preview or commit"`
Expected: FAIL — 404 (rota inexistente).

- [ ] **Step 3: Implementar `backend/routers/importacao.py`**

```python
"""Endpoints de importação do CSV legado."""
from __future__ import annotations
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.importacao import processar_csv
from backend.models import Instrumento, Disciplina
from backend.schemas import PreviewResposta, CommitResposta

router = APIRouter(prefix="/api/v1/importacao", tags=["importacao"])


@router.post("/preview", response_model=PreviewResposta)
async def preview(arquivo: UploadFile = File(...)):
    conteudo = await arquivo.read()
    return processar_csv(conteudo)


@router.post("/commit", response_model=CommitResposta)
async def commit(arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    conteudo = await arquivo.read()
    resultado = processar_csv(conteudo)
    inseridos = ignorados = 0
    for linha in resultado["linhas"]:
        if any(p["severidade"] == "erro" for p in linha["problemas"]):
            ignorados += 1
            continue
        d = dict(linha["dados"])
        disc = d.get("disciplina")
        d["disciplina"] = Disciplina(disc) if disc in ("ELE", "MEC") else None
        db.add(Instrumento(**{k: v for k, v in d.items()
                              if k in Instrumento.__table__.columns.keys()}))
        inseridos += 1
    db.commit()
    return CommitResposta(inseridos=inseridos, ignorados=ignorados)
```

- [ ] **Step 4: Incluir router em `backend/main.py`**

Modificar `backend/main.py`:
```python
"""App FastAPI do SisCalib."""
from fastapi import FastAPI
from backend.routers import instrumentos, importacao

app = FastAPI(title="SisCalib", version="0.1.0")
app.include_router(instrumentos.router)
app.include_router(importacao.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_api.py -q`
Expected: PASS (todos).

- [ ] **Step 6: Commit**

```bash
git add backend/routers/importacao.py backend/main.py tests/test_api.py
git commit -m "feat: endpoints de importação preview/commit do CSV"
```

---

## Task 9: Dashboard (KPIs) e alertas (com export CSV)

**Files:**
- Create: `backend/routers/dashboard.py`
- Modify: `backend/main.py`
- Test: adicionar testes a `tests/test_api.py`

- [ ] **Step 1: Escrever os testes que falham (anexar a `tests/test_api.py`)**

```python
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
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_api.py -q -k "kpis or alertas"`
Expected: FAIL — 404.

- [ ] **Step 3: Implementar `backend/routers/dashboard.py`**

```python
"""Endpoints de dashboard e alertas."""
from __future__ import annotations
import csv
import io
from collections import Counter
from datetime import date
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import Instrumento
from backend.servico import instrumento_para_out

router = APIRouter(prefix="/api/v1", tags=["dashboard"])

LABEL = {
    "VENCIDO": "Vencidos", "A_VENCER_7": "A vencer (7d)",
    "A_VENCER_30": "A vencer (30d)", "A_VENCER_60": "A vencer (60d)",
    "VALIDO": "Válidos", "SEM_DATA": "Sem data", "BAIXADO": "Baixados",
}
URGENCIA = {"VENCIDO": 0, "A_VENCER_7": 1, "A_VENCER_30": 2,
            "A_VENCER_60": 3, "SEM_DATA": 4}


def _todos(db, hoje):
    return [instrumento_para_out(i, hoje) for i in db.query(Instrumento).all()]


@router.get("/dashboard/kpis")
def kpis(db: Session = Depends(get_db)):
    hoje = date.today()
    itens = _todos(db, hoje)
    cont = Counter(i.status for i in itens)
    a_vencer_30 = cont.get("A_VENCER_7", 0) + cont.get("A_VENCER_30", 0)
    return {
        "total": len(itens),
        "vencidos": cont.get("VENCIDO", 0),
        "a_vencer_30": a_vencer_30,
        "sem_data": cont.get("SEM_DATA", 0),
        "n_sistemas": len({i.sistema for i in itens if i.sistema}),
        "por_status": [{"status": s, "label": LABEL.get(s, s), "total": cont[s]}
                       for s in cont],
    }


@router.get("/alertas")
def alertas(
    db: Session = Depends(get_db),
    disciplina: str | None = Query(None),
    sistema: str | None = Query(None),
    formato: str | None = Query(None),
):
    hoje = date.today()
    itens = [i for i in _todos(db, hoje) if i.status in URGENCIA]
    if disciplina:
        itens = [i for i in itens if i.disciplina == disciplina.upper()]
    if sistema:
        itens = [i for i in itens if (i.sistema or "") == sistema]
    itens.sort(key=lambda i: (URGENCIA[i.status],
                              i.dias_restantes if i.dias_restantes is not None else 99999))

    if formato == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["codigo_interno", "equipamento", "sistema", "disciplina",
                    "data_validade", "status", "dias_restantes"])
        for i in itens:
            w.writerow([i.codigo_interno, i.equipamento, i.sistema, i.disciplina,
                        i.data_validade, i.status, i.dias_restantes])
        return Response(content=buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=alertas.csv"})

    return [i.model_dump() for i in itens]
```

- [ ] **Step 4: Incluir router em `backend/main.py`**

```python
from backend.routers import instrumentos, importacao, dashboard
# ...
app.include_router(dashboard.router)
```
(adicionar `dashboard` ao import e a linha `app.include_router(dashboard.router)`)

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS (suíte inteira).

- [ ] **Step 6: Commit**

```bash
git add backend/routers/dashboard.py backend/main.py tests/test_api.py
git commit -m "feat: KPIs do dashboard e painel de alertas com export CSV"
```

---

## Task 10: Wiring final do app + estáticos + smoke run

**Files:**
- Modify: `backend/main.py`
- Create: `entrypoint.sh`

- [ ] **Step 1: Atualizar `backend/main.py` para servir o frontend e migrar**

```python
"""App FastAPI do SisCalib."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.routers import instrumentos, importacao, dashboard

app = FastAPI(title="SisCalib", version="0.1.0")
app.include_router(instrumentos.router)
app.include_router(importacao.router)
app.include_router(dashboard.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
```

- [ ] **Step 2: Criar `entrypoint.sh`**

```bash
#!/bin/sh
set -e
alembic upgrade head
exec uvicorn backend.main:app --host 0.0.0.0 --port 8080
```

- [ ] **Step 3: Smoke run local (sem Docker)**

Run:
```bash
.venv/bin/alembic upgrade head
.venv/bin/python -m uvicorn backend.main:app --port 8099 &
sleep 2
curl -s localhost:8099/api/v1/health
curl -s "localhost:8099/api/v1/instrumentos" | head -c 120
kill %1
```
Expected: `{"status":"ok"}` e um JSON de lista (possivelmente `{"total":0,...}` se o banco estiver vazio).

- [ ] **Step 4: Rodar a suíte completa**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py entrypoint.sh
git commit -m "feat: servir frontend estático e entrypoint com migração"
```

---

## Task 11: Vendorizar assets visuais + CSS + SDK/render do frontend

**Files:**
- Create: `frontend/vendor/` (assets do cmasm.erp)
- Create: `frontend/siscalib.css`
- Create: `frontend/app.js`

- [ ] **Step 1: Baixar os assets do cmasm.erp para `frontend/vendor/`**

Run:
```bash
mkdir -p frontend/vendor/fonts frontend/vendor/icons
for f in assets/fonts.css assets/xcmasm-govbr.css \
         assets/bootstrap-icons.min.css \
         assets/icons_MB/Logo_of_the_Brazilian_Navy.svg.png; do
  out="frontend/vendor/$(basename $f)"
  gh api "repos/luctronics-ET/cmasm.erp/contents/$f" \
    -q '.content' | base64 -d > "$out"
done
for f in dm-sans-latin-400-normal.woff2 dm-sans-latin-500-normal.woff2 \
         dm-sans-latin-600-normal.woff2 dm-sans-latin-700-normal.woff2 \
         jetbrains-mono-latin-400-normal.woff2; do
  gh api "repos/luctronics-ET/cmasm.erp/contents/assets/fonts/$f" \
    -q '.content' | base64 -d > "frontend/vendor/fonts/$f"
done
gh api "repos/luctronics-ET/cmasm.erp/contents/assets/bootstrap-icons-fonts/bootstrap-icons.woff2" \
  -q '.content' | base64 -d > "frontend/vendor/bootstrap-icons.woff2"
gh api "repos/luctronics-ET/cmasm.erp/contents/assets/bootstrap-icons-fonts/bootstrap-icons.woff" \
  -q '.content' | base64 -d > "frontend/vendor/bootstrap-icons.woff"
ls -la frontend/vendor frontend/vendor/fonts
```
Expected: arquivos `.css`, `.woff2`, logo `.png` presentes. (Se `fonts.css`/`bootstrap-icons.min.css` referenciarem caminhos relativos diferentes, ajustar os `url(...)` para `./fonts/` e `./` no Step 2.)

- [ ] **Step 2: Ajustar caminhos de fonte (se necessário)**

Editar `frontend/vendor/fonts.css` e `frontend/vendor/bootstrap-icons.min.css` para que os `url(...)` apontem para os arquivos vendorizados:
- em `fonts.css`: `url(./fonts/dm-sans-latin-400-normal.woff2)` etc.
- em `bootstrap-icons.min.css`: `url(./bootstrap-icons.woff2)` e `url(./bootstrap-icons.woff)`.

Run para conferir referências restantes:
```bash
grep -oE "url\([^)]*\)" frontend/vendor/fonts.css frontend/vendor/bootstrap-icons.min.css
```
Expected: todas as URLs apontam para arquivos existentes em `frontend/vendor/`.

- [ ] **Step 3: Criar `frontend/siscalib.css`** (tokens do cmasm.erp + shell próprio)

```css
:root{
  --bg:#07111f; --sf:#0f2035; --sf2:#0d1e33; --bd:#1f3552; --bd2:#2e4b72;
  --tx:#e2e8f0; --tx2:#9fb4d1; --tx3:#6f86a8;
  --blue:#00b4d8; --green:#22c55e; --green-bg:#0b2f1c;
  --red:#ef4444; --red-bg:#351316; --amber:#f59e0b; --amber-bg:#3b2a0d;
  --orange:#fb923c; --orange-bg:#3a220f; --slate-bg:#1e293b;
  --r:8px; --rl:12px;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DM Sans',system-ui,sans-serif;background:var(--bg);color:var(--tx);font-size:14px}
.app{display:flex;min-height:100vh}
.sb{width:210px;background:#0f172a;color:#fff;flex-shrink:0;padding:14px 8px}
.sb-logo{display:flex;align-items:center;gap:8px;padding:8px 8px 16px;font-weight:700}
.sb-logo img{width:26px;height:26px}
.sb a{display:flex;align-items:center;gap:9px;padding:9px 10px;border-radius:var(--r);
      color:#94a3b8;text-decoration:none;font-weight:500;margin-bottom:2px}
.sb a:hover{background:var(--slate-bg);color:#fff}
.sb a.act{background:#1d4ed8;color:#fff}
.main{flex:1;padding:22px;overflow-x:auto}
h1{font-size:20px;margin-bottom:16px;font-weight:700}
.card{background:var(--sf);border:1px solid var(--bd);border-radius:var(--rl);padding:16px 18px;margin-bottom:16px}
.kpi-g{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}
.kpi{background:var(--sf);border:1px solid var(--bd);border-radius:var(--rl);padding:14px 16px}
.kpi .v{font-size:30px;font-weight:700;line-height:1}
.kpi .l{font-size:12px;color:var(--tx2);margin-top:5px}
.kpi.red .v{color:var(--red)} .kpi.amber .v{color:var(--amber)} .kpi.blue .v{color:var(--blue)}
.twrap{overflow-x:auto;border:1px solid var(--bd);border-radius:var(--rl)}
table{width:100%;border-collapse:collapse;font-size:13px}
thead tr{background:var(--sf2)}
th{padding:9px 12px;text-align:left;font-size:11px;text-transform:uppercase;
   letter-spacing:.04em;color:var(--tx2);white-space:nowrap}
td{padding:9px 12px;border-top:1px solid var(--bd)}
tbody tr:hover{background:var(--sf2)}
.bdg{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap}
.bdg.green{background:var(--green-bg);color:var(--green)}
.bdg.red{background:var(--red-bg);color:var(--red)}
.bdg.amber{background:var(--amber-bg);color:var(--amber)}
.bdg.orange{background:var(--orange-bg);color:var(--orange)}
.bdg.slate{background:var(--slate-bg);color:var(--tx2)}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}
input,select{background:var(--sf2);border:1px solid var(--bd);color:var(--tx);
             padding:8px 10px;border-radius:var(--r);font-size:13px}
input[type=search]{min-width:240px}
.btn{background:#1d4ed8;color:#fff;border:none;padding:8px 14px;border-radius:var(--r);
     cursor:pointer;font-weight:600;font-size:13px;text-decoration:none;display:inline-block}
.btn.ghost{background:var(--sf2);border:1px solid var(--bd);color:var(--tx)}
.sev-erro{color:var(--red)} .sev-aviso{color:var(--amber)} .sev-info{color:var(--tx3)}
.bar{display:flex;height:14px;border-radius:7px;overflow:hidden;margin:6px 0 10px}
.bar>span{display:block}
.muted{color:var(--tx3)} a{color:var(--blue)}
```

- [ ] **Step 4: Criar `frontend/app.js`** (SDK + helpers de render + shell)

```javascript
// SisCalib — SDK + helpers de UI (vanilla). Inspirado em xcmasm-sdk.js.
const API = "/api/v1";

const SDK = {
  async get(path, params) {
    const url = new URL(API + path, location.origin);
    if (params) Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
    const r = await fetch(url);
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  },
  async upload(path, file) {
    const fd = new FormData();
    fd.append("arquivo", file);
    const r = await fetch(API + path, { method: "POST", body: fd });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  },
};

const STATUS_BADGE = {
  VENCIDO: "red", A_VENCER_7: "orange", A_VENCER_30: "amber",
  A_VENCER_60: "amber", VALIDO: "green", SEM_DATA: "slate", BAIXADO: "slate",
};
const STATUS_LABEL = {
  VENCIDO: "Vencido", A_VENCER_7: "A vencer 7d", A_VENCER_30: "A vencer 30d",
  A_VENCER_60: "A vencer 60d", VALIDO: "Válido", SEM_DATA: "Sem data", BAIXADO: "Baixado",
};

function badgeStatus(s) {
  return `<span class="bdg ${STATUS_BADGE[s] || "slate"}">${STATUS_LABEL[s] || s}</span>`;
}
function esc(v) {
  return v == null ? "" : String(v).replace(/[&<>"]/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function fmtData(iso) { return iso ? iso.split("-").reverse().join("/") : "—"; }

const NAV = [
  ["index.html", "speedometer2", "Dashboard"],
  ["inventario.html", "list-ul", "Inventário"],
  ["alertas.html", "bell", "Alertas"],
  ["importar.html", "upload", "Importar"],
];

function montarShell(ativo) {
  const links = NAV.map(([h, ic, lbl]) =>
    `<a href="${h}" class="${h === ativo ? "act" : ""}"><i class="bi bi-${ic}"></i> ${lbl}</a>`
  ).join("");
  document.body.insertAdjacentHTML("afterbegin", `
    <div class="sb">
      <div class="sb-logo"><img src="vendor/Logo_of_the_Brazilian_Navy.svg.png" alt="MB"> SisCalib</div>
      ${links}
    </div>`);
}
```

- [ ] **Step 5: Verificar sintaxe do JS**

Run: `.venv/bin/python -c "print('css/js criados')" && test -f frontend/app.js && test -f frontend/siscalib.css && echo ok`
Expected: `ok`. (Validação visual ocorre na Task 13.)

- [ ] **Step 6: Commit**

```bash
git add frontend/vendor frontend/siscalib.css frontend/app.js
git commit -m "feat: assets visuais vendorizados + CSS e SDK do frontend"
```

---

## Task 12: Páginas do frontend

**Files:**
- Create: `frontend/index.html`, `inventario.html`, `alertas.html`, `importar.html`, `ficha.html`

> Todas as páginas têm a mesma estrutura: `<head>` com os CSS vendorizados + `siscalib.css`, `<body class="app">`, `app.js`, depois um `<script>` de init que monta o shell e a `<main>`.

- [ ] **Step 1: `frontend/index.html` (Dashboard)**

```html
<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SisCalib · Dashboard</title>
<link rel="stylesheet" href="vendor/fonts.css">
<link rel="stylesheet" href="vendor/bootstrap-icons.min.css">
<link rel="stylesheet" href="vendor/xcmasm-govbr.css">
<link rel="stylesheet" href="siscalib.css">
</head><body class="app">
<script src="app.js"></script>
<main class="main">
  <h1>Dashboard de Calibração</h1>
  <div class="kpi-g" id="kpis"></div>
  <div class="card"><b>Status do inventário</b><div id="barra"></div><div id="legenda" class="muted"></div></div>
  <div class="card"><b>Próximos a vencer</b><div class="twrap" style="margin-top:10px"><table id="tab"><thead>
    <tr><th>Código</th><th>Instrumento</th><th>Sistema</th><th>Validade</th><th>Status</th></tr>
  </thead><tbody></tbody></table></div></div>
</main>
<script>
montarShell("index.html");
(async () => {
  const k = await SDK.get("/dashboard/kpis");
  document.getElementById("kpis").innerHTML = [
    ["", "Total", k.total], ["red", "Vencidos", k.vencidos],
    ["amber", "A vencer 30d", k.a_vencer_30], ["blue", "Sem data", k.sem_data],
    ["", "Sistemas", k.n_sistemas],
  ].map(([c, l, v]) => `<div class="kpi ${c}"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");

  const cor = { VENCIDO: "var(--red)", A_VENCER_7: "var(--orange)", A_VENCER_30: "var(--amber)",
                A_VENCER_60: "var(--amber)", VALIDO: "var(--green)", SEM_DATA: "var(--tx3)", BAIXADO: "var(--bd2)" };
    const tot = k.por_status.reduce((s, x) => s + x.total, 0) || 1;
  document.getElementById("barra").innerHTML = `<div class="bar">` +
    k.por_status.map(s => `<span title="${s.label}: ${s.total}" style="width:${100 * s.total / tot}%;background:${cor[s.status] || "var(--bd2)"}"></span>`).join("") + `</div>`;
  document.getElementById("legenda").textContent =
    k.por_status.map(s => `${s.label}: ${s.total}`).join("   ·   ");

  const alertas = await SDK.get("/alertas");
  document.querySelector("#tab tbody").innerHTML = alertas.slice(0, 20).map(i => `
    <tr><td><a href="ficha.html?id=${i.id}">${esc(i.codigo_interno)}</a></td>
    <td>${esc(i.equipamento)}</td><td>${esc(i.sistema)}</td>
    <td>${fmtData(i.data_validade)}</td><td>${badgeStatus(i.status)}</td></tr>`).join("")
    || `<tr><td colspan="5" class="muted">Nenhum alerta. Importe o inventário em “Importar”.</td></tr>`;
})();
</script></body></html>
```

- [ ] **Step 2: `frontend/inventario.html`**

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
  </div>
  <div class="muted" id="cont" style="margin-bottom:8px"></div>
  <div class="twrap"><table id="tab"><thead><tr>
    <th>Código</th><th>Equipamento</th><th>Marca/Modelo</th><th>Disc.</th>
    <th>Sistema</th><th>Validade</th><th>Status</th></tr></thead><tbody></tbody></table></div>
</main>
<script>
montarShell("inventario.html");
let timer;
async function carregar() {
  const params = {
    busca: busca.value, disciplina: disciplina.value,
    sistema: sistema.value, status: status.value,
  };
  const r = await SDK.get("/instrumentos", params);
  cont.textContent = `${r.total} instrumento(s)`;
  document.querySelector("#tab tbody").innerHTML = r.itens.map(i => `
    <tr><td><a href="ficha.html?id=${i.id}">${esc(i.codigo_interno)}</a></td>
    <td>${esc(i.equipamento)}</td><td>${esc([i.marca, i.modelo].filter(Boolean).join(" "))}</td>
    <td>${esc(i.disciplina)}</td><td>${esc(i.sistema)}</td>
    <td>${fmtData(i.data_validade)}</td><td>${badgeStatus(i.status)}</td></tr>`).join("")
    || `<tr><td colspan="7" class="muted">Nada encontrado.</td></tr>`;
}
const busca = document.getElementById("busca"), disciplina = document.getElementById("disciplina"),
      sistema = document.getElementById("sistema"), status = document.getElementById("status"),
      cont = document.getElementById("cont");
[disciplina, sistema, status].forEach(e => e.onchange = carregar);
busca.oninput = () => { clearTimeout(timer); timer = setTimeout(carregar, 250); };
(async () => {
  const r = await SDK.get("/instrumentos");
  [...new Set(r.itens.map(i => i.sistema).filter(Boolean))].sort()
    .forEach(s => sistema.add(new Option(s, s)));
  carregar();
})();
</script></body></html>
```

- [ ] **Step 3: `frontend/alertas.html`**

```html
<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SisCalib · Alertas</title>
<link rel="stylesheet" href="vendor/fonts.css">
<link rel="stylesheet" href="vendor/bootstrap-icons.min.css">
<link rel="stylesheet" href="vendor/xcmasm-govbr.css">
<link rel="stylesheet" href="siscalib.css">
</head><body class="app">
<script src="app.js"></script>
<main class="main">
  <h1>Painel de Alertas</h1>
  <div class="toolbar">
    <select id="disciplina"><option value="">Disciplina</option><option>ELE</option><option>MEC</option></select>
    <select id="sistema"><option value="">Sistema</option></select>
    <a class="btn ghost" id="csv"><i class="bi bi-download"></i> Exportar CSV</a>
  </div>
  <div class="muted" id="cont" style="margin-bottom:8px"></div>
  <div class="twrap"><table id="tab"><thead><tr>
    <th>Código</th><th>Equipamento</th><th>Sistema</th><th>Validade</th>
    <th>Dias</th><th>Status</th></tr></thead><tbody></tbody></table></div>
</main>
<script>
montarShell("alertas.html");
const disciplina = document.getElementById("disciplina"), sistema = document.getElementById("sistema"),
      cont = document.getElementById("cont"), csv = document.getElementById("csv");
function params() { return { disciplina: disciplina.value, sistema: sistema.value }; }
async function carregar() {
  const itens = await SDK.get("/alertas", params());
  cont.textContent = `${itens.length} alerta(s)`;
  const u = new URL("/api/v1/alertas", location.origin);
  u.searchParams.set("formato", "csv");
  Object.entries(params()).forEach(([k, v]) => v && u.searchParams.set(k, v));
  csv.href = u;
  document.querySelector("#tab tbody").innerHTML = itens.map(i => `
    <tr><td><a href="ficha.html?id=${i.id}">${esc(i.codigo_interno)}</a></td>
    <td>${esc(i.equipamento)}</td><td>${esc(i.sistema)}</td>
    <td>${fmtData(i.data_validade)}</td>
    <td>${i.dias_restantes == null ? "—" : i.dias_restantes}</td>
    <td>${badgeStatus(i.status)}</td></tr>`).join("")
    || `<tr><td colspan="6" class="muted">Sem alertas.</td></tr>`;
}
[disciplina, sistema].forEach(e => e.onchange = carregar);
(async () => {
  const r = await SDK.get("/instrumentos");
  [...new Set(r.itens.map(i => i.sistema).filter(Boolean))].sort()
    .forEach(s => sistema.add(new Option(s, s)));
  carregar();
})();
</script></body></html>
```

- [ ] **Step 4: `frontend/importar.html`**

```html
<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SisCalib · Importar</title>
<link rel="stylesheet" href="vendor/fonts.css">
<link rel="stylesheet" href="vendor/bootstrap-icons.min.css">
<link rel="stylesheet" href="vendor/xcmasm-govbr.css">
<link rel="stylesheet" href="siscalib.css">
</head><body class="app">
<script src="app.js"></script>
<main class="main">
  <h1>Importar Inventário (CSV)</h1>
  <div class="card">
    <input type="file" id="arq" accept=".csv">
    <button class="btn" id="btnPreview">Pré-visualizar</button>
    <button class="btn" id="btnCommit" style="display:none">Confirmar importação</button>
    <div id="totais" style="margin-top:12px"></div>
  </div>
  <div class="twrap" id="wrap" style="display:none"><table id="tab"><thead><tr>
    <th>#</th><th>Código</th><th>Equipamento</th><th>Validade</th><th>Problemas</th>
  </tr></thead><tbody></tbody></table></div>
</main>
<script>
montarShell("importar.html");
const arq = document.getElementById("arq"), totais = document.getElementById("totais"),
      wrap = document.getElementById("wrap"), btnCommit = document.getElementById("btnCommit");
document.getElementById("btnPreview").onclick = async () => {
  if (!arq.files[0]) return alert("Escolha um arquivo CSV.");
  const r = await SDK.upload("/importacao/preview", arq.files[0]);
  const t = r.totais;
  totais.innerHTML = `<b>${t.total_linhas}</b> linhas · 
    <span class="sev-info">${t.validas} válidas</span> · 
    <span class="sev-aviso">${t.com_aviso} com aviso</span> · 
    <span class="sev-erro">${t.com_erro} com erro</span>`;
  wrap.style.display = "";
  btnCommit.style.display = t.validas ? "" : "none";
  document.querySelector("#tab tbody").innerHTML = r.linhas.map(l => {
    const probs = l.problemas.map(p => `<div class="sev-${p.severidade}">[${p.severidade}] ${esc(p.campo)}: ${esc(p.mensagem)}</div>`).join("") || "—";
    return `<tr><td>${l.numero}</td><td>${esc(l.dados.codigo_interno)}</td>
      <td>${esc(l.dados.equipamento)}</td><td>${fmtData(l.dados.data_validade)}</td><td>${probs}</td></tr>`;
  }).join("");
};
btnCommit.onclick = async () => {
  if (!confirm("Confirmar gravação das linhas válidas?")) return;
  const r = await SDK.upload("/importacao/commit", arq.files[0]);
  alert(`Importado: ${r.inseridos} inseridos, ${r.ignorados} ignorados.`);
  location.href = "index.html";
};
</script></body></html>
```

- [ ] **Step 5: `frontend/ficha.html`**

```html
<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SisCalib · Ficha</title>
<link rel="stylesheet" href="vendor/fonts.css">
<link rel="stylesheet" href="vendor/bootstrap-icons.min.css">
<link rel="stylesheet" href="vendor/xcmasm-govbr.css">
<link rel="stylesheet" href="siscalib.css">
</head><body class="app">
<script src="app.js"></script>
<main class="main">
  <a href="inventario.html" class="muted">&larr; Inventário</a>
  <h1 id="titulo" style="margin-top:8px">Ficha do Instrumento</h1>
  <div id="status" style="margin-bottom:14px"></div>
  <div class="card"><table><tbody id="campos"></tbody></table></div>
</main>
<script>
montarShell("");
(async () => {
  const id = new URLSearchParams(location.search).get("id");
  const i = await SDK.get("/instrumentos/" + id);
  document.getElementById("titulo").textContent =
    `${i.codigo_interno || "(sem código)"} — ${i.equipamento || ""}`;
  let aviso = i.divergencia_flag
    ? ` <span class="bdg amber">divergência flag×data</span>` : "";
  document.getElementById("status").innerHTML = badgeStatus(i.status) +
    (i.dias_restantes != null ? ` <span class="muted">(${i.dias_restantes} dias)</span>` : "") + aviso;
  const linhas = [
    ["Série", i.serial], ["Marca", i.marca], ["Modelo", i.modelo],
    ["Faixa", [i.faixa, i.unidade_faixa].filter(Boolean).join(" ")],
    ["Disciplina", i.disciplina], ["Sistema", i.sistema],
    ["Ciclo (meses)", i.ciclo_meses],
    ["Última calibração", fmtData(i.data_ultima_calibracao)],
    ["Validade", fmtData(i.data_validade)],
    ["Flag de origem (CSV)", i.flag_origem],
    ["Organização calibradora", i.organizacao_calibradora],
    ["Local de calibração", i.local_calibracao],
    ["Custo estimado", i.custo_estimado], ["Custo contratado", i.custo_contratado],
    ["Certificado", i.certificado_ref], ["Observações", i.observacoes],
  ];
  document.getElementById("campos").innerHTML = linhas.map(([k, v]) =>
    `<tr><th style="width:200px">${k}</th><td>${esc(v) || "—"}</td></tr>`).join("");
})();
</script></body></html>
```

- [ ] **Step 6: Commit**

```bash
git add frontend/*.html
git commit -m "feat: páginas do frontend (dashboard, inventário, alertas, importar, ficha)"
```

---

## Task 13: Docker + README + verificação end-to-end com o CSV real

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `README.md`

- [ ] **Step 1: Criar `Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY frontend/ frontend/
COPY alembic/ alembic/
COPY alembic.ini entrypoint.sh ./
RUN chmod +x entrypoint.sh
ENV SISCALIB_DATA=/data
VOLUME ["/data"]
EXPOSE 8080
CMD ["./entrypoint.sh"]
```

- [ ] **Step 2: Criar `.dockerignore`**

```
.venv/
__pycache__/
*.pyc
tests/
data/
.git/
docs/
.reference_readonly/
```

- [ ] **Step 3: Criar `README.md`**

```markdown
# SisCalib — Sistema de Gestão Metrológica (fatia fina)

App standalone para controle de calibração de instrumentos. FastAPI + SQLite + frontend vanilla.

## Rodar em desenvolvimento
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m uvicorn backend.main:app --reload --port 8080
```
Acesse http://localhost:8080

## Rodar via Docker
```bash
docker build -t siscalib:latest .
docker run -d --name siscalib --restart unless-stopped \
  -p 8080:8080 -v siscalib_data:/data siscalib:latest
```

## Importar o inventário
1. Abra **Importar** no menu.
2. Envie o CSV (ex.: `CMASM_Controle de Calibracao ... .csv`).
3. Revise o relatório dry-run (linhas válidas / avisos / erros).
4. Clique **Confirmar importação**.

## Backup
O estado todo está em `/data/siscalib.db` — basta copiar esse arquivo.

## Testes
```bash
.venv/bin/python -m pytest tests/ -q
```

## Fora desta fatia (próximas entregas da Fase 1)
Autenticação JWT, QR Code/etiquetas, upload de certificado PDF, gestão de
laboratórios, página pública por seção, export PDF. Ver
`docs/superpowers/specs/2026-06-14-siscalib-fatia-fina-design.md`.
```

- [ ] **Step 4: Build da imagem**

Run: `docker build -t siscalib:latest .`
Expected: build conclui sem erro.

- [ ] **Step 5: Subir o container e importar o CSV real**

Run:
```bash
docker run -d --name siscalib -p 8080:8080 -v siscalib_data:/data siscalib:latest
sleep 3
curl -s localhost:8080/api/v1/health
# importar o CSV real de referência
curl -s -F "arquivo=@.reference_readonly/CMASM_Controle de Calibracao 2026_lote2_jun2026_REV00.csv" \
  localhost:8080/api/v1/importacao/commit
curl -s localhost:8080/api/v1/dashboard/kpis
```
Expected: `{"status":"ok"}`; commit retorna `{"inseridos": <~490+>, "ignorados": <poucos>}`; kpis mostra `total` próximo de 496 com `vencidos`/`a_vencer_30` plausíveis.

- [ ] **Step 6: Verificação visual**

Abrir `http://localhost:8080` no navegador: dashboard com KPIs preenchidos, inventário pesquisável, painel de alertas ordenado, ficha acessível. Conferir que a busca e os filtros respondem.

- [ ] **Step 7: Parar o container de teste**

Run: `docker rm -f siscalib`
Expected: remove o container.

- [ ] **Step 8: Commit**

```bash
git add Dockerfile .dockerignore README.md
git commit -m "feat: Docker, README e verificação end-to-end com CSV real"
```

---

## Self-Review (preenchido pelo autor do plano)

**Cobertura do spec:**
- §2 standalone FastAPI+SQLAlchemy+Alembic+SQLite → Tasks 1, 4, 10, 13. ✓
- §2 assets vendorizados do cmasm.erp → Task 11. ✓
- §2 sem auth nesta fatia → respeitado (nenhuma task adiciona auth); registrado no README/spec. ✓
- §3 modelo Instrumento + mapeamento por conteúdo → Tasks 4, 5. ✓
- §4 importador preview/commit + severidades + datas US/DD-MM + moeda + 496<60s → Tasks 3, 5, 8, 13. ✓
- §5 motor de status com precedência e divergência → Task 2. ✓
- §6 endpoints + 5 páginas → Tasks 7, 8, 9, 12. ✓
- §7 testes (motor, importador, API) → Tasks 2, 3, 5, 7, 8, 9. ✓

**Placeholders:** nenhum "TBD/TODO"; todo passo de código mostra o código. O passo de autogenerate do Alembic (Task 4 Step 4) é um comando real com saída verificável, não um placeholder.

**Consistência de tipos/nomes:** `calcular_status`/`StatusCalibracao`/`ResultadoStatus` (Task 2) usados em `servico.py` (Task 6) e routers (7/9); `processar_csv` retorna `{totais:{total_linhas,validas,com_aviso,com_erro}, linhas:[{numero,dados,problemas}]}` consumido igual em Tasks 8 e 12; valores de status (`VENCIDO/A_VENCER_7/...`) idênticos em backend (calibracao.py) e frontend (app.js `STATUS_BADGE`/`STATUS_LABEL`). ✓

**Observação de risco conhecida:** o número exato de `inseridos` no CSV real (Task 13 Step 5) depende dos dados; o critério é "≈496 e erros plausíveis", não um número fixo — coerente com a natureza do legado.
```
