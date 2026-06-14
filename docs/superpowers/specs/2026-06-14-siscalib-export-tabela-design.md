# Design — Exportação + Tabela com Ordenação e Filtros Multi-seleção

**Data:** 2026-06-14
**Projeto:** xCalibracao / SisCalib
**Escopo:** No inventário — exportar a visão atual para CSV/XLSX/PDF (arquivos reais gerados no backend) e tornar a tabela ordenável por coluna com filtros multi-seleção (checkbox) no cabeçalho. Filtro/ordenação client-side; exportação reflete exatamente a visão filtrada+ordenada.
**Status:** Aprovado pelo usuário; pronto para plano
**Continuação de:** `2026-06-14-siscalib-edicao-massa-design.md`

---

## 1. Objetivo

Dar ao inventário capacidade de relatório e análise:
- **Exportar** a lista atual (após filtros/ordenação) em **CSV, XLSX e PDF**.
- **Ordenar** por qualquer coluna (clique no cabeçalho).
- **Filtrar** por múltiplos valores via **checkbox** por coluna categórica (Disciplina, Sistema, Status, Família, Prioridade).

Decisões do usuário (2026-06-14): exportação **gerada no backend** (arquivos reais; cliente envia os IDs visíveis); filtro/ordenação **no cliente** sobre os ~498 já carregados.

---

## 2. Tabela client-side (busca + ordenação + filtros multi-seleção)

Muda o fluxo de dados de `inventario.html`: **carrega todos os instrumentos uma vez** (`GET /instrumentos` sem params, ~498) e processa busca/ordenação/filtros **no navegador**. Re-consulta apenas após edições (lote/cadastro) ou refresh manual.

### Estado client-side
- `todos` — lista completa carregada do backend.
- `filtrosCol` — `{coluna: Set(valoresSelecionados)}` para os filtros multi-seleção.
- `ordenacao` — `{coluna, dir}` (dir: `asc` | `desc` | null).
- `busca` — texto livre (sem acento, igual ao backend).
- `selecionados` — Set de ids (edição em lote, já existente).
- `visiveis()` — função pura que aplica busca → filtros → ordenação sobre `todos` e devolve a lista exibida. É a **fonte única** para render e exportação.

### Ordenação
Clique no cabeçalho alterna `asc → desc → sem ordem`, com indicador ▲/▼. Chaves por coluna:
- `data_validade` → ordena por data (nulos por último).
- `status` (validade) → ordem de urgência (VENCIDO < A_VENCER_7 < … < VALIDO < SEM_DATA < BAIXADO).
- demais (`codigo`, `equipamento`, `marca/modelo`, `disciplina`, `sistema`) → texto sem acento, case-insensitive.
Sort estável (preserva ordem anterior em empates).

### Filtros multi-seleção
Ícone de funil no cabeçalho das colunas categóricas: **Disciplina, Sistema, Status, Família, Prioridade**. Abre um popover com checkboxes dos **valores distintos presentes em `todos`** + "Marcar todos"/"Limpar". Semântica: **E** entre colunas diferentes, **OU** dentro da mesma coluna (nenhum marcado = sem filtro naquela coluna). Funil destacado quando há seleção ativa. Fecha no clique fora/Esc.

### Toolbar e integração
- Toolbar final: **busca** + **Novo** + grupo **Exportar** (Seção 4).
- Os dropdowns atuais (disciplina/sistema/status/família/classe) são **removidos** — substituídos pelos filtros de coluna.
- Edição em lote e seleção por checkbox permanecem; **qualquer mudança de busca/filtro/ordenação limpa a seleção** (não agir sobre itens ocultos).
- A coluna de status mantém os badges; a primeira coluna continua com o checkbox de seleção (não recebe ordenação/filtro).

---

## 3. Backend de exportação

Novo router `backend/routers/exportacao.py`; incluído em `backend/main.py`.

`POST /api/v1/instrumentos/export`
- **Corpo** (`ExportRequest` em `schemas.py`): `{ "ids": list[int], "formato": "csv" | "xlsx" | "pdf" }`.
- Busca os instrumentos por id e os ordena **na ordem do array `ids`** (preserva a ordenação do cliente). Passa cada um por `instrumento_para_out` (status/IGP/nomes de FK frescos).
- **Resposta:** `Response` com bytes do arquivo, `media_type` e `Content-Disposition: attachment; filename=inventario_<YYYY-MM-DD>.<ext>` (data via `date.today()`).

