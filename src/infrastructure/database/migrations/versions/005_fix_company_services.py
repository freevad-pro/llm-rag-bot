"""Fix company_services table structure

Revision ID: 005_fix_company_services
Revises: 004_add_prompt_metadata
Create Date: 2025-09-22 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_fix_company_services'
down_revision = '004_add_prompt_metadata'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Проверяем существование таблицы и колонок
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Обновляем company_services если она существует
    if 'company_services' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('company_services')]
        
        # Добавляем недостающие колонки
        if 'name' not in existing_columns:
            op.add_column('company_services', sa.Column('name', sa.String(length=255), nullable=True))
            # Заполняем name значениями из title если он есть
            if 'title' in existing_columns:
                op.execute("UPDATE company_services SET name = title WHERE name IS NULL")
            op.alter_column('company_services', 'name', nullable=False)
        
        if 'price_info' not in existing_columns:
            op.add_column('company_services', sa.Column('price_info', sa.String(length=255), nullable=True))
        
        if 'is_active' not in existing_columns:
            op.add_column('company_services', sa.Column('is_active', sa.Boolean(), nullable=True))
            # Заполняем is_active значениями из active если он есть
            if 'active' in existing_columns:
                op.execute("UPDATE company_services SET is_active = active WHERE is_active IS NULL")
            else:
                op.execute("UPDATE company_services SET is_active = true WHERE is_active IS NULL")
            op.alter_column('company_services', 'is_active', nullable=False)
        
        if 'sort_order' not in existing_columns:
            op.add_column('company_services', sa.Column('sort_order', sa.Integer(), nullable=True))
            op.execute("UPDATE company_services SET sort_order = 0 WHERE sort_order IS NULL")
            op.alter_column('company_services', 'sort_order', nullable=False)
        
        # Изменяем тип category если нужно
        op.alter_column('company_services', 'category',
                       existing_type=sa.VARCHAR(length=255),
                       type_=sa.String(length=100),
                       existing_nullable=True)
        
        # Создаем индекс
        try:
            op.create_index('idx_services_active_sort', 'company_services', ['is_active', 'sort_order'], unique=False)
        except:
            pass  # Индекс уже существует
        
        # Удаляем старые колонки если они есть
        if 'title' in existing_columns and 'name' in [col['name'] for col in inspector.get_columns('company_services')]:
            op.drop_column('company_services', 'title')
        
        if 'active' in existing_columns and 'is_active' in [col['name'] for col in inspector.get_columns('company_services')]:
            op.drop_column('company_services', 'active')
    
    else:
        # Создаем таблицу с нуля если её нет
        op.create_table('company_services',
            sa.Column('id', sa.BigInteger(), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('category', sa.String(length=100), nullable=True),
            sa.Column('keywords', sa.Text(), nullable=True),
            sa.Column('price_info', sa.String(length=255), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
            sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_services_active_sort', 'company_services', ['is_active', 'sort_order'], unique=False)


def downgrade() -> None:
    # Удаляем индекс
    try:
        op.drop_index('idx_services_active_sort', table_name='company_services')
    except:
        pass
    
    # Возвращаем старые колонки
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'company_services' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('company_services')]
        
        # Возвращаем title если name существует
        if 'name' in existing_columns:
            op.add_column('company_services', sa.Column('title', sa.String(length=255), nullable=True))
            op.execute("UPDATE company_services SET title = name")
            op.drop_column('company_services', 'name')
        
        # Возвращаем active если is_active существует
        if 'is_active' in existing_columns:
            op.add_column('company_services', sa.Column('active', sa.Boolean(), nullable=True))
            op.execute("UPDATE company_services SET active = is_active")
            op.drop_column('company_services', 'is_active')
        
        # Удаляем новые колонки
        if 'price_info' in existing_columns:
            op.drop_column('company_services', 'price_info')
        if 'sort_order' in existing_columns:
            op.drop_column('company_services', 'sort_order')
        
        # Возвращаем исходный тип category
        op.alter_column('company_services', 'category',
                       existing_type=sa.String(length=100),
                       type_=sa.VARCHAR(length=255),
                       existing_nullable=True)




