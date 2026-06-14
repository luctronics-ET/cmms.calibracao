# Design — Base Metrológica + Cadastro Completo (6.1)

**Data:** 2026-06-14
**Projeto:** xCalibracao / SisCalib
**Escopo:** Completar o cadastro de instrumentos (PRD 6.1) com a base de dados metrológica — taxonomia RBC/INMETRO, especificação técnica, localização, estado operacional, anexos e o modelo de criticidade/priorização IGP. Inclui a tela de cadastro/edição.
**Status:** Aprovado pelo usuário; pronto para plano de implementação
**Continuação de:** `2026-06-14-siscalib-fatia-fina-design.md` (fatia já entregue e mergeada)

---

## 1. Objetivo e contexto

A fatia fina entregou um rastreador de inventário e validade. Faltam os campos **metrológicos** do 6.1 — sem eles o sistema não suporta as Fases 2/3 (pontos de calibração, deriva, conformidade, regras de calibração interna).

Este ciclo:
- Cria as **tabelas de domínio** (família, tipo, grandeza, unidade) com taxonomia oficial da RBC/INMETRO.
- Expande `instrumento` com classificação, especificação técnica, localização, estado operacional e anexos.
- Adota o modelo **IGP** (Índice Global de Prioridade do Equipamento) de criticidade/priorização, baseado no documento de referência do usuário (`.reference_readonly/Modelo técnico e direto.txt`), em substituição ao "Classe A/B/C/D" simples do PRD.
- Entrega a **tela de cadastro/edição** (hoje só há ficha read-only).

**Decisões do usuário (2026-06-14):**
- Manter os 496 registros existentes; colunas novas são anuláveis e preenchidas aos poucos.
- Construir a tela de cadastro/edição neste ciclo.
- Modelar **uma** grandeza/faixa principal por instrumento agora; multi-faixa fica para a Fase 2.
- `familia_metrologica` = 15 grupos oficiais da RBC; `tipo` = semente expansível.
- IGP com faixas **reescaladas** para o intervalo real 7–21.
- Abandonar o enum Classe A/B/C/D em favor do IGP.

Stack inalterado: FastAPI + SQLAlchemy/Alembic + SQLite + frontend vanilla. (O documento de referência cita "Laravel/SQLite" apenas como enquadramento; a implementação segue o stack existente.)

---

## 2. Tabelas de domínio (lookup) e sementes

Quatro tabelas, cada uma com `id`, `nome`, `ativo` (bool, default true), `ordem` (int). Seed idempotente via migração/seed.

| Tabela | Campos extra | Semente |
|---|---|---|
| `familia_metrologica` | — | **15 grupos RBC/INMETRO**: Acústica e Vibrações; Alta Frequência e Telecomunicações; Dimensional; Eletricidade e Magnetismo; Físico-Química; Força, Torque e Dureza; Massa; Óptica; Pressão; Radiações Ionizantes; Temperatura e Umidade; Tempo e Frequência; Vazão e Velocidade de Fluidos; Viscosidade; Volume e Massa Específica |
| `unidade_medida` | `simbolo` (str) | V, A, Ω, Hz, m, mm, µm, kg, g, N·m, Pa, bar, °C, %UR, L, mL… (SI e usuais) |
| `grandeza` | `familia_id` → familia, `unidade_padrao_id` → unidade | Tensão DC, Tensão AC, Corrente DC, Resistência, Frequência, Comprimento, Massa, Torque, Pressão, Temperatura, Umidade… (cada uma ligada à família e a uma unidade padrão) |
| `tipo_instrumento` | `familia_id` → familia (opcional) | Multímetro, Osciloscópio, Fonte DC, Calibrador, Gerador de Funções, Paquímetro, Micrômetro, Torquímetro, Manômetro, Termômetro, Balança, Dinamômetro… |

Hierarquia: na tela, escolher a **família** filtra os `tipo` e `grandeza` exibidos; escolher a grandeza sugere a `unidade` padrão. `familia` é conjunto fechado (norma); as demais são expansíveis (semente inicial + crescem conforme uso). `ativo=false` "aposenta" um item sem apagar (preserva FKs históricas).

---

## 3. Novas colunas em `instrumento`

Todas **aditivas e anuláveis** (preservam os 496 registros). Em `backend/models.py`:

**Identificação**
- `codigo_patrimonial` (str, indexado, **único quando preenchido** — índice único parcial `WHERE codigo_patrimonial IS NOT NULL`)

**Classificação (FK → Seção 2)**
- `familia_id`, `tipo_id`, `grandeza_id`, `unidade_id`

