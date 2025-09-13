"""
Бизнес-сущность лида для domain слоя.
Согласно @vision.md - чистая бизнес-логика без зависимостей.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class LeadStatus(Enum):
    """Статусы синхронизации лида с CRM"""
    PENDING_SYNC = "pending_sync"
    SYNCED = "synced"
    FAILED = "failed"


class LeadSource(Enum):
    """Источники лидов"""
    TELEGRAM_BOT = "Telegram Bot"
    WEBSITE_WIDGET = "SalesIQ Chat"


@dataclass
class Lead:
    """
    Бизнес-сущность лида.
    Минимальные требования: имя + один контакт (email/телефон/telegram).
    """
    # Обязательные поля
    name: str
    
    # Контактные данные (минимум один)
    phone: Optional[str] = None
    email: Optional[str] = None
    telegram: Optional[str] = None
    
    # Дополнительные поля
    company: Optional[str] = None
    question: Optional[str] = None
    
    # Метаданные
    status: LeadStatus = LeadStatus.PENDING_SYNC
    sync_attempts: int = 0
    zoho_lead_id: Optional[str] = None
    last_sync_attempt: Optional[datetime] = None
    auto_created: bool = False
    lead_source: LeadSource = LeadSource.TELEGRAM_BOT
    created_at: Optional[datetime] = None
    
    # Системные поля
    id: Optional[int] = None
    user_id: Optional[int] = None
    
    def has_required_contact(self) -> bool:
        """Проверка наличия минимум одного контакта"""
        return bool(self.phone or self.email or self.telegram)
    
    def is_valid(self) -> bool:
        """Проверка валидности лида"""
        return bool(
            self.name and 
            self.name.strip() and 
            self.has_required_contact()
        )
    
    def can_retry_sync(self) -> bool:
        """Проверка возможности повторной синхронизации"""
        return self.sync_attempts < 2 and self.status == LeadStatus.FAILED
    
    def get_display_name(self) -> str:
        """Получение отображаемого имени"""
        return self.name.strip()
    
    def get_primary_contact(self) -> Optional[str]:
        """Получение основного контакта для отображения"""
        if self.phone:
            return f"📞 {self.phone}"
        elif self.email:
            return f"📧 {self.email}"
        elif self.telegram:
            return f"📱 {self.telegram}"
        return None
    
    def to_dict(self) -> dict:
        """Преобразование в словарь для JSON сериализации"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "telegram": self.telegram,
            "company": self.company,
            "question": self.question,
            "status": self.status.value,
            "sync_attempts": self.sync_attempts,
            "zoho_lead_id": self.zoho_lead_id,
            "last_sync_attempt": self.last_sync_attempt.isoformat() if self.last_sync_attempt else None,
            "auto_created": self.auto_created,
            "lead_source": self.lead_source.value,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
