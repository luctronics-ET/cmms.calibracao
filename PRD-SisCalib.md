# PRD — SisCalib: Sistema de Gestão Metrológica
**Versão:** 1.2  
**Data:** Junho 2026  
**Autor:** Divisão de Manutenção Especializada — CMASM / Seção de Eletrônica  
**Status:** 🚧 Fase 1 (MVP) em implementação — repo `xCalibracao`

> **v1.2 (atualização de reconciliação):** o PRD foi atualizado para refletir o que já está construído e mergeado em `main`. As mudanças mais relevantes em relação à v1.1:
> - O modelo de criticidade **Classe A/B/C/D** foi **substituído pelo IGP** (Índice Global de Prioridade do Equipamento) — ver §6.1 e §0.
> - A geração de arquivos da exportação usa **fpdf2 + openpyxl** (CSV/XLSX/PDF resumo); **WeasyPrint** permanece previsto apenas para certificados/etiquetas HTML→PDF (Fase 1/2, ainda não feito).
> - O frontend é **HTML/JS vanilla reaproveitando a camada visual do cmasm.erp vendorizada** (fontes, ícones, `xcmasm-govbr.css`, tokens dark), não o govbr-ds puro.
> - Há o eixo **Disciplina (ELE/MEC)** no instrumento, não previsto na v1.1.
> - Ver §0 (Status de Implementação) para o checklist real por requisito.

---

## 0. Status de Implementação (v1.2)

Snapshot do que está **entregue e mergeado em `main`** vs. pendente. Stack real: FastAPI + SQLAlchemy/Alembic + SQLite, 1 container Docker (porta 8080); frontend HTML/JS vanilla; **89 testes** passando.

| Bloco | Estado | Observações |
|-------|--------|-------------|
| Importação CSV do inventário (~497 instrumentos) | ✅ Entregue | `backend/importacao.py` + `routers/importacao.py`; tela `importar.html` |
| Inventário + busca | ✅ Entregue | **client-side**: carrega tudo uma vez, ordenação por cabeçalho, filtros multi-seleção (disc, equipamento, marca, modelo, sistema, status, prioridade) |
| Motor de status/validade | ✅ Entregue | `backend/calibracao.py` (vencido / a vencer 7·30·60 / válido) |
| Dashboard + painel de alertas | ✅ Entregue | `routers/dashboard.py`, `index.html`, `alertas.html` |
| Cadastro 6.1 + base metrológica | ✅ Entregue | 4 tabelas de domínio (15 famílias RBC/INMETRO), `GET /dominios`, `cadastro.html`, upload foto/manual |
| Modelo de criticidade **IGP** | ✅ Entregue | `backend/criticidade.py` — substitui Classe A/B/C/D (ver §6.1) |
| Edição em massa | ✅ Entregue | `PATCH /instrumentos/{id}` parcial, modal de ficha, multi-seleção + edição em lote |
| Exportação CSV/XLSX/PDF | ✅ Entregue | `POST /api/v1/instrumentos/export`; CSV UTF-8-BOM, XLSX openpyxl, PDF resumo fpdf2 |
| **Registro de calibrações (6.2)** | ✅ Entregue | entidade `calibracao` (histórico 1→N), `backend/routers/calibracoes.py` (GET histórico, POST registrar, upload certificado PDF, DELETE); validade/status do instrumento **derivados** da última calibração; REPROVADO bloqueia (validade null + status REPROVADO); backfill `origem=IMPORTACAO` no startup; UI na ficha + página `calibracao.html` |
| **Gestão de laboratórios (6.4)** | ✅ Entregue | entidade `laboratorio` (razão social, CNPJ, contato, acreditação CGCRE/RBC, escopo texto-livre, validade), `backend/routers/laboratorios.py` (CRUD + `/alertas` + histórico por lab); status de acreditação reusa `calcular_status`; calibração ganhou FK opcional `laboratorio_id` com **snapshot** dos dados do lab; UI `laboratorios.html` + select no form de calibração + seção "Acreditações a vencer" em `alertas.html` |
| Etiquetas com QR Code (6.6) | ⬜ Pendente | — |
| Página pública por seção (`/qr/{codigo}`) | ⬜ Pendente | — |
| Autenticação JWT | ⬜ Pendente | sistema roda sem login na rede local interna |

**Eixos de classificação reais no instrumento:** Disciplina (ELE/MEC), Família metrológica (FK), Tipo (FK), Grandeza (FK), Unidade (FK), e os 5 fatores IGP (fu, nc, ab, cm, ci).

---

