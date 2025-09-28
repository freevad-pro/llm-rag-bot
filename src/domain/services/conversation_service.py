"""
Сервис управления диалогами и контекстом.
Согласно @vision.md: контекст последних 20 сообщений для LLM.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from ...infrastructure.database.models import User, Conversation, Message


class ConversationService:
    """
    Сервис для управления диалогами и их контекстом.
    Реализует бизнес-логику работы с сообщениями согласно @vision.md.
    """
    
    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def get_conversation_context(
        self, 
        chat_id: int, 
        session: AsyncSession,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Получает контекст последних сообщений для LLM.
        
        Args:
            chat_id: ID чата пользователя (основной идентификатор)
            session: Сессия базы данных
            limit: Максимальное количество сообщений (по умолчанию 20)
            
        Returns:
            Список последних сообщений в формате для LLM
        """
        try:
            # Находим пользователя по chat_id
            user_query = select(User).where(User.chat_id == chat_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                self._logger.warning(f"Пользователь с chat_id {chat_id} не найден")
                return []
            
            # Получаем активную беседу пользователя
            conversation = await self._get_or_create_active_conversation(
                user.id, chat_id, session
            )
            
            # Получаем последние сообщения
            messages_query = select(Message).where(
                Message.conversation_id == conversation.id
            ).order_by(desc(Message.created_at)).limit(limit)
            
            messages_result = await session.execute(messages_query)
            messages = messages_result.scalars().all()
            
            # Формируем контекст (в правильном хронологическом порядке)
            context = []
            for message in reversed(messages):
                context.append({
                    "role": message.role,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                    "id": message.id
                })
            
            self._logger.debug(f"Получен контекст из {len(context)} сообщений для chat_id {chat_id}")
            return context
            
        except Exception as e:
            self._logger.error(f"Ошибка получения контекста диалога: {e}")
            return []
    
    async def save_user_message(
        self,
        chat_id: int,
        content: str,
        session: AsyncSession,
        extra_data: Optional[str] = None
    ) -> Optional[int]:
        """
        Сохраняет сообщение пользователя.
        
        Args:
            chat_id: ID чата пользователя
            content: Содержимое сообщения
            session: Сессия базы данных
            extra_data: Дополнительные данные как JSON строка
            
        Returns:
            ID созданного сообщения или None при ошибке
        """
        try:
            # Находим пользователя
            user_query = select(User).where(User.chat_id == chat_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                self._logger.error(f"Пользователь с chat_id {chat_id} не найден")
                return None
            
            # Получаем активную беседу
            conversation = await self._get_or_create_active_conversation(
                user.id, chat_id, session
            )
            
            # Создаем сообщение
            message = Message(
                conversation_id=conversation.id,
                role="user",
                content=content,
                extra_data=extra_data
            )
            
            session.add(message)
            await session.commit()
            await session.refresh(message)
            
            self._logger.debug(f"Сохранено сообщение пользователя ID {message.id}")
            return message.id
            
        except Exception as e:
            self._logger.error(f"Ошибка сохранения сообщения пользователя: {e}")
            await session.rollback()
            return None
    
    async def save_assistant_message(
        self,
        chat_id: int,
        content: str,
        session: AsyncSession,
        llm_provider: Optional[str] = None,
        tokens_used: Optional[int] = None,
        processing_time_ms: Optional[int] = None,
        extra_data: Optional[str] = None
    ) -> Optional[int]:
        """
        Сохраняет ответ ассистента с метриками использования.
        
        Args:
            chat_id: ID чата пользователя
            content: Содержимое ответа
            session: Сессия базы данных
            llm_provider: Провайдер LLM (openai, yandexgpt)
            tokens_used: Количество использованных токенов
            processing_time_ms: Время обработки в миллисекундах
            extra_data: Дополнительные данные как JSON строка
            
        Returns:
            ID созданного сообщения или None при ошибке
        """
        try:
            # Находим пользователя
            user_query = select(User).where(User.chat_id == chat_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                self._logger.error(f"Пользователь с chat_id {chat_id} не найден")
                return None
            
            # Получаем активную беседу
            conversation = await self._get_or_create_active_conversation(
                user.id, chat_id, session
            )
            
            # Создаем сообщение с метриками
            message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=content,
                llm_provider=llm_provider,
                tokens_used=tokens_used,
                processing_time_ms=processing_time_ms,
                extra_data=extra_data
            )
            
            session.add(message)
            await session.commit()
            await session.refresh(message)
            
            # Обновляем статистику использования токенов
            if llm_provider and tokens_used and tokens_used > 0:
                from .usage_statistics_service import usage_statistics_service
                # Определяем модель из extra_data или используем дефолтную
                model = "unknown"
                if extra_data:
                    import json
                    try:
                        data = json.loads(extra_data)
                        model = data.get("model", "unknown")
                    except:
                        pass
                
                await usage_statistics_service.add_tokens_usage(
                    session, llm_provider, model, tokens_used
                )
            
            self._logger.debug(f"Сохранен ответ ассистента ID {message.id}, токенов: {tokens_used}")
            return message.id
            
        except Exception as e:
            self._logger.error(f"Ошибка сохранения ответа ассистента: {e}")
            await session.rollback()
            return None
    
    async def _get_or_create_active_conversation(
        self,
        user_id: int,
        chat_id: int,
        session: AsyncSession
    ) -> Conversation:
        """
        Получает активную беседу пользователя или создает новую.
        
        Args:
            user_id: ID пользователя в БД
            chat_id: ID чата
            session: Сессия базы данных
            
        Returns:
            Активная беседа
        """
        try:
            # Ищем активную беседу
            conversation_query = select(Conversation).where(
                and_(
                    Conversation.chat_id == chat_id,
                    Conversation.user_id == user_id,
                    Conversation.status == "active"
                )
            ).order_by(desc(Conversation.created_at))
            
            conversation_result = await session.execute(conversation_query)
            conversation = conversation_result.scalar_one_or_none()
            
            if conversation:
                return conversation
            
            # Создаем новую беседу
            new_conversation = Conversation(
                chat_id=chat_id,
                user_id=user_id,
                platform="telegram",
                status="active",
                created_at=datetime.utcnow()
            )
            
            session.add(new_conversation)
            await session.commit()
            await session.refresh(new_conversation)
            
            self._logger.info(f"Создана новая беседа ID {new_conversation.id} для пользователя {user_id}")
            return new_conversation
            
        except Exception as e:
            self._logger.error(f"Ошибка получения/создания беседы: {e}")
            await session.rollback()
            raise
    
    async def get_conversation_summary(
        self, 
        chat_id: int, 
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Возвращает краткую сводку по диалогу.
        
        Args:
            chat_id: ID чата пользователя
            session: Сессия базы данных
            
        Returns:
            Сводка по диалогу
        """
        try:
            # Находим пользователя
            user_query = select(User).where(User.chat_id == chat_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                return {"error": "Пользователь не найден"}
            
            # Получаем активную беседу
            conversation_query = select(Conversation).where(
                and_(
                    Conversation.chat_id == chat_id,
                    Conversation.user_id == user.id,
                    Conversation.status == "active"
                )
            ).order_by(desc(Conversation.created_at))
            
            conversation_result = await session.execute(conversation_query)
            conversation = conversation_result.scalar_one_or_none()
            
            if not conversation:
                return {"messages_count": 0, "created_at": None}
            
            # Подсчитываем сообщения
            messages_count_query = select(Message.id).where(
                Message.conversation_id == conversation.id
            )
            messages_result = await session.execute(messages_count_query)
            messages_count = len(messages_result.scalars().all())
            
            return {
                "conversation_id": conversation.id,
                "messages_count": messages_count,
                "created_at": conversation.created_at.isoformat(),
                "platform": conversation.platform,
                "status": conversation.status
            }
            
        except Exception as e:
            self._logger.error(f"Ошибка получения сводки диалога: {e}")
            return {"error": str(e)}
    
    async def end_conversation(
        self, 
        chat_id: int, 
        session: AsyncSession
    ) -> bool:
        """
        Завершает активную беседу пользователя.
        
        Args:
            chat_id: ID чата пользователя
            session: Сессия базы данных
            
        Returns:
            True если беседа завершена успешно
        """
        try:
            # Находим пользователя
            user_query = select(User).where(User.chat_id == chat_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                return False
            
            # Обновляем статус активной беседы
            from sqlalchemy import update
            
            update_query = update(Conversation).where(
                and_(
                    Conversation.chat_id == chat_id,
                    Conversation.user_id == user.id,
                    Conversation.status == "active"
                )
            ).values(
                status="ended",
                ended_at=datetime.utcnow()
            )
            
            result = await session.execute(update_query)
            await session.commit()
            
            if result.rowcount > 0:
                self._logger.info(f"Завершена беседа для chat_id {chat_id}")
                return True
            
            return False
            
        except Exception as e:
            self._logger.error(f"Ошибка завершения беседы: {e}")
            await session.rollback()
            return False


# Глобальный экземпляр сервиса диалогов
conversation_service = ConversationService()
