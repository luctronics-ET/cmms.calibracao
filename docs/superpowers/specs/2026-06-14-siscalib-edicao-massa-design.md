# Design — Edição em Massa no Inventário (modal + multi-seleção)

**Data:** 2026-06-14
**Projeto:** xCalibracao / SisCalib
**Escopo:** Melhorias de UX no inventário — ficha em modal ao clicar na linha, multi-seleção por checkbox e edição em lote dos itens selecionados via tabela editável por item. Inclui endpoint de atualização parcial (PATCH).
**Status:** Aprovado pelo usuário; pronto para plano
**Continuação de:** `2026-06-14-siscalib-base-metrologica-design.md`

---

## 1. Objetivo

Acelerar o preenchimento dos campos metrológicos dos ~497 instrumentos (hoje majoritariamente vazios) e melhorar a consulta rápida, sem sair da tela de inventário:
- **Clicar na linha → modal da ficha** (consulta rápida, sem navegar).
- **Checkbox de multi-seleção** + **editar selecionados** num modal com **tabela editável por item**.
- **PATCH parcial** no backend, base segura para qualquer edição que altere só alguns campos.

Fora de escopo: edição inline célula-a-célula direto na grade (descartada — sobrepõe-se à edição em lote com mais risco de erro).

---

## 2. Infra de modal + ficha em modal

Em `frontend/app.js`, componente de modal reutilizável:
- `abrirModal(titulo, htmlConteudo, acoes)` — cria overlay (fundo escurecido), título, área de conteúdo e rodapé de ações; fecha no **X**, **Esc** e **clique no fundo**.
- `fecharModal()`.
- CSS do modal em `frontend/siscalib.css` (overlay fixo, cartão centralizado, responsivo).

Helper compartilhado de renderização da ficha (evita duplicar markup entre `ficha.html` e o modal):
- `renderFichaResumo(i)` → HTML com badges (status de validade, status_operacional, IGP/classe, divergência) + tabela de campos principais + bloco de anexos. Usado pela página `ficha.html` e pelo modal.

**Comportamento:** clique na linha (exceto na célula do checkbox) → `SDK.get('/instrumentos/'+id)` → `abrirModal` com `renderFichaResumo(i)` e ações **Abrir ficha completa** (`ficha.html?id=`) e **Editar** (`cadastro.html?id=`). O link no código da 1ª coluna permanece (navegação direta intacta).

---

## 3. Multi-seleção

Na tabela de `frontend/inventario.html`:
- **Coluna de checkbox** como primeira coluna; checkbox no cabeçalho = **selecionar/desmarcar todos** os itens da consulta atual (respeita filtros/busca ativos).
- Estado de seleção em memória: `Set` de ids (`selecionados`).
- **Trocar filtro/busca limpa a seleção** (evita selecionar itens fora da visão atual).
- **Barra de ação** acima da tabela, visível quando `selecionados.size ≥ 1`: `N selecionado(s)` + botão **Editar selecionados** + **Limpar seleção**.
- Clique no checkbox **não** abre o modal de ficha (distinguir alvo do clique: `event.target` é o checkbox vs resto da linha).

---

## 4. Modal de edição em lote (tabela editável por item)

Dois passos no modal:

**Passo 1 — escolher campos a editar.** Checkboxes dos campos preenchíveis em massa: `codigo_patrimonial`, `familia_id`, `tipo_id`, `grandeza_id`, `unidade_id`, `status_operacional`, `ciclo_meses`, `secao`, `bancada`, `fu`, `nc`, `ab`, `cm`, `ci`. Marcar só o que vai mexer mantém a tabela estreita.

**Passo 2 — tabela editável.** Uma linha por item selecionado:
- Colunas read-only de identidade: `codigo_interno` (ou patrimonial), `equipamento`.
- Uma coluna editável por campo escolhido no Passo 1, com o controle adequado: `<select>` para família/tipo/grandeza/unidade/status_operacional; `<input type=number>` para ciclo e IGP (1–3); `<input type=text>` para patrimônio/seção/bancada.
- Pré-preenche cada célula com o valor atual do item.
- **"Preencher coluna ↓"** no cabeçalho de cada campo: copia o valor da 1ª linha para as demais (conveniência; valores continuam editáveis por linha).

