"""Add missing columns to system_logs table

Revision ID: 007_add_system_logs_columns
Revises: 006_add_service_categories
Create Date: 2025-09-23 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_add_system_logs_columns'
down_revision = '006_add_service_categories'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем недостающие колонки в system_logs
    with op.batch_alter_table('system_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('module', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('function', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('line_number', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Удаляем добавленные колонки
    with op.batch_alter_table('system_logs', schema=None) as batch_op:
        batch_op.drop_column('line_number')
        batch_op.drop_column('function')
        batch_op.drop_column('module')






