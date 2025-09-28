"""fix_message_role_constraint_to_lowercase

Revision ID: 010_fix_message_role_constraint
Revises: 009_add_catalog_versions_table
Create Date: 2025-09-28 20:00:00.000000

Исправляет CHECK constraint для поля role в таблице messages.
Меняет с ('USER', 'ASSISTANT', 'SYSTEM') на ('user', 'assistant', 'system')
для соответствия API провайдеров LLM и естественности кода.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010_fix_message_role_constraint'
down_revision = '009_add_catalog_versions_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Изменяет CHECK constraint для роли сообщений на нижний регистр
    """
    # Удаляем старый constraint
    op.drop_constraint('check_message_role', 'messages', type_='check')
    
    # Создаем новый constraint с ролями в нижнем регистре
    op.create_check_constraint(
        'check_message_role',
        'messages',
        "role IN ('user', 'assistant', 'system')"
    )


def downgrade() -> None:
    """
    Возвращает CHECK constraint к верхнему регистру
    """
    # Удаляем новый constraint
    op.drop_constraint('check_message_role', 'messages', type_='check')
    
    # Восстанавливаем старый constraint с ролями в верхнем регистре
    op.create_check_constraint(
        'check_message_role', 
        'messages',
        "role IN ('USER', 'ASSISTANT', 'SYSTEM')"
    )
