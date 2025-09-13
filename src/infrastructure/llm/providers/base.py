"""
Базовый протокол для LLM провайдеров.
Согласно @vision.md - настраиваемый (OpenAI/YandexGPT через фабрику)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """Сообщение для LLM"""
    role: str  # user, assistant, system
    content: str


@dataclass 
class LLMResponse:
    """Ответ от LLM"""
    content: str
    provider: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """
    Абстрактный провайдер LLM.
    Реализует единый интерфейс для всех LLM сервисов.
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Инициализация провайдера.
        
        Args:
            config: Конфигурация провайдера из БД
        """
        self.config = config
        self.provider_name = self._get_provider_name()
    
    @abstractmethod
    def _get_provider_name(self) -> str:
        """Возвращает название провайдера."""
        pass
    
    @abstractmethod
    async def generate_response(
        self, 
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """
        Генерирует ответ на основе сообщений.
        
        Args:
            messages: Список сообщений для обработки
            temperature: Температура генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов
            
        Returns:
            LLMResponse с сгенерированным ответом
        """
        pass
    
    @abstractmethod
    async def classify_query(self, query: str) -> str:
        """
        Классифицирует запрос пользователя.
        
        Args:
            query: Запрос пользователя
            
        Returns:
            Тип запроса: PRODUCT, SERVICE, GENERAL, CONTACT, COMPANY_INFO
        """
        pass
    
    @abstractmethod
    async def is_healthy(self) -> bool:
        """
        Проверяет доступность провайдера.
        
        Returns:
            True если провайдер доступен
        """
        pass


class LLMError(Exception):
    """Базовое исключение для LLM операций"""
    pass


class LLMProviderError(LLMError):
    """Ошибка провайдера LLM"""
    
    def __init__(self, provider: str, message: str, original_error: Optional[Exception] = None):
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"[{provider}] {message}")


class LLMTimeoutError(LLMError):
    """Таймаут при обращении к LLM"""
    pass


class LLMRateLimitError(LLMError):
    """Превышен лимит запросов к LLM"""
    pass
