"""contrato.laboratorio_id NOT NULL (sempre tem fornecedor)

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-06-16

Um contrato/ATA sempre tem um laboratório (fornecedor). Remove contratos
órfãos (sem laboratório — dados de teste) e torna a FK obrigatória.
"""
from alembic import op
import sqlalchemy as sa

revision = "a4b5c6d7e8f9"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade():
    # remove itens dos contratos órfãos (FK pode não estar ON no alembic), depois os contratos
    op.execute(
        "DELETE FROM item_contrato WHERE contrato_id IN "
        "(SELECT id FROM contrato WHERE laboratorio_id IS NULL)"
    )
    op.execute("DELETE FROM contrato WHERE laboratorio_id IS NULL")
    with op.batch_alter_table("contrato") as b:
        b.alter_column("laboratorio_id", existing_type=sa.Integer(), nullable=False)


def downgrade():
    with op.batch_alter_table("contrato") as b:
        b.alter_column("laboratorio_id", existing_type=sa.Integer(), nullable=True)
