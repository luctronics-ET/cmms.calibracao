"""calibracao

Revision ID: ba250c7eb571
Revises: c00a5e8ec52e
Create Date: 2026-06-14 20:42:09.607693

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba250c7eb571'
down_revision: Union[str, Sequence[str], None] = 'c00a5e8ec52e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'calibracao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('instrumento_id', sa.Integer(), nullable=False),
        sa.Column('data_calibracao', sa.Date(), nullable=False),
        sa.Column('data_validade', sa.Date(), nullable=True),
        sa.Column('ciclo_meses', sa.Integer(), nullable=False),
        sa.Column('resultado',
                  sa.Enum('APROVADO', 'APROVADO_COM_RESTRICOES', 'REPROVADO', name='resultado'),
                  nullable=False),
        sa.Column('laboratorio', sa.String(), nullable=True),
        sa.Column('laboratorio_cnpj', sa.String(), nullable=True),
        sa.Column('acreditacao_rbc', sa.Boolean(), nullable=False),
        sa.Column('numero_cgcre', sa.String(), nullable=True),
        sa.Column('numero_certificado', sa.String(), nullable=True),
        sa.Column('custo', sa.Numeric(12, 2), nullable=True),
        sa.Column('responsavel', sa.String(), nullable=True),
        sa.Column('certificado_path', sa.String(), nullable=True),
        sa.Column('origem', sa.String(), nullable=False),
        sa.Column('observacoes', sa.String(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['instrumento_id'], ['instrumento.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_calibracao_instrumento_id', 'calibracao', ['instrumento_id'])


def downgrade() -> None:
    op.drop_index('ix_calibracao_instrumento_id', table_name='calibracao')
    op.drop_table('calibracao')
