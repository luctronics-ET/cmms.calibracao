"""contrato.fornecedor (texto) -> laboratorio_id (FK)

Revision ID: e2b3c4d5f6a7
Revises: d1a2b3c4e5f6
Create Date: 2026-06-16

Fornecedor do contrato passa a ser um laboratório (FK). Migra o texto
existente para laboratorio.id por correspondência de razão social
(best-effort); o que não casar fica NULL e é religado via seed/UI.
"""
from alembic import op
import sqlalchemy as sa

revision = "e2b3c4d5f6a7"
down_revision = "d1a2b3c4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("contrato", sa.Column("laboratorio_id", sa.Integer(), nullable=True))
    # best-effort: casa fornecedor texto com razão social de laboratório existente
    op.execute(
        "UPDATE contrato SET laboratorio_id = "
        "(SELECT id FROM laboratorio WHERE laboratorio.razao_social = contrato.fornecedor) "
        "WHERE fornecedor IS NOT NULL"
    )
    op.create_index(op.f("ix_contrato_laboratorio_id"), "contrato", ["laboratorio_id"])
    with op.batch_alter_table("contrato") as b:
        b.drop_column("fornecedor")


def downgrade():
    op.add_column("contrato", sa.Column("fornecedor", sa.String(), nullable=True))
    op.execute(
        "UPDATE contrato SET fornecedor = "
        "(SELECT razao_social FROM laboratorio WHERE laboratorio.id = contrato.laboratorio_id) "
        "WHERE laboratorio_id IS NOT NULL"
    )
    op.drop_index(op.f("ix_contrato_laboratorio_id"), table_name="contrato")
    with op.batch_alter_table("contrato") as b:
        b.drop_column("laboratorio_id")
