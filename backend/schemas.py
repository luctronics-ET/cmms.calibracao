"""Modelos de entrada/saída da API."""
from __future__ import annotations
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class InstrumentoOut(BaseModel):
    id: int
    codigo_interno: str | None
    codigo_patrimonial: str | None
    serial: str | None
    equipamento: str | None
    marca: str | None
    modelo: str | None
    faixa: str | None
    unidade_faixa: str | None
    faixa_min: float | None
    faixa_max: float | None
    resolucao: str | None
    emp: str | None
    disciplina: str | None
    familia_id: int | None
    familia_nome: str | None
    tipo_id: int | None
    tipo_nome: str | None
    grandeza_id: int | None
    grandeza_nome: str | None
    unidade_id: int | None
    unidade_simbolo: str | None
    setor: str | None
    organizacao: str | None
    unidade_org: str | None
    secao: str | None
    bancada: str | None
    ciclo_meses: int
    data_ultima_calibracao: date | None
    data_validade: date | None
    flag_origem: str | None
    organizacao_calibradora: str | None
    local_calibracao: str | None
    custo_estimado: float | None
    custo_contratado: float | None
    certificado_ref: str | None
    status_operacional: str
    foto_path: str | None
    manual_path: str | None
    fu: int | None
    nc: int | None
    ab: int | None
    cm: int | None
    ci: int | None
    observacoes: str | None
    # derivados
    status: str
    dias_restantes: int | None
    divergencia_flag: bool
    igp: int | None
    classe_prioridade: str


class InstrumentoIn(BaseModel):
    """Entrada de criação/edição."""
    equipamento: str
    familia_id: int
    tipo_id: int
    ciclo_meses: int = 12
    status_operacional: str = "ATIVO"
    codigo_interno: str | None = None
    codigo_patrimonial: str | None = None
    serial: str | None = None
    marca: str | None = None
    modelo: str | None = None
    faixa_min: float | None = None
    faixa_max: float | None = None
    resolucao: str | None = None
    emp: str | None = None
    disciplina: str | None = None
    grandeza_id: int | None = None
    unidade_id: int | None = None
    setor: str | None = None
    organizacao: str | None = None
    unidade_org: str | None = None
    secao: str | None = None
    bancada: str | None = None
    data_ultima_calibracao: date | None = None
    data_validade: date | None = None
    organizacao_calibradora: str | None = None
    local_calibracao: str | None = None
    certificado_ref: str | None = None
    observacoes: str | None = None
    fu: int | None = Field(None, ge=1, le=3)
    nc: int | None = Field(None, ge=1, le=3)
    ab: int | None = Field(None, ge=1, le=3)
    cm: int | None = Field(None, ge=1, le=3)
    ci: int | None = Field(None, ge=1, le=3)


class InstrumentoPatch(BaseModel):
    """Atualização parcial: todos os campos opcionais; só os enviados são aplicados."""
    equipamento: str | None = None
    familia_id: int | None = None
    tipo_id: int | None = None
    ciclo_meses: int | None = None
    status_operacional: str | None = None
    codigo_interno: str | None = None
    codigo_patrimonial: str | None = None
    serial: str | None = None
    marca: str | None = None
    modelo: str | None = None
    faixa_min: float | None = None
    faixa_max: float | None = None
    resolucao: str | None = None
    emp: str | None = None
    disciplina: str | None = None
    grandeza_id: int | None = None
    unidade_id: int | None = None
    setor: str | None = None
    organizacao: str | None = None
    unidade_org: str | None = None
    secao: str | None = None
    bancada: str | None = None
    data_ultima_calibracao: date | None = None
    data_validade: date | None = None
    organizacao_calibradora: str | None = None
    local_calibracao: str | None = None
    certificado_ref: str | None = None
    observacoes: str | None = None
    fu: int | None = Field(None, ge=1, le=3)
    nc: int | None = Field(None, ge=1, le=3)
    ab: int | None = Field(None, ge=1, le=3)
    cm: int | None = Field(None, ge=1, le=3)
    ci: int | None = Field(None, ge=1, le=3)


class ProblemaImport(BaseModel):
    severidade: str
    campo: str
    mensagem: str


class TotaisImport(BaseModel):
    total_linhas: int
    validas: int
    com_aviso: int
    com_erro: int


class LinhaPreview(BaseModel):
    numero: int
    dados: dict
    problemas: list[ProblemaImport]


class PreviewResposta(BaseModel):
    totais: TotaisImport
    linhas: list[LinhaPreview]


class CommitResposta(BaseModel):
    inseridos: int
    ignorados: int


class ListaInstrumentos(BaseModel):
    total: int
    itens: list[InstrumentoOut]


class ItemDominio(BaseModel):
    id: int
    nome: str
    simbolo: str | None = None
    familia_id: int | None = None
    unidade_padrao_id: int | None = None


class DominiosOut(BaseModel):
    familias: list[ItemDominio]
    tipos: list[ItemDominio]
    grandezas: list[ItemDominio]
    unidades: list[ItemDominio]


class ExportRequest(BaseModel):
    """Pedido de exportação: ids na ordem desejada + formato do arquivo."""
    ids: list[int]
    formato: Literal["csv", "xlsx", "pdf"]