**Especificação técnica (grandeza/faixa principal)**
- `faixa_min` (Numeric), `faixa_max` (Numeric)
- `resolucao` (str — ex.: "0,01 mm", "1 µV")
- `emp` (str — Erro Máximo Permitido/exatidão, ex.: "±(0,5% + 2d)")
- (o `faixa` textual atual permanece como legado; não é mais preenchido por cadastro novo)

**Localização hierárquica (campos planos)**
- `organizacao`, `unidade_org`, `secao`, `bancada` (str). `sistema` (sistema de armas) permanece.

**Estado operacional**
- `status_operacional` (Enum `StatusOperacional`: ATIVO, EM_CALIBRACAO, EM_MANUTENCAO, REPROVADO, BLOQUEADO, BAIXADO), default ATIVO.

**Anexos**
- `foto_path`, `manual_path` (str) → arquivos em `/data/uploads/{instrumento_id}/`.

**Criticidade/priorização IGP**
- `fu`, `nc`, `ab`, `cm`, `ci` (Integer, anuláveis, valores 1–3) — ver Seção 4.

### Status derivado x status operacional
O **status de validade** (VALIDO/VENCIDO/A_VENCER_*/SEM_DATA/BAIXADO) continua calculado pelo motor existente (`calibracao.py`) a partir das datas — inalterado. O `status_operacional` é **manual** e ortogonal (um instrumento pode ser ATIVO e VENCIDO). Dashboard/alertas podem passar a excluir itens com `status_operacional` em {BAIXADO, BLOQUEADO}. (Nota: há um BAIXADO em cada eixo — o derivado vem de `flag_origem` do CSV legado; o operacional é o estado gerenciado. Não se fundem neste ciclo.)

---

## 4. Modelo IGP (criticidade e priorização)

Substitui Classe A/B/C/D. Cinco variáveis em `instrumento`, inteiros **1–3** (anuláveis):

| Campo | Variável | 1 | 2 | 3 |
|---|---|---|---|---|
| `fu` | Frequência de uso | <5 usos/mês | 5–20/mês | >20/mês |
| `nc` | Necessidade crítica | baixo impacto | importante | crítico |
| `ab` | Abundância/redundância | alta redundância | média | única/insubstituível |
| `cm` | Criticidade metrológica | tolerância alta | moderada | baixa tolerância |
| `ci` | Custo de indisponibilidade | mínimo | moderado | afeta operação |

**Motor puro** `calcular_igp(fu, nc, ab, cm, ci, hoje?)` em `backend/criticidade.py` (sem I/O, testável):
```
IGP = fu·1 + nc·2 + ab·1 + cm·2 + ci·1      # 7 (tudo=1) … 21 (tudo=3)
```

**Faixas reescaladas (intervalo real 7–21):**
| IGP | classe_prioridade | Ação recomendada |
|---|---|---|
| 18–21 | Máxima | calibração mais frequente, backup, substituto |
| 14–17 | Média | manter plano normal |
| 11–13 | Baixa | ampliar intervalos, agrupar calibrações |
| 7–10 | Muito baixa | ampliar intervalos / candidato a não-cronometrado |

Constantes de limiar no topo do módulo (configuráveis). Se **qualquer** das 5 variáveis estiver vazia → `igp=null`, `classe_prioridade="NAO_CLASSIFICADO"`. `igp` e `classe_prioridade` são **derivados** (recalculados a cada request/edição, nunca persistidos), como o status de validade.

**Relação com o PRD:** `cm` (criticidade metrológica 1–3) governa a futura regra da Fase 2 "instrumento muito crítico não pode ser calibrado internamente" (`cm=3` ≈ a antiga "Classe A"). Não se cria mais o enum A/B/C/D.

**Fora de escopo (futuro):** modulação automática de `ciclo_meses` pelo IGP (item 4 do documento) — alterar periodicidade exige histórico/justificativa (PRD 6.9); tratar em ciclo próprio.

---

## 5. Migração, API, cadastro/edição e upload

### Migração (Alembic)
Uma revisão aditiva: cria as 4 tabelas de domínio; adiciona as novas colunas a `instrumento` (todas anuláveis); cria índice único parcial em `codigo_patrimonial`. Seed das sementes idempotente (re-rodar não duplica). Os 496 registros permanecem; campos novos vazios.

