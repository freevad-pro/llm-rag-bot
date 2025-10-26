"""
Оркестратор поиска и маршрутизации запросов.
Согласно @vision.md: маршрутизация между Chroma (товары) и PostgreSQL (услуги).
"""
import json
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

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
                    extra_data=json.dumps({
                        "model": llm_response.model,
                        "usage": llm_response.usage
                    })
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
            # Извлекаем ключевые слова из запроса с помощью LLM для максимальной точности
            search_query = await self._extract_search_query_with_llm(user_query, session)
            self._logger.debug(f"Оригинальный запрос: '{user_query}' -> Поисковый запрос: '{search_query}'")
            
            # Поиск в каталоге через Chroma
            search_results = await self.catalog_service.search_products(
                query=search_query,
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
            # Поиск услуг в PostgreSQL с загрузкой категорий
            services_query = select(CompanyService).options(
                joinedload(CompanyService.category_rel)
            ).where(
                CompanyService.is_active == True
            )
            
            services_result = await session.execute(services_query)
            services = services_result.scalars().all()
            
            # Если услуги найдены - используем их
            if services:
                # Конвертируем в словари
                services_data = [
                    {
                        "title": service.name,
                        "description": service.description,
                        "category": service.category_rel.display_name if service.category_rel else "Без категории",
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
            
            # Если услуги не найдены - используем информацию о компании как fallback
            self._logger.info("Услуги не найдены в БД, используем информацию о компании как fallback")
            
            # Загружаем активную информацию о компании
            company_info_query = select(CompanyInfo).where(
                CompanyInfo.is_active == True
            ).order_by(CompanyInfo.created_at.desc())
            
            result = await session.execute(company_info_query)
            company_info_record = result.scalar_one_or_none()
            
            if company_info_record:
                company_info = company_info_record.content
                self._logger.info(f"Используем информацию о компании из файла: {company_info_record.original_filename}")
                
                # Генерируем ответ на основе информации о компании
                response = await llm_service.generate_company_info_response(
                    user_query, company_info, session
                )
                
                return {
                    "response": response,
                    "metadata": {
                        "services_count": 0,
                        "source": "company_info_fallback",
                        "has_custom_info": True,
                        "info_file": company_info_record.original_filename
                    },
                    "suggested_actions": ["contact_manager", "learn_more"]
                }
            else:
                # Если и информация о компании отсутствует - базовый ответ
                self._logger.warning("Информация о компании не найдена, используем базовый ответ")
                
                fallback_response = (
                    "К сожалению, подробная информация об услугах компании в данный момент недоступна. "
                    "Наша компания специализируется на поставке оборудования и запчастей, "
                    "предоставляет профессиональные консультации и техническую поддержку. "
                    "Для получения подробной информации о наших услугах и возможностях "
                    "рекомендую связаться с нашими менеджерами."
                )
                
                return {
                    "response": fallback_response,
                    "metadata": {
                        "services_count": 0,
                        "source": "basic_fallback"
                    },
                    "suggested_actions": ["contact_manager"]
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
    
    def _extract_product_keywords(self, user_query: str) -> str:
        """
        Извлекает ключевые слова для поиска товаров из пользовательского запроса.
        Использует LLM для умного извлечения поисковых терминов.
        
        Args:
            user_query: Оригинальный запрос пользователя
            
        Returns:
            Очищенный поисковый запрос с ключевыми словами
        """
        try:
            # Простая очистка для базовых случаев
            query_lower = user_query.lower().strip()
            
            # Удаляем распространенные фразы о наличии
            stop_phrases = [
                "есть ли у вас", "do you have", "продаете ли", "do you sell",
                "найдется ли", "can be found", "имеется ли", "is available",
                "у вас есть", "you have", "в наличии", "in stock",
                "есть в наличии", "available in stock", "можно ли купить", 
                "can i buy", "можно ли заказать", "can i order",
                "есть ли возможность", "is it possible", "реализуете ли", "do you supply",
                "есть ли", "is there", "имеется", "available", "доступно", "accessible",
                "можно найти", "can find", "можно получить", "can get",
                "продается", "sold", "предлагается", "offered", "предлагаете", "do you offer"
            ]
            
            cleaned_query = query_lower
            for phrase in stop_phrases:
                cleaned_query = cleaned_query.replace(phrase, "").strip()
            
            # Удаляем вопросительные слова в начале
            question_words = ["ли", "как", "где", "когда", "что", "кто", "почему", "зачем"]
            words = cleaned_query.split()
            if words and words[0] in question_words:
                words = words[1:]
            
            # Удаляем знаки препинания
            cleaned_query = " ".join(words).strip("?.,!;:")
            
            # Если запрос стал слишком коротким, возвращаем оригинал
            if len(cleaned_query) < 3:
                return user_query.strip()
            
            return cleaned_query
            
        except Exception as e:
            self._logger.error(f"Ошибка извлечения ключевых слов: {e}")
            return user_query.strip()
    
    async def _extract_search_query_with_llm(
        self, 
        user_query: str, 
        session: AsyncSession
    ) -> str:
        """
        Извлекает поисковый запрос с помощью LLM для максимальной точности.
        
        Args:
            user_query: Оригинальный запрос пользователя
            session: Сессия базы данных
            
        Returns:
            Очищенный поисковый запрос
        """
        try:
            # Получаем управляемый промпт для извлечения поискового запроса
            from .prompt_management import prompt_management_service
            extraction_prompt_obj = await prompt_management_service.get_prompt_by_name(session, "search_query_extraction_prompt")
            
            if extraction_prompt_obj:
                extraction_prompt = extraction_prompt_obj.content.format(user_query=user_query)
            else:
                # Fallback на базовый промпт если управляемый не найден
                extraction_prompt = f"""
Ты помощник для извлечения ключевых слов поиска товаров из пользовательских запросов.

Пользователь спрашивает: "{user_query}"

Твоя задача: извлечь из этого запроса только ключевые слова для поиска товаров.
Удали все служебные слова, фразы о наличии, вопросительные конструкции.

Правила:
1. Оставь только названия товаров, артикулы, характеристики
2. Сохрани важные технические термины (размеры, модели, типы)
3. Удали фразы типа "есть ли", "продаете ли", "можно ли купить"
4. Удали вопросительные слова в начале
5. Сохрани порядок слов если он важен

Примеры:
- "есть ли у вас сверло без керна?" → "сверло без керна"
- "продаете ли болты м8?" → "болты м8" 
- "нужен подшипник 6205" → "подшипник 6205"
- "можно ли заказать фильтр масляный?" → "фильтр масляный"
- "есть ли в наличии двигатель 1.5 квт?" → "двигатель 1.5 квт"

Верни только ключевые слова без дополнительных объяснений:
"""

            llm_result = await llm_service.generate_contextual_response(
                extraction_prompt,
                conversation_context=[],
                context_data={
                    "action": "extract_search_keywords",
                    "original_query": user_query
                },
                session=session
            )
            
            extracted_query = llm_result["text"].strip()
            
            # Валидация результата
            if len(extracted_query) < 2:
                self._logger.warning(f"LLM вернул слишком короткий запрос: '{extracted_query}', используем простую очистку")
                return self._extract_product_keywords(user_query)
            
            self._logger.debug(f"LLM извлек поисковый запрос: '{user_query}' -> '{extracted_query}'")
            return extracted_query
            
        except Exception as e:
            self._logger.error(f"Ошибка LLM извлечения ключевых слов: {e}")
            # Fallback на простую очистку
            return self._extract_product_keywords(user_query)


# Глобальный экземпляр оркестратора
search_orchestrator = SearchOrchestrator()
