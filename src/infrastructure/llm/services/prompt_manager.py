"""
Менеджер промптов для работы с базой данных.
Управляет системными промптами согласно @vision.md.
"""
import logging
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update

from src.infrastructure.database.models import Prompt


class PromptManager:
    """
    Менеджер системных промптов.
    Загружает и кэширует промпты из БД с hot-reload функциональностью.
    """
    
    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._prompts_cache: Dict[str, str] = {}
    
    async def get_prompt(self, name: str, session: AsyncSession) -> str:
        """
        Получает промпт по имени из БД или кэша.
        
        Args:
            name: Имя промпта
            session: Сессия базы данных
            
        Returns:
            Содержимое промпта или промпт по умолчанию
        """
        # Проверяем кэш
        if name in self._prompts_cache:
            return self._prompts_cache[name]
        
        try:
            # Ищем активный промпт в БД
            query = select(Prompt).where(
                Prompt.name == name,
                Prompt.active == True
            ).order_by(Prompt.version.desc())
            
            result = await session.execute(query)
            prompt = result.scalar_one_or_none()
            
            if prompt:
                self._prompts_cache[name] = prompt.content
                self._logger.debug(f"Загружен промпт '{name}' из БД")
                return prompt.content
            else:
                # Если промпт не найден, создаем дефолтный
                default_prompt = self._get_default_prompt(name)
                await self._create_default_prompt(name, default_prompt, session)
                self._prompts_cache[name] = default_prompt
                self._logger.info(f"Создан дефолтный промпт '{name}'")
                return default_prompt
                
        except Exception as e:
            self._logger.error(f"Ошибка получения промпта '{name}': {e}")
            # Возвращаем дефолтный промпт
            return self._get_default_prompt(name)
    
    def _get_default_prompt(self, name: str) -> str:
        """
        Возвращает дефолтный промпт по имени.
        Промпты согласно @vision.md и @product_idea.md.
        """
        default_prompts = {
            "system_prompt": """Ты - AI консультант компании по поставке оборудования и запчастей.

Твоя задача:
- Помогать клиентам найти нужные товары в каталоге
- Консультировать по услугам компании  
- Отвечать на общие вопросы
- Собирать контакты заинтересованных клиентов

Важные правила:
1. ВСЕГДА отвечай на том же языке, на котором пишет пользователь
2. Если пользователь пишет на русском - отвечай на русском
3. Если пользователь пишет на английском - отвечай на английском
4. Будь дружелюбным и профессиональным
5. При поиске товаров используй предоставленную информацию из каталога
6. Если не можешь помочь - предложи связаться с менеджером

Ты можешь помочь с:
- Поиском товаров и оборудования
- Информацией об услугах компании
- Техническими консультациями
- Оформлением заявок""",

            "product_search_prompt": """На основе результатов поиска по каталогу предоставь клиенту информацию о найденных товарах.

Правила ответа:
1. Отвечай на языке пользователя
2. Покажи наиболее релевантные товары (максимум 5)
3. Для каждого товара укажи: название, артикул, описание
4. Если есть фото - упомяни об этом
5. Предложи дополнительную помощь
6. Если ничего не найдено - предложи уточнить запрос или связаться с менеджером

Найденные товары: {search_results}
Запрос пользователя: {user_query}""",

            "service_answer_prompt": """Ответь на вопрос пользователя об услугах компании на основе предоставленной информации.

Правила ответа:
1. Отвечай на языке пользователя
2. Используй только предоставленную информацию об услугах
3. Будь конкретным и полезным
4. Если информации недостаточно - предложи связаться с менеджером
5. Упомяни релевантные услуги

Информация об услугах: {services_info}
Вопрос пользователя: {user_query}""",

            "general_conversation_prompt": """Ответь на общий запрос пользователя как консультант компании.

Правила ответа:
1. Отвечай на языке пользователя
2. Будь дружелюбным и профессиональным
3. Направляй разговор к потребностям клиента
4. Предлагай помощь с поиском товаров или услуг
5. При необходимости предлагай связаться с менеджером

Запрос пользователя: {user_query}""",

            "lead_qualification_prompt": """Проанализируй диалог с клиентом и определи, нужно ли создать лид.

Создавай лид если:
- Клиент интересуется конкретными товарами
- Клиент спрашивает о ценах, доставке, условиях
- Клиент хочет сделать заказ
- Клиент просит связаться с менеджером
- Клиент предоставил контактные данные

НЕ создавай лид если:
- Это общие вопросы
- Клиент просто знакомится с компанией
- Нет явного интереса к покупке

Ответь только: CREATE_LEAD или NO_LEAD

История диалога: {conversation_history}""",

            "company_info_prompt": """Ответь на вопрос о компании на основе предоставленной информации.

Правила ответа:
1. Отвечай на языке пользователя
2. Используй только проверенную информацию о компании
3. Будь конкретным и информативным
4. Если информации недостаточно - предложи связаться напрямую

Информация о компании: {company_info}
Вопрос пользователя: {user_query}"""
        }
        
        return default_prompts.get(name, f"Дефолтный промпт для '{name}' не настроен.")
    
    async def _create_default_prompt(
        self, 
        name: str, 
        content: str, 
        session: AsyncSession
    ) -> None:
        """Создает дефолтный промпт в БД."""
        try:
            stmt = insert(Prompt).values(
                name=name,
                content=content,
                version=1,
                active=True
            )
            await session.execute(stmt)
            await session.commit()
            
        except Exception as e:
            self._logger.error(f"Ошибка создания дефолтного промпта '{name}': {e}")
            await session.rollback()
    
    async def update_prompt(
        self, 
        name: str, 
        content: str, 
        session: AsyncSession
    ) -> bool:
        """
        Обновляет промпт в БД и очищает кэш.
        
        Args:
            name: Имя промпта
            content: Новое содержимое
            session: Сессия базы данных
            
        Returns:
            True если обновление успешно
        """
        try:
            # Деактивируем старые версии
            deactivate_stmt = update(Prompt).where(
                Prompt.name == name
            ).values(active=False)
            await session.execute(deactivate_stmt)
            
            # Получаем следующую версию
            query = select(Prompt.version).where(
                Prompt.name == name
            ).order_by(Prompt.version.desc())
            
            result = await session.execute(query)
            last_version = result.scalar_one_or_none() or 0
            new_version = last_version + 1
            
            # Создаем новую версию
            insert_stmt = insert(Prompt).values(
                name=name,
                content=content,
                version=new_version,
                active=True
            )
            await session.execute(insert_stmt)
            await session.commit()
            
            # Очищаем кэш
            if name in self._prompts_cache:
                del self._prompts_cache[name]
            
            self._logger.info(f"Промпт '{name}' обновлен до версии {new_version}")
            return True
            
        except Exception as e:
            self._logger.error(f"Ошибка обновления промпта '{name}': {e}")
            await session.rollback()
            return False
    
    async def list_prompts(self, session: AsyncSession) -> Dict[str, Dict]:
        """
        Возвращает список всех промптов с метаданными.
        
        Args:
            session: Сессия базы данных
            
        Returns:
            Словарь {name: {version, active, content_preview}}
        """
        try:
            query = select(Prompt).where(Prompt.active == True)
            result = await session.execute(query)
            prompts = result.scalars().all()
            
            prompt_info = {}
            for prompt in prompts:
                prompt_info[prompt.name] = {
                    "version": prompt.version,
                    "active": prompt.active,
                    "content_preview": prompt.content[:100] + "..." if len(prompt.content) > 100 else prompt.content,
                    "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None
                }
            
            return prompt_info
            
        except Exception as e:
            self._logger.error(f"Ошибка получения списка промптов: {e}")
            return {}
    
    def clear_cache(self) -> None:
        """Очищает кэш промптов для hot-reload."""
        self._prompts_cache.clear()
        self._logger.info("Кэш промптов очищен")


# Глобальный экземпляр менеджера промптов
prompt_manager = PromptManager()
