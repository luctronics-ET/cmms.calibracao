# Design — SisCalib (Fatia Fina Vertical)

**Data:** 2026-06-14
**Projeto:** xCalibracao / SisCalib — Sistema de Gestão Metrológica
**Escopo deste documento:** Primeira fatia fina vertical da Fase 1 do PRD-SisCalib v1.1
**Status:** Aprovado pelo usuário; pronto para plano de implementação

---

## 1. Objetivo da fatia

Entregar uma aplicação **rodando de ponta a ponta** que prove o stack e dê visibilidade imediata:

> Importar o CSV real (~496 instrumentos) → inventário com busca/filtros → cálculo automático de status/validade → painel de alertas + dashboard.

É um subconjunto da Fase 1 do PRD, escolhido para validar o stack e o dado real antes de expandir. As demais capacidades da Fase 1 (autenticação, QR Code/etiquetas, upload de certificado PDF, gestão de laboratórios, página pública por seção, export PDF) ficam para o ciclo seguinte e estão listadas na Seção 8.

### Critério de aceite da fatia
- Subir 1 container, abrir a tela de importação, enviar o CSV real, revisar o relatório dry-run, confirmar.
- Dashboard e inventário populados com os 496 instrumentos, **status calculado a cada request**.
- Importação dos 496 registros em < 60s, com problemas reportados linha a linha (PRD 6.5).

---

## 2. Decisões de arquitetura

- **Standalone**, repo `xCalibracao`. Independente do cmasm.erp (não é módulo, não segue regras do PMOC). Integração futura com cmasm.erp via API `/sync` permanece como Fase 3 do PRD.
- **Backend:** FastAPI (Python 3.12) + **SQLAlchemy + Alembic** + SQLite (decisão do PRD §9). Alembic dá migrações versionadas para o schema crescer nas fases seguintes; upgrade futuro para PostgreSQL = trocar connection string.
- **Frontend:** HTML + JS vanilla. Assets visuais do cmasm.erp são **vendorizados** (copiados para `frontend/vendor/`), não referenciados externamente — preserva independência. Reusa: `xcmasm-shell.css/js`, `xcmasm-govbr.css`, `fonts.css`, `pmoc-engine.css/js` (widgets de KPI/donut/linha/tabela), `bootstrap-icons`, `icons_MB`.
- **SDK do frontend:** `frontend/app.js`, modelado no `xcmasm-sdk.js` do cmasm.erp (helper HTTP + funções por recurso), apontando para a API local `/api/v1`.
- **Sem autenticação nesta fatia.** Single-user na LAN. JWT (cookie HttpOnly, PRD §9) entra no fechamento da Fase 1. **Pendência registrada** — ver Seção 8.
- **API versionada `/api/v1/`** desde já, conforme PRD.

