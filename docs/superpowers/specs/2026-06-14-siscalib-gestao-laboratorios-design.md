# Design — Gestão de Laboratórios (PRD §6.4)

**Data:** 2026-06-14
**Repo:** xCalibracao (SisCalib)
**Fase:** 1 (MVP) — feature P0
**Status:** aprovado, pronto para plano de implementação

## Objetivo

Cadastrar laboratórios de calibração (externos) com seus dados de acreditação RBC/CGCRE,
vincular (opcionalmente) cada calibração a um laboratório registrado, e alertar quando a
acreditação de um laboratório estiver próxima do vencimento. Atende US-D01 (parcial) e o
requisito §6.4 do PRD. Sucede o "laboratório como texto livre" introduzido no Registro de
Calibrações (§6.2).

## Decisões de brainstorming

1. **Vínculo FK opcional + texto como snapshot.** `Calibracao` ganha `laboratorio_id`
   (FK nullable, `ondelete SET NULL`). Os campos texto existentes (`laboratorio`,
   `laboratorio_cnpj`, `numero_cgcre`, `acreditacao_rbc`) viram **snapshot**: ao registrar
   uma calibração com `laboratorio_id`, o backend copia razão social/CNPJ/CGCRE/RBC do lab
   para esses campos, de modo que o histórico sobrevive a edição/exclusão do laboratório.
   Calibrações antigas (texto livre, sem FK) permanecem como estão. **Sem migração de dados.**
2. **Escopo de grandezas em texto livre** (campo `escopo`), não estruturado.
3. **Alerta de acreditação:** badge de status na lista de laboratórios **e** uma seção nova
   no Painel de Alertas existente (`alertas.html`) para acreditações a vencer.
4. **Reuso do motor de status:** a validade da acreditação usa o mesmo
   `calcular_status(validade, None, hoje)` de `backend/calibracao.py` (limiares 7/30/60d,
   enum VENCIDO/A_VENCER_7/30/60/VALIDO/SEM_DATA). Sem motor novo.

## Modelo de dados

Nova tabela `laboratorio`:

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `razao_social` | str | obrigatório |
| `cnpj` | str \| null | |
| `endereco` | str \| null | |
| `contato` | str \| null | nome do contato |
| `telefone` | str \| null | |
| `email` | str \| null | |
| `numero_cgcre` | str \| null | número da acreditação CGCRE/INMETRO |
| `acreditado_rbc` | bool | default False |
| `escopo` | str \| null | grandezas acreditadas (texto livre) |
| `acreditacao_validade` | Date \| null | validade da acreditação |
| `ativo` | bool | default True |
| `observacoes` | str \| null | |
| `criado_em` | DateTime | server_default now() |
| `atualizado_em` | DateTime | server_default now(), onupdate now() |

Alteração em `Calibracao`: adicionar coluna `laboratorio_id: int | null`
(`ForeignKey("laboratorio.id", ondelete="SET NULL")`, indexed). Os campos texto continuam
existindo e passam a ser snapshot quando há FK.

## Status de acreditação (reuso)

Sem motor novo. A serialização do laboratório calcula:
`st = calcular_status(lab.acreditacao_validade, None, hoje)` → expõe
`status_acreditacao = st.status.value` e `dias_restantes = st.dias_restantes`.
(`flag_origem=None` → sem categoria; `divergencia_flag` ignorado para labs.)

## API

Novo router `backend/routers/laboratorios.py`, prefixo `/api/v1`, registrado em `main.py`.
**Importante:** definir as rotas estáticas (`/laboratorios/alertas`) ANTES das dinâmicas
(`/laboratorios/{lab_id}`) para evitar conflito de path.

| Método | Rota | Função |
|--------|------|--------|
| GET | `/laboratorios` | lista (cada item com `status_acreditacao` + `dias_restantes`) → `ListaLaboratorios` |
| GET | `/laboratorios/alertas` | labs com acreditação em {VENCIDO, A_VENCER_7/30/60}, ordenados por urgência → lista de `LaboratorioOut` |
| GET | `/laboratorios/{id}` | um laboratório → `LaboratorioOut` (404 se não existe) |
| POST | `/laboratorios` | cria (201) → `LaboratorioOut` |
| PUT | `/laboratorios/{id}` | atualiza (replace) → `LaboratorioOut` |
| DELETE | `/laboratorios/{id}` | remove; o handler **explicitamente** zera `laboratorio_id` nas calibrações vinculadas antes de deletar (não confia no SET NULL do DB, que é não-confiável em SQLite sem pragma); snapshot texto permanece → 204 |
| GET | `/laboratorios/{id}/calibracoes` | histórico de calibrações desse lab (where `laboratorio_id == id`, desc por data) → `ListaCalibracoes` (reusa `CalibracaoOut`) |

