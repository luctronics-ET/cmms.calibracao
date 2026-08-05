# Schema do Banco de Dados — SisCalib

SQLite em `$SISCALIB_DATA/siscalib.db`. Migrations via Alembic.

## Tabelas

### `instrumento`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INTEGER PK | Autoincremento |
| codigo_interno | TEXT UNIQUE | Código interno / TAG |
| equipamento | TEXT | Nome/descrição do instrumento |
| disciplina | TEXT | Disciplina metrológica |
| fabricante | TEXT | Fabricante |
| modelo | TEXT | Modelo |
| serial | TEXT | Número de série |
| patrimonio | TEXT | Número de patrimônio |
| setor | TEXT | Setor/localização |
| familia | TEXT | Família metrológica |
| tipo | TEXT | Tipo de instrumento |
| grandeza | TEXT | Grandeza medida |
| unidade | TEXT | Unidade de medida |
| faixa_min | REAL | Faixa mínima |
| faixa_max | REAL | Faixa máxima |
| resolucao | REAL | Resolução / EMP |
| classe | TEXT | Classe de prioridade (derivada do IGP) |
| igp_fator_* | REAL | 5 fatores IGP (1–3 cada) |
| igp | REAL | Índice Global de Prioridade (calculado) |
| ativo | BOOLEAN | Instrumento ativo |
| data_validade | DATE | Validade da última calibração (desnormalizado) |
| status | TEXT | VALIDO / A_VENCER_30 / VENCIDO / SEM_DATA / BAIXADO |

### `calibracao`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INTEGER PK | Autoincremento |
| instrumento_id | INTEGER FK | Instrumento calibrado |
| data_calibracao | DATE | Data de realização |
| data_validade | DATE | Data de vencimento |
| resultado | TEXT | APROVADO / REPROVADO / CONDICIONADO |
| certificado | TEXT | Path do PDF em /data/uploads |
| laboratorio_id | INTEGER FK | Laboratório executor |
| item_contrato_id | INTEGER FK | Item do contrato vinculado (opcional) |
| observacoes | TEXT | Observações |
| origem | TEXT | INTERNA / EXTERNA |

### `laboratorio`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INTEGER PK | Autoincremento |
| nome | TEXT | Nome do laboratório |
| acreditacao | TEXT | Número de acreditação RBC/CGCRE |
| validade_acreditacao | DATE | Validade da acreditação |
| contato | TEXT | E-mail ou telefone |
| ativo | BOOLEAN | Laboratório ativo |

### `contrato`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INTEGER PK | Autoincremento |
| numero | TEXT | Número do contrato/ATA |
| laboratorio_id | INTEGER FK | Laboratório fornecedor |
| data_inicio | DATE | Início de vigência |
| data_fim | DATE | Fim de vigência |
| valor_total | REAL | Valor total contratado (R$) |

### `item_contrato`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INTEGER PK | Autoincremento |
| contrato_id | INTEGER FK | Contrato pai |
| descricao | TEXT | Descrição do item de serviço |
| preco_unitario | REAL | Preço unitário (R$) |
| quantidade | INTEGER | Quantidade contratada |
| saldo | INTEGER | Saldo disponível (decrementado por calibração vinculada) |

## Migrations (ordem)

| Revision | Descrição |
|---|---|
| `160033a39d59` | instrumento — tabela base |
| `c00a5e8ec52e` | base metrológica (família, grandeza, unidade, IGP) |
| `ba250c7eb571` | calibracao |
| `a5e01e43b2d8` | laboratorio |
| `2dae72dfab3d` | contrato |
| `bcf9de0eaaac` | catalogo_preco (deprecado) |
| `d1a2b3c4e5f6` | rename instrumento.sistema → setor |
| `e2b3c4d5f6a7` | contrato.fornecedor → laboratorio_id (FK) |
| `f3a4b5c6d7e8` | calibracao.item_contrato_id (FK opcional) |
| `a4b5c6d7e8f9` | contrato.laboratorio_id NOT NULL |
| `b5c6d7e8f9a0` | drop catalogo_preco (visão derivada) |

## Status de calibração (enum)

| Status | Critério |
|---|---|
| `VALIDO` | data_validade > hoje + 60 dias |
| `A_VENCER_60` | data_validade entre hoje e hoje+60d |
| `A_VENCER_30` | data_validade entre hoje e hoje+30d |
| `A_VENCER_7` | data_validade entre hoje e hoje+7d |
| `VENCIDO` | data_validade < hoje |
| `SEM_DATA` | nenhuma calibração registrada |
| `BAIXADO` | instrumento inativo |
