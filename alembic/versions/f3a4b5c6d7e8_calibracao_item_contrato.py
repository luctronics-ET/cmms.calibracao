"""calibracao.item_contrato_id (FK opcional)

Revision ID: f3a4b5c6d7e8
Revises: e2b3c4d5f6a7
Create Date: 2026-06-16

Vincula calibração a um item de contrato (serviço de calibração consumido).
Opcional: calibrações importadas/internas ficam sem vínculo.
"""
from alembic import op
import sqlalchemy as sa

revision = "f3a4b5c6d7e8"
down_revision = "e2b3c4d5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("calibracao", sa.Column("item_contrato_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_calibracao_item_contrato_id"), "calibracao", ["item_contrato_id"])


def downgrade():
    op.drop_index(op.f("ix_calibracao_item_contrato_id"), table_name="calibracao")
    with op.batch_alter_table("calibracao") as b:
        b.drop_column("item_contrato_id")
