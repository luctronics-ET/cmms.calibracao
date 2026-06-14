# Design — Registro de Calibrações (PRD §6.2)

**Data:** 2026-06-14
**Repo:** xCalibracao (SisCalib)
**Fase:** 1 (MVP) — feature P0
**Status:** aprovado, pronto para plano de implementação

## Objetivo

Substituir o controle de validade "solto" no instrumento (`data_ultima_calibracao` /
`data_validade` gravados direto) por um **histórico de calibrações** por instrumento
(entidade `calibracao`, 1→N), com laboratório, certificado PDF, resultado e cálculo
automático de validade e status. Atende US-B01, US-B03, US-B05 e o requisito 6.2 do PRD.

## Decisões de brainstorming

1. **Campos do instrumento viram derivados + backfill.** `data_ultima_calibracao`,
   `data_validade` e `status_operacional` passam a ser sempre recalculados a partir da
   última calibração. Migração cria 1 "calibração de origem" (`origem='IMPORTACAO'`) para
   cada instrumento que já tem data importada → histórico íntegro desde o início.
2. **Laboratório em texto livre agora, FK depois.** Sem entidade Laboratório (Fase 6.4);
   campos texto na calibração. Migração futura promove para FK.
3. **Entrada na UI em dois lugares:** seção "Calibrações" na ficha (modal) **e** página
   dedicada `calibracao.html`, ambas reusando o mesmo form e os mesmos endpoints.
4. **Automação por resultado:** APROVADO / APROVADO_COM_RESTRICOES → status ATIVO e
   `validade = data_calibracao + ciclo_meses`; REPROVADO → status REPROVADO e validade null
   (instrumento bloqueado p/ uso, cumpre US-B05). `ciclo_meses` vem do instrumento (snapshot
   na calibração), **não** é editável por calibração nesta entrega.

## Modelo de dados

Nova tabela `calibracao`:

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `instrumento_id` | FK → instrumento.id | indexed; ondelete cascade |
| `data_calibracao` | Date | obrigatório |
| `data_validade` | Date \| null | derivada = data_calibracao + ciclo_meses; null se REPROVADO |
| `ciclo_meses` | int | snapshot de instrumento.ciclo_meses (default 12) |
| `resultado` | Enum Resultado | APROVADO / APROVADO_COM_RESTRICOES / REPROVADO |
| `laboratorio` | str \| null | texto livre |
| `laboratorio_cnpj` | str \| null | |
| `acreditacao_rbc` | bool | default False |
| `numero_cgcre` | str \| null | |
| `numero_certificado` | str \| null | |
| `custo` | Numeric(12,2) \| null | |
| `responsavel` | str \| null | quem recebeu o certificado |
| `certificado_path` | str \| null | `uploads/{inst_id}/cert_{cal_id}.pdf` |
| `origem` | str | MANUAL (novas) / IMPORTACAO (backfill) |
| `observacoes` | str \| null | |
| `criado_em` | DateTime | server_default now() |

- Novo `enum.Enum Resultado` em `backend/models.py`.
- Relação `Instrumento.calibracoes` (lazy), consultada ordenada por `data_calibracao desc, id desc`.

### Recompute (regra central)

Função **pura** nova em `backend/calibracao.py`:

```
derivar_de_calibracoes(calibracoes: list) -> DadosDerivados
    # pega a calibração mais recente (data_calibracao, desempate id)
    # retorna (data_ultima_calibracao, data_validade, status_operacional_sugerido)
    # lista vazia -> (None, None, None) = não altera
```

Validade já vem gravada na própria calibração (calculada no POST). `status_operacional_sugerido`:
REPROVADO na última calibração → `StatusOperacional.REPROVADO`; senão → `StatusOperacional.ATIVO`.

Helper em `backend/servico.py` (`aplicar_derivados(inst, db)`) lê as calibrações do
instrumento, chama `derivar_de_calibracoes`, grava os 3 campos no instrumento e dá commit.
O motor `calcular_status` existente permanece intacto (continua lendo `data_validade`).

## API

Novo router `backend/routers/calibracoes.py`, prefixo `/api/v1`, registrado em `backend/main.py`.

