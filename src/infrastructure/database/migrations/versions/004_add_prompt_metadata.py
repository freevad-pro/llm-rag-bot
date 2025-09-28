"""Add display_name and description to prompts

Revision ID: 004_add_prompt_metadata
Revises: 003_classic_auth
Create Date: 2025-09-22 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_add_prompt_metadata'
down_revision = '003_classic_auth'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем новые поля в таблицу prompts
    op.add_column('prompts', sa.Column('display_name', sa.String(length=200), nullable=True))
    op.add_column('prompts', sa.Column('description', sa.Text(), nullable=True))
    
    # Заполняем существующие записи базовыми значениями
    connection = op.get_bind()
    
    # Словарь переводов для существующих промптов
    translations = {
        'system_prompt': {
            'display_name': 'Основной системный промпт',
            'description': 'Основные инструкции для AI-агента, определяющие его поведение и роль'
        },
        'product_search_prompt': {
            'display_name': 'Поиск товаров',
            'description': 'Промпт для поиска и рекомендации товаров из каталога'
        },
        'service_answer_prompt': {
            'display_name': 'Ответы об услугах',
            'description': 'Промпт для ответов о услугах компании'
        },
        'general_conversation_prompt': {
            'display_name': 'Общие вопросы',
            'description': 'Промпт для общения и поддержания диалога'
        },
        'lead_qualification_prompt': {
            'display_name': 'Квалификация лидов',
            'description': 'Промпт для определения и квалификации потенциальных клиентов'
        },
        'company_info_prompt': {
            'display_name': 'Информация о компании',
            'description': 'Промпт для ответов на вопросы о компании'
        },
        'conversation_closing_prompt': {
            'display_name': 'Завершение диалога',
            'description': 'Промпт для корректного завершения разговора с клиентом'
        },
        'error_handling_prompt': {
            'display_name': 'Обработка ошибок',
            'description': 'Промпт для обработки ошибочных ситуаций и непонятных запросов'
        },
        'objection_handling_prompt': {
            'display_name': 'Работа с возражениями',
            'description': 'Промпт для обработки возражений и сомнений клиентов'
        }
    }
    
    # Обновляем существующие записи
    for name, data in translations.items():
        connection.execute(
            sa.text("""
                UPDATE prompts 
                SET display_name = :display_name, description = :description 
                WHERE name = :name
            """),
            {
                'name': name,
                'display_name': data['display_name'],
                'description': data['description']
            }
        )


def downgrade() -> None:
    # Удаляем добавленные колонки
    op.drop_column('prompts', 'description')
    op.drop_column('prompts', 'display_name')





