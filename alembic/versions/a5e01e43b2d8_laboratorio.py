"""laboratorio

Revision ID: a5e01e43b2d8
Revises: ba250c7eb571
Create Date: 2026-06-14 21:41:47.185174

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5e01e43b2d8'
down_revision: Union[str, Sequence[str], None] = 'ba250c7eb571'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'laboratorio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('razao_social', sa.String(), nullable=False),
        sa.Column('cnpj', sa.String(), nullable=True),
        sa.Column('endereco', sa.String(), nullable=True),
        sa.Column('contato', sa.String(), nullable=True),
        sa.Column('telefone', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('numero_cgcre', sa.String(), nullable=True),
        sa.Column('acreditado_rbc', sa.Boolean(), nullable=False),
        sa.Column('escopo', sa.String(), nullable=True),
        sa.Column('acreditacao_validade', sa.Date(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('observacoes', sa.String(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('calibracao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('laboratorio_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_calibracao_laboratorio', 'laboratorio',
            ['laboratorio_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('ix_calibracao_laboratorio_id', ['laboratorio_id'])


def downgrade() -> None:
    with op.batch_alter_table('calibracao', schema=None) as batch_op:
        batch_op.drop_index('ix_calibracao_laboratorio_id')
        batch_op.drop_constraint('fk_calibracao_laboratorio', type_='foreignkey')
        batch_op.drop_column('laboratorio_id')
    op.drop_table('laboratorio')
