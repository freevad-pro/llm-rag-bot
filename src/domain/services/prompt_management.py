"""
Сервис управления промптами (обновленная версия)
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from ..entities.prompt import Prompt, PromptType
from ...infrastructure.database.models import Prompt as PromptModel
from ...infrastructure.logging.hybrid_logger import hybrid_logger


class PromptManagementService:
    """Сервис для управления промптами"""
    
    def _model_to_entity(self, prompt_model: PromptModel) -> Prompt:
        """Конвертирует модель БД в domain entity"""
        return Prompt(
            id=prompt_model.id,
            name=prompt_model.name,
            display_name=prompt_model.display_name,
            description=prompt_model.description,
            content=prompt_model.content,
            version=prompt_model.version,
            active=prompt_model.active,
            created_at=prompt_model.created_at,
            updated_at=prompt_model.updated_at
        )
    
    async def get_all_prompts(self, session: AsyncSession) -> List[Prompt]:
        """Получить все промпты"""
        stmt = select(PromptModel).where(PromptModel.active == True).order_by(PromptModel.name)
        result = await session.execute(stmt)
        prompt_models = result.scalars().all()
        
        return [self._model_to_entity(p) for p in prompt_models]
    
    async def get_prompt_by_id(self, session: AsyncSession, prompt_id: int) -> Optional[Prompt]:
        """Получить промпт по ID"""
        stmt = select(PromptModel).where(PromptModel.id == prompt_id)
        result = await session.execute(stmt)
        prompt_model = result.scalar_one_or_none()
        
        if not prompt_model:
            return None
            
        return self._model_to_entity(prompt_model)
    
    async def get_prompt_by_name(self, session: AsyncSession, name: str) -> Optional[Prompt]:
        """Получить промпт по имени"""
        stmt = select(PromptModel).where(PromptModel.name == name, PromptModel.active == True)
        result = await session.execute(stmt)
        prompt_model = result.scalar_one_or_none()
        
        if not prompt_model:
            return None
            
        return self._model_to_entity(prompt_model)
    
    async def update_prompt(
        self, 
        session: AsyncSession, 
        prompt_id: int, 
        new_content: str,
        updated_by: int,
        new_display_name: Optional[str] = None,
        new_description: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Обновить промпт с версионностью"""
        try:
            # Получаем текущий промпт
            prompt = await self.get_prompt_by_id(session, prompt_id)
            if not prompt:
                return False
            
            # Логируем изменение
            await hybrid_logger.info(
                f"Промпт '{prompt.name}' обновлен пользователем {updated_by}. "
                f"Версия {prompt.version} -> {prompt.version + 1}"
            )
            
            # Подготавливаем данные для обновления
            update_data = {
                'content': new_content,
                'version': prompt.version + 1
            }
            
            # Добавляем метаданные если они переданы
            if new_display_name is not None:
                update_data['display_name'] = new_display_name
            if new_description is not None:
                update_data['description'] = new_description
            
            # Обновляем промпт
            stmt = (
                update(PromptModel)
                .where(PromptModel.id == prompt_id)
                .values(**update_data)
            )
            await session.execute(stmt)
            await session.commit()
            
            return True
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка обновления промпта {prompt_id}: {e}")
            await session.rollback()
            return False
    
    async def create_prompt(
        self, 
        session: AsyncSession, 
        name: str, 
        content: str,
        created_by: int,
        display_name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Prompt]:
        """Создать новый промпт"""
        try:
            prompt_model = PromptModel(
                name=name,
                display_name=display_name,
                description=description,
                content=content,
                version=1,
                active=True
            )
            
            session.add(prompt_model)
            await session.commit()
            await session.refresh(prompt_model)
            
            await hybrid_logger.info(f"Создан новый промпт '{name}' пользователем {created_by}")
            
            return self._model_to_entity(prompt_model)
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка создания промпта '{name}': {e}")
            await session.rollback()
            return None
    
    async def initialize_default_prompts(self, session: AsyncSession) -> None:
        """Инициализация промптов по умолчанию если их нет"""
        # Импортируем улучшенные промпты
        from ...infrastructure.llm.services.improved_prompts import IMPROVED_PROMPTS
        
        default_prompts = {
            "system_prompt": {
                "content": IMPROVED_PROMPTS["system_prompt"],
                "display_name": "Основной системный промпт",
                "description": "Основные инструкции для AI-агента, определяющие его поведение и роль"
            },

            "product_search_prompt": {
                "content": IMPROVED_PROMPTS["product_search_prompt"],
                "display_name": "Поиск товаров",
                "description": "Промпт для поиска и рекомендации товаров из каталога"
            },

            "service_answer_prompt": {
                "content": IMPROVED_PROMPTS["service_answer_prompt"],
                "display_name": "Ответы об услугах",
                "description": "Промпт для ответов о услугах компании"
            },

            "general_conversation_prompt": {
                "content": IMPROVED_PROMPTS["general_conversation_prompt"],
                "display_name": "Общие вопросы",
                "description": "Промпт для общения и поддержания диалога"
            },

            "lead_qualification_prompt": {
                "content": IMPROVED_PROMPTS["lead_qualification_prompt"],
                "display_name": "Квалификация лидов",
                "description": "Промпт для определения и квалификации потенциальных клиентов"
            },

            "company_info_prompt": {
                "content": IMPROVED_PROMPTS["company_info_prompt"],
                "display_name": "Информация о компании",
                "description": "Промпт для ответов на вопросы о компании"
            },

            "search_query_extraction_prompt": {
                "content": IMPROVED_PROMPTS["search_query_extraction_prompt"],
                "display_name": "Извлечение поискового запроса",
                "description": "Промпт для извлечения ключевых слов из пользовательских запросов для поиска товаров"
            }
        }
        
        for name, data in default_prompts.items():
            existing = await self.get_prompt_by_name(session, name)
            if not existing:
                await self.create_prompt(
                    session, 
                    name, 
                    data["content"], 
                    0,  # 0 = система
                    data["display_name"],
                    data["description"]
                )







