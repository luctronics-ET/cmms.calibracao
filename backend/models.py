"""ORM do SisCalib."""
from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import (
    String, Integer, Date, DateTime, Numeric, Enum, ForeignKey, Boolean, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db import Base


class Disciplina(str, enum.Enum):
    ELE = "ELE"
    MEC = "MEC"


class StatusOperacional(str, enum.Enum):
    ATIVO = "ATIVO"
    EM_CALIBRACAO = "EM_CALIBRACAO"
    EM_MANUTENCAO = "EM_MANUTENCAO"
    REPROVADO = "REPROVADO"
    BLOQUEADO = "BLOQUEADO"
    BAIXADO = "BAIXADO"


class Resultado(str, enum.Enum):
    APROVADO = "APROVADO"
    APROVADO_COM_RESTRICOES = "APROVADO_COM_RESTRICOES"
    REPROVADO = "REPROVADO"


class ContratoTipo(str, enum.Enum):
    ATA = "ATA"
    CONTRATO = "CONTRATO"
    CMS = "CMS"


class FamiliaMetrologica(Base):
    __tablename__ = "familia_metrologica"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String, unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)


class UnidadeMedida(Base):
    __tablename__ = "unidade_medida"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String, unique=True)
    simbolo: Mapped[str | None] = mapped_column(String)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)


class Grandeza(Base):
    __tablename__ = "grandeza"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String, unique=True)
    familia_id: Mapped[int | None] = mapped_column(ForeignKey("familia_metrologica.id"))
    unidade_padrao_id: Mapped[int | None] = mapped_column(ForeignKey("unidade_medida.id"))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    familia: Mapped["FamiliaMetrologica | None"] = relationship()
    unidade_padrao: Mapped["UnidadeMedida | None"] = relationship()


class TipoInstrumento(Base):
    __tablename__ = "tipo_instrumento"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String, unique=True)
    familia_id: Mapped[int | None] = mapped_column(ForeignKey("familia_metrologica.id"))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    familia: Mapped["FamiliaMetrologica | None"] = relationship()


