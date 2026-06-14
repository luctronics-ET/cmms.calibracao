"""ORM do SisCalib (fatia fina: apenas Instrumento)."""
from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import String, Integer, Date, DateTime, Numeric, Enum, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.db import Base


class Disciplina(str, enum.Enum):
    ELE = "ELE"
    MEC = "MEC"


class Instrumento(Base):
    __tablename__ = "instrumento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_interno: Mapped[str | None] = mapped_column(String, index=True)
    serial: Mapped[str | None] = mapped_column(String, index=True)
    equipamento: Mapped[str | None] = mapped_column(String)
    marca: Mapped[str | None] = mapped_column(String)
    modelo: Mapped[str | None] = mapped_column(String)
    faixa: Mapped[str | None] = mapped_column(String)
    unidade_faixa: Mapped[str | None] = mapped_column(String)
    disciplina: Mapped[Disciplina | None] = mapped_column(Enum(Disciplina))
    sistema: Mapped[str | None] = mapped_column(String, index=True)
    ciclo_meses: Mapped[int] = mapped_column(Integer, default=12)
    data_ultima_calibracao: Mapped[Date | None] = mapped_column(Date)
    data_validade: Mapped[Date | None] = mapped_column(Date)
    flag_origem: Mapped[str | None] = mapped_column(String)
    organizacao_calibradora: Mapped[str | None] = mapped_column(String)
    local_calibracao: Mapped[str | None] = mapped_column(String)
    custo_estimado: Mapped[float | None] = mapped_column(Numeric(12, 2))
    custo_contratado: Mapped[float | None] = mapped_column(Numeric(12, 2))
    certificado_ref: Mapped[str | None] = mapped_column(String)
    observacoes: Mapped[str | None] = mapped_column(String)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
