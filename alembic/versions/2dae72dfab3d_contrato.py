"""contrato

Revision ID: 2dae72dfab3d
Revises: a5e01e43b2d8
Create Date: 2026-06-14 22:38:56.195131

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2dae72dfab3d'
down_revision: Union[str, Sequence[str], None] = 'a5e01e43b2d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'contrato',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('numero', sa.String(), nullable=False),
        sa.Column('tipo', sa.Enum('ATA', 'CONTRATO', 'CMS', name='contratotipo'), nullable=False),
        sa.Column('fornecedor', sa.String(), nullable=True),
        sa.Column('objeto', sa.String(), nullable=True),
        sa.Column('vigencia_inicio', sa.Date(), nullable=True),
        sa.Column('vigencia_fim', sa.Date(), nullable=True),
        sa.Column('valor_total', sa.Numeric(14, 2), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('observacoes', sa.String(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'item_contrato',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contrato_id', sa.Integer(), nullable=False),
        sa.Column('numero', sa.String(), nullable=True),
        sa.Column('descricao', sa.String(), nullable=True),
        sa.Column('quantidade', sa.Integer(), nullable=False),
        sa.Column('valor_unitario', sa.Numeric(12, 2), nullable=True),
        sa.Column('usado', sa.Integer(), nullable=False),
        sa.Column('observacoes', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['contrato_id'], ['contrato.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_item_contrato_contrato_id', 'item_contrato', ['contrato_id'])


def downgrade() -> None:
    op.drop_index('ix_item_contrato_contrato_id', table_name='item_contrato')
    op.drop_table('item_contrato')
    op.drop_table('contrato')