### Dependências novas (puras-Python)
- `openpyxl` — geração de XLSX.
- `fpdf2` — geração de PDF.
Adicionadas ao `requirements.txt`; instaladas no rebuild do Docker.

### Colunas
- **CSV + XLSX (completo):** codigo_interno, codigo_patrimonial, serial, equipamento, marca, modelo, familia_nome, tipo_nome, grandeza_nome, unidade_simbolo, faixa (min…max), resolucao, emp, disciplina, sistema, localizacao (org→unidade→seção→bancada), status_operacional, status (validade), dias_restantes, data_ultima_calibracao, data_validade, ciclo_meses, igp, classe_prioridade, observacoes. Datas em ISO; cabeçalho legível na 1ª linha. XLSX com a primeira linha em negrito e auto-largura simples.
- **PDF (resumo compacto, A4 paisagem):** codigo, equipamento, sistema, validade, status, IGP/classe. Cabeçalho da organização ("CMASM / DME — Inventário de Calibração"), data de geração e total de itens. (PDF não comporta todas as colunas; é um relatório de visão geral, enquanto XLSX/CSV trazem o dado completo.)

### Validações
- `ids` vazio → **400** ("nada a exportar").
- `formato` fora do conjunto → **422** (validação do schema via `Literal`).
- ids inexistentes são ignorados (exporta os encontrados, na ordem dada).

### Estrutura de código
- `exportacao.py` separa: `_linhas_completas(instrumentos)` (lista de dicts/colunas), `_gerar_csv`, `_gerar_xlsx`, `_gerar_pdf` — funções focadas e testáveis; o endpoint orquestra.

---

## 4. Frontend de exportação

Na toolbar, grupo **Exportar** com botões **CSV**, **XLSX**, **PDF**. Ao clicar:
- monta `ids` = `visiveis().map(i => i.id)` (ordem atual);
- se vazio, avisa "nada a exportar" e não chama;
- `SDK.exportar(ids, formato)` → `POST /instrumentos/export` retornando **blob**; dispara download via `URL.createObjectURL` + `<a download>`;
- indicador "gerando…" no botão durante a requisição.

`SDK.exportar(ids, formato)` em `app.js`: `fetch` com `Accept` apropriado, retorna `await r.blob()` (lança em erro HTTP).

---

## 5. Arquivos

| Arquivo | Mudança |
|---|---|
| `requirements.txt` | + `openpyxl`, `fpdf2` |
| `backend/schemas.py` | + `ExportRequest` (ids + formato Literal) |
| `backend/routers/exportacao.py` | **novo** — endpoint + geradores csv/xlsx/pdf |
| `backend/main.py` | inclui router de exportação |
| `frontend/app.js` | + `SDK.exportar`; helpers de ordenação/filtro de tabela |
| `frontend/inventario.html` | cabeçalhos ordenáveis, popovers de filtro multi-seleção, botões de export; fluxo client-side |
| `frontend/siscalib.css` | estilos de funil/sort/popover e grupo de export |
| `tests/test_api.py` | testes do endpoint de exportação |

---

## 6. Testes

- **CSV:** `POST /export {ids,"csv"}` → `text/csv`; contém os códigos dos ids; ordem preservada conforme `ids`.
- **XLSX:** media type `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`; bytes legíveis por `openpyxl.load_workbook` (confere nº de linhas = itens+1 e cabeçalho).
- **PDF:** `application/pdf`; bytes começam com `%PDF`.
- **Ordem dos ids preservada**; **ids inexistentes ignorados** (export dos válidos).
- **`ids` vazio → 400**; **formato inválido → 422**.
- **Regressão:** os 81 testes atuais continuam passando.
- **Frontend:** verificação de sintaxe/refs (sort, popovers, `SDK.exportar`); validação visual/e2e no fechamento.

---

## 7. Riscos

| Risco | Mitigação |
|---|---|
| Exportar "tudo" enviando centenas de IDs num POST | ~500 ids é payload pequeno; aceitável. Se crescer muito, migrar para export por filtros server-side |
| PDF com muitas linhas (centenas) ficar pesado/longo | fpdf2 pagina automaticamente; PDF é resumo de 6 colunas; aceitável para ~500 |
| Mudança do fluxo para client-side quebrar a edição em lote | `visiveis()` é a fonte única; seleção é limpa em mudança de filtro; testes de regressão + e2e |
| Acento/encoding em CSV no Excel | CSV em UTF-8 com BOM para abrir corretamente no Excel pt-BR |
| Deps nativas de PDF | Uso de `fpdf2` (pura-Python), evitando WeasyPrint e suas deps de sistema |
