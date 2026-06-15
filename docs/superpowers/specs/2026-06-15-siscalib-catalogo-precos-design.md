# Design — Catálogo de Preços (sub-projeto #2 de 3)

**Data:** 2026-06-15
**Repo:** xCalibracao (SisCalib)
**Fase:** 3 (Gestão/Custos) — segunda fatia do "Lote de Calibração"
**Status:** aprovado, pronto para plano de implementação

## Contexto

Segundo de três sub-projetos que reimplementam o "Lote de Calibração" do protótipo
descartado `.reference_readonly/calibracao_erp.html` na stack real. #1 Contratos & Saldo da
ATA (✅ mergeado) → **#2 Catálogo de Preços** (este) → #3 Lotes. Depende do #1 (vincula a
`item_contrato`). Cobre parte do PRD §6.14/§6.15 (base de custos).

## Objetivo

Cadastrar, por tipo de instrumento, as opções de preço de calibração (fornecedor × contrato),
cada uma com preço próprio e vínculo opcional a um item de contrato (para o #3 calcular custo
do lote e consumir saldo da ATA). Semear os dados reais da ATA 129/2025 do protótipo.

## Decisões de brainstorming

1. **Preço próprio + vínculo opcional ao item.** Cada `CatalogoPreco` tem seu `preco` e um
   `item_contrato_id` OPCIONAL (FK → `ItemContrato`). Opções de ATA linkam ao item (p/ saldo
   no #3); opções internas/CMS têm só preço, sem contrato.
2. **Semear os dados reais** (ATA 129/2025: contrato + ~22 itens + entradas de catálogo) via
   módulo de startup idempotente, casando o tipo do protótipo → `TipoInstrumento` por nome
   normalizado; não-casados são pulados e logados.

## Modelo de dados

Nova tabela `catalogo_preco`:

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `tipo_id` | FK → tipo_instrumento.id | obrigatório, indexed |
| `fornecedor` | str \| null | |
| `preco` | Numeric(12,2) \| null | preço próprio da opção |
| `item_contrato_id` | FK → item_contrato.id \| null | `ondelete SET NULL`, indexed |
| `ativo` | bool | default True |
| `observacoes` | str \| null | |
| `criado_em` / `atualizado_em` | DateTime | server_default / onupdate |

Relações (lazy): `tipo` (TipoInstrumento), `item_contrato` (ItemContrato). Nenhuma alteração
em tabelas existentes.

## Derivados (serialização)

`CatalogoPrecoOut` expõe os campos + derivados de exibição:
- `tipo_nome` = `catalogo.tipo.nome` (ou None)
- `item_numero` = `item_contrato.numero` (None se sem vínculo)
- `contrato_id` / `contrato_numero` = do `item_contrato.contrato` (None se sem vínculo)

Sem motor de status (não há datas).

## API

Novo router `backend/routers/catalogo.py`, prefixo `/api/v1`, registrado em `main.py`.

| Método | Rota | Função |
|--------|------|--------|
| GET | `/catalogo` | lista; filtro opcional `?tipo_id=` (serve o #3) → `ListaCatalogo` |
| GET | `/catalogo/{id}` | um registro → `CatalogoPrecoOut` (404) |
| POST | `/catalogo` | cria (201); valida `tipo_id` existe (404 senão) e, se enviado, `item_contrato_id` existe (404) |
| PUT | `/catalogo/{id}` | atualiza (replace) → `CatalogoPrecoOut` |
| DELETE | `/catalogo/{id}` | remove → 204 |

Schemas: `CatalogoPrecoIn` (tipo_id obrigatório, fornecedor, preco, item_contrato_id, ativo,
observacoes), `CatalogoPrecoOut` (com derivados), `ListaCatalogo`.

## Seed dos dados reais — `backend/seed_ata.py`

Módulo de startup idempotente (padrão `backend/dominios.py` / `backend/backfill.py`), rodado
pelo `entrypoint.sh` **após** `python -m backend.backfill`. Os dados de origem
(`CATALOG_DEFAULT`, `ATA_ITEMS_SEED`, `ATA_INFO`) são transcritos do arquivo de referência
`.reference_readonly/calibracao_erp.html` (dados do próprio projeto) para constantes Python no
módulo. O seed:

1. **Contrato:** cria `Contrato(numero="ATA MQT 129/2025", tipo=ATA, fornecedor="MQT Serviços
   Metrológicos Ltda", valor_total=112114.00, vigencia_fim=None)` se ainda não existir
   (idempotente por `numero`). Guarda a ref.
2. **Itens:** para cada entrada de `ATA_ITEMS_SEED` (`{item, desc, quant, valor, usado, saldo}`),
   cria `ItemContrato(contrato_id, numero=str(item), descricao=desc, quantidade=quant,
   valor_unitario=valor, usado=usado)` se não existir item com aquele `numero` nesse contrato.
3. **Catálogo:** para cada tipo de `CATALOG_DEFAULT` (chave = nome do protótipo) e cada opção
   (`{forn, contrato, preco, item, tipo}`):
   - casa o nome do tipo com um `TipoInstrumento` por **nome normalizado** (sem acento,
     case-insensitive — função `_norm`); se não casar, **pula e loga** (não cria tipo).
   - resolve `item_contrato_id`: se a opção tem `item` (≠ "—"), busca o `ItemContrato` do
     contrato ATA com `numero == str(item)`; senão None.
   - cria `CatalogoPreco(tipo_id, fornecedor=forn, preco=preco, item_contrato_id, ativo=True)`
     se ainda não existir registro igual (idempotente por `(tipo_id, fornecedor,
     item_contrato_id)`).
   - imprime um resumo: N criados, N pulados (lista os nomes de tipo não-casados).

> Ressalva: o matching de tipo é best-effort. Os nomes do protótipo (ex.: "MULTÍMETRO") nem
> sempre coincidem com o domínio (ex.: "Multímetro"); a normalização resolve acentos/caixa, mas
> tipos inexistentes no domínio ficam de fora (logados) — o usuário pode cadastrá-los manualmente.

## Frontend

- **`catalogo.html` (nova):** mirror de `laboratorios.html`/`contratos.html`. Tabela: Tipo ·
  Fornecedor · Preço (money) · Contrato/Item (`contrato_numero` + "· item " + `item_numero`,
  ou "—") · Ativo · Ações (Editar/Excluir). Filtro por tipo (select de `/dominios` tipos).
  - "Novo"/"Editar" → modal (`abrirModal`): tipo (select de `/dominios` tipos, obrigatório),
    fornecedor, preco (number), item_contrato (select OPCIONAL — carregado de `/contratos`:
    opções "{contrato.numero} · item {item.numero} — {descricao}" achatando os itens de todos
    os contratos; value = item.id), ativo (checkbox), observacoes. Salvar → POST/PUT → recarrega.
  - "Excluir" → confirm → `SDK.del` → recarrega.
  - `money()` helper local; `esc()` em todo valor de usuário.
- **NAV:** item "Catálogo" (ícone `tags` ou `cash-coin`) após "Contratos".

## Migração

Migration Alembic schema-only: `create_table('catalogo_preco')` com FKs (`tipo_id` →
tipo_instrumento, `item_contrato_id` → item_contrato `ondelete SET NULL`) e índices.
`down_revision` = head atual (`2dae72dfab3d`). Sem dados (o seed roda no startup, não na migração).

## Testes (TDD)

- **API** (`tests/test_catalogo_api.py`): POST cria + GET lista com `tipo_nome`; filtro
  `?tipo_id=`; POST com `item_contrato_id` → derivados `contrato_numero`/`item_numero`
  populados; POST com tipo_id inexistente → 404; POST com item_contrato_id inexistente → 404;
  PUT atualiza; DELETE (204); GET 404.
- **Seed** (`tests/test_seed_ata.py`): rodar `seed_ata(db)` cria o contrato ATA + 22 itens +
  os catálogos dos tipos que casam (criar no teste alguns `TipoInstrumento` com nomes
  equivalentes p/ garantir ≥1 match); idempotência (rodar 2× não duplica contrato/itens/
  catálogo); tipos não-casados são pulados (retorno do seed reporta contagens). O `seed_ata`
  retorna um dict de contagens `{contrato, itens, catalogo, tipos_nao_casados}` para o teste.

## Fora de escopo (vai pro #3)

- Uso do catálogo no construtor de lote (custo, seleção de opção por item).
- Consumo automático do saldo da ATA.
- Edição em massa de preços / reajuste.
