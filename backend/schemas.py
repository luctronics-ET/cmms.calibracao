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
    sistema: str | None
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
    sistema: str | None = None
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
    sistema: str | None = None
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
