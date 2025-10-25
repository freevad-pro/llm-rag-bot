"""
OpenAI провайдер для LLM.
Реализует интерфейс LLMProvider для работы с OpenAI GPT моделями.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional

import openai
from openai import AsyncOpenAI

from .base import LLMProvider, LLMMessage, LLMResponse, LLMProviderError, LLMTimeoutError, LLMRateLimitError
from src.infrastructure.utils.text_utils import safe_format


class OpenAIProvider(LLMProvider):
    """
    Провайдер для OpenAI GPT моделей.
    Поддерживает GPT-3.5-turbo и GPT-4.
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Инициализация OpenAI провайдера.
        
        Args:
            config: Конфигурация с api_key, model, и другими параметрами
        """
        super().__init__(config)
        
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("OpenAI API key не предоставлен в конфигурации")
        
        from src.config.settings import settings
        self.model = config.get("model", settings.openai_default_model)
        self.timeout = config.get("timeout", 30)
        
        # Инициализируем клиент
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            timeout=self.timeout
        )
        
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _get_provider_name(self) -> str:
        """Возвращает название провайдера."""
        return "openai"
    
    async def generate_response(
        self, 
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """
        Генерирует ответ через OpenAI API.
        
        Args:
            messages: Список сообщений
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            
        Returns:
            LLMResponse с ответом
        """
        try:
            # Конвертируем сообщения в формат OpenAI
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            self._logger.debug(f"Отправка запроса к OpenAI: {len(openai_messages)} сообщений")
            
            # Отправляем запрос
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Извлекаем ответ
            content = response.choices[0].message.content or ""
            
            # Создаем ответ
            llm_response = LLMResponse(
                content=content,
                provider=self.provider_name,
                model=self.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                }
            )
            
            self._logger.debug(f"Получен ответ от OpenAI: {len(content)} символов")
            return llm_response
            
        except openai.RateLimitError as e:
            self._logger.warning(f"Rate limit превышен: {e}")
            raise LLMRateLimitError(f"Rate limit превышен: {e}")
            
        except openai.APITimeoutError as e:
            self._logger.error(f"Таймаут OpenAI API: {e}")
            raise LLMTimeoutError(f"Таймаут при обращении к OpenAI: {e}")
            
        except Exception as e:
            self._logger.error(f"Ошибка OpenAI API: {e}")
            raise LLMProviderError(self.provider_name, f"Ошибка генерации ответа: {e}", e)
    
    async def classify_query(self, query: str) -> str:
        """
        Классифицирует запрос пользователя.
        
        Args:
            query: Запрос пользователя
            
        Returns:
            Тип запроса: PRODUCT, SERVICE, GENERAL, CONTACT, COMPANY_INFO
        """
        classification_prompt = """Классифицируй следующий запрос пользователя на одну из категорий:

PRODUCT - поиск конкретного товара, оборудования, запчастей
SERVICE - вопрос об услугах компании (техническая поддержка, условия поставки, сервис)
COMPANY_INFO - вопросы о компании (название, местоположение, контакты, история)
GENERAL - общий вопрос, приветствие
CONTACT - желание связаться с менеджером

Отвечай только одним словом из списка выше.

Запрос: {query}

Классификация:"""
        
        try:
            messages = [
                LLMMessage(role="user", content=safe_format(classification_prompt, query=query))
            ]
            
            response = await self.generate_response(
                messages=messages,
                temperature=0.1,  # Низкая температура для точной классификации
                max_tokens=50
            )
            
            # Извлекаем и очищаем результат
            classification = response.content.strip().upper()
            
            # Проверяем валидность
            valid_types = {"PRODUCT", "SERVICE", "COMPANY_INFO", "GENERAL", "CONTACT"}
            if classification in valid_types:
                return classification
            else:
                self._logger.warning(f"Неизвестная классификация: {classification}")
                return "GENERAL"  # По умолчанию
                
        except Exception as e:
            self._logger.error(f"Ошибка классификации запроса: {e}")
            return "GENERAL"  # Fallback
    
    async def is_healthy(self) -> bool:
        """
        Проверяет доступность OpenAI API.
        
        Returns:
            True если API доступен
        """
        try:
            # Простой тестовый запрос
            test_messages = [
                LLMMessage(role="user", content="Привет")
            ]
            
            response = await asyncio.wait_for(
                self.generate_response(test_messages, max_tokens=10),
                timeout=10  # Короткий таймаут для health check
            )
            
            return len(response.content) > 0
            
        except Exception as e:
            self._logger.error(f"Health check неудачен: {e}")
            return False