### Estrutura de pastas
```
xCalibracao/
├── backend/
│   ├── main.py              # app FastAPI; monta /api/v1 e estáticos
│   ├── db.py                # engine SQLAlchemy + session (SQLite → data/siscalib.db)
│   ├── models.py            # ORM (fatia: Instrumento)
│   ├── schemas.py           # Pydantic (entrada/saída)
│   ├── calibracao.py        # MOTOR de status/validade (função pura)
│   ├── importacao.py        # parser + validação do CSV real
│   └── routers/
│       ├── instrumentos.py  # list/get/search
│       ├── importacao.py    # POST preview, POST commit
│       └── dashboard.py     # kpis + alertas
├── alembic/                 # migrações
├── frontend/
│   ├── index.html           # dashboard
│   ├── inventario.html      # tabela busca/filtros
│   ├── alertas.html         # painel de alertas + export CSV
│   ├── importar.html        # upload + relatório dry-run
│   ├── ficha.html           # ficha read-only
│   ├── app.js               # SDK SisCalib
│   └── vendor/              # assets COPIADOS do cmasm.erp
├── data/                    # siscalib.db + uploads (gitignored)
├── tests/                   # pytest: motor de status + importador
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## 3. Modelo de dados (fatia)

Uma tabela principal: `instrumento`. O **status não é armazenado** — é derivado pelo motor (Seção 5) a cada request. O flag bruto do CSV é guardado separado para auditar divergências do legado.

### Tabela `instrumento`

| Campo | Tipo | Origem no CSV | Observação |
|---|---|---|---|
| `id` | PK int | — | |
| `codigo_interno` | str, indexado | `COD INTERNO` | busca (488/496 preenchidos) |
| `serial` | str, indexado | `SERIAL` | |
| `equipamento` | str | `EQUIPAMENTO` | tipo/descrição |
| `marca` | str | `MARCA` | |
| `modelo` | str | `MODELO` | |
| `faixa` | str | `RANGE` | texto livre nesta fatia |
| `unidade_faixa` | str | `UNIDADE RANGE` | coluna com `\n` no cabeçalho |
| `disciplina` | enum | `ELE/MEC` | ELE \| MEC |
| `sistema` | str, indexado | `DIVISÃO` | MK-48, MK-46, F-21, EXOCET... (filtro) |
| `ciclo_meses` | int (default 12) | `CICLO CALIBRAÇÃO` | periodicidade |
| `data_ultima_calibracao` | date null | `ULTIMA CALIBRAÇÃO` | US→ISO |
| `data_validade` | date null | `PRÓXIMA CALIBRAÇÃO` | US→ISO; vencimento real |
| `flag_origem` | str | `VALIDADE CALIBRAÇÃO` | CALIBRADO / DESCALIBRADO / SEM CONDIÇÕES DE USO / inativo |
| `organizacao_calibradora` | str | `SITUAÇÃO` | CMASM=interno; CMS/MSMI/BACS=externo |
| `local_calibracao` | str | `LOCAL CALIBRAÇÃO` | |
| `custo_estimado` | decimal null | `CUSTO ESTIMADO` | "R$ 1,234.56"→número |
| `custo_contratado` | decimal null | `CUSTO CONTRAT (R$)` | |
| `certificado_ref` | str | `CERTIFICADO` | texto/número (PDF fica p/ Fase 1 completa) |
| `observacoes` | str | `COMENTÁRIOS` | |
| `criado_em` / `atualizado_em` | datetime | — | |

**Atenção — os nomes das colunas do CSV enganam.** O mapeamento acima é por **conteúdo real**, não pelo cabeçalho:
- `SITUAÇÃO` contém a **organização calibradora** (CMASM/CMS/MSMI/BACS), não o status.
- `VALIDADE CALIBRAÇÃO` contém o **status textual** (CALIBRADO/DESCALIBRADO/...), não uma data.
- `PRÓXIMA CALIBRAÇÃO` contém a **data de vencimento** (formato US MM/DD/YY).
- `CICLO CALIBRAÇÃO` é a **periodicidade em meses** (12/24/36...).
- `ELE/MEC` é a **disciplina** (MEC=371, ELE=123).
- `DIVISÃO` é o **sistema de armas/projeto** (MK-48=278, MK-46=89, F-21=77, EXOCET=32...).

**Campos do CSV ignorados nesta fatia:** `PS`, `ENTRADA OF ET`, `SAÍDA/CAL`, `RETORNO CAL` (logística → Fase 3), `PAGAMENTO` (0/496 preenchidos), `item`, 2ª coluna `CERTIFICADO`.

**Unicidade:** não há chave natural confiável (`COD INTERNO` repete em duplicatas reais do Excel). Sem constraint de unicidade no banco. O importador **detecta e reporta** prováveis duplicatas (`codigo_interno`+`serial`+`modelo` iguais) no dry-run, mas não bloqueia — o usuário decide.

---

## 4. Importador de CSV (preview/commit)

Dois endpoints: preview faz dry-run sem gravar; commit grava.

### Pipeline de parsing/normalização
1. **Detecção de cabeçalho por nome normalizado** (não por ordem cega): trata o `\n` em "UNIDADE RANGE" e as 2 colunas "CERTIFICADO".
2. **Datas US→ISO**: `MM/DD/YY` → `date`. Ano 2 dígitos: `00–69`→20xx, `70–99`→19xx. Parsing falho = aviso, não erro fatal.
3. **Moeda**: `"R$ 1,234.56"` → `1234.56` (remove `R$` e vírgula de milhar).
4. **Flag de origem**: `VALIDADE CALIBRAÇÃO` → `flag_origem`. `#VALUE!` → vazio + aviso.
5. **Linhas vazias** e duplicatas exatas puladas (496 linhas úteis confirmadas).

### Validações do dry-run (com severidade)
- 🔴 **erro** (linha não importa): sem `equipamento` **e** sem `codigo_interno` (linha-fantasma).
- 🟡 **aviso** (importa e sinaliza): data ilegível; `ciclo_meses` ausente (assume 12 — PRD Q7); **divergência** flag×data (ex.: CALIBRADO mas `data_validade` no passado); provável duplicata.
- ℹ️ **info**: campos opcionais vazios.

### Contrato da API
- `POST /api/v1/importacao/preview` — recebe o arquivo; devolve `{totais:{validas,com_aviso,com_erro}, linhas:[{numero, dados_normalizados, problemas:[{severidade,campo,mensagem}]}]}`. Não grava.
- `POST /api/v1/importacao/commit` — grava as linhas válidas. Devolve `{inseridos, ignorados}`.

**Critério de aceite:** 496 registros em < 60s; problemas linha a linha (PRD 6.5). Testes com amostra real do CSV.

---

## 5. Motor de status/validade

