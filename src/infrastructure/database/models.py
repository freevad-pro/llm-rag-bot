"""
Модели SQLAlchemy для базы данных
Согласно схеме из @vision.md
"""
from sqlalchemy import (
    Column, BigInteger, String, DateTime, Text, Boolean, Integer, 
    ForeignKey, Index, CheckConstraint, desc
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional


Base = declarative_base()


class User(Base):
    """
    Пользователи системы
    Основной идентификатор: chat_id (НЕ telegram_user_id)
    """
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    telegram_user_id = Column(BigInteger, nullable=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Отношения
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="user", cascade="all, delete-orphan")


class Lead(Base):
    """
    Лиды (потенциальные клиенты)
    """
    __tablename__ = "leads"
    
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    
    # Контактная информация (соответствует реальной структуре БД)
    name = Column(String(255), nullable=True)
    phone = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    telegram = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    question = Column(Text, nullable=True)
    
    # Метаданные синхронизации
    status = Column(String(50), nullable=True)
    sync_attempts = Column(Integer, default=0, nullable=True)
    zoho_lead_id = Column(String(255), nullable=True)
    last_sync_attempt = Column(DateTime(timezone=True), nullable=True)
    auto_created = Column(Boolean, default=False, nullable=True)
    lead_source = Column(String(255), nullable=True)
    
    # Системные поля
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Отношения
    user = relationship("User", back_populates="leads")


class Conversation(Base):
    """
    Диалоги пользователей с ботом
    """
    __tablename__ = "conversations"
    
    id = Column(BigInteger, primary_key=True)
    chat_id = Column(BigInteger, nullable=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    
    # Метаданные разговора (соответствует реальной структуре БД)
    status = Column(String(50), nullable=True)
    platform = Column(String(50), nullable=True)
    extra_data = Column(Text, nullable=True)
    
    # Системные поля
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Отношения
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """
    Сообщения в диалогах
    """
    __tablename__ = "messages"
    
    id = Column(BigInteger, primary_key=True)
    conversation_id = Column(BigInteger, ForeignKey("conversations.id"), nullable=False)
    
    # Содержимое сообщения
    content = Column(Text, nullable=False)
    role = Column(String(20), nullable=False)  # USER, ASSISTANT, SYSTEM
    message_type = Column(String(20), default="TEXT", nullable=False)  # TEXT, IMAGE, DOCUMENT
    
    # Метаданные обработки
    processing_time_ms = Column(Integer, nullable=True)
    llm_provider = Column(String(50), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    
    # Системные поля
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Отношения
    conversation = relationship("Conversation", back_populates="messages")
    
    # Ограничения
    __table_args__ = (
        CheckConstraint("role IN ('USER', 'ASSISTANT', 'SYSTEM')", name="check_message_role"),
        CheckConstraint("message_type IN ('TEXT', 'IMAGE', 'DOCUMENT')", name="check_message_type"),
        Index("idx_messages_conversation_created", "conversation_id", "created_at"),
    )


class Prompt(Base):
    """
    Системные промпты
    """
    __tablename__ = "prompts"
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200), nullable=True)  # Человеко-читаемое название
    description = Column(Text, nullable=True)  # Описание назначения промпта
    content = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AdminUser(Base):
    """
    Администраторы и менеджеры системы
    Классическая авторизация через username/password
    """
    __tablename__ = "admin_users"
    
    id = Column(BigInteger, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False, default="ADMIN")  # MANAGER, ADMIN
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Поля для восстановления пароля
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Ограничения
    __table_args__ = (
        CheckConstraint("role IN ('MANAGER', 'ADMIN')", name="check_admin_role"),
    )


class CompanyInfo(Base):
    """
    Информация о компании (версионная)
    """
    __tablename__ = "company_info"
    
    id = Column(BigInteger, primary_key=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(10), nullable=False)  # DOCX, PDF, TXT
    content = Column(Text, nullable=False)  # Извлеченный текст
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    uploaded_by = Column(BigInteger, ForeignKey("admin_users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UsageStatistics(Base):
    """
    Статистика использования AI токенов по месяцам
    """
    __tablename__ = "usage_statistics"
    
    id = Column(BigInteger, primary_key=True)
    provider = Column(String(50), nullable=False)  # 'openai', 'yandexgpt'
    model = Column(String(100), nullable=False)    # 'gpt-4o-mini', 'gpt-4o', 'yandexgpt-lite'
    year = Column(Integer, nullable=False)         # 2024
    month = Column(Integer, nullable=False)        # 1-12
    total_tokens = Column(BigInteger, default=0, nullable=False)  # Общее количество токенов
    price_per_1k_tokens = Column(String(20), nullable=True)      # Цена за 1K токенов (строка для гибкости)
    currency = Column(String(3), default='USD', nullable=False)  # 'USD', 'RUB'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Уникальный индекс по провайдеру, модели, году и месяцу
    __table_args__ = (
        Index("idx_usage_stats_provider_model_date", "provider", "model", "year", "month", unique=True),
        Index("idx_usage_stats_date", "year", "month"),
    )


class CatalogVersion(Base):
    """
    Версии каталога товаров
    """
    __tablename__ = "catalog_versions"
    
    id = Column(BigInteger, primary_key=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    products_count = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="UPLOADING", nullable=False)  # UPLOADING, INDEXING, ACTIVE, FAILED
    is_active = Column(Boolean, default=False, nullable=False)
    uploaded_by = Column(BigInteger, ForeignKey("admin_users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    indexed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Ограничения
    __table_args__ = (
        CheckConstraint("status IN ('UPLOADING', 'INDEXING', 'ACTIVE', 'FAILED')", name="check_catalog_status"),
        Index("idx_catalog_versions_status_created", "status", "created_at"),
    )


class SystemLog(Base):
    """
    Системные логи
    """
    __tablename__ = "system_logs"
    
    id = Column(BigInteger, primary_key=True)
    level = Column(String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)
    module = Column(String(100), nullable=True)
    function = Column(String(100), nullable=True)
    line_number = Column(Integer, nullable=True)
    extra_data = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Ограничения
    __table_args__ = (
        CheckConstraint("level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')", name="check_log_level"),
        Index("idx_logs_level_created", "level", "created_at"),
        Index("idx_logs_created", "created_at"),
    )


class LLMSetting(Base):
    """
    Настройки LLM провайдеров
    """
    __tablename__ = "llm_settings"
    
    id = Column(BigInteger, primary_key=True)
    provider = Column(String(50), nullable=False)  # openai, yandexgpt
    is_active = Column(Boolean, default=False, nullable=False)
    config = Column(Text, nullable=False)  # JSON с настройками
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Ограничения
    __table_args__ = (
        CheckConstraint("provider IN ('openai', 'yandexgpt')", name="check_llm_provider"),
    )


class ServiceCategory(Base):
    """
    Категории услуг компании
    """
    __tablename__ = "service_categories"
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)  # Техническое имя
    display_name = Column(String(200), nullable=False)  # Отображаемое название
    description = Column(Text, nullable=True)  # Описание категории
    color = Column(String(7), nullable=True)  # Цвет для UI (hex)
    icon = Column(String(50), nullable=True)  # Иконка Bootstrap Icons
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    services = relationship("CompanyService", back_populates="category_rel")
    
    # Индексы
    __table_args__ = (
        Index("idx_categories_active_sort", "is_active", "sort_order"),
    )


class CompanyService(Base):
    """
    Услуги компании
    """
    __tablename__ = "company_services"
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category_id = Column(BigInteger, ForeignKey("service_categories.id"), nullable=True)  # Связь с категорией
    keywords = Column(Text, nullable=True)  # Ключевые слова для поиска
    price_info = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    category_rel = relationship("ServiceCategory", back_populates="services")
    
    # Индексы
    __table_args__ = (
        Index("idx_services_active_sort", "is_active", "sort_order"),
        Index("idx_services_category", "category_id"),
    )


class CatalogVersion(Base):
    """
    Версии каталога товаров для blue-green deployment
    """
    __tablename__ = "catalog_versions"
    
    id = Column(BigInteger, primary_key=True)
    filename = Column(String(255), nullable=False)  # Имя загруженного файла
    original_filename = Column(String(500), nullable=False)  # Оригинальное имя файла
    file_path = Column(String(500), nullable=True)  # Путь к файлу на диске
    file_size = Column(BigInteger, nullable=False)  # Размер файла в байтах
    
    # Статус версии
    status = Column(String(20), nullable=False, default="uploaded")  # uploaded, processing, completed, failed, active
    is_active = Column(Boolean, default=False, nullable=False)  # Активная версия
    
    # Информация о процессе индексации
    products_count = Column(Integer, nullable=True)  # Количество проиндексированных товаров
    progress = Column(Integer, nullable=True, default=0)  # Прогресс в процентах (0-100)
    progress_message = Column(String(500), nullable=True)  # Текущее сообщение о прогрессе
    error_message = Column(Text, nullable=True)  # Сообщение об ошибке
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Время загрузки
    indexed_at = Column(DateTime(timezone=True), nullable=True)  # Время индексации
    started_at = Column(DateTime(timezone=True), nullable=True)  # Время начала индексации
    completed_at = Column(DateTime(timezone=True), nullable=True)  # Время завершения
    
    # Пользователь, загрузивший версию
    uploaded_by = Column(BigInteger, ForeignKey("admin_users.id"), nullable=False)
    
    # Связи
    uploaded_by_user = relationship("AdminUser", foreign_keys=[uploaded_by])
    
    # Ограничения и индексы
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded', 'processing', 'completed', 'failed', 'active')", 
            name="check_catalog_version_status"
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="check_catalog_version_progress"),
        Index("idx_catalog_versions_status", "status"),
        Index("idx_catalog_versions_created", "created_at"),
        Index("idx_catalog_versions_active", "status", "created_at"),
        {'extend_existing': True}  # Позволяет переопределить существующую таблицу
    )
