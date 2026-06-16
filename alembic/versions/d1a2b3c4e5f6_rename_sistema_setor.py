"""rename instrumento.sistema -> setor

Revision ID: d1a2b3c4e5f6
Revises: bcf9de0eaaac
Create Date: 2026-06-16

Renomeia a coluna `sistema` (que representa a divisão: EXOCET, MK-48, ...)
para `setor`, nome mais genérico. Dados preservados.
"""
from alembic import op

revision = "d1a2b3c4e5f6"
down_revision = "bcf9de0eaaac"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ix_instrumento_sistema", table_name="instrumento")
    with op.batch_alter_table("instrumento") as b:
        b.alter_column("sistema", new_column_name="setor")
    op.create_index(op.f("ix_instrumento_setor"), "instrumento", ["setor"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_instrumento_setor"), table_name="instrumento")
    with op.batch_alter_table("instrumento") as b:
        b.alter_column("setor", new_column_name="sistema")
    op.create_index("ix_instrumento_sistema", "instrumento", ["sistema"], unique=False)
