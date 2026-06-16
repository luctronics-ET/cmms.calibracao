"""drop catalogo_preco (catálogo agora é visão derivada dos itens de contrato)

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = "b5c6d7e8f9a0"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("catalogo_preco")


def downgrade():
    op.create_table(
        "catalogo_preco",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo_id", sa.Integer(), sa.ForeignKey("tipo_instrumento.id"), index=True),
        sa.Column("fornecedor", sa.String()),
        sa.Column("preco", sa.Numeric(12, 2)),
        sa.Column("item_contrato_id", sa.Integer(),
                  sa.ForeignKey("item_contrato.id", ondelete="SET NULL"), index=True),
        sa.Column("ativo", sa.Boolean()),
        sa.Column("observacoes", sa.String()),
        sa.Column("criado_em", sa.DateTime()),
        sa.Column("atualizado_em", sa.DateTime()),
    )
