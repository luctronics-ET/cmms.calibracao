# Design — Etiquetas com QR Code (PRD §6.6)

**Data:** 2026-06-15
**Repo:** xCalibracao (SisCalib)
**Fase:** 1 (MVP) — feature P0
**Status:** aprovado, pronto para plano de implementação

## Objetivo

Gerar etiquetas por instrumento (código, status, validade, QR Code) imprimíveis individualmente
ou em lote, com o QR apontando para uma ficha pública (sem login) lida por qualquer leitor.
Atende PRD §6.6 e US-A04.

## Decisões de brainstorming

1. **Geração client-side + impressão do navegador.** QR gerado no browser por lib JS vendorizada
   (MIT, sem CDN); página de etiquetas em HTML com CSS `@media print`. Sem nova dependência Python.
2. **Ficha pública = página estática + endpoint público dedicado, por `id`.** `publica.html?id=N`
   consome `GET /api/v1/publico/instrumentos/{id}` (subconjunto curado). Isola o que é público para
   quando o JWT existir (`/publico/*` permanece liberado).

## Componentes

### 1. Endpoint público — `backend/routers/publico.py`

`GET /api/v1/publico/instrumentos/{id}` → `InstrumentoPublicoOut` (404 se não existir).
Campos **curados, não-sensíveis** (reusa `calcular_status` para o status derivado):

| Campo | Origem |
|-------|--------|
| `id`, `codigo_interno`, `codigo_patrimonial` | instrumento |
| `equipamento`, `marca`, `modelo` | instrumento |
| `tipo_nome` | `instrumento.tipo.nome` |
| `secao`, `sistema` | instrumento |
| `status` + `status_label` | `calcular_status` (VALIDO/VENCIDO/A_VENCER_*/SEM_DATA/BAIXADO) |
| `status_operacional` | instrumento |
| `data_ultima_calibracao`, `data_validade`, `dias_restantes` | instrumento + status |

**NÃO expõe:** custo_estimado/contratado, observações, anexos, fatores IGP, dados de calibração
internos. Schema novo `InstrumentoPublicoOut` em `schemas.py`; serializador
`instrumento_publico_para_out(inst, hoje)` em `servico.py`. Router registrado em `main.py`.

### 2. Página pública — `frontend/publica.html`

- Layout **standalone, sem sidebar** (não chama `montarShell`). Carrega `vendor` CSS/fontes +
  `siscalib.css` + `app.js` (só para reaproveitar `badgeStatus`/`fmtData`/`esc`; nenhuma chamada
  que monte o shell). Legível no celular (viewport mobile, fonte grande para o código).
- Lê `?id=` da query → `GET /publico/instrumentos/{id}`. Exibe: código (interno + patrimonial)
  em destaque, equipamento, **badge de status** + validade, última calibração, tipo/marca/modelo,
  localização (seção/sistema), e `status_operacional`. 404 → "Instrumento não encontrado".
- Aplica o tema (claro/escuro) via o init de tema já existente em `app.js` (que roda no topo do
  script) — fica coerente com o resto.

### 3. Página de etiquetas — `frontend/etiquetas.html`

- Lê `?ids=1,2,3` da query (1 = individual; N = lote). Para cada id, busca via
  `GET /publico/instrumentos/{id}` (mesmo dado curado).
- Renderiza um **card de etiqueta** por instrumento numa grade: logo MB pequeno + código interno
  (grande) + código patrimonial, equipamento, status (badge) + validade (`fmtData`), e o **QR**
  codificando `${location.origin}/publica.html?id=${id}` (usa o IP/host atual da LAN
  automaticamente). QR via a lib vendorizada (renderiza em `<canvas>` ou SVG).
- **Toolbar (não imprime):** botão "Imprimir / Salvar PDF" (`window.print()`) + "Voltar ao
  inventário". CSS `@media print`: esconde a toolbar/sidebar, grade de etiquetas com tamanho fixo
  (~ etiqueta de 70×40 mm, ajustável), `page-break` adequado. Sem sidebar (não chama `montarShell`).
- Erro por id inexistente: card com "Instrumento N não encontrado" (não quebra o lote).

### 4. Integração — `frontend/inventario.html` + ficha

- **Inventário:** botão **"Etiquetas"** na toolbar (grupo de export) que abre
  `etiquetas.html?ids=<ids visíveis na ordem atual>` — reusa exatamente a fonte de ids do export
  (`visiveis()`/seleção). Se houver linhas selecionadas por checkbox, usa as selecionadas; senão,
  as visíveis (mesma regra do export atual — verificar e seguir).
- **Ficha / modal:** botão **"Gerar etiqueta"** → `etiquetas.html?ids=<id>` (individual).

### 5. Lib de QR vendorizada — `frontend/vendor/`

Vendorizar uma biblioteca **MIT** de geração de QR puro-JS (ex.: `qrcode-generator`). O implementador
**obtém o arquivo real** via `npm pack <lib>` (registry acessível neste ambiente), extrai o `.js`
para `frontend/vendor/qrcode-generator.min.js` e **commita junto o arquivo de licença**
(`frontend/vendor/qrcode-generator.LICENSE`). Nenhuma fonte da lib é transcrita à mão; nenhum CDN
em runtime. `etiquetas.html` referencia o arquivo vendorizado.

## Testes (TDD)

- **Endpoint público** (`tests/test_publico_api.py`): GET retorna os campos curados + `status`
  derivado (instrumento com validade futura → VALIDO; passada → VENCIDO); `tipo_nome` resolvido;
  **404** para id inexistente; **assert de não-vazamento** — a resposta NÃO contém as chaves
  `custo_estimado`, `custo_contratado`, `observacoes`, `fu`/`nc`/`ab`/`cm`/`ci`.
- **Frontend** (QR/etiquetas/impressão/página pública): smoke test no navegador (Playwright) —
  página pública carrega e mostra status; etiquetas renderizam o QR (um `<canvas>`/`<svg>` por id);
  o QR codifica a URL `…/publica.html?id=N`; `window.print()` não quebra. Sem testes unitários de UI.

## Migração / dados

Nenhuma — feature de leitura/apresentação. Sem mudança de schema.

## Fora de escopo

- Página pública **por seção** (visão geral) — item separado da Fase 1.
- Geração server-side de PDF de etiquetas.
- Personalização de layout/tamanho de etiqueta por configuração (tamanho fixo, ajustável só no CSS).