class CalibracaoIn(BaseModel):
    """Entrada de registro de calibração. validade/ciclo/status são derivados no servidor."""
    data_calibracao: date
    laboratorio_id: int | None = None
    item_contrato_id: int | None = None  # vincula a item de contrato vigente (consome saldo)
    resultado: Literal["APROVADO", "APROVADO_COM_RESTRICOES", "REPROVADO"] = "APROVADO"
    laboratorio: str | None = None
    laboratorio_cnpj: str | None = None
    acreditacao_rbc: bool = False
    numero_cgcre: str | None = None
    numero_certificado: str | None = None
    custo: float | None = None
    responsavel: str | None = None
    observacoes: str | None = None


class CalibracaoOut(BaseModel):
    id: int
    instrumento_id: int
    laboratorio_id: int | None
    item_contrato_id: int | None
    contrato_numero: str | None  # derivado (via item)
    data_calibracao: date
    data_validade: date | None
    ciclo_meses: int
    resultado: str
    laboratorio: str | None
    laboratorio_cnpj: str | None
    acreditacao_rbc: bool
    numero_cgcre: str | None
    numero_certificado: str | None
    custo: float | None
    responsavel: str | None
    certificado_path: str | None
    origem: str
    observacoes: str | None


class ListaCalibracoes(BaseModel):
    total: int
    itens: list[CalibracaoOut]


class RegistroCalibracaoOut(BaseModel):
    instrumento: InstrumentoOut
    calibracao: CalibracaoOut


class CalibracaoRecenteOut(BaseModel):
    """Item da lista global de calibrações (landing de calibracao.html)."""
    id: int
    instrumento_id: int
    instrumento_codigo: str | None
    instrumento_equipamento: str | None
    data_calibracao: date
    data_validade: date | None
    resultado: str
    laboratorio: str | None
    custo: float | None
    contrato_numero: str | None
    origem: str


class ListaCalibracoesRecentes(BaseModel):
    total: int
    itens: list[CalibracaoRecenteOut]


class LaboratorioIn(BaseModel):
    razao_social: str
    cnpj: str | None = None
    endereco: str | None = None
    contato: str | None = None
    telefone: str | None = None
    email: str | None = None
    numero_cgcre: str | None = None
    acreditado_rbc: bool = False
    escopo: str | None = None
    acreditacao_validade: date | None = None
    ativo: bool = True
    observacoes: str | None = None


class LaboratorioOut(BaseModel):
    id: int
    razao_social: str
    cnpj: str | None
    endereco: str | None
    contato: str | None
    telefone: str | None
    email: str | None
    numero_cgcre: str | None
    acreditado_rbc: bool
    escopo: str | None
    acreditacao_validade: date | None
    ativo: bool
    observacoes: str | None
    # derivados
    status_acreditacao: str
    dias_restantes: int | None


class ListaLaboratorios(BaseModel):
    total: int
    itens: list[LaboratorioOut]


class ItemContratoIn(BaseModel):
    numero: str | None = None
    descricao: str | None = None
    quantidade: int = 0
    valor_unitario: float | None = None
    usado: int = 0
    observacoes: str | None = None


class ItemContratoOut(BaseModel):
    id: int
    contrato_id: int
    numero: str | None
    descricao: str | None
    quantidade: int
    valor_unitario: float | None
    usado: int
    observacoes: str | None
    # derivados
    saldo: int
    valor_saldo: float


class ContratoIn(BaseModel):
    numero: str
    tipo: Literal["ATA", "CONTRATO", "CMS"] = "ATA"
    laboratorio_id: int  # contrato sempre tem um laboratório (fornecedor)
    objeto: str | None = None
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    valor_total: float | None = None
    ativo: bool = True
    observacoes: str | None = None


class ContratoOut(BaseModel):
    id: int
    numero: str
    tipo: str
    laboratorio_id: int | None
    laboratorio: str | None  # razão social (derivado)
    objeto: str | None
    vigencia_inicio: date | None
    vigencia_fim: date | None
    valor_total: float | None
    ativo: bool
    observacoes: str | None
    itens: list[ItemContratoOut]
    # derivados
    status_vigencia: str
    dias_restantes: int | None
    valor_saldo_total: float
    saldo_percent: float | None
    status_saldo: str


class ListaContratos(BaseModel):
    total: int
    itens: list[ContratoOut]


class CatalogoItemOut(BaseModel):
    """Linha do catálogo = item (serviço de calibração) de um contrato.
    Visão derivada dos contratos: preço, saldo, vigência por laboratório."""
    item_id: int
    item_numero: str | None
    descricao: str | None          # serviço (ex.: CALIBRAÇÃO DE MULTÍMETRO)
    laboratorio_id: int | None
    laboratorio: str | None
    contrato_id: int
    contrato_numero: str
    contrato_tipo: str
    preco: float | None            # valor_unitário do item
    quantidade: int
    usado: int
    saldo: int
    valor_saldo: float
    vigencia_fim: date | None
    status_vigencia: str
    vigente: bool                  # contrato não-vencido + item com saldo


class ListaCatalogoItens(BaseModel):
    total: int
    itens: list[CatalogoItemOut]


class InstrumentoPublicoOut(BaseModel):
    id: int
    codigo_interno: str | None
    codigo_patrimonial: str | None
    equipamento: str | None
    marca: str | None
    modelo: str | None
    tipo_nome: str | None
    secao: str | None
    setor: str | None
    status: str
    status_label: str
    status_operacional: str
    data_ultima_calibracao: date | None
    data_validade: date | None
    dias_restantes: int | None
