"""Add admin users and catalog management tables

Revision ID: 002_admin_tables
Revises: 
Create Date: 2025-09-22 14:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_admin_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create admin_users table
    op.create_table('admin_users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role IN ('MANAGER', 'ADMIN')", name='check_admin_role'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    op.create_index(op.f('ix_admin_users_telegram_id'), 'admin_users', ['telegram_id'], unique=False)

    # Create company_info table
    op.create_table('company_info',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('original_filename', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_type', sa.String(length=10), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('uploaded_by', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['uploaded_by'], ['admin_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create catalog_versions table
    op.create_table('catalog_versions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('original_filename', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('products_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('uploaded_by', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('UPLOADING', 'INDEXING', 'ACTIVE', 'FAILED')", name='check_catalog_status'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['admin_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_catalog_versions_status_created', 'catalog_versions', ['status', 'created_at'], unique=False)

    # Set default values
    op.execute("ALTER TABLE admin_users ALTER COLUMN role SET DEFAULT 'MANAGER'")
    op.execute("ALTER TABLE admin_users ALTER COLUMN is_active SET DEFAULT true")
    op.execute("ALTER TABLE company_info ALTER COLUMN version SET DEFAULT 1")
    op.execute("ALTER TABLE company_info ALTER COLUMN is_active SET DEFAULT false")
    op.execute("ALTER TABLE catalog_versions ALTER COLUMN products_count SET DEFAULT 0")
    op.execute("ALTER TABLE catalog_versions ALTER COLUMN status SET DEFAULT 'UPLOADING'")
    op.execute("ALTER TABLE catalog_versions ALTER COLUMN is_active SET DEFAULT false")


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_catalog_versions_status_created', table_name='catalog_versions')
    op.drop_index(op.f('ix_admin_users_telegram_id'), table_name='admin_users')
    
    # Drop tables
    op.drop_table('catalog_versions')
    op.drop_table('company_info')
    op.drop_table('admin_users')