| Método | Rota | Função |
|--------|------|--------|
| GET | `/instrumentos/{id}/calibracoes` | histórico (desc por data) → `ListaCalibracoes` |
| POST | `/instrumentos/{id}/calibracoes` | registra (JSON `CalibracaoIn`) → grava validade derivada → `aplicar_derivados` → retorna `{instrumento: InstrumentoOut, calibracao: CalibracaoOut}` |
| POST | `/instrumentos/{id}/calibracoes/{cal_id}/certificado` | upload PDF (valida `application/pdf`, reusa padrão `_salvar`) → `CalibracaoOut` |
| DELETE | `/instrumentos/{id}/calibracoes/{cal_id}` | remove → `aplicar_derivados` → `InstrumentoOut` |

Schemas novos em `backend/schemas.py`: `CalibracaoIn`, `CalibracaoOut`, `ListaCalibracoes`,
`RegistroCalibracaoOut` (`{instrumento, calibracao}`).

- `CalibracaoIn` **não** recebe `id`, `data_validade`, `ciclo_meses`, `origem`,
  `certificado_path`, `status` — todos derivados/servidor. Recebe `data_calibracao`
  (obrigatório), `resultado`, e os campos de laboratório/certificado/custo/responsável/obs.
- `data_validade` calculada no servidor: REPROVADO → null; senão `data_calibracao` +
  `ciclo_meses` (do instrumento) meses. **Sem nova dependência** (`dateutil` não está no
  projeto): helper puro `adicionar_meses(data, meses)` em `backend/calibracao.py`, que soma
  meses e faz clamp do dia ao último dia do mês de destino (ex.: 31/01 + 1 mês → 28/02).
  Coberto por teste unitário (incl. virada de ano e fim de mês).
- 404 se instrumento ou calibração não existir; 415 se upload não for PDF.

## UI

Função compartilhada `renderFormCalibracao(instId, onSaved)` em `app.js` (form + POST +
upload opcional) e `renderHistoricoCalibracoes(instId)` (tabela do histórico). Usadas nos
dois pontos de entrada:

- **Ficha (modal):** abaixo do resumo, seção "Calibrações" = histórico + botão
  "Registrar calibração" que revela o form inline. Ciclo mostrado read-only (herdado do
  instrumento). Ao salvar → recarrega histórico + linha do inventário (`todos`/`visiveis`).
- **Página `calibracao.html`:** seletor de instrumento no topo (reusa busca existente) +
  o mesmo form/histórico abaixo. Entra na NAV global do `app.js`.

Coluna/badge de certificado: link 📎 para `uploads/{inst_id}/cert_{cal_id}.pdf` (mount estático já existe).

## Migração / backfill

Migration Alembic nova `*_calibracao.py`:

1. `create_table('calibracao', ...)` com FK e índice em `instrumento_id`.
2. **Backfill data-only, idempotente:** para cada instrumento com `data_ultima_calibracao`
   preenchida e **sem** calibração de origem ainda, insere
   `Calibracao(origem='IMPORTACAO', data_calibracao=data_ultima_calibracao,
   data_validade=data_validade, ciclo_meses=ciclo_meses, resultado='APROVADO',
   laboratorio=organizacao_calibradora, numero_certificado=certificado_ref)`.

Campos do instrumento **não** são apagados — viram saída derivada e o backfill garante
coerência. Roda no volume Docker populado via `alembic upgrade head` (já no `entrypoint.sh`).

## Testes (TDD)

- **Motor puro** (`tests/test_calibracao.py`): `derivar_de_calibracoes` — lista vazia →
  (None,None,None); 1 registro; múltiplos com desempate por data/id; REPROVADO → validade null.
- **API** (`tests/test_calibracoes_api.py`): POST cria e recalcula validade/status;
  APROVADO → ATIVO + validade = data+ciclo; REPROVADO → REPROVADO + validade null;
  calibração mais recente prevalece; GET histórico ordenado desc; DELETE recalcula a partir
  do que sobrou; upload valida content-type (415 não-PDF); 404 instrumento/calibração inexistente.
- **Backfill:** aplicar sobre instrumentos com data → 1 calibração `IMPORTACAO` por
  instrumento + derivados coerentes; idempotência (rodar 2× não duplica).

## Fora de escopo (YAGNI)

- Edição de calibração (usar delete + re-add).
- Pontos de calibração, incerteza, condições ambientais → Fase 2 §6.7.
- FK de laboratório e cadastro de laboratório → Fase 6.4.
- Calibração interna → Fase 2 §6.13.