class Instrumento(Base):
    __tablename__ = "instrumento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_interno: Mapped[str | None] = mapped_column(String, index=True)
    codigo_patrimonial: Mapped[str | None] = mapped_column(String, index=True)
    serial: Mapped[str | None] = mapped_column(String, index=True)
    equipamento: Mapped[str | None] = mapped_column(String)
    marca: Mapped[str | None] = mapped_column(String)
    modelo: Mapped[str | None] = mapped_column(String)
    # especificação técnica
    faixa: Mapped[str | None] = mapped_column(String)            # legado (texto livre)
    unidade_faixa: Mapped[str | None] = mapped_column(String)    # legado
    faixa_min: Mapped[float | None] = mapped_column(Numeric(18, 6))
    faixa_max: Mapped[float | None] = mapped_column(Numeric(18, 6))
    resolucao: Mapped[str | None] = mapped_column(String)
    emp: Mapped[str | None] = mapped_column(String)
    # classificação
    disciplina: Mapped[Disciplina | None] = mapped_column(Enum(Disciplina))
    familia_id: Mapped[int | None] = mapped_column(ForeignKey("familia_metrologica.id"))
    tipo_id: Mapped[int | None] = mapped_column(ForeignKey("tipo_instrumento.id"))
    grandeza_id: Mapped[int | None] = mapped_column(ForeignKey("grandeza.id"))
    unidade_id: Mapped[int | None] = mapped_column(ForeignKey("unidade_medida.id"))
    # localização
    sistema: Mapped[str | None] = mapped_column(String, index=True)
    organizacao: Mapped[str | None] = mapped_column(String)
    unidade_org: Mapped[str | None] = mapped_column(String)
    secao: Mapped[str | None] = mapped_column(String)
    bancada: Mapped[str | None] = mapped_column(String)
    # calibração
    ciclo_meses: Mapped[int] = mapped_column(Integer, default=12)
    data_ultima_calibracao: Mapped[Date | None] = mapped_column(Date)
    data_validade: Mapped[Date | None] = mapped_column(Date)
    flag_origem: Mapped[str | None] = mapped_column(String)
    organizacao_calibradora: Mapped[str | None] = mapped_column(String)
    local_calibracao: Mapped[str | None] = mapped_column(String)
    custo_estimado: Mapped[float | None] = mapped_column(Numeric(12, 2))
    custo_contratado: Mapped[float | None] = mapped_column(Numeric(12, 2))
    certificado_ref: Mapped[str | None] = mapped_column(String)
    # estado operacional
    status_operacional: Mapped[StatusOperacional] = mapped_column(
        Enum(StatusOperacional), default=StatusOperacional.ATIVO
    )
    # anexos
    foto_path: Mapped[str | None] = mapped_column(String)
    manual_path: Mapped[str | None] = mapped_column(String)
    # criticidade IGP (1..3, anuláveis)
    fu: Mapped[int | None] = mapped_column(Integer)
    nc: Mapped[int | None] = mapped_column(Integer)
    ab: Mapped[int | None] = mapped_column(Integer)
    cm: Mapped[int | None] = mapped_column(Integer)
    ci: Mapped[int | None] = mapped_column(Integer)
    # observações / auditoria
    observacoes: Mapped[str | None] = mapped_column(String)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    # relationships (lazy)
    familia: Mapped["FamiliaMetrologica | None"] = relationship()
    tipo: Mapped["TipoInstrumento | None"] = relationship()
    grandeza: Mapped["Grandeza | None"] = relationship()
    unidade: Mapped["UnidadeMedida | None"] = relationship()
    calibracoes: Mapped[list["Calibracao"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class Calibracao(Base):
    __tablename__ = "calibracao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrumento_id: Mapped[int] = mapped_column(
        ForeignKey("instrumento.id", ondelete="CASCADE"), index=True
    )
    laboratorio_id: Mapped[int | None] = mapped_column(
        ForeignKey("laboratorio.id", ondelete="SET NULL"), index=True
    )
    data_calibracao: Mapped[Date] = mapped_column(Date)
    data_validade: Mapped[Date | None] = mapped_column(Date)
    ciclo_meses: Mapped[int] = mapped_column(Integer, default=12)
    resultado: Mapped[Resultado] = mapped_column(Enum(Resultado), default=Resultado.APROVADO)
    laboratorio: Mapped[str | None] = mapped_column(String)
    laboratorio_cnpj: Mapped[str | None] = mapped_column(String)
    acreditacao_rbc: Mapped[bool] = mapped_column(Boolean, default=False)
    numero_cgcre: Mapped[str | None] = mapped_column(String)
    numero_certificado: Mapped[str | None] = mapped_column(String)
    custo: Mapped[float | None] = mapped_column(Numeric(12, 2))
    responsavel: Mapped[str | None] = mapped_column(String)
    certificado_path: Mapped[str | None] = mapped_column(String)
    origem: Mapped[str] = mapped_column(String, default="MANUAL")
    observacoes: Mapped[str | None] = mapped_column(String)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Laboratorio(Base):
    __tablename__ = "laboratorio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    razao_social: Mapped[str] = mapped_column(String)
    cnpj: Mapped[str | None] = mapped_column(String)
    endereco: Mapped[str | None] = mapped_column(String)
    contato: Mapped[str | None] = mapped_column(String)
    telefone: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    numero_cgcre: Mapped[str | None] = mapped_column(String)
    acreditado_rbc: Mapped[bool] = mapped_column(Boolean, default=False)
    escopo: Mapped[str | None] = mapped_column(String)
    acreditacao_validade: Mapped[Date | None] = mapped_column(Date)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    observacoes: Mapped[str | None] = mapped_column(String)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Contrato(Base):
    __tablename__ = "contrato"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero: Mapped[str] = mapped_column(String)
    tipo: Mapped[ContratoTipo] = mapped_column(Enum(ContratoTipo), default=ContratoTipo.ATA)
    fornecedor: Mapped[str | None] = mapped_column(String)
    objeto: Mapped[str | None] = mapped_column(String)
    vigencia_inicio: Mapped[Date | None] = mapped_column(Date)
    vigencia_fim: Mapped[Date | None] = mapped_column(Date)
    valor_total: Mapped[float | None] = mapped_column(Numeric(14, 2))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    observacoes: Mapped[str | None] = mapped_column(String)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    itens: Mapped[list["ItemContrato"]] = relationship(
        cascade="all, delete-orphan", order_by="ItemContrato.id"
    )


class ItemContrato(Base):
    __tablename__ = "item_contrato"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contrato_id: Mapped[int] = mapped_column(
        ForeignKey("contrato.id", ondelete="CASCADE"), index=True
    )
    numero: Mapped[str | None] = mapped_column(String)
    descricao: Mapped[str | None] = mapped_column(String)
    quantidade: Mapped[int] = mapped_column(Integer, default=0)
    valor_unitario: Mapped[float | None] = mapped_column(Numeric(12, 2))
    usado: Mapped[int] = mapped_column(Integer, default=0)
    observacoes: Mapped[str | None] = mapped_column(String)


class CatalogoPreco(Base):
    __tablename__ = "catalogo_preco"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo_id: Mapped[int] = mapped_column(
        ForeignKey("tipo_instrumento.id"), index=True
    )
    fornecedor: Mapped[str | None] = mapped_column(String)
    preco: Mapped[float | None] = mapped_column(Numeric(12, 2))
    item_contrato_id: Mapped[int | None] = mapped_column(
        ForeignKey("item_contrato.id", ondelete="SET NULL"), index=True
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    observacoes: Mapped[str | None] = mapped_column(String)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    tipo: Mapped["TipoInstrumento | None"] = relationship()
    item_contrato: Mapped["ItemContrato | None"] = relationship()
