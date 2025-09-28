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
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Обратные связи
    conversations = relationship("Conversation", back_populates="user")
    leads = relationship("Lead", back_populates="user")


class CompanyService(Base):
    """
    Услуги компании (НЕ товары из каталога)
    Хранится в PostgreSQL для быстрого поиска
    """
    __tablename__ = "company_services"
    
    id = Column(BigInteger, primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(255), nullable=True)
    keywords = Column(Text, nullable=True)  # Через запятую для простоты
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Lead(Base):
    """
    Лиды для синхронизации с Zoho CRM
    """
    __tablename__ = "leads"
    
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # Обязательные поля
    name = Column(String(200), nullable=False)
    
    # Контактные данные (минимум одно)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    telegram = Column(String(255), nullable=True)
    
    # Дополнительные поля
    company = Column(String(300), nullable=True)
    question = Column(Text, nullable=True)
    
    # Статус синхронизации
    status = Column(String(20), default="pending_sync", nullable=False)  # pending_sync, synced, failed
    sync_attempts = Column(Integer, default=0, nullable=False)
    zoho_lead_id = Column(String(100), nullable=True)
    last_sync_attempt = Column(DateTime(timezone=True), nullable=True)
    
    # Метаданные
    auto_created = Column(Boolean, default=False, nullable=False)
    lead_source = Column(String(50), default="Telegram Bot", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    user = relationship("User", back_populates="leads")
    
    # Ограничения
    __table_args__ = (
        CheckConstraint("sync_attempts <= 2", name="check_max_sync_attempts"),
        CheckConstraint(
            "phone IS NOT NULL OR email IS NOT NULL OR telegram IS NOT NULL",
            name="check_contact_required"
        ),
        Index("idx_leads_status_created", "status", "created_at"),
    )


class Conversation(Base):
    """
    Диалоги пользователей
    """
    __tablename__ = "conversations"
    
    id = Column(BigInteger, primary_key=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    platform = Column(String(50), default="telegram", nullable=False)  # telegram, web
    status = Column(String(20), default="active", nullable=False)  # active, ended, timeout
    
    # Метаданные как JSON строка для простоты
    extra_data = Column(Text, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    """
    Сообщения в диалогах
    """
    __tablename__ = "messages"
    
    id = Column(BigInteger, primary_key=True)
    conversation_id = Column(BigInteger, ForeignKey("conversations.id"), nullable=False)
    
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Метаданные как JSON строка
    extra_data = Column(Text, nullable=True)
    
    # Связи
    conversation = relationship("Conversation", back_populates="messages")
    
    # Индексы
    __table_args__ = (
        Index("idx_messages_conversation_created", "conversation_id", "created_at"),
    )


class LLMSetting(Base):
    """
    Настройки LLM провайдеров
    """
    __tablename__ = "llm_settings"
    
    id = Column(BigInteger, primary_key=True)
    provider = Column(String(50), nullable=False)  # openai, yandex, anthropic
    is_active = Column(Boolean, default=False, nullable=False)
    config = Column(Text, nullable=False)  # JSON как строка
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Prompt(Base):
    """
    Системные промпты
    """
    __tablename__ = "prompts"
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
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
    Информация о компании для LLM промптов
    Версионность файлов DOCX/TXT/PDF
    """
    __tablename__ = "company_info"
    
    id = Column(BigInteger, primary_key=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(10), nullable=False)  # docx, txt, pdf
    content = Column(Text, nullable=False)  # Извлеченный текст
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    uploaded_by = Column(BigInteger, ForeignKey("admin_users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    admin_user = relationship("AdminUser")


class SystemLog(Base):
    """
    Системные логи для мониторинга
    """
    __tablename__ = "system_logs"
    
    id = Column(BigInteger, primary_key=True)
    level = Column(String(20), nullable=False, index=True)  # ERROR, WARNING, CRITICAL, BUSINESS
    message = Column(Text, nullable=False)
    extra_data = Column(Text, nullable=True)  # JSON как строка
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Индексы
    __table_args__ = (
        Index("idx_logs_level_created", "level", desc("created_at")),
    )
