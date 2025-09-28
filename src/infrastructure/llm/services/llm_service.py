"""
Основной LLM сервис для генерации ответов.
Координирует работу провайдеров и промптов согласно @vision.md.
"""
import logging
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..factory import llm_factory
from ..providers import LLMMessage, LLMResponse, LLMError
from .prompt_manager import prompt_manager


class LLMService:
    """
    Основной сервис для работы с LLM.
    Предоставляет высокоуровневые методы для генерации ответов.
    """
    
    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def generate_contextual_response(
        self,
        user_query: str,
        conversation_history: List[Dict[str, str]],
        context_data: Optional[Dict[str, Any]] = None,
        session: AsyncSession = None
    ) -> str:
        """
        Генерирует контекстуальный ответ на запрос пользователя.
        
        Args:
            user_query: Запрос пользователя
            conversation_history: История диалога (последние 20 сообщений)
            context_data: Дополнительные данные (результаты поиска, услуги и т.д.)
            session: Сессия базы данных
            
        Returns:
            Сгенерированный ответ
        """
        try:
            # Получаем провайдера
            provider = await llm_factory.get_active_provider(session)
            
            # Получаем системный промпт
            system_prompt = await prompt_manager.get_prompt("system_prompt", session)
            
            # Формируем сообщения для LLM
            messages = [
                LLMMessage(role="system", content=system_prompt)
            ]
            
            # Добавляем историю диалога (максимум 20 сообщений)
            history_messages = conversation_history[-20:] if conversation_history else []
            for msg in history_messages:
                messages.append(LLMMessage(
                    role=msg.get("role", "user"),
                    content=msg.get("content", "")
                ))
            
            # Добавляем контекстные данные если есть
            if context_data:
                context_prompt = self._format_context_prompt(context_data)
                if context_prompt:
                    messages.append(LLMMessage(role="system", content=context_prompt))
            
            # Добавляем текущий запрос
            messages.append(LLMMessage(role="user", content=user_query))
            
            # Генерируем ответ
            response = await provider.generate_response(
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            self._logger.debug(f"Сгенерирован ответ длиной {len(response.content)} символов")
            
            # Возвращаем структуру с текстом и полным LLM ответом для метрик
            return {
                "text": response.content,
                "llm_response": response
            }
            
        except Exception as e:
            self._logger.error(f"Ошибка генерации ответа: {e}")
            return {
                "text": "Извините, произошла ошибка при генерации ответа. Попробуйте еще раз.",
                "llm_response": None
            }
    
    async def classify_user_query(
        self, 
        user_query: str, 
        session: AsyncSession
    ) -> str:
        """
        Классифицирует запрос пользователя.
        
        Args:
            user_query: Запрос пользователя
            session: Сессия базы данных
            
        Returns:
            Тип запроса: PRODUCT, SERVICE, GENERAL, CONTACT, COMPANY_INFO
        """
        try:
            provider = await llm_factory.get_active_provider(session)
            classification = await provider.classify_query(user_query)
            
            self._logger.debug(f"Запрос классифицирован как: {classification}")
            return classification
            
        except Exception as e:
            self._logger.error(f"Ошибка классификации запроса: {e}")
            return "GENERAL"  # Fallback
    
    async def generate_product_response(
        self,
        user_query: str,
        search_results: List[Dict[str, Any]],
        session: AsyncSession
    ) -> str:
        """
        Генерирует ответ на основе результатов поиска товаров.
        
        Args:
            user_query: Запрос пользователя
            search_results: Результаты поиска из Chroma
            session: Сессия базы данных
            
        Returns:
            Сгенерированный ответ о товарах
        """
        try:
            provider = await llm_factory.get_active_provider(session)
            product_prompt = await prompt_manager.get_prompt("product_search_prompt", session)
            
            # Форматируем результаты поиска
            formatted_results = self._format_search_results(search_results)
            
            # Подставляем данные в промпт
            formatted_prompt = product_prompt.format(
                search_results=formatted_results,
                user_query=user_query
            )
            
            messages = [
                LLMMessage(role="user", content=formatted_prompt)
            ]
            
            response = await provider.generate_response(
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.content
            
        except Exception as e:
            self._logger.error(f"Ошибка генерации ответа о товарах: {e}")
            return "Извините, произошла ошибка при обработке результатов поиска."
    
    async def generate_service_response(
        self,
        user_query: str,
        services_info: List[Dict[str, Any]],
        session: AsyncSession
    ) -> str:
        """
        Генерирует ответ об услугах компании.
        
        Args:
            user_query: Запрос пользователя
            services_info: Информация об услугах из PostgreSQL
            session: Сессия базы данных
            
        Returns:
            Сгенерированный ответ об услугах
        """
        try:
            provider = await llm_factory.get_active_provider(session)
            service_prompt = await prompt_manager.get_prompt("service_answer_prompt", session)
            
            # Форматируем информацию об услугах
            formatted_services = self._format_services_info(services_info)
            
            # Подставляем данные в промпт
            formatted_prompt = service_prompt.format(
                services_info=formatted_services,
                user_query=user_query
            )
            
            messages = [
                LLMMessage(role="user", content=formatted_prompt)
            ]
            
            response = await provider.generate_response(
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.content
            
        except Exception as e:
            self._logger.error(f"Ошибка генерации ответа об услугах: {e}")
            return "Извините, произошла ошибка при получении информации об услугах."
    
    async def generate_company_info_response(
        self,
        user_query: str,
        company_info: str,
        session: AsyncSession
    ) -> str:
        """
        Генерирует ответ о компании.
        
        Args:
            user_query: Запрос пользователя
            company_info: Информация о компании
            session: Сессия базы данных
            
        Returns:
            Сгенерированный ответ о компании
        """
        try:
            provider = await llm_factory.get_active_provider(session)
            company_prompt = await prompt_manager.get_prompt("company_info_prompt", session)
            
            # Подставляем данные в промпт
            formatted_prompt = company_prompt.format(
                company_info=company_info,
                user_query=user_query
            )
            
            messages = [
                LLMMessage(role="user", content=formatted_prompt)
            ]
            
            response = await provider.generate_response(
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.content
            
        except Exception as e:
            self._logger.error(f"Ошибка генерации ответа о компании: {e}")
            return "Извините, произошла ошибка при получении информации о компании."
    
    async def should_create_lead(
        self,
        conversation_history: List[Dict[str, str]],
        session: AsyncSession
    ) -> bool:
        """
        Определяет, нужно ли создать лид на основе диалога.
        
        Args:
            conversation_history: История диалога
            session: Сессия базы данных
            
        Returns:
            True если нужно создать лид
        """
        try:
            provider = await llm_factory.get_active_provider(session)
            lead_prompt = await prompt_manager.get_prompt("lead_qualification_prompt", session)
            
            # Форматируем историю диалога
            formatted_history = self._format_conversation_history(conversation_history)
            
            # Подставляем данные в промпт
            formatted_prompt = lead_prompt.format(
                conversation_history=formatted_history
            )
            
            messages = [
                LLMMessage(role="user", content=formatted_prompt)
            ]
            
            response = await provider.generate_response(
                messages=messages,
                temperature=0.1,  # Низкая температура для точности
                max_tokens=50
            )
            
            decision = response.content.strip().upper()
            return decision == "CREATE_LEAD"
            
        except Exception as e:
            self._logger.error(f"Ошибка определения создания лида: {e}")
            return False  # Безопасный fallback
    
    def _format_search_results(self, search_results: List[Dict[str, Any]]) -> str:
        """Форматирует результаты поиска для промпта."""
        if not search_results:
            return "Товары не найдены."
        
        formatted = []
        for i, result in enumerate(search_results[:5], 1):  # Максимум 5 товаров
            item = f"{i}. {result.get('name', 'Без названия')}"
            if result.get('article'):
                item += f" (арт. {result['article']})"
            if result.get('description'):
                item += f"\n   Описание: {result['description']}"
            if result.get('category'):
                item += f"\n   Категория: {result['category']}"
            formatted.append(item)
        
        return "\n\n".join(formatted)
    
    def _format_services_info(self, services_info: List[Dict[str, Any]]) -> str:
        """Форматирует информацию об услугах для промпта."""
        if not services_info:
            return "Информация об услугах не найдена."
        
        formatted = []
        for service in services_info:
            item = f"• {service.get('title', 'Без названия')}"
            if service.get('description'):
                item += f": {service['description']}"
            formatted.append(item)
        
        return "\n".join(formatted)
    
    def _format_conversation_history(self, history: List[Dict[str, str]]) -> str:
        """Форматирует историю диалога для промпта."""
        if not history:
            return "История диалога пуста."
        
        formatted = []
        for msg in history[-10:]:  # Последние 10 сообщений
            role = "Пользователь" if msg.get("role") == "user" else "Консультант"
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def _format_context_prompt(self, context_data: Dict[str, Any]) -> Optional[str]:
        """Форматирует контекстные данные для промпта."""
        if not context_data:
            return None
        
        context_parts = []
        
        if "search_results" in context_data:
            results = self._format_search_results(context_data["search_results"])
            context_parts.append(f"Результаты поиска:\n{results}")
        
        if "services_info" in context_data:
            services = self._format_services_info(context_data["services_info"])
            context_parts.append(f"Информация об услугах:\n{services}")
        
        if "company_info" in context_data:
            context_parts.append(f"Информация о компании:\n{context_data['company_info']}")
        
        return "\n\n".join(context_parts) if context_parts else None


# Глобальный экземпляр LLM сервиса
llm_service = LLMService()
