"""
Domain entities для промптов (обновленная версия)
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class PromptType(Enum):
    """Типы промптов в системе"""
    SYSTEM = "system_prompt"
    PRODUCT_SEARCH = "product_search_prompt"
    SERVICE_ANSWER = "service_answer_prompt"
    GENERAL_CONVERSATION = "general_conversation_prompt"
    LEAD_QUALIFICATION = "lead_qualification_prompt"


@dataclass
class Prompt:
    """Сущность промпта с редактируемыми названием и описанием"""
    id: Optional[int]
    name: str
    content: str
    display_name: Optional[str] = None  # Редактируемое название
    description: Optional[str] = None   # Редактируемое описание
    version: int = 1
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def effective_display_name(self) -> str:
        """Возвращает display_name из БД или fallback к жестко заданному"""
        if self.display_name:
            return self.display_name
            
        # Fallback к старым жестко заданным значениям
        fallback_names = {
            "system_prompt": "Основной системный промпт",
            "product_search_prompt": "Поиск товаров",
            "service_answer_prompt": "Ответы об услугах",
            "general_conversation_prompt": "Общие вопросы",
            "lead_qualification_prompt": "Квалификация лидов"
        }
        return fallback_names.get(self.name, self.name)
    
    @property
    def effective_description(self) -> str:
        """Возвращает description из БД или fallback к жестко заданному"""
        if self.description:
            return self.description
            
        # Fallback к старым жестко заданным значениям
        fallback_descriptions = {
            "system_prompt": "Основные инструкции для AI-агента, определяющие его поведение и роль",
            "product_search_prompt": "Промпт для поиска и рекомендации товаров из каталога",
            "service_answer_prompt": "Промпт для ответов о услугах компании",
            "general_conversation_prompt": "Промпт для общения и поддержания диалога",
            "lead_qualification_prompt": "Промпт для определения и квалификации потенциальных клиентов"
        }
        return fallback_descriptions.get(self.name, "Системный промпт")
    
    @property
    def word_count(self) -> int:
        """Количество слов в промпте"""
        return len(self.content.split())
    
    @property
    def char_count(self) -> int:
        """Количество символов в промпте"""
        return len(self.content)
    
    @property
    def is_system_prompt(self) -> bool:
        """Проверяет, является ли промпт системным"""
        system_prompts = {
            "system_prompt", "product_search_prompt", "service_answer_prompt",
            "general_conversation_prompt", "lead_qualification_prompt"
        }
        return self.name in system_prompts


@dataclass
class PromptHistory:
    """История изменений промпта"""
    id: Optional[int]
    prompt_id: int
    old_content: str
    new_content: str
    changed_by: int  # ID админ-пользователя
    change_reason: Optional[str]
    created_at: Optional[datetime] = None







