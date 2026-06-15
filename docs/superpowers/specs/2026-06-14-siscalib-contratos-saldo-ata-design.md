# Design — Contratos & Saldo da ATA (sub-projeto #1 de 3)

**Data:** 2026-06-14
**Repo:** xCalibracao (SisCalib)
**Fase:** 3 (Gestão/Custos) — primeira fatia do "Lote de Calibração"
**Status:** aprovado, pronto para plano de implementação

## Contexto

Primeiro de três sub-projetos que, juntos, replicam o "Lote de Calibração" do protótipo
descartado `calibracao_erp.html` na stack real (FastAPI/SQLite + HTML/JS vanilla):
**#1 Contratos & Saldo da ATA** (este) → #2 Catálogo de Preços → #3 Lotes. Cada um é
entregável e mergeável sozinho. Cobre parte do PRD §6.14 (gestão de contratos e ARPs).

## Objetivo

Cadastrar contratos/ATAs com seus itens (linhas com quantidade, valor e consumo), exibir o
saldo restante por item e agregado, e alertar contratos com vigência próxima do fim ou saldo
baixo. O consumo (`usado`) é manual nesta entrega; o #3 (Lotes) passará a incrementá-lo.

## Decisões de brainstorming

1. **`usado` manual agora, automático no #3.** Cada `ItemContrato` tem `usado` editável;
   `saldo = quantidade − usado` é derivado. Sem consumo automático nesta fatia.
2. **Alertas:** badge na lista de contratos (vigência + saldo) **e** seção nova no Painel de
   Alertas (`alertas.html`).
3. **Status de vigência reusa** `calcular_status(vigencia_fim, None, hoje)` (limiares 7/30/60d).

## Modelo de dados

Nova tabela `contrato`:

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `numero` | str | obrigatório (ex.: "ATA MQT 129/2025") |
| `tipo` | Enum ContratoTipo | ATA / CONTRATO / CMS |
| `fornecedor` | str \| null | |
| `objeto` | str \| null | descrição/objeto |
| `vigencia_inicio` | Date \| null | |
| `vigencia_fim` | Date \| null | |
| `valor_total` | Numeric(14,2) \| null | teto registrado |
| `ativo` | bool | default True |
| `observacoes` | str \| null | |
| `criado_em` / `atualizado_em` | DateTime | server_default now() / onupdate |

Nova tabela `item_contrato`:

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `contrato_id` | FK → contrato.id | `ondelete CASCADE`, indexed |
| `numero` | str \| null | número do item na ATA (ex.: "14") |
| `descricao` | str \| null | |
| `quantidade` | int | default 0 |
| `valor_unitario` | Numeric(12,2) \| null | |
| `usado` | int | default 0 |
| `observacoes` | str \| null | |

`ContratoTipo` é um novo `enum.Enum` em `models.py`. Relação `Contrato.itens` com
`cascade="all, delete-orphan"` **sem** `passive_deletes` — assim o ORM deleta os filhos
ao remover o contrato (funciona em SQLite sem depender do PRAGMA; o `ondelete=CASCADE` do
FK fica como rede de segurança no nível do banco).

## Derivados

Por item (`ItemContratoOut`):
- `saldo = quantidade - usado`
- `valor_saldo = max(saldo, 0) * valor_unitario` (0 se `valor_unitario` é None)

Por contrato (`ContratoOut`):
- `status_vigencia = calcular_status(vigencia_fim, None, hoje).status.value` + `dias_restantes`
- `valor_saldo_total = Σ valor_saldo dos itens`
- `saldo_percent = valor_saldo_total / valor_total` (None se `valor_total` é None/0)
- `status_saldo`: `ESGOTADO` se `valor_saldo_total <= 0`; `BAIXO` se `saldo_percent` definido e `< 0.20`; senão `OK`

Motor puro novo em `backend/contratos_calc.py` (sem I/O): `saldo_item(quantidade, usado,
valor_unitario)` e `status_saldo(valor_saldo_total, valor_total)`. Testável isolado.

## API

Novo router `backend/routers/contratos.py`, prefixo `/api/v1`, registrado em `main.py`.
Rota estática `/contratos/alertas` declarada ANTES de `/contratos/{contrato_id}`.

