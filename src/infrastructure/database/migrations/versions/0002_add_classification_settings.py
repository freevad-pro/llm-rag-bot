"""add_classification_settings_table

Revision ID: 0002_add_classification_settings
Revises: c779ff28525e
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002_add_classification_settings'
down_revision = 'c779ff28525e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создаем таблицу classification_settings
    op.create_table('classification_settings',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('enable_fast_classification', sa.Boolean(), nullable=False, default=True),
        sa.Column('enable_llm_classification', sa.Boolean(), nullable=False, default=True),
        sa.Column('product_keywords', sa.Text(), nullable=True),
        sa.Column('contact_keywords', sa.Text(), nullable=True),
        sa.Column('company_keywords', sa.Text(), nullable=True),
        sa.Column('availability_phrases', sa.Text(), nullable=True),
        sa.Column('search_words', sa.Text(), nullable=True),
        sa.Column('specific_products', sa.Text(), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['admin_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создаем индексы
    op.create_index('idx_classification_settings_active', 'classification_settings', ['is_active'])
    op.create_index('idx_classification_settings_created', 'classification_settings', ['created_at'])
    
    # Инициализируем дефолтные настройки
    # Получаем ID первого админа (предполагаем что он существует)
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT id FROM admin_users ORDER BY id LIMIT 1"))
    admin_id = result.fetchone()
    
    if admin_id:
        admin_id = admin_id[0]
        
        # Вставляем дефолтные настройки
        op.execute(f"""
            INSERT INTO classification_settings (
                enable_fast_classification,
                enable_llm_classification,
                product_keywords,
                contact_keywords,
                company_keywords,
                availability_phrases,
                search_words,
                specific_products,
                description,
                is_active,
                created_by
            ) VALUES (
                true,
                true,
                '["товар", "product", "оборудование", "equipment", "запчасть", "part", "spare", "деталь", "detail", "артикул", "article", "sku", "модель", "model", "компонент", "component", "изделие", "item"]',
                '["менеджер", "manager", "связаться", "contact", "позвонить", "call", "заказать", "order", "купить", "buy", "цена", "price", "консультация", "consultation", "помощь менеджера", "manager help", "связаться с менеджером", "contact manager", "нужна помощь", "need help", "консультант", "consultant"]',
                '["компания", "company", "о вас", "about you", "адрес", "address", "контакты", "contacts", "история", "history", "местоположение", "location", "офис", "office", "где находитесь", "where are you located", "информация о компании", "company information"]',
                '["есть ли у вас", "do you have", "продаете ли", "do you sell", "найдется ли", "can be found", "имеется ли", "is available", "у вас есть", "you have", "в наличии", "in stock", "есть в наличии", "available in stock", "можно ли купить", "can I buy", "можно ли заказать", "can I order", "есть ли возможность", "is it possible", "реализуете ли", "do you supply"]',
                '["найти", "find", "искать", "search", "нужен", "need", "требуется", "required", "looking for", "ищу", "поиск", "подобрать", "select", "выбрать", "choose"]',
                '["сверло", "drill", "bit", "керн", "core", "болт", "винт", "гайка", "шайба", "nut", "bolt", "screw", "washer", "подшипник", "bearing", "фильтр", "filter", "масло", "oil", "ремень", "belt", "насос", "pump", "двигатель", "motor", "engine", "компрессор", "compressor", "клапан", "valve", "шланг", "hose", "кабель", "cable", "wire", "провод", "провода", "резистор", "resistor", "конденсатор", "capacitor", "транзистор", "transistor", "микросхема", "chip", "плата", "board", "разъем", "connector", "датчик", "sensor", "реле", "relay", "контроллер", "controller"]',
                'Дефолтные настройки классификации (автоматически созданы при миграции)',
                true,
                {admin_id}
            )
        """)


def downgrade() -> None:
    # Удаляем индексы
    op.drop_index('idx_classification_settings_created', table_name='classification_settings')
    op.drop_index('idx_classification_settings_active', table_name='classification_settings')
    
    # Удаляем таблицу
    op.drop_table('classification_settings')
