# TODO — sisCalibracao

Pendências priorizadas. Ver `PRD-SisCalib.md` para o contexto completo.

## Fase 1 — fechar o MVP
- [ ] Relatório de conformidade exportável para auditoria (PDF) — objetivo G6 (ISO 9001/10012).
- [ ] Badge numérico de alertas no menu lateral.
- [ ] Autenticação JWT (baixa prioridade — roda em LAN interna sem login).

## Limpeza / dívida técnica
- [ ] Remover `ItemContrato.fornecedor` (texto redundante; fornecedor vem do contrato → laboratório).
- [ ] `catalogo.html` "Calibrações recentes" e demais listas pequenas: avaliar migrar para `montarTabela`.
- [ ] Padronizar nome do arquivo de banco/marca (`siscalib.db` / `siscalib.css`) se quiser alinhar a "sisCalibracao".

## Catálogo / seleção de laboratórios (evolução)
- [ ] Avaliações por laboratório: qualidade, tempo de calibração, atendimento.
- [ ] Contatos e histórico por laboratório → comparar e selecionar fornecedores.

## Fase 2 — Metrologia e rastreabilidade
- [ ] §6.7 Pontos de calibração + incerteza + declaração de conformidade.
- [ ] §6.8 Padrões metrológicos + cadeia de rastreabilidade.
- [ ] §6.9 Análise de deriva (gráfico histórico, alerta > 50% do EMP).
- [ ] §6.10 Ajustes / §6.11 Lacres / §6.12 Não conformidades.
- [ ] §6.13 Calibração interna (padrão interno, certificado PDF).

## Fase 3 — Gestão e integração
- [ ] §6.15 Plano Anual de Calibração (cálculo/agregação de custo — base pronta: catálogo + periodicidades).
- [ ] §6.14 Integração PNCP (consulta de ARPs vigentes).
- [ ] §6.16 Movimentação logística (envio/retorno).
- [ ] §6.17 Dashboard executivo com KPIs de custo.
- [ ] §6.18 Integração cmasm.erp (depende de Q10 — campos exportados por instrumento).
