"""
YandexGPT провайдер для LLM.
Реализует интерфейс LLMProvider для работы с Yandex Cloud GPT.
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional

import httpx

from .base import LLMProvider, LLMMessage, LLMResponse, LLMProviderError, LLMTimeoutError, LLMRateLimitError
from src.infrastructure.utils.text_utils import safe_format


class YandexGPTProvider(LLMProvider):
    """
    Провайдер для YandexGPT.
    Использует Yandex Cloud API для генерации ответов.
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Инициализация YandexGPT провайдера.
        
        Args:
            config: Конфигурация с api_key, folder_id и другими параметрами
        """
        super().__init__(config)
        
        self.api_key = config.get("api_key")
        self.folder_id = config.get("folder_id")
        
        if not self.api_key:
            raise ValueError("Yandex API key не предоставлен в конфигурации")
        if not self.folder_id:
            raise ValueError("Yandex folder_id не предоставлен в конфигурации")
        
        self.model = config.get("model", "yandexgpt")
        self.timeout = config.get("timeout", 30)
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1"
        
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _get_provider_name(self) -> str:
        """Возвращает название провайдера."""
        return "yandex"
    
    async def generate_response(
        self, 
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """
        Генерирует ответ через YandexGPT API.
        
        Args:
            messages: Список сообщений
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            
        Returns:
            LLMResponse с ответом
        """
        try:
            # Подготавливаем данные для запроса
            request_data = {
                "modelUri": f"gpt://{self.folder_id}/{self.model}",
                "completionOptions": {
                    "stream": False,
                    "temperature": temperature,
                    "maxTokens": str(max_tokens)
                },
                "messages": [
                    {"role": msg.role, "text": msg.content}
                    for msg in messages
                ]
            }
            
            headers = {
                "Authorization": f"Api-Key {self.api_key}",
                "Content-Type": "application/json"
            }
            
            self._logger.debug(f"Отправка запроса к YandexGPT: {len(messages)} сообщений")
            
            # Отправляем запрос
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/completion",
                    json=request_data,
                    headers=headers
                )
                
                if response.status_code == 429:
                    raise LLMRateLimitError("Rate limit превышен для YandexGPT")
                
                response.raise_for_status()
                result = response.json()
            
            # Извлекаем ответ
            if "result" not in result or "alternatives" not in result["result"]:
                raise LLMProviderError(
                    self.provider_name, 
                    f"Неожиданный формат ответа: {result}"
                )
            
            alternatives = result["result"]["alternatives"]
            if not alternatives:
                raise LLMProviderError(
                    self.provider_name, 
                    "Нет альтернатив в ответе YandexGPT"
                )
            
            content = alternatives[0]["message"]["text"]
            
            # Создаем ответ
            llm_response = LLMResponse(
                content=content,
                provider=self.provider_name,
                model=self.model,
                usage=result["result"].get("usage", {}),
                metadata={
                    "finish_reason": alternatives[0].get("status", "unknown"),
                }
            )
            
            self._logger.debug(f"Получен ответ от YandexGPT: {len(content)} символов")
            return llm_response
            
        except httpx.TimeoutException:
            self._logger.error("Таймаут YandexGPT API")
            raise LLMTimeoutError("Таймаут при обращении к YandexGPT")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise LLMRateLimitError("Rate limit превышен для YandexGPT")
            
            self._logger.error(f"HTTP ошибка YandexGPT: {e}")
            raise LLMProviderError(
                self.provider_name, 
                f"HTTP ошибка: {e.response.status_code}", 
                e
            )
            
        except Exception as e:
            self._logger.error(f"Ошибка YandexGPT API: {e}")
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

PRODUCT - поиск конкретного товара, оборудования, запчастей, вопросы о наличии товаров ("есть ли у вас", "продаете ли", "найдется ли", "имеется ли")
SERVICE - вопрос об услугах компании (техническая поддержка, условия поставки, сервис)
COMPANY_INFO - вопросы о компании (название, местоположение, контакты, история)
GENERAL - общий вопрос, приветствие
CONTACT - желание связаться с менеджером

ВАЖНО: Если в запросе упоминается конкретное название товара, оборудования или запчасти - это всегда PRODUCT, даже если это вопрос о наличии.

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
        Проверяет доступность YandexGPT API.
        
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
