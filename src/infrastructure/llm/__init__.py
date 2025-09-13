"""
LLM модуль для работы с языковыми моделями.
Содержит провайдеров, фабрику и сервисы согласно @vision.md.
"""
from .providers import (
    LLMProvider, LLMMessage, LLMResponse, 
    LLMError, LLMProviderError, LLMTimeoutError, LLMRateLimitError,
    OpenAIProvider, YandexGPTProvider
)
from .factory import LLMProviderFactory, llm_factory
from .services import LLMService, llm_service, PromptManager, prompt_manager

__all__ = [
    # Базовые типы
    "LLMProvider",
    "LLMMessage", 
    "LLMResponse",
    "LLMError",
    "LLMProviderError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    
    # Провайдеры
    "OpenAIProvider",
    "YandexGPTProvider",
    
    # Фабрика
    "LLMProviderFactory",
    "llm_factory",
    
    # Сервисы
    "LLMService",
    "llm_service",
    "PromptManager",
    "prompt_manager",
]
