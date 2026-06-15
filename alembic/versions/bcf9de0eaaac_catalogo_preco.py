"""catalogo_preco

Revision ID: bcf9de0eaaac
Revises: 2dae72dfab3d
Create Date: 2026-06-15 00:16:39.621324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcf9de0eaaac'
down_revision: Union[str, Sequence[str], None] = '2dae72dfab3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'catalogo_preco',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tipo_id', sa.Integer(), nullable=False),
        sa.Column('fornecedor', sa.String(), nullable=True),
        sa.Column('preco', sa.Numeric(12, 2), nullable=True),
        sa.Column('item_contrato_id', sa.Integer(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('observacoes', sa.String(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['tipo_id'], ['tipo_instrumento.id']),
        sa.ForeignKeyConstraint(['item_contrato_id'], ['item_contrato.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_catalogo_preco_tipo_id', 'catalogo_preco', ['tipo_id'])
    op.create_index('ix_catalogo_preco_item_contrato_id', 'catalogo_preco', ['item_contrato_id'])


def downgrade() -> None:
    op.drop_index('ix_catalogo_preco_item_contrato_id', table_name='catalogo_preco')
    op.drop_index('ix_catalogo_preco_tipo_id', table_name='catalogo_preco')
    op.drop_table('catalogo_preco')