| Método | Rota | Função |
|--------|------|--------|
| GET | `/contratos` | lista (cada um com status_vigencia, valor_saldo_total, saldo_percent, status_saldo; **sem** itens) → `ListaContratos` |
| GET | `/contratos/alertas` | contratos com vigência em {VENCIDO,A_VENCER_*} OU status_saldo em {BAIXO,ESGOTADO}, ordenados (vencidos/esgotados primeiro) |
| GET | `/contratos/{id}` | um contrato com `itens: [ItemContratoOut]` + agregados → `ContratoOut` (404) |
| POST | `/contratos` | cria (201) → `ContratoOut` |
| PUT | `/contratos/{id}` | atualiza (replace dos campos do contrato; NÃO mexe nos itens) → `ContratoOut` |
| DELETE | `/contratos/{id}` | remove; itens caem por cascade (handler deleta itens explicitamente antes, p/ SQLite) → 204 |
| POST | `/contratos/{id}/itens` | adiciona item (201) → `ContratoOut` atualizado |
| PUT | `/contratos/{id}/itens/{item_id}` | atualiza item → `ContratoOut` atualizado |
| DELETE | `/contratos/{id}/itens/{item_id}` | remove item → `ContratoOut` atualizado |

Schemas: `ContratoIn` (campos do contrato, sem itens), `ContratoOut` (com `itens` + derivados),
`ListaContratos`, `ItemContratoIn`, `ItemContratoOut` (com `saldo`, `valor_saldo`). Os endpoints
de item retornam o `ContratoOut` recalculado para a UI atualizar agregados de uma vez.

> Nota PUT contrato é replace-total dos campos do contrato (consistente com instrumentos/labs);
> não afeta os itens (gerenciados pelos subendpoints).

## Frontend

- **`contratos.html` (nova):** mirror de `laboratorios.html`. Tabela de contratos: Número ·
  Tipo · Fornecedor · Vigência (`fmtData(vigencia_fim)` + `badgeStatus(status_vigencia)`) ·
  Valor total · Saldo (`valor_saldo_total` + badge de `status_saldo`) · Ações (Abrir/Editar/Excluir).
  - "Novo contrato" / "Editar" → modal (`abrirModal`) com os campos de `ContratoIn`.
  - "Abrir" → modal de detalhe com a **tabela de itens** (item nº · descrição · quant · valor
    unit · usado · saldo · valor saldo) + botões adicionar/editar/excluir item (consomem os
    subendpoints; cada ação recarrega o detalhe a partir do `ContratoOut` devolvido).
  - `badgeStatus` aceita os valores de vigência (já existentes) e os de saldo (mapear
    OK→verde, BAIXO→amber, ESGOTADO→vermelho via classes `.bdg`).
  - `esc()` em todo valor de usuário.
- **NAV:** item "Contratos" (ícone `file-earmark-text`) após "Laboratórios".
- **`alertas.html`:** nova seção "Contratos a vencer / saldo baixo" consumindo
  `GET /contratos/alertas` (tabela: Número · Fornecedor · Vigência+badge · Saldo+badge).

## Migração

Migration Alembic schema-only: `create_table('contrato')` + `create_table('item_contrato')`
com FK `ondelete='CASCADE'` e índice em `contrato_id`. `down_revision` = head atual.
Sem backfill.

## Testes (TDD)

- **Motor puro** (`tests/test_contratos_calc.py`): `saldo_item` (saldo, valor_saldo, clamp em
  0 quando usado>quant, None em valor_unitario); `status_saldo` (OK ≥20%, BAIXO <20%,
  ESGOTADO ≤0, None em valor_total None).
- **API** (`tests/test_contratos_api.py`): POST contrato + GET lista (status_vigencia,
  agregados); GET /{id} com itens; POST/PUT/DELETE item recalcula `valor_saldo_total`/
  `status_saldo`; vigência futura→VALIDO, passada→VENCIDO; saldo baixo (item quase todo usado →
  status_saldo BAIXO/ESGOTADO); `/contratos/alertas` traz vencendo OU saldo baixo, ordenado;
  DELETE contrato remove itens; 404s.

## Fora de escopo (próximos sub-projetos)

- Catálogo de preços e vínculo preço↔item de contrato → #2.
- Consumo automático do `usado` via lotes → #3.
- Integração PNCP (PRD §6.14) → futuro.