## Índice
0. [Status de Implementação (v1.2)](#0-status-de-implementação-v12)
1. [Contexto e Problema](#1-contexto-e-problema)
2. [Objetivos](#2-objetivos)
3. [Não-Objetivos (Escopo Excluído)](#3-não-objetivos-escopo-excluído)
4. [Usuários e Personas](#4-usuários-e-personas)
5. [User Stories](#5-user-stories)
6. [Requisitos por Fase](#6-requisitos-por-fase)
7. [Modelo de Dados — Visão Geral](#7-modelo-de-dados--visão-geral)
8. [Métricas de Sucesso](#8-métricas-de-sucesso)
9. [Decisões de Arquitetura](#9-decisões-de-arquitetura)
10. [Questões em Aberto](#10-questões-em-aberto)
11. [Roadmap e Fases de Entrega](#11-roadmap-e-fases-de-entrega)
12. [Riscos](#12-riscos)

---

## 1. Contexto e Problema

### Situação atual
O controle de calibração dos instrumentos e equipamentos de medição do CMASM é realizado **exclusivamente em planilhas Excel**, mantidas de forma descentralizada por cada seção. Esse modelo apresenta falhas críticas:

- **Sem controle de vencimento automatizado** — alertas dependem de alguém lembrar de abrir o arquivo.
- **Sem rastreabilidade** — não é possível saber quais medições foram feitas com um instrumento que estava vencido.
- **Sem histórico metrológico** — deriva, tendências e variações entre ciclos não são analisadas.
- **Sem controle de contratos** — não há relação entre o custo pago a laboratórios e os equipamentos calibrados.
- **Certificados dispersos** — PDFs em pastas de rede sem organização, sem vínculo com o instrumento.
- **Sem conformidade com normas** — ISO 9001, ISO 10012 e ISO/IEC 17025 exigem registros que o Excel não garante.

### Impacto direto
Um equipamento de medição com calibração vencida utilizado em manutenção ou inspeção de sistemas de missão crítica (mísseis, armas submarinas, sistemas de navegação) representa **risco operacional, de segurança e de conformidade normativa** com consequências sérias em auditorias internas e externas.

### Problema central
> **Não existe um sistema confiável que garanta que todos os instrumentos em uso estejam dentro do prazo de calibração válido e rastreável.**

---

## 2. Objetivos

| # | Objetivo | Indicador de Sucesso |
|---|----------|----------------------|
| G1 | Eliminar o uso de Excel como ferramenta de controle de calibração | 0 planilhas de controle em uso 6 meses após implantação |
| G2 | Garantir visibilidade em tempo real do status de todos os instrumentos | Dashboard mostrando status atualizado com latência < 24h |
| G3 | Reduzir instrumentos vencidos não identificados para zero | 0 ocorrências de instrumento vencido em uso sem registro de NC |
| G4 | Centralizar certificados, manuais e evidências por instrumento | 100% dos certificados vinculados ao instrumento no sistema |
| G5 | Rastrear custos de calibração por contrato, fornecedor e seção | Relatório mensal de custo gerado automaticamente |
| G6 | Gerar evidências para auditorias ISO 9001 / ISO 10012 | Passar auditorias sem NC relacionadas à gestão metrológica |

---

## 3. Não-Objetivos (Escopo Excluído)

Itens **intencionalmente fora de escopo** para evitar over-engineering na v1:

| Item | Justificativa |
|------|---------------|
| **Notificações por email** | *(resolvido — não necessário)* Alertas cobertos pelo painel in-app; sem dependência de SMTP ou relay |
| **MSA / Gage R&R** | Requer estrutura de processo industrial; não aplicável à maioria dos instrumentos da organização no momento atual |
| **OCR automático de certificados PDF** | Dependência de IA externa, custo operacional e risco de erro; fase futura após estabilizar o fluxo manual |
| **Assinatura digital ICP-Brasil** | Requer infraestrutura PKI que precisa de aprovação de TI/Marinha; fase futura |
| **Integração IoT com ESP32 / sensores ambientais** | Módulo de alto valor mas independente; deve ser tratado como microsserviço separado com API própria |
| **FMEA metrológico completo** | Complexidade de modelagem elevada; coberto parcialmente pelo controle de criticidade |
| **EAM/CMMS completo** | O sistema é de calibração; gestão de manutenção predial é escopo do xPredial |
| **App mobile nativo** | Web responsivo cobre o caso de uso; QR Code funciona em qualquer browser; app nativo sem benefício claro na v1 |
| **Cálculo de orçamento de incerteza** | Requer metrologista; o sistema armazena os dados do certificado, não recalcula |
| **Integração com SINGRA/SisPMB** | Fora de escopo; integração com cmasm.erp cobre a necessidade de sincronização patrimonial |

---

## 4. Usuários e Personas

### P1 — Técnico de Manutenção
- **Quem:** Praças e técnicos das seções (Eletrônica, Refrigeração, Metalurgia etc.)
- **Necessidade:** Saber rapidamente se o instrumento que vai usar está calibrado e válido
- **Frequência de uso:** Diária
- **Nível técnico:** Básico no sistema; especialista no instrumento

### P2 — Encarregado de Seção / Oficial Técnico
- **Quem:** 1º e 2º Tenentes responsáveis por cada seção
- **Necessidade:** Visão do status dos instrumentos da seção, controle de envio para calibração, assinatura de solicitações
- **Frequência de uso:** Semanal
- **Nível técnico:** Intermediário

### P3 — Metrológista / Responsável Técnico de Calibração
- **Quem:** Responsável pela gestão metrológica da organização
- **Necessidade:** Análise completa: conformidade, histórico, deriva, custos, plano anual
- **Frequência de uso:** Diária
- **Nível técnico:** Avançado

### P4 — Gestor / Comandante
- **Quem:** Chefe da DME, Comandante do CMASM
- **Necessidade:** Dashboard executivo, indicadores, custos, conformidade
- **Frequência de uso:** Mensal / sob demanda
- **Nível técnico:** Básico no sistema

### P5 — Administrador do Sistema
- **Quem:** TI / responsável pela implantação interna
- **Necessidade:** Cadastros mestre, usuários, parâmetros, backups
- **Frequência de uso:** Baixa (configuração)
- **Nível técnico:** Avançado

---

## 5. User Stories

### Bloco A — Inventário de Instrumentos
```
US-A01 | Como técnico, quero pesquisar um instrumento pelo código patrimônio ou número de série
        para verificar rapidamente se está calibrado e válido.

US-A02 | Como encarregado, quero cadastrar um novo instrumento com dados completos
        (fabricante, modelo, série, faixa, grandeza, criticidade) para manter o inventário atualizado.

US-A03 | Como metrológista, quero visualizar todos os instrumentos com calibração próxima do
        vencimento (30, 60, 90 dias) para planejar envios com antecedência.

US-A04 | Como técnico, quero escanear o QR Code da etiqueta do instrumento para acessar
        imediatamente seu histórico e status no celular.

US-A05 | Como administrador, quero importar o inventário atual via planilha Excel/CSV
        para não precisar recadastrar manualmente centenas de instrumentos.
```

### Bloco B — Calibração e Certificados
```
US-B01 | Como encarregado, quero registrar uma nova calibração com laboratório, data, validade e
        certificado vinculado para manter o histórico completo.

US-B02 | Como metrológista, quero registrar os pontos de calibração (nominal, medido, erro,
        incerteza) para cada instrumento, permitindo análise de deriva futura.

US-B03 | Como técnico, quero acessar o PDF do certificado de calibração diretamente na ficha
        do instrumento sem precisar acessar pastas de rede.

US-B04 | Como metrológista, quero registrar a declaração de conformidade e a regra de decisão
        utilizada no certificado para atender ISO 17025.

US-B05 | Como encarregado, quero registrar um instrumento como REPROVADO com justificativa
        e bloquear automaticamente seu uso até nova calibração.
```

### Bloco C — Alertas e Workflow
```
US-C01 | Como metrológista, quero ver no dashboard um painel de alertas permanentemente atualizado
        com instrumentos vencidos e a vencer em 30/60/90 dias, sem depender de email,
        para consultar sempre que acessar o sistema.

US-C01b| Como encarregado, quero imprimir ou exportar a lista de instrumentos a vencer da minha
        seção para afixar na bancada ou incluir em relatório semanal.

US-C02 | Como metrológista, quero abrir uma Solicitação de Calibração, vincular ao contrato
        correto e acompanhar o status (solicitado → enviado → em calibração → recebido → registrado).

US-C03 | Como gestor, quero aprovar solicitações de calibração acima de determinado valor
        para controle de custos.

US-C04 | Como técnico, quero registrar a saída de um instrumento para calibração externa com
        data, transportadora e número de rastreio.
```

### Bloco D — Contratos e Custos
```
US-D01 | Como metrológista, quero cadastrar contratos e ARPs com laboratórios, incluindo
        vigência, saldo e itens cobertos, para controlar os gastos de calibração.

US-D02 | Como gestor, quero visualizar o custo total de calibração por seção, por laboratório
        e por ano para análise de orçamento.

US-D03 | Como encarregado, quero vincular cada calibração ao contrato e à nota fiscal
        correspondente para manter a rastreabilidade financeira.
```

### Bloco F — Calibração Interna *(novo — Fase 2)*
```
US-F01 | Como metrológista, quero registrar uma calibração interna realizada pela Seção de
        Eletrônica usando um instrumento padrão já cadastrado no sistema (ex.: Fluke 87V
        calibrado externamente), para rastrear sensores e equipamentos calibrados internamente.

US-F02 | Como metrológista, quero vincular qual instrumento padrão foi usado na calibração
        interna para que a cadeia de rastreabilidade fique registrada: Lab RBC → padrão interno
        → instrumento calibrado.

US-F03 | Como encarregado, quero gerar um Certificado de Calibração Interna simplificado em PDF
        com os dados do instrumento, padrão utilizado, pontos medidos e assinatura do responsável,
        para ter evidência documentada mesmo sem laboratório externo.

US-F04 | Como metrológista, quero configurar quais instrumentos ou famílias são elegíveis para
        calibração interna e quais exigem laboratório externo acreditado, para garantir que
        itens críticos não sejam calibrados internamente por engano.
```
```
US-E01 | Como metrológista, quero visualizar o histórico de erros de um instrumento ao longo
        de seus ciclos de calibração para identificar deriva e ajustar periodicidade.

US-E02 | Como gestor, quero exportar o relatório de conformidade metrológica da organização
        em PDF para apresentar em auditorias.

US-E03 | Como metrológista, quero gerar o Plano Anual de Calibração com previsão de datas
        e estimativa de custo por instrumento.

US-E04 | Como metrológista, quero registrar justificativa quando alterar o intervalo de
        calibração de um instrumento (ex.: reduzir de 12 para 6 meses por deriva detectada).
```

---

## 6. Requisitos por Fase

### FASE 1 — MVP: Controle e Visibilidade (P0 — Deve ter)

#### 6.1 Cadastro de Instrumentos
- [ ] Cadastro completo: fabricante, modelo, número de série, código patrimonial, código interno
- [ ] Tipo de instrumento (Multímetro, Osciloscópio, Fonte DC, Paquímetro, etc.)
- [ ] Família metrológica (Elétrica, Eletrônica, Dimensional, Temperatura, Pressão, Torque, Massa, RF, Acústica)
- [ ] Grandeza medida principal + unidade SI
- [ ] Faixa nominal + resolução + exatidão/EMP
- [ ] Periodicidade de calibração (padrão: 12 meses, configurável)
- [x] **Criticidade via IGP** (Índice Global de Prioridade do Equipamento) — substitui o Classe A/B/C/D da v1.1. Ver detalhamento abaixo.
- [ ] Localização: Organização → Unidade → Seção → Bancada
- [ ] Status: ATIVO / EM CALIBRAÇÃO / EM MANUTENÇÃO / REPROVADO / BLOQUEADO / BAIXADO
- [ ] Campos de observação livre
- [ ] Upload de foto do equipamento e do manual (PDF)
- [ ] **Critério de aceitação:** Cadastro salvo em < 2 minutos; campos obrigatórios validados; código patrimonial único

##### Modelo de criticidade — IGP (implementado)
O Classe A/B/C/D do PRD v1.1 foi substituído por um índice multifatorial, mais aderente à realidade da DME. São **5 fatores**, cada um pontuado de **1 a 3** (`backend/criticidade.py`, motor puro sem I/O):

| Sigla | Fator | Peso | Escala 1 → 3 |
|-------|-------|------|--------------|
| FU | Frequência de uso | 1 | esporádico → regular → diário |
| NC | Necessidade crítica | 2 | baixo impacto → importante → crítico |
| AB | Abundância/redundância | 1 | alta redundância → média → única |
| CM | Criticidade metrológica | 2 | tolerância alta → moderada → baixa tolerância |
| CI | Custo de indisponibilidade | 1 | mínimo → moderado → afeta operação |

`IGP = FU·1 + NC·2 + AB·1 + CM·2 + CI·1` → faixa real **7..21** quando todos os fatores estão preenchidos.

| Classe de prioridade | Faixa IGP |
|----------------------|-----------|
| MAXIMA | ≥ 18 |
| MEDIA | 14–17 |
| BAIXA | 11–13 |
| MUITO_BAIXA | 7–10 |
| NAO_CLASSIFICADO | qualquer fator ausente |

> `CM` (criticidade metrológica) é também a base prevista para a futura **regra de elegibilidade de calibração interna** (Fase 2).

#### 6.2 Registro de Calibrações ✅ Entregue (entidade `calibracao`)
- [x] Vínculo de calibração ao instrumento (histórico 1→N)
- [x] Data de calibração
- [x] Data de validade (calculada automaticamente = data calibração + ciclo_meses; null se REPROVADO)
- [x] Laboratório executante em texto livre (nome, CNPJ, acreditação RBC sim/não, número CGCRE) — *FK para entidade Laboratório fica para 6.4*
- [x] Número do certificado
- [x] Resultado: APROVADO / APROVADO COM RESTRIÇÕES / REPROVADO (REPROVADO bloqueia o uso — US-B05)
- [x] Upload do certificado PDF (`uploads/{inst_id}/cert_{cal_id}.pdf`)
- [x] Custo da calibração *(vínculo ao contrato/ARP é Fase 3 §6.14)*
- [x] Responsável técnico que recebeu o certificado
- [x] **Critério de aceitação:** Após registro, status e validade do instrumento atualizam automaticamente (campos derivados da última calibração); certificado acessível por link direto na ficha
- *Pontos de calibração / incerteza / condições ambientais → Fase 2 §6.7 (fora de escopo desta entrega)*

#### 6.3 Painel de Alertas In-App (sem email)
- [ ] Widget permanente no dashboard: contadores de VENCIDOS / A VENCER 7 dias / A VENCER 30 dias / A VENCER 60 dias
- [ ] Painel dedicado de alertas: lista completa ordenada por urgência com filtro por seção
- [ ] Badge numérico no menu lateral indicando alertas pendentes (similar a notificação de app)
- [ ] Cada alerta tem link direto para a ficha do instrumento
- [ ] Exportação da lista de alertas em PDF e CSV (para afixar em quadro de avisos ou incluir em relatório)
- [ ] Página pública por seção (sem login) mostrando apenas o painel de status dos instrumentos daquela seção — pode ser deixada aberta em tablet ou monitor da bancada
- [ ] **Critério de aceitação:** Status de todos os instrumentos recalculado a cada acesso ao dashboard; lista de alertas exportável em < 3 cliques; sem dependência de SMTP ou serviço externo

#### 6.4 Gestão de Laboratórios ✅ Entregue (entidade `laboratorio`)
- [x] Cadastro de laboratórios: razão social, CNPJ, endereço, contato (+ telefone, email)
- [x] Acreditação RBC/CGCRE: número, escopo de grandezas (texto livre), validade da acreditação
- [x] Alerta quando acreditação do laboratório estiver próxima do vencimento (badge na lista + `/laboratorios/alertas` na seção "Acreditações a vencer" do Painel de Alertas; reusa os limiares 7/30/60d)
- [x] Histórico de calibrações por laboratório (`GET /laboratorios/{id}/calibracoes`)
- [x] Vínculo opcional calibração→laboratório (`laboratorio_id` FK) com **snapshot** dos dados do lab na calibração (sobrevive a edição/exclusão do lab)
- *Escopo estruturado por grandeza/validação de cobertura → fora de escopo (YAGNI)*

#### 6.5 Importação Inicial
- [ ] Importação via CSV/Excel com template pré-definido para migração do inventário atual
- [ ] Validação de erros com relatório antes de confirmar a importação
- [ ] **Critério de aceitação:** Importação de 500 registros em < 60 segundos; erros identificados linha a linha

#### 6.6 Etiquetas com QR Code
- [ ] Geração de etiqueta por instrumento com: código patrimonial, status, data calibração, validade, QR Code
- [ ] QR Code aponta para a ficha pública do instrumento (sem necessidade de login)
- [ ] Impressão individual ou em lote
- [ ] **Critério de aceitação:** QR Code lido por qualquer leitor padrão; página carregada em < 2s

---

### FASE 2 — Metrologia e Rastreabilidade (P1 — Deve ter na v2)

#### 6.7 Pontos de Calibração
- [ ] Registro de pontos medidos por calibração: ponto nominal, valor referência, valor indicado, erro, unidade
- [ ] Incerteza expandida por ponto: valor, fator de cobertura k, nível de confiança (%)
- [ ] Declaração de conformidade: CONFORME / NÃO CONFORME / SEM DECLARAÇÃO
- [ ] Regra de decisão utilizada (aceitação simples, banda de guarda, ILAC G8)
- [ ] Condições ambientais durante a calibração: temperatura, umidade, pressão

#### 6.8 Padrões Metrológicos Utilizados
- [ ] Registro dos padrões usados em cada calibração: fabricante, modelo, série, certificado, validade, laboratório
- [ ] Cadeia de rastreabilidade: INMETRO → Laboratório RBC → Padrão → Instrumento

#### 6.9 Análise de Deriva
- [ ] Gráfico histórico de erro por grandeza/ponto ao longo dos ciclos
- [ ] Indicação de tendência (estável, crescente, decrescente)
- [ ] Alerta automático quando deriva superar 50% do EMP
- [ ] Histórico de alterações de periodicidade com justificativa obrigatória

#### 6.10 Controle de Ajustes
- [ ] Registro separado de AJUSTE (distinto de calibração): antes e depois
- [ ] Ajuste automaticamente gera solicitação de nova calibração após a intervenção

#### 6.11 Lacres
- [ ] Controle de lacres: número, data instalação, data remoção, motivo
- [ ] Remoção de lacre gera NC automática e bloqueia o instrumento

#### 6.12 Não Conformidades
- [ ] Registro de NC metrológica: origem, descrição, ação corretiva, ação preventiva, prazo, encerramento
- [ ] NC automática gerada em: instrumento vencido em uso, lacre rompido, reprovação, perda de rastreabilidade

#### 6.13 Calibração Interna *(novo — Fase 2)*

Esta funcionalidade permite que a Seção de Eletrônica (ou outro setor autorizado) execute calibrações de instrumentos de menor criticidade usando padrões internos já calibrados externamente.

**Regra fundamental:** um instrumento só pode ser usado como padrão em calibração interna se estiver com calibração **VÁLIDA** e rastreável a laboratório RBC/CGCRE.

- [ ] Flag por instrumento: `permite_calibracao_interna` (configurável por família/tipo)
- [ ] Flag por instrumento: `pode_ser_usado_como_padrao` (Classe A ou B com calibração válida)
- [ ] Registro de calibração interna com campos:
  - Instrumento calibrado
  - Instrumento padrão usado (FK para instrumento no sistema — validado como VÁLIDO)
  - Procedimento interno (número + revisão)
  - Técnico responsável
  - Data da calibração
  - Validade definida manualmente (não automática — metrológista decide)
  - Pontos medidos + erros + incerteza estimada
  - Condições ambientais
  - Resultado: APROVADO / REPROVADO
- [ ] Geração de Certificado de Calibração Interna em PDF com:
  - Cabeçalho da organização (CMASM / DME)
  - Identificação do instrumento calibrado e do padrão
  - Tabela de pontos medidos
  - Declaração de conformidade simplificada
  - Assinatura do técnico + visto do encarregado
- [ ] Cadeia de rastreabilidade visível na ficha: `Lab RBC → [padrão interno] → [instrumento]`
- [ ] Lista de instrumentos autorizados para calibração interna (configuração do metrológista)
- [ ] Bloqueio automático: instrumento Classe A não pode ser calibrado internamente
- [ ] **Critério de aceitação:** Geração do certificado PDF em < 10s; rastreabilidade registrada e auditável; padrão com calibração vencida bloqueado de ser selecionado

---

### FASE 3 — Gestão e Planejamento (P1 — Deve ter na v3)

#### 6.14 Gestão de Contratos e ARPs
- [ ] Cadastro de contratos: número, processo, fornecedor, vigência, valor total, saldo
- [ ] Suporte a ARPs (Atas de Registro de Preços) com controle de saldo por item
- [ ] Vinculação de cada calibração ao contrato correspondente
- [ ] Alerta de contrato próximo do vencimento ou com saldo baixo
- [ ] Integração com dados do PNCP para consulta de ARPs vigentes

#### 6.15 Plano Anual de Calibração
- [ ] Geração automática do plano baseado nas periodicidades cadastradas
- [ ] Estimativa de custo por instrumento baseada no histórico de contratos
- [ ] Exportação em PDF e Excel para aprovação e licitação
- [ ] Comparação entre o planejado e o realizado

#### 6.16 Movimentação Logística
- [ ] Registro de envio externo: data, destinatário, transportadora, número de rastreio, OS
- [ ] Status de movimentação: COLETADO / EM TRÂNSITO / RECEBIDO NO LAB / DEVOLVIDO / RECEBIDO NA ORGANIZAÇÃO
- [ ] Alerta de instrumento fora há mais de X dias sem retorno

#### 6.17 Dashboard Executivo com KPIs de Custo
- [ ] Total de instrumentos por status
- [ ] Percentual de conformidade (instrumentos válidos / total ativos)
- [ ] Custo de calibração: mês atual, acumulado anual, por seção, por laboratório
- [ ] Instrumentos críticos (Classe A/B) com status vencido ou a vencer
- [ ] Próximas calibrações nos 30/60/90 dias
- [ ] Exportação do relatório executivo em PDF

#### 6.18 Integração com cmasm.erp *(depende de Q10)*
- [ ] Endpoint `POST /api/v1/sync/instrumento` — recebe dados de instrumentos do ERP
- [ ] Endpoint `POST /api/v1/sync/usuario` — sincroniza usuários e setores
- [ ] Endpoint `GET /api/v1/instrumentos/status` — exporta status de calibração para o ERP
- [ ] Log de sincronização com status OK / CONFLITO / PENDENTE

---

### FASE 4 — Inteligência e Integração (P2 — Futuro)

#### 6.19 Funcionalidades Futuras (parking lot)
- [ ] Integração com sensores IoT (ESP32/MQTT) para monitoramento ambiental de salas de calibração
- [ ] OCR + IA para preenchimento automático de dados do certificado PDF
- [ ] MSA / Gage R&R para instrumentos de processo
- [ ] Assinatura digital ICP-Brasil em certificados internos
- [ ] FMEA metrológico e gestão de risco com RPN
- [ ] Módulo de competência técnica: treinamentos e autorizações por operador
- [ ] Intervalo dinâmico calculado por histórico de deriva + criticidade + uso
- [ ] Integração com sistema de patrimônio da Marinha
- [ ] Módulo de estudo de obsolescência (peças, suporte, substitutos)

---

## 7. Modelo de Dados — Visão Geral

### Entidades principais

```
ativo_metrologico (entidade base — permite futura expansão para EAM)
  └── instrumento (foco da v1)
       ├── especificacoes_tecnicas (faixas, grandeza, resolução, EMP por faixa)
       ├── calibracoes
       │    ├── tipo: EXTERNA | INTERNA                  ← novo
       │    ├── [EXTERNA] laboratorio_id + certificado
       │    ├── [INTERNA] instrumento_padrao_id + procedimento_interno + tecnico_id
       │    ├── calibracao_pontos (pontos medidos, erros, incerteza)
       │    ├── calibracao_padroes (padrões com rastreabilidade)
       │    ├── conformidade (regra de decisão, resultado)
       │    ├── condicoes_ambientais
       │    └── anexos (certificado PDF — externo ou gerado internamente)
       ├── ajustes
       ├── lacres
       ├── nao_conformidades
       ├── historico_periodicidade (mudanças de intervalo + justificativa)
       ├── historico_erros (pivot temporal para análise de deriva)
       └── movimentacoes (logística externa)

laboratorios
  └── escopo_acreditacao (grandeza, faixa, CMC, validade)

padroes_metrologicos
  └── rastreabilidade (cadeia INMETRO → RBC → padrão → instrumento)

contratos
  └── itens_contrato
       └── calibracao (vinculação financeira)

solicitacoes_calibracao (workflow simplificado)
  └── movimentacoes

plano_anual_calibracao

usuarios
  ├── perfis (TECNICO, ENCARREGADO, METROLOGISTA, GESTOR, ADMIN)
  └── unidades_responsaveis

alertas (calculados e persistidos — substitui email)
  ├── tipo: VENCIDO | A_VENCER_7 | A_VENCER_30 | A_VENCER_60 | PADRAO_VENCENDO
  ├── instrumento_id
  ├── data_geracao
  └── reconhecido: BOOLEAN

-- Tabela de sincronização com cmasm.erp
erp_sync_log
  ├── entidade: INSTRUMENTO | USUARIO | SETOR
  ├── erp_id (chave no ERP externo)
  ├── siscalib_id
  ├── ultima_sincronizacao
  └── status: OK | CONFLITO | PENDENTE
```

### Tabelas de Domínio (lookup)
```
familias_metrologicas    (Elétrica, Eletrônica, Dimensional, Temperatura, Pressão...)
grandezas               (VDC, VAC, IDC, FREQ, TEMP, PRESS, TORQUE, LEN...)
unidades_medida         (V, A, Ω, Hz, °C, Pa, Nm, mm, kg...)
tipos_instrumento       (Multímetro, Osciloscópio, Fonte DC, Paquímetro...)
classes_instrumento     (Padrão Primário, Padrão Secundário, Padrão Trabalho, Instrumento, Auxiliar)
regras_decisao          (Simples, Banda de guarda, ILAC G8, ANSI Z540.3)

-- Criticidade NÃO é tabela de domínio: é calculada pelo IGP (5 fatores 1..3
-- gravados no próprio instrumento → fu, nc, ab, cm, ci). Ver §6.1.
-- Tabelas de domínio implementadas: familia_metrologica, tipo_instrumento,
-- grandeza, unidade_medida (4 lookups, seed em backend/dominios.py).
```

---

## 8. Métricas de Sucesso

### Leading Indicators (primeiros 90 dias)
| Métrica | Meta |
|---------|------|
| Instrumentos cadastrados | > 90% do inventário atual |
| Certificados digitalizados e vinculados | > 80% dos ativos |
| Taxa de adoção pelos encarregados | > 85% das seções usando ativamente |
| Tempo médio para registrar uma calibração | < 5 minutos |
| Alertas de vencimento enviados com sucesso | > 99% de entregabilidade |

### Lagging Indicators (6–12 meses)
| Métrica | Meta |
|---------|------|
| Instrumentos vencidos em uso detectados | 0 ocorrências não registradas |
| NCs metrológicas em auditoria por falha de sistema | 0 |
| Redução do tempo de preparação para auditoria | > 70% |
| Custo de calibração dentro do orçamento anual planejado | Desvio < 10% |
| Instrumentos com análise de deriva disponível | > 60% após 2 ciclos |

---

## 9. Decisões de Arquitetura

### Premissa definida: servidor = qualquer máquina na rede local

A resposta à Q2 ("pode ser até um conjunto de HTMLs ou um HTML se possível") define o objetivo de **máxima leveza operacional**. A estrutura abaixo entrega isso sem sacrificar a integridade dos dados.

> ⚠️ **Por que não pode ser 100% HTML estático:** o sistema precisa de upload de arquivos (certificados PDF), banco de dados com integridade referencial (rastreabilidade metrológica não pode ficar em localStorage — risco de perda de dados), e geração de PDF server-side (certificados internos, etiquetas, relatórios). A solução abaixo é a mais leve possível que ainda resolve o problema real.

### Stack: Contêiner único

```
┌─────────────────────────────────────────────┐
│         siscalib  (1 Docker container)       │
│                                              │
│  FastAPI (Python 3.12)                       │
│  ├── /api/v1/*     → REST API JSON           │
│  ├── /static/*     → HTML + govbr-ds + JS   │
│  ├── /uploads/*    → Certificados, fotos     │
│  └── /qr/{codigo} → Ficha pública (s/ login)│
│                                              │
│  SQLite  → /data/siscalib.db                 │
│  Files   → /data/uploads/                   │
└─────────────────────────────────────────────┘
         ↕ porta 8080
   Rede local CMASM
```

**Início do sistema:**
```bash
docker run -d \
  --name siscalib \
  --restart unless-stopped \
  -p 8080:8080 \
  -v siscalib_data:/data \
  siscalib:latest
```

Qualquer computador na rede acessa em `http://[ip-servidor]:8080`.

### Stack detalhado

| Camada | Tecnologia | Justificativa |
|--------|-----------|---------------|
| Backend | FastAPI (Python 3.12) | Familiar, async nativo, auto-documentação OpenAPI para integração com cmasm.erp |
| Banco de dados | **SQLite** (não PostgreSQL) | 500 instrumentos ≈ < 50 MB; sem serviço separado; backup = copiar 1 arquivo; ACID completo |
| ORM | SQLAlchemy + Alembic | Migrações seguras; compatível com upgrade futuro para PostgreSQL se escala crescer |
| Frontend | HTML/JS vanilla + camada visual do cmasm.erp vendorizada | Reaproveita fontes DM Sans/JetBrains Mono, bootstrap-icons, `xcmasm-govbr.css` e tokens dark do cmasm.erp (todos em `frontend/vendor/`, sem CDN externo); sem framework JS pesado |
| Geração de arquivos (export) | **fpdf2** (PDF resumo) + **openpyxl** (XLSX) + CSV UTF-8-BOM | ✅ implementado em `routers/exportacao.py`; PDF sanitiza para Latin-1 |
| Geração de PDF (certificados/etiquetas) | WeasyPrint *(previsto)* | Certificados internos e etiquetas QR via template HTML → PDF; ainda não implementado |
| QR Code | qrcode (Python) *(previsto)* | Geração server-side; embutido na etiqueta PDF |
| Autenticação | JWT com cookie HttpOnly *(previsto)* | Hoje roda sem login na LAN interna; sessão de 8h quando implementado |
| Armazenamento de arquivos | Volume Docker `/data/uploads/` | Local; sem nuvem; backup junto com o banco |
| Notificações | **In-app apenas** — sem SMTP | Badge + painel de alertas + exportação PDF/CSV |
| Deploy | Docker (imagem única) | 1 comando; sem docker-compose necessário na v1 |

### Integração com cmasm.erp

A integração é bidirecional via REST API e deve ser planejada para a **Fase 3**, mas a API do SisCalib deve ser projetada desde a v1 para suportá-la:

```
cmasm.erp  ──────────────────────────────→  SisCalib
           POST /api/v1/sync/instrumento     (cria/atualiza instrumento a partir do ERP)
           POST /api/v1/sync/usuario         (sincroniza pessoal)
           POST /api/v1/sync/setor           (sincroniza estrutura organizacional)

SisCalib   ──────────────────────────────→  cmasm.erp
           GET  /api/v1/instrumentos/status  (status de calibração para exibir no ERP)
           GET  /api/v1/alertas/ativos       (alertas para dashboard do ERP)
```

**Questão em aberto para a Fase 3:** quais campos o cmasm.erp exporta para cada instrumento? (código patrimônio, setor, responsável?) — definir antes de implementar o endpoint de sync.

### Decisões importantes

1. **SQLite → PostgreSQL**: upgrade possível sem mudar uma linha da lógica de negócio (troca apenas a connection string no Alembic). Fazer quando/se a organização crescer para múltiplas unidades.
2. **API RESTful versionada `/api/v1/`** desde o início — integração com cmasm.erp e futura IoT sem quebrar clientes.
3. **Ficha pública do instrumento** (`/qr/{codigo}`) não requer login — permite uso em tablet na bancada e leitura de QR em campo.
4. **Backup automático** via cron job dentro do container: cópia diária do `siscalib.db` com retenção de 30 dias em `/data/backups/`.
5. **Certificados internos gerados por template HTML→PDF** (WeasyPrint): modificável sem recompilar o sistema.

### Requisitos mínimos do servidor
| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | 1 core | 2 cores |
| RAM | 512 MB | 1 GB |
| Disco | 10 GB (para uploads) | 50 GB |
| SO | Qualquer com Docker | Ubuntu 24 LTS |
| Rede | IP fixo na LAN | IP fixo na LAN |

---

## 10. Questões em Aberto ✅ Todas respondidas

| # | Questão | Resposta | Impacto na arquitetura |
|---|---------|----------|------------------------|
| Q1 | Classificação dos certificados? | **Ostensivos** — servidor local OK | Armazenamento local no volume Docker; sem nuvem |
| Q2 | Infraestrutura disponível? | **Qualquer computador na rede com Docker** | Stack leve: FastAPI + SQLite, 1 container, ~512 MB RAM |
| Q3 | Integração com patrimônio? | **Não SINGRA; integrar com cmasm.erp** | API `/sync/` versionada desde v1; integração na Fase 3 |
| Q4 | Administrador do sistema? | **DME — Seção de Eletrônica** | Perfil ADMIN pré-criado para a seção; sem dependência de TI externo |
| Q5 | Volume do inventário? | **~500 instrumentos** | SQLite suficiente; sem necessidade de PostgreSQL |
| Q6 | SMTP disponível? | **Sim, mas não necessário** | Alertas 100% in-app; painel + exportação PDF/CSV; sem email |
| Q7 | Periodicidade padrão? | **12 meses para todos não especificados** | Valor padrão do sistema; configurável por instrumento |
| Q8 | Workflow de aprovação formal? | **Não** | Sem módulo de aprovação na v1; solicitação simplificada |
| Q9 | Calibrações internas? | **Sim — simplificado, Fase 2** | Nova entidade `calibracao.tipo = INTERNA`; padrão vinculado por FK; geração de cert. interno em PDF |

### Questão nova — pendente (Q10)
| Q10 | Quais campos o cmasm.erp exporta por instrumento/ativo? (código patrimônio, setor, responsável, etc.) | DME / responsável pelo ERP | **SIM para Fase 3** |

---

## 11. Roadmap e Fases de Entrega

```
FASE 1 — MVP: Controle e Visibilidade                         [6–8 semanas]
──────────────────────────────────────────────────────────────────────────
Stack: FastAPI + SQLite + HTML/JS vanilla (visual cmasm.erp vendorizado) — 1 container Docker
Legenda: [x] entregue em `main` · [ ] pendente

  [x] Inventário de instrumentos completo (~497 registros) — client-side, ordenação + filtros
  [x] Importação CSV do Excel atual
  [x] Cadastro 6.1 + base metrológica (domínios) + criticidade IGP + edição em massa
  [x] Painel de alertas in-app (vencido / a vencer) — sem email
  [x] Dashboard de status com filtros por seção/grandeza/prioridade
  [x] Exportação do inventário (CSV / XLSX / PDF resumo)
  [x] API /api/v1/ versionada (base para integração futura com cmasm.erp)
  [x] Registro de calibrações externas + upload de certificados PDF (entidade `calibracao`, histórico + validade derivada)
  [ ] Etiquetas com QR Code (impressão individual e em lote)
  [x] Gestão de laboratórios externos (acreditação, escopo, alerta de vencimento, histórico)
  [ ] Relatório de conformidade exportável para auditoria
  [ ] Página pública de seção (tablet na bancada, sem login)
  [ ] Autenticação JWT

Critério de aceite da Fase 1:
  → Planilhas Excel descontinuadas para controle de validade
  → 100% dos instrumentos ativos cadastrados
  → Painel acessível por qualquer máquina da rede

────────────────────────────────────────────────────────────────

FASE 2 — Metrologia, Rastreabilidade e Calibração Interna     [6–8 semanas]
──────────────────────────────────────────────────────────────────────────
  ✓ Pontos de calibração + incerteza + declaração de conformidade
  ✓ Padrões metrológicos + cadeia de rastreabilidade
  ✓ Análise de deriva (gráfico histórico por grandeza/ponto)
  ✓ Alertas de tendência (deriva > 50% do EMP)
  ✓ Ajustes (pré/pós), lacres e não conformidades
  ✓ Calibração INTERNA — novo módulo:
       ├── Vínculo instrumento padrão → instrumento calibrado
       ├── Registro de pontos + incerteza estimada
       ├── Geração de Certificado Interno PDF (assinado pelo técnico)
       └── Cadeia de rastreabilidade visível na ficha
  ✓ Histórico de periodicidade com justificativa

────────────────────────────────────────────────────────────────

FASE 3 — Gestão, Custos e Integração ERP                      [4–6 semanas]
──────────────────────────────────────────────────────────────────────────
Depende de: resposta à Q10 (campos do cmasm.erp)

  ✓ Gestão de contratos e ARPs + integração PNCP
  ✓ Plano Anual de Calibração (previsão de datas + custo)
  ✓ Logística de movimentação (envio/retorno de instrumentos)
  ✓ Dashboard executivo com KPIs de custo
  ✓ Integração bidirecional com cmasm.erp via API sync

────────────────────────────────────────────────────────────────

FASE 4 — Inteligência (futuro / sem data)
──────────────────────────────────────────────────────────────────────────
  → IoT: sensores ambientais ESP32/MQTT integrados às salas
  → OCR + IA para extração automática de dados de certificados
  → Intervalo dinâmico de calibração por deriva + uso + criticidade
  → Assinatura digital ICP-Brasil nos certificados internos
  → MSA / Gage R&R para instrumentos de processo industrial
```

---

## 12. Riscos

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|-------|--------------|---------|-----------|
| R1 | Resistência à adoção pelos técnicos (acostumados com Excel) | Alta | Alto | Treinamento hands-on; interface extremamente simples para consulta; QR Code elimina barreira de entrada |
| R2 | Dados do inventário atual incompletos ou inconsistentes no Excel | Alta | Alto | Script de importação com validação rigorosa + relatório de erros linha a linha antes de confirmar |
| R3 | Servidor desligado por acidente (sem política de uptime definida) | Média | Alto | `--restart unless-stopped` no Docker; backup diário automático; procedimento de restauração documentado |
| R4 | Scope creep — Fase 3 solicitada antes de estabilizar Fase 1 | Alta | Médio | Roadmap com critério de aceite por fase; aceite formal antes de avançar |
| R5 | Certificados antigos em papel sem digitalização | Alta | Baixo | Upload de PDF é opcional na v1; campo `tem_certificado_fisico` para controle; digitalização gradual |
| R6 | Dependência de um único desenvolvedor | Alta | Alto | Código documentado; stack simples e conhecida; README com instruções de deploy e backup |
| R7 | Integração com cmasm.erp mais complexa que o esperado | Média | Médio | API do SisCalib projetada desde v1; integração apenas na Fase 3 após mapeamento dos campos (Q10) |
| R8 | Instrumento padrão vencido usado em calibração interna por engano | Baixa | Alto | Validação hard no backend: FK para instrumento com status=VÁLIDO obrigatória; instrumento vencido não aparece na seleção |

---

## Anexos

### A. Template CSV para Importação de Inventário
```csv
codigo_patrimonio,codigo_interno,descricao,fabricante,modelo,serie,familia,
grandeza,faixa_min,faixa_max,unidade,resolucao,emp,criticidade,periodicidade_meses,
localizacao_setor,localizacao_detalhe,status,data_ultima_calibracao,validade_calibracao,
laboratorio_ultima_cal,numero_certificado,observacoes
```

### B. Referências Normativas
- **ISO/IEC 17025:2017** — Requisitos gerais para competência de laboratórios
- **ISO 10012:2003** — Sistemas de gestão de medição
- **ISO 9001:2015** — Sistemas de gestão da qualidade (cláusula 7.1.5 — Recursos de monitoramento e medição)
- **ABNT NBR ISO/IEC 17025** — versão brasileira
- **VIM — Vocabulário Internacional de Metrologia** (INMETRO / BIPM)
- **ILAC G8:09/2019** — Guidelines on Decision Rules and Statements of Conformity
- **Vocabulário de Expressão da Incerteza de Medição (GUM)** — BIPM/INMETRO

### C. Glossário
| Termo | Definição |
|-------|-----------|
| EMP | Erro Máximo Permitido — maior desvio tolerável do valor verdadeiro |
| CMC | Capability of Measurement and Calibration — capacidade do laboratório acreditado |
| RBC | Rede Brasileira de Calibração (INMETRO) |
| CGCRE | Coordenação Geral de Acreditação (INMETRO) |
| Deriva | Variação lenta e sistemática do erro ao longo do tempo |
| Rastreabilidade | Cadeia ininterrupta de comparações até padrão nacional ou internacional |
| Incerteza expandida | Intervalo que engloba o valor verdadeiro com probabilidade definida |
| Fator de cobertura k | Multiplicador da incerteza padrão para obter incerteza expandida (k=2 → 95%) |
| ARP | Ata de Registro de Preços — instrumento de compras públicas |

---

*PRD v1.1 — Questões em aberto respondidas. Pronto para produção do Plano de Implementação Técnica (schema SQL, estrutura de rotas, protótipo de telas).*
