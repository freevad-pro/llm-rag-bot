"""add_message_extra_data_field

Revision ID: 011_add_message_extra_data
Revises: 010_fix_message_role_constraint
Create Date: 2025-09-29 16:00:00.000000

Добавляет поле extra_data в таблицу messages для хранения 
дополнительных метаданных сообщений в формате JSON.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011_add_message_extra_data'
down_revision = '010_fix_message_role_constraint'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет столбец extra_data в таблицу messages"""
    op.add_column('messages', sa.Column('extra_data', sa.Text(), nullable=True))


def downgrade() -> None:
    """Удаляет столбец extra_data из таблицы messages"""
    op.drop_column('messages', 'extra_data')
