"""
Бизнес-сущность взаимодействия с лидом для domain слоя.
Согласно @vision.md - чистая бизнес-логика без зависимостей.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class InteractionType(Enum):
    """Типы взаимодействий с лидом"""
    NOTE = "note"
    STATUS_CHANGE = "status_change"
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    QUALIFICATION = "qualification"


@dataclass
class LeadInteraction:
    """
    Бизнес-сущность взаимодействия с лидом.
    Отслеживает все действия менеджеров с лидами.
    """
    # Обязательные поля
    lead_id: int
    interaction_type: InteractionType
    content: str
    
    # Метаданные
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None
    
    # Системные поля
    id: Optional[int] = None
    
    def is_valid(self) -> bool:
        """Проверка валидности взаимодействия"""
        return bool(
            self.lead_id and 
            self.interaction_type and 
            self.content and 
            self.content.strip()
        )
    
    def get_display_type(self) -> str:
        """Получение отображаемого типа взаимодействия"""
        type_names = {
            InteractionType.NOTE: "Заметка",
            InteractionType.STATUS_CHANGE: "Изменение статуса",
            InteractionType.CALL: "Звонок",
            InteractionType.EMAIL: "Email",
            InteractionType.MEETING: "Встреча",
            InteractionType.QUALIFICATION: "Квалификация"
        }
        return type_names.get(self.interaction_type, "Неизвестно")
    
    def to_dict(self) -> dict:
        """Преобразование в словарь для JSON сериализации"""
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "interaction_type": self.interaction_type.value,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by
        }
