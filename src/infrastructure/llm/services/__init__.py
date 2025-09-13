"""
LLM сервисы для работы с языковыми моделями.
Экспортирует основные сервисы.
"""
from .llm_service import LLMService, llm_service
from .prompt_manager import PromptManager, prompt_manager

__all__ = [
    "LLMService",
    "llm_service",
    "PromptManager", 
    "prompt_manager",
]
