"""Add service categories table

Revision ID: 006_add_service_categories
Revises: 005_fix_company_services
Create Date: 2025-09-22 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_add_service_categories'
down_revision = '005_fix_company_services'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создаем таблицу категорий
    op.create_table('service_categories',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Создаем индекс для категорий
    op.create_index('idx_categories_active_sort', 'service_categories', ['is_active', 'sort_order'], unique=False)
    
    # Добавляем колонку category_id в company_services
    op.add_column('company_services', sa.Column('category_id', sa.BigInteger(), nullable=True))
    
    # Создаем foreign key на категории
    op.create_foreign_key('fk_services_category', 'company_services', 'service_categories', ['category_id'], ['id'])
    
    # Создаем индекс для category_id
    op.create_index('idx_services_category', 'company_services', ['category_id'], unique=False)
    
    # Инициализируем дефолтные категории
    connection = op.get_bind()
    
    # Данные дефолтных категорий
    default_categories = [
        ("development", "Разработка", "Создание программного обеспечения, веб-приложений и мобильных приложений", "#007bff", "code-slash", 1),
        ("consulting", "Консалтинг", "Консультационные услуги по IT и бизнес-процессам", "#28a745", "people", 2),
        ("support", "Поддержка", "Техническая поддержка и сопровождение проектов", "#ffc107", "headset", 3),
        ("design", "Дизайн", "UI/UX дизайн, графический дизайн и брендинг", "#e83e8c", "palette", 4),
        ("analytics", "Аналитика", "Анализ данных, бизнес-аналитика и отчетность", "#17a2b8", "graph-up", 5),
        ("marketing", "Маркетинг", "Цифровой маркетинг, SEO и продвижение", "#fd7e14", "megaphone", 6),
        ("training", "Обучение", "Образовательные программы и тренинги", "#6f42c1", "book", 7),
        ("integration", "Интеграция", "Интеграция систем и API", "#20c997", "diagram-3", 8),
        ("other", "Прочее", "Другие услуги", "#6c757d", "gear", 99)
    ]
    
    for name, display_name, description, color, icon, sort_order in default_categories:
        connection.execute(
            sa.text("""
                INSERT INTO service_categories (name, display_name, description, color, icon, is_active, sort_order, created_at)
                VALUES (:name, :display_name, :description, :color, :icon, true, :sort_order, NOW())
            """),
            {
                "name": name,
                "display_name": display_name,
                "description": description,
                "color": color,
                "icon": icon,
                "sort_order": sort_order
            }
        )


def downgrade() -> None:
    # Удаляем foreign key
    op.drop_constraint('fk_services_category', 'company_services', type_='foreignkey')
    
    # Удаляем индексы
    op.drop_index('idx_services_category', table_name='company_services')
    op.drop_index('idx_categories_active_sort', table_name='service_categories')
    
    # Удаляем колонку category_id
    op.drop_column('company_services', 'category_id')
    
    # Удаляем таблицу категорий
    op.drop_table('service_categories')