Função pura, isolada e testável em `backend/calibracao.py`. `hoje` é injetado como parâmetro → testes determinísticos.

```python
def calcular_status(data_validade, flag_origem, hoje) -> ResultadoStatus
# ResultadoStatus = {status, dias_restantes, divergencia_flag}
```

### Regras (ordem de precedência)
1. `flag_origem` ∈ {`SEM CONDIÇÕES DE USO`, `inativo`} → **`BAIXADO`** (não entra em alerta de vencimento).
2. Sem `data_validade` → **`SEM_DATA`** (aparece em painel próprio).
3. `data_validade < hoje` → **`VENCIDO`** (`dias_restantes` negativo).
4. `data_validade ≤ hoje + 7` → **`A_VENCER_7`**.
5. `data_validade ≤ hoje + 30` → **`A_VENCER_30`**.
6. `data_validade ≤ hoje + 60` → **`A_VENCER_60`**.
7. senão → **`VALIDO`**.

`divergencia_flag = true` quando `flag_origem=DESCALIBRADO` mas a data daria VÁLIDO (ou vice-versa) — apoia o metrologista a auditar o legado do Excel.

Limiares **7/30/60** (do painel, PRD 6.3) em constantes no topo do módulo, configuráveis depois. **Toda** resposta de instrumento da API passa pelo motor → status sempre fresco (PRD G2/6.3).

---

## 6. Páginas, API e fluxo

### Endpoints `/api/v1/`
| Método | Rota | Função |
|---|---|---|
| `GET` | `/instrumentos` | lista paginada; params: `busca`, `disciplina`, `sistema`, `status` |
| `GET` | `/instrumentos/{id}` | ficha completa |
| `POST` | `/importacao/preview` | dry-run (Seção 4) |
| `POST` | `/importacao/commit` | grava |
| `GET` | `/dashboard/kpis` | total, vencidos, a_vencer_30, sem_data, nº sistemas; donut por status; série de validades/mês |
| `GET` | `/alertas` | instrumentos por urgência; filtros disciplina/sistema; `?formato=csv` exporta |

### Páginas (vanilla JS + shell vendorizado)
1. **`index.html` (Dashboard)** — cards de KPI + donut de status + tabela "próximos a vencer" via `pmoc-engine.js`. (PRD G2)
2. **`inventario.html`** — tabela com busca instantânea e filtros (disciplina, sistema, status); linha → ficha. (US-A01)
3. **`alertas.html`** — painel ordenado por urgência (vencidos primeiro), badge de contagem, filtro por seção/sistema, **Exportar CSV**. (US-C01/C01b)
4. **`importar.html`** — upload → relatório dry-run (contadores + tabela colorida por severidade) → **Confirmar importação**.
5. **`ficha.html`** — visão read-only com status calculado em destaque.

### Fluxo de estreia
Subir o container → `importar.html` → enviar CSV real → revisar dry-run → confirmar → dashboard e inventário populados com os 496 instrumentos e status calculado.

---

## 7. Testes

- **Motor de status** (`calibracao.py`): tabela de casos cobrindo cada regra e a precedência, com `hoje` fixo; casos de divergência flag×data.
- **Importador** (`importacao.py`): amostra real do CSV — datas US, moeda, flag→status, `\n` no cabeçalho, `#VALUE!`, duplicatas, linha-fantasma.
- **API**: smoke test dos endpoints (preview/commit, lista com filtros, kpis, alertas csv).

---

## 8. Fora de escopo desta fatia (próximos passos da Fase 1)

Registrados para não se perderem; cada um entra num ciclo spec→plano→implementação próprio:
- **Autenticação JWT** (cookie HttpOnly, perfis) — **pendência a decidir antes do uso multiusuário**.
- QR Code + geração de etiquetas (PRD 6.6).
- Upload de certificado PDF vinculado ao instrumento (PRD 6.2).
- Tabela de calibrações como histórico (hoje as datas estão denormalizadas no instrumento).
- Gestão de laboratórios + acreditação (PRD 6.4).
- Página pública por seção sem login (PRD 6.3).
- Export de alertas/relatórios em **PDF** (WeasyPrint) — nesta fatia só CSV.

Fases 2–4 do PRD (metrologia/rastreabilidade, gestão/custos, IoT/IA) seguem o roadmap original.

---

## 9. Riscos específicos da fatia

| Risco | Mitigação |
|---|---|
| Dados do Excel inconsistentes (datas, flags divergentes) | Dry-run com relatório linha a linha + `divergencia_flag`; nada grava antes da confirmação (PRD R2) |
| Semântica enganosa das colunas do CSV | Mapeamento documentado (Seção 3) e fixado em testes do importador |
| Duplicatas reais no inventário | Detecção e report no dry-run; decisão fica com o usuário |
```