Rodapé: **Salvar tudo** (com progresso "salvando X/N") e **Cancelar**.

**Salvar:** para cada linha, monta um corpo só com os campos escolhidos e chama `PATCH /api/v1/instrumentos/{id}`. Erros por linha (ex.: 409 patrimônio duplicado) são coletados e exibidos ao final, sem abortar as demais. Ao concluir, fecha o modal, limpa a seleção e recarrega o inventário.

**Simplificação consciente:** nos selects de família/tipo/grandeza da tabela em lote, mostrar **todas** as opções (sem cascata família→tipo por linha — complexo demais por linha). A cascata completa permanece no cadastro individual (`cadastro.html`). Os selects são populados uma vez via `GET /dominios`.

---

## 5. Backend — atualização parcial (PATCH)

`PATCH /api/v1/instrumentos/{id}` em `backend/routers/instrumentos.py`:
- Schema `InstrumentoPatch` (em `backend/schemas.py`): todos os campos de `InstrumentoIn` como opcionais (sem obrigatórios); IGP com `Field(None, ge=1, le=3)`.
- Aplica somente os campos presentes: `dados.model_dump(exclude_unset=True)`; converte enums (`disciplina`, `status_operacional`) quando presentes; `setattr` nos demais.
- Valida patrimônio único ignorando o próprio id → 409; 404 se inexistente.
- `db.commit()` + `db.refresh()`; retorna `InstrumentoOut` (status e IGP recalculados pelo serviço).
- Reaproveita os helpers existentes `_checar_patrimonio` e a lógica de conversão (refatorar `_aplicar` para suportar parcial, ou criar `_aplicar_parcial`).

Frontend: `SDK.patch(path, body)` em `app.js` (espelha `SDK.put`, tratando 409).

O salvar-tudo do lote faz **um PATCH por item** (loop no cliente). Para dezenas de itens em LAN é instantâneo e mantém o backend simples/testável. Endpoint batch fica como otimização futura, se necessário.

Benefício colateral: o PATCH oferece edição parcial segura que o `PUT`-replace não tinha.

---

## 6. Arquivos

| Arquivo | Mudança |
|---|---|
| `backend/schemas.py` | + `InstrumentoPatch` (todos opcionais) |
| `backend/routers/instrumentos.py` | + `PATCH /instrumentos/{id}`; refatorar conversão p/ parcial |
| `frontend/app.js` | + `abrirModal`/`fecharModal`, `renderFichaResumo`, `SDK.patch` |
| `frontend/siscalib.css` | + estilos de modal e barra de seleção |
| `frontend/inventario.html` | coluna checkbox + selecionar-todos, barra de ação, modal de ficha no clique, modal de edição em lote |
| `frontend/ficha.html` | usar `renderFichaResumo` (DRY com o modal) |
| `tests/test_api.py` | testes do PATCH |

---

## 7. Testes

- **PATCH parcial preserva o resto**: criar instrumento com vários campos; `PATCH` só `familia_id`; confirmar que `equipamento`/`ciclo_meses`/demais permanecem.
- **PATCH recalcula IGP**: enviar `fu/nc/ab/cm/ci` → `igp`/`classe_prioridade` corretos no retorno.
- **PATCH 404** em inexistente; **409** em patrimônio duplicado (ignorando o próprio id).
- **PATCH não exige obrigatórios** (corpo parcial com 1 campo é aceito).
- **Regressão**: os 75 testes atuais continuam passando.
- Frontend: verificação de sintaxe/refs (modal, checkbox, SDK.patch); validação visual/e2e no fechamento (subir container, selecionar itens, editar em lote, conferir persistência).

---

## 8. Riscos

| Risco | Mitigação |
|---|---|
| Edição em lote aplicar valor errado a muitos itens | Passo 1 (escolher campos) + tabela mostra cada item; PATCH só toca campos escolhidos; nada é alterado sem "Salvar tudo" |
| Selects sem cascata no lote permitirem tipo de família "errada" | Aceito nesta fatia; cascata completa no cadastro individual; correção pontual sempre possível |
| Muitos PATCH sequenciais lentos | LAN + ~dezenas de itens = rápido; progresso exibido; batch fica como evolução futura |
| Seleção perdida ao filtrar surpreender o usuário | Comportamento documentado e previsível (filtro limpa seleção); barra mostra a contagem atual |