Schemas novos em `schemas.py`: `LaboratorioIn` (sem id/timestamps/status), `LaboratorioOut`
(com `status_acreditacao`, `dias_restantes`), `ListaLaboratorios`.

Alteração em `CalibracaoIn`: adicionar `laboratorio_id: int | null = None`.
Alteração em `CalibracaoOut`: adicionar `laboratorio_id: int | null`.

### Snapshot no registro de calibração

No `registrar` (router de calibrações), se `dados.laboratorio_id` vier preenchido:
- carregar o `Laboratorio` (404 se não existe);
- definir `cal.laboratorio_id`, e snapshot: `cal.laboratorio = lab.razao_social`,
  `cal.laboratorio_cnpj = lab.cnpj`, `cal.numero_cgcre = lab.numero_cgcre`,
  `cal.acreditacao_rbc = lab.acreditado_rbc`.
- Se `laboratorio_id` for None, mantém o comportamento atual (texto livre dos campos enviados).

## Frontend

- **`laboratorios.html` (nova página):** mirror de `cadastro.html`/`calibracao.html`
  (shell, vendor CSS). Tabela: Razão social · CNPJ · CGCRE · Acreditação (validade + badge
  de status reusando `badgeStatus`) · Escopo · Ações (Editar/Excluir). Botão "Novo
  laboratório". Form de criar/editar em modal (reusa `abrirModal` do `app.js`), com todos os
  campos. Excluir → confirm → DELETE → recarrega.
- **NAV:** item "Laboratórios" (ícone `building` ou `award`) na array `NAV` do `app.js`,
  seguindo o padrão `[href, icon, label]`. Posição: após "Calibrações".
- **`renderFormCalibracao` (app.js):** adicionar um `<select>` "Laboratório" no topo do form,
  populado por `GET /laboratorios` (opção vazia = usar texto livre). Se um lab for escolhido,
  incluir `laboratorio_id` no POST. O campo texto `laboratorio` permanece como fallback.
- **`alertas.html`:** abaixo da lista de instrumentos, nova seção "Acreditações a vencer"
  consumindo `GET /laboratorios/alertas` (tabela: laboratório · CGCRE · validade · status badge).

## Migração

Migration Alembic `*_laboratorio.py` (schema-only, padrão do projeto):
1. `create_table('laboratorio', ...)`.
2. `op.add_column('calibracao', sa.Column('laboratorio_id', sa.Integer, nullable=True))`
   + `create_foreign_key(..., 'calibracao', 'laboratorio', ['laboratorio_id'], ['id'],
   ondelete='SET NULL')` + index.

Nota SQLite/Alembic: alterar FK/coluna em SQLite requer `batch_alter_table`. Usar
`with op.batch_alter_table('calibracao') as batch_op:` para o add_column + create FK.
Sem backfill de dados (decisão 1).

## Testes (TDD)

- **API laboratório** (`tests/test_laboratorios_api.py`): POST cria (201) e GET lista com
  `status_acreditacao` calculado (validade futura → VALIDO; passada → VENCIDO; ~20 dias →
  A_VENCER_30); GET /{id} (200 e 404); PUT atualiza; DELETE remove (204) e a calibração
  vinculada fica com `laboratorio_id=None` mas conserva o texto snapshot; `/laboratorios/alertas`
  retorna só os vencidos/a vencer, ordenados; `/laboratorios/{id}/calibracoes` lista as do lab.
- **Snapshot na calibração** (estender `tests/test_calibracoes_api.py`): registrar calibração
  com `laboratorio_id` de um lab criado → a calibração retorna `laboratorio_id` setado e os
  campos texto (`laboratorio`, `numero_cgcre`) preenchidos com os dados do lab; registrar sem
  `laboratorio_id` mantém o comportamento texto-livre.
- Conftest: nenhuma mudança estrutural (usa `create_all`); criar labs via API nos testes.

## Fora de escopo (YAGNI)

- Escopo estruturado por grandeza/família + validação de cobertura.
- Migração dos textos de laboratório antigos para FK.
- KPI de laboratórios no dashboard.
- Histórico de mudança de acreditação.
