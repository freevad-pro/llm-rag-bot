"""
Моки для LLM провайдеров в тестах
"""
from typing import Dict, Any, List, Optional, AsyncGenerator
from unittest.mock import AsyncMock

from src.infrastructure.llm.providers.base import LLMProvider
from src.domain.entities.lead import Lead


class MockLLMProvider(LLMProvider):
    """Мок LLM провайдера для тестирования"""
    
    def __init__(self, provider_name: str = "test", **kwargs):
        self.provider_name = provider_name
        self.config = kwargs
        self.call_history: List[Dict[str, Any]] = []
        self._responses = []
        self._current_response_index = 0
    
    def set_responses(self, responses: List[str]):
        """Устанавливает предустановленные ответы"""
        self._responses = responses
        self._current_response_index = 0
    
    def add_response(self, response: str):
        """Добавляет ответ в очередь"""
        self._responses.append(response)
    
    def get_next_response(self) -> str:
        """Получает следующий предустановленный ответ"""
        if self._current_response_index < len(self._responses):
            response = self._responses[self._current_response_index]
            self._current_response_index += 1
            return response
        return "Тестовый ответ от LLM провайдера"
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Генерирует мокированный ответ"""
        # Записываем вызов для проверки в тестах
        call_data = {
            "messages": messages,
            "context": context,
            "provider": self.provider_name
        }
        self.call_history.append(call_data)
        
        # Возвращаем предустановленный или дефолтный ответ
        response = self.get_next_response()
        
        # Имитируем обработку разных типов запросов
        last_message = messages[-1]["content"].lower() if messages else ""
        
        if "поиск" in last_message or "ищу" in last_message or "нужен" in last_message:
            return f"🔍 По вашему запросу найдено несколько товаров:\n\n{response}"
        elif "цена" in last_message or "стоимость" in last_message:
            return f"💰 Информация о ценах:\n\n{response}"
        elif "помощь" in last_message or "как" in last_message:
            return f"📋 Рад помочь!\n\n{response}"
        
        return response
    
    async def generate_response_stream(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Генерирует мокированный потоковый ответ"""
        response = await self.generate_response(messages, context)
        
        # Имитируем потоковую отдачу по словам
        words = response.split()
        for word in words:
            yield word + " "
    
    async def is_healthy(self) -> bool:
        """Проверка здоровья мок провайдера"""
        return True
    
    def get_model_info(self) -> Dict[str, Any]:
        """Информация о модели"""
        return {
            "provider": self.provider_name,
            "model": "test-model",
            "max_tokens": 4000,
            "supports_streaming": True
        }
    
    def clear_history(self):
        """Очищает историю вызовов"""
        self.call_history.clear()
        self._current_response_index = 0


class MockTelegramNotifier:
    """Мок для Telegram уведомлений"""
    
    def __init__(self):
        self.sent_notifications: List[Dict[str, Any]] = []
    
    async def notify_new_lead(self, lead: Lead, user_id: int):
        """Мокированное уведомление о новом лиде"""
        notification = {
            "type": "new_lead",
            "lead_id": lead.id,
            "user_id": user_id,
            "lead_name": lead.name,
            "timestamp": "2025-09-14T12:00:00"
        }
        self.sent_notifications.append(notification)
    
    async def notify_error(self, error_message: str, context: Optional[Dict] = None):
        """Мокированное уведомление об ошибке"""
        notification = {
            "type": "error",
            "message": error_message,
            "context": context,
            "timestamp": "2025-09-14T12:00:00"
        }
        self.sent_notifications.append(notification)
    
    def clear_notifications(self):
        """Очищает список уведомлений"""
        self.sent_notifications.clear()


class MockCRMService:
    """Мок для CRM интеграции (Zoho)"""
    
    def __init__(self):
        self.created_leads: List[Dict[str, Any]] = []
        self.should_fail = False
        self.failure_message = "Test CRM failure"
    
    def set_failure(self, should_fail: bool, message: str = "Test CRM failure"):
        """Настраивает мок на возврат ошибки"""
        self.should_fail = should_fail
        self.failure_message = message
    
    async def create_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Мокированное создание лида в CRM"""
        if self.should_fail:
            raise Exception(self.failure_message)
        
        # Имитируем успешное создание в Zoho
        zoho_lead = {
            "id": f"zoho_{len(self.created_leads) + 1000000}",
            "status": "created",
            "data": lead_data,
            "created_at": "2025-09-14T12:00:00Z"
        }
        
        self.created_leads.append(zoho_lead)
        return zoho_lead
    
    async def update_lead(self, lead_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Мокированное обновление лида в CRM"""
        if self.should_fail:
            raise Exception(self.failure_message)
        
        # Находим лид по ID и обновляем
        for lead in self.created_leads:
            if lead["id"] == lead_id:
                lead["data"].update(update_data)
                lead["updated_at"] = "2025-09-14T12:00:00Z"
                return lead
        
        raise Exception(f"Lead {lead_id} not found")
    
    def clear_leads(self):
        """Очищает список созданных лидов"""
        self.created_leads.clear()


# Утилиты для создания моков в тестах
def create_mock_llm_conversation():
    """Создает мок провайдера с предустановленным диалогом"""
    mock = MockLLMProvider("test")
    mock.set_responses([
        "Здравствуйте! Чем могу помочь?",
        "Конечно, помогу вам найти подходящий насос.",
        "У нас есть несколько вариантов насосов для дачи. Какие характеристики важны?",
        "Отлично! Рекомендую обратиться к нашему менеджеру для подробной консультации."
    ])
    return mock


def create_search_mock_responses():
    """Создает мок ответы для поисковых запросов"""
    return [
        "🔍 Найдено 5 товаров по запросу 'насос':\n\n1. Насос циркуляционный GRUNDFOS UPS 25-40\n2. Насос дренажный ДЖИЛЕКС...",
        "📋 Показываю детали товара:\n\nНасос циркуляционный GRUNDFOS UPS 25-40\nЦена: 15 000 руб.\nХарактеристики: ...",
        "💰 Актуальные цены на насосы:\n\n- Циркуляционные: от 8 000 руб.\n- Дренажные: от 12 000 руб.",
    ]


# Фикстуры для pytest
def create_test_fixtures():
    """Создает набор мок объектов для тестов"""
    return {
        "llm_provider": MockLLMProvider(),
        "telegram_notifier": MockTelegramNotifier(),
        "crm_service": MockCRMService()
    }
