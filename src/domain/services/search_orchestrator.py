"""
Оркестратор поиска и маршрутизации запросов.
Согласно @vision.md: маршрутизация между Chroma (товары) и PostgreSQL (услуги).
"""
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .query_classifier import QueryType, classify_user_query
from .conversation_service import conversation_service
from ...infrastructure.database.models import CompanyService, CompanyInfo
from ...infrastructure.search.catalog_service import CatalogSearchService
from ...infrastructure.llm import llm_service


class SearchOrchestrator:
    """
    Оркестратор поиска и генерации ответов.
    Маршрутизирует запросы согласно их типу:
    - PRODUCT → CatalogSearchService (Chroma)
    - SERVICE → KnowledgeBaseService (PostgreSQL)  
    - COMPANY_INFO → Информация о компании
    - GENERAL → Базовый промпт LLM
    - CONTACT → Процесс создания лида
    """
    
    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.catalog_service = CatalogSearchService()
    
    async def process_user_query(
        self,
        user_query: str,
        chat_id: int,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Обрабатывает запрос пользователя и генерирует ответ.
        
        Args:
            user_query: Запрос пользователя
            chat_id: ID чата пользователя
            session: Сессия базы данных
            
        Returns:
            Словарь с ответом и метаданными
        """
        try:
            # 1. Сохраняем сообщение пользователя
            await conversation_service.save_user_message(
                chat_id, user_query, session
            )
            
            # 2. Классифицируем запрос
            query_type = await classify_user_query(user_query, session)
            self._logger.info(f"Запрос классифицирован как {query_type.value}")
            
            # 3. Получаем контекст диалога
            conversation_context = await conversation_service.get_conversation_context(
                chat_id, session, limit=20
            )
            
            # 4. Маршрутизируем запрос по типу
            response_data = await self._route_query(
                query_type, user_query, conversation_context, session
            )
            
            # 5. Сохраняем ответ ассистента с метриками
            llm_response = response_data.get("llm_response")
            if llm_response and hasattr(llm_response, 'usage'):
                # Извлекаем метрики из LLMResponse
                tokens_used = llm_response.usage.get("total_tokens", 0) if llm_response.usage else 0
                processing_time = response_data.get("processing_time_ms", 0)
                
                await conversation_service.save_assistant_message(
                    chat_id=chat_id,
                    content=response_data["response"],
                    session=session,
                    llm_provider=llm_response.provider,
                    tokens_used=tokens_used,
                    processing_time_ms=processing_time,
                    extra_data=f'{{"model": "{llm_response.model}", "usage": {llm_response.usage}}}'
                )
            else:
                # Fallback для случаев без LLM
                await conversation_service.save_assistant_message(
                    chat_id, response_data["response"], session
                )
            
            # 6. Формируем финальный ответ
            return {
                "response": response_data["response"],
                "query_type": query_type.value,
                "metadata": response_data.get("metadata", {}),
                "suggested_actions": response_data.get("suggested_actions", [])
            }
            
        except Exception as e:
            self._logger.error(f"Ошибка обработки запроса: {e}")
            error_response = "Извините, произошла ошибка при обработке вашего запроса. Попробуйте еще раз."
            
            # Сохраняем ошибочный ответ
            await conversation_service.save_assistant_message(
                chat_id, error_response, session
            )
            
            return {
                "response": error_response,
                "query_type": "ERROR",
                "metadata": {"error": str(e)},
                "suggested_actions": ["contact_manager"]
            }
    
    async def _route_query(
        self,
        query_type: QueryType,
        user_query: str,
        conversation_context: List[Dict[str, Any]],
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Маршрутизирует запрос по типу и генерирует ответ.
        
        Args:
            query_type: Тип запроса
            user_query: Запрос пользователя
            conversation_context: Контекст диалога
            session: Сессия базы данных
            
        Returns:
            Словарь с ответом и метаданными
        """
        if query_type == QueryType.PRODUCT:
            return await self._handle_product_query(
                user_query, conversation_context, session
            )
        
        elif query_type == QueryType.SERVICE:
            return await self._handle_service_query(
                user_query, conversation_context, session
            )
        
        elif query_type == QueryType.COMPANY_INFO:
            return await self._handle_company_info_query(
                user_query, conversation_context, session
            )
        
        elif query_type == QueryType.CONTACT:
            return await self._handle_contact_request(
                user_query, conversation_context, session
            )
        
        else:  # GENERAL
            return await self._handle_general_query(
                user_query, conversation_context, session
            )
    
    async def _handle_product_query(
        self,
        user_query: str,
        conversation_context: List[Dict[str, Any]],
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Обрабатывает запрос поиска товаров."""
        try:
            # Поиск в каталоге через Chroma
            search_results = await self.catalog_service.search_products(
                query=user_query,
                k=10
            )
            
            if search_results:
                # Генерируем ответ о товарах
                response = await llm_service.generate_product_response(
                    user_query, search_results, session
                )
                
                return {
                    "response": response,
                    "metadata": {
                        "search_results_count": len(search_results),
                        "source": "chroma_catalog"
                    },
                    "suggested_actions": ["contact_manager", "search_more"]
                }
            else:
                # Если товары не найдены
                import time
                start_time = time.time()
                
                llm_result = await llm_service.generate_contextual_response(
                    user_query,
                    conversation_context,
                    context_data={
                        "search_results": [],
                        "message": "Товары по вашему запросу не найдены"
                    },
                    session=session
                )
                
                processing_time = int((time.time() - start_time) * 1000) if 'start_time' in locals() else 0
                
                return {
                    "response": llm_result["text"],
                    "llm_response": llm_result["llm_response"],
                    "processing_time_ms": processing_time,
                    "metadata": {
                        "search_results_count": 0,
                        "source": "llm_fallback"
                    },
                    "suggested_actions": ["contact_manager", "refine_search"]
                }
                
        except Exception as e:
            self._logger.error(f"Ошибка обработки запроса товаров: {e}")
            return {
                "response": "Извините, произошла ошибка при поиске товаров. Попробуйте уточнить запрос или свяжитесь с менеджером.",
                "metadata": {"error": str(e)},
                "suggested_actions": ["contact_manager"]
            }
    
    async def _handle_service_query(
        self,
        user_query: str,
        conversation_context: List[Dict[str, Any]],
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Обрабатывает запрос об услугах компании."""
        try:
            # Поиск услуг в PostgreSQL
            services_query = select(CompanyService).where(
                CompanyService.active == True
            )
            
            services_result = await session.execute(services_query)
            services = services_result.scalars().all()
            
            # Конвертируем в словари
            services_data = [
                {
                    "title": service.title,
                    "description": service.description,
                    "category": service.category,
                    "keywords": service.keywords
                }
                for service in services
            ]
            
            # Генерируем ответ об услугах
            response = await llm_service.generate_service_response(
                user_query, services_data, session
            )
            
            return {
                "response": response,
                "metadata": {
                    "services_count": len(services_data),
                    "source": "postgresql_services"
                },
                "suggested_actions": ["contact_manager", "learn_more"]
            }
            
        except Exception as e:
            self._logger.error(f"Ошибка обработки запроса услуг: {e}")
            return {
                "response": "Извините, произошла ошибка при получении информации об услугах. Свяжитесь с менеджером для получения подробной консультации.",
                "metadata": {"error": str(e)},
                "suggested_actions": ["contact_manager"]
            }
    
    async def _handle_company_info_query(
        self,
        user_query: str,
        conversation_context: List[Dict[str, Any]],
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Обрабатывает запрос о компании."""
        try:
            # Загружаем активную информацию о компании из БД
            company_info_query = select(CompanyInfo).where(
                CompanyInfo.is_active == True
            ).order_by(CompanyInfo.created_at.desc())
            
            result = await session.execute(company_info_query)
            company_info_record = result.scalar_one_or_none()
            
            if company_info_record:
                company_info = company_info_record.content
                self._logger.info(f"Загружена информация о компании из файла: {company_info_record.original_filename}")
            else:
                # Fallback на базовую информацию если файл не загружен
                company_info = """
                Наша компания специализируется на поставке оборудования и запчастей.
                Мы работаем с широким каталогом товаров и предоставляем профессиональные консультации.
                Для получения подробной информации свяжитесь с нашими менеджерами.
                """
                self._logger.warning("Файл с информацией о компании не найден, используется базовая информация")
            
            # Генерируем ответ о компании
            response = await llm_service.generate_company_info_response(
                user_query, company_info, session
            )
            
            return {
                "response": response,
                "metadata": {
                    "source": "company_info",
                    "has_custom_info": company_info_record is not None,
                    "info_file": company_info_record.original_filename if company_info_record else None
                },
                "suggested_actions": ["contact_manager", "learn_services"]
            }
            
        except Exception as e:
            self._logger.error(f"Ошибка обработки запроса о компании: {e}")
            return {
                "response": "Извините, произошла ошибка при получении информации о компании. Свяжитесь с нами напрямую для получения подробностей.",
                "metadata": {"error": str(e)},
                "suggested_actions": ["contact_manager"]
            }
    
    async def _handle_contact_request(
        self,
        user_query: str,
        conversation_context: List[Dict[str, Any]],
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Обрабатывает запрос на связь с менеджером."""
        try:
            import time
            start_time = time.time()
            
            llm_result = await llm_service.generate_contextual_response(
                user_query,
                conversation_context,
                context_data={
                    "action": "contact_request",
                    "message": "Пользователь хочет связаться с менеджером"
                },
                session=session
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return {
                "response": llm_result["text"],
                "llm_response": llm_result["llm_response"],
                "processing_time_ms": processing_time,
                "metadata": {
                    "source": "contact_handler",
                    "action_required": "create_lead"
                },
                "suggested_actions": ["provide_contacts", "create_lead"]
            }
            
        except Exception as e:
            self._logger.error(f"Ошибка обработки запроса контакта: {e}")
            return {
                "response": "Конечно! Для связи с менеджером, пожалуйста, предоставьте ваши контактные данные.",
                "metadata": {"error": str(e)},
                "suggested_actions": ["provide_contacts"]
            }
    
    async def _handle_general_query(
        self,
        user_query: str,
        conversation_context: List[Dict[str, Any]],
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Обрабатывает общие запросы."""
        try:
            import time
            start_time = time.time()
            
            llm_result = await llm_service.generate_contextual_response(
                user_query,
                conversation_context,
                session=session
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return {
                "response": llm_result["text"],
                "llm_response": llm_result["llm_response"],
                "processing_time_ms": processing_time,
                "metadata": {
                    "source": "general_llm"
                },
                "suggested_actions": ["search_products", "learn_services", "contact_manager"]
            }
            
        except Exception as e:
            self._logger.error(f"Ошибка обработки общего запроса: {e}")
            return {
                "response": "Здравствуйте! Я могу помочь вам найти товары в нашем каталоге или ответить на вопросы об услугах компании. Чем могу помочь?",
                "metadata": {"error": str(e)},
                "suggested_actions": ["search_products", "contact_manager"]
            }


# Глобальный экземпляр оркестратора
search_orchestrator = SearchOrchestrator()
