"""Rename started_at to created_at in conversations table

Revision ID: 008_rename_started_at_to_created_at
Revises: 007_add_system_logs_columns
Create Date: 2025-09-23 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008_rename_started_at'
down_revision = '007_add_system_logs_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Переименовываем started_at в created_at
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.alter_column('started_at', new_column_name='created_at')


def downgrade() -> None:
    # Возвращаем обратно
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.alter_column('created_at', new_column_name='started_at')