### Endpoints novos `/api/v1/`
- `GET /dominios` → `{familias, tipos, grandezas, unidades}`; aceita `?familia_id=` para filtrar tipos/grandezas.
- `POST /instrumentos` (criar) e `PUT /instrumentos/{id}` (editar) — validam obrigatórios e patrimônio único; resposta inclui IGP/classe derivados.
- `POST /instrumentos/{id}/foto` e `POST /instrumentos/{id}/manual` — upload multipart → `/data/uploads/{id}/`; servidos em `/uploads/...`.
- `GET /instrumentos` ganha filtros `familia_id` e `classe_prioridade`.

**Obrigatórios no cadastro:** `equipamento`, `familia_id`, `tipo_id`, `status_operacional`, `ciclo_meses`. Demais (grandeza, faixa, IGP, patrimônio, anexos) opcionais — permite preenchimento gradual. Patrimônio, quando informado, deve ser único (409 em duplicata).

### Frontend
- **`cadastro.html`** (criar/editar): campos do 6.1 agrupados — Identificação · Classificação · Especificação · Localização · Criticidade (IGP) · Anexos. Selects encadeados família→(tipo, grandeza); grandeza sugere unidade. Os 5 controles 1–3 do IGP exibem `igp` e `classe_prioridade` **ao vivo** (cálculo no cliente espelhando o motor, com os mesmos limiares). Validação de obrigatórios; aviso de patrimônio duplicado.
- **`ficha.html`**: exibe os novos campos + IGP/classe + foto/manual; botão "Editar" → cadastro.
- **`inventario.html`**: filtros por família e por classe de prioridade.

### Validação de upload
- `foto`: aceita imagem (content-type image/*; extensões jpg/png/webp).
- `manual`: aceita PDF (application/pdf).
- Arquivo salvo como `/data/uploads/{id}/foto.<ext>` e `manual.pdf`; caminho relativo gravado em `foto_path`/`manual_path`.

---

## 6. Testes
- **Motor `calcular_igp`** (`backend/criticidade.py`): IGP correto; faixas com casos de fronteira (7, 10, 11, 13, 14, 17, 18, 21); qualquer variável nula → null/NAO_CLASSIFICADO.
- **Domínios**: seed cria as 15 famílias e as sementes; idempotência (rodar 2x não duplica).
- **API criar/editar**: obrigatórios validados; patrimônio único duplicado → 409; IGP derivado no retorno; FKs inválidas rejeitadas.
- **`GET /dominios`** e filtros novos do inventário (familia_id, classe_prioridade).
- **Upload**: foto aceita imagem e rejeita não-imagem; manual aceita PDF e rejeita não-PDF; arquivo persistido e servível.
- **Regressão**: os 48 testes da fatia anterior continuam passando.

---

## 7. Arquivos (visão)

| Arquivo | Mudança |
|---|---|
| `backend/models.py` | novas colunas + enum `StatusOperacional`; 4 modelos de domínio (em `backend/models.py` ou `backend/models_dominio.py` se ficar grande) |
| `backend/criticidade.py` | **novo** — motor IGP puro |
| `backend/dominios.py` | **novo** — seed idempotente das tabelas de domínio |
| `backend/schemas.py` | `InstrumentoOut` ampliado (novos campos + igp/classe); `InstrumentoIn` (criar/editar); `DominiosOut` |
| `backend/servico.py` | aplica IGP além do status; resolve nomes de FK para o output |
| `backend/routers/instrumentos.py` | POST/PUT, filtros novos, upload de foto/manual |
| `backend/routers/dominios.py` | **novo** — `GET /dominios` |
| `backend/main.py` | inclui router de domínios; monta `/uploads` |
| `alembic/versions/*` | revisão aditiva + seed |
| `frontend/cadastro.html` | **novo** — form criar/editar |
| `frontend/ficha.html`, `inventario.html`, `app.js` | novos campos, filtros, IGP ao vivo |

---

## 8. Riscos

| Risco | Mitigação |
|---|---|
| Campos novos ficam muito tempo vazios (preenchimento manual de ~500 itens) | Tudo anulável; IGP/grandeza opcionais; sistema funciona com preenchimento parcial; relatório futuro de "completude do cadastro" |
| Faixas do IGP reescaladas não refletirem a intenção do gestor | Limiares em constantes; fácil reajustar; documentado no spec |
| Taxonomia RBC evoluir ou faltar item | `familia` fechada mas com `ativo`; tipos/grandezas expansíveis sem migração (linhas novas) |
| Upload de arquivos grandes/maliciosos | Validação de content-type/extensão; tamanho limitado; armazenamento local sob `/data` |
| `codigo_patrimonial` único conflitar com dados legados ruins | Índice único **parcial** (só quando não-nulo); 409 informativo no cadastro |
