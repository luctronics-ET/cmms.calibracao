# Schema do Banco de Dados — SisCalib

Banco SQLite em `$SISCALIB_DATA/siscalib.db`. Migrations gerenciadas via Alembic.

## Tabelas principais

### `instrumento`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INTEGER PK | ID automático |
| tag | TEXT UNIQUE | Identificador único (ex: TAG-001) |
| descricao | TEXT | Descrição do instrumento |
| fabricante | TEXT | Fabricante |
| modelo | TEXT | Modelo |
| n_serie | TEXT | Número de série |
| patrimonio | TEXT | Número de patrimônio |
| setor | TEXT | Setor/localização |
| familia | TEXT | Família metrológica (RBC/INMETRO) |
| tipo | TEXT | Tipo de instrumento |
| grandeza | TEXT | Grandeza medida |
| unidade | TEXT | Unidade de medida |
| faixa_min | REAL | Faixa mínima de medição |
| faixa_max | REAL | Faixa máxima de medição |
| resolucao | REAL | Resolução / EMP |
| igp | REAL | Índice Global de Prioridade (1–3, 5 fatores) |
| ativo | BOOLEAN | Instrumento ativo no inventário |

### `calibracao`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INTEGER PK | ID automático |
| instrumento_id | INTEGER FK | Referência ao instrumento |
| data_calibracao | DATE | Data de calibração |
| data_vencimento | DATE | Data de vencimento do certificado |
| resultado | TEXT | APROVADO / REPROVADO / CONDICIONADO |
| certificado_path | TEXT | Caminho do PDF do certificado em /data/uploads |
| laboratorio_id | INTEGER FK | Laboratório executor |
| item_contrato_id | INTEGER FK | Item de contrato vinculado (opcional) |
| observacoes | TEXT | Observações livres |

### `laboratorio`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INTEGER PK | ID automático |
| nome | TEXT | Nome do laboratório |
| acreditacao | TEXT | Número de acreditação RBC/CGCRE |
| validade_acreditacao | DATE | Validade da acreditação |
| contato | TEXT | E-mail ou telefone |
| ativo | BOOLEAN | Laboratório ativo |

### `contrato`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INTEGER PK | ID automático |
| numero | TEXT | Número do contrato/ATA |
| laboratorio_id | INTEGER FK | Laboratório fornecedor |
| data_inicio | DATE | Início de vigência |
| data_fim | DATE | Fim de vigência |
| valor_total | REAL | Valor total contratado |

### `item_contrato`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INTEGER PK | ID automático |
| contrato_id | INTEGER FK | Referência ao contrato |
| descricao | TEXT | Descrição do item |
| preco_unitario | REAL | Preço unitário (R$) |
| quantidade | INTEGER | Quantidade contratada |
| saldo | INTEGER | Saldo disponível (quantidade - usado) |

## Migrations (ordem cronológica)

| Revision | Descrição |
|---|---|
| `160033a39d59` | instrumento — tabela base |
| `c00a5e8ec52e` | base metrológica (família, grandeza, unidade) |
| `ba250c7eb571` | calibracao |
| `a5e01e43b2d8` | laboratorio |
| `2dae72dfab3d` | contrato |
| `bcf9de0eaaac` | catalogo_preco (deprecado) |
| `d1a2b3c4e5f6` | rename instrumento.sistema → setor |
| `e2b3c4d5f6a7` | contrato.fornecedor → laboratorio_id (FK) |
| `f3a4b5c6d7e8` | calibracao.item_contrato_id (FK opcional) |
| `a4b5c6d7e8f9` | contrato.laboratorio_id NOT NULL |
| `b5c6d7e8f9a0` | drop catalogo_preco (visão derivada) |
