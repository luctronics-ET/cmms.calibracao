"""Modelos de entrada/saída da API."""
from __future__ import annotations
from datetime import date
from pydantic import BaseModel


class InstrumentoOut(BaseModel):
    id: int
    codigo_interno: str | None
    serial: str | None
    equipamento: str | None
    marca: str | None
    modelo: str | None
    faixa: str | None
    unidade_faixa: str | None
    disciplina: str | None
    sistema: str | None
    ciclo_meses: int
    data_ultima_calibracao: date | None
    data_validade: date | None
    flag_origem: str | None
    organizacao_calibradora: str | None
    local_calibracao: str | None
    custo_estimado: float | None
    custo_contratado: float | None
    certificado_ref: str | None
    observacoes: str | None
    # derivados
    status: str
    dias_restantes: int | None
    divergencia_flag: bool


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
