"""
Сервис для работы с сообщениями и диалогами
Согласно @vision.md сохраняет ВСЕ сообщения в PostgreSQL
"""
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.infrastructure.database.models import Conversation, Message, User
from src.infrastructure.logging.hybrid_logger import hybrid_logger


async def get_or_create_conversation(
    session: AsyncSession,
    chat_id: int,
    platform: str = "telegram"
) -> Conversation:
    """
    Получает активный диалог или создает новый
    """
    try:
        # Получаем пользователя
        user_result = await session.execute(
            select(User).where(User.chat_id == chat_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"Пользователь с chat_id {chat_id} не найден")
        
        # Ищем активный диалог
        conv_result = await session.execute(
            select(Conversation)
            .where(
                Conversation.chat_id == chat_id,
                Conversation.status == "active"
            )
            .order_by(desc(Conversation.started_at))
        )
        conversation = conv_result.scalar_one_or_none()
        
        if conversation is None:
            # Создаем новый диалог
            conversation = Conversation(
                chat_id=chat_id,
                user_id=user.id,
                platform=platform,
                status="active"
            )
            session.add(conversation)
            await session.flush()
            
            await hybrid_logger.business(
                f"Новый диалог создан: {chat_id}",
                {"chat_id": chat_id, "conversation_id": conversation.id}
            )
        
        return conversation
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в get_or_create_conversation: {e}")
        raise


async def save_message(
    session: AsyncSession,
    chat_id: int,
    role: str,  # user, assistant, system
    content: str,
    extra_data: Optional[str] = None
) -> Message:
    """
    Сохраняет сообщение в диалоге
    Согласно @vision.md - сохраняем ВСЕ сообщения
    """
    try:
        # Получаем или создаем диалог
        conversation = await get_or_create_conversation(session, chat_id)
        
        # Создаем сообщение
        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            extra_data=extra_data
        )
        
        session.add(message)
        await session.flush()
        
        await hybrid_logger.debug(
            f"Сообщение сохранено: {role} в диалоге {conversation.id}"
        )
        
        return message
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в save_message: {e}")
        raise


async def get_conversation_history(
    session: AsyncSession,
    chat_id: int,
    limit: int = 20
) -> list[Message]:
    """
    Получает последние сообщения диалога
    Согласно @vision.md - максимум 20 сообщений для LLM контекста
    """
    try:
        # Получаем активный диалог
        conversation = await get_or_create_conversation(session, chat_id)
        
        # Получаем последние сообщения
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        
        messages = result.scalars().all()
        
        # Возвращаем в хронологическом порядке (старые сначала)
        return list(reversed(messages))
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в get_conversation_history: {e}")
        return []


async def end_conversation(
    session: AsyncSession,
    chat_id: int,
    reason: str = "timeout"
) -> bool:
    """
    Завершает активный диалог
    """
    try:
        # Найти активный диалог
        result = await session.execute(
            select(Conversation)
            .where(
                Conversation.chat_id == chat_id,
                Conversation.status == "active"
            )
        )
        conversation = result.scalar_one_or_none()
        
        if conversation:
            conversation.status = "ended"
            conversation.ended_at = datetime.utcnow()
            
            # Сохраняем причину в метаданных
            import json
            metadata = {"end_reason": reason}
            conversation.extra_data = json.dumps(metadata)
            
            await hybrid_logger.business(
                f"Диалог завершен: {chat_id}",
                {"chat_id": chat_id, "reason": reason, "conversation_id": conversation.id}
            )
            
            return True
            
        return False
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в end_conversation: {e}")
        return False


async def get_conversation_stats(session: AsyncSession, chat_id: int) -> dict:
    """Получить статистику по диалогам пользователя"""
    try:
        # Количество диалогов
        conv_result = await session.execute(
            select(Conversation).where(Conversation.chat_id == chat_id)
        )
        conversations = conv_result.scalars().all()
        
        # Количество сообщений
        msg_count = 0
        for conv in conversations:
            msg_result = await session.execute(
                select(Message).where(Message.conversation_id == conv.id)
            )
            msg_count += len(msg_result.scalars().all())
        
        return {
            "total_conversations": len(conversations),
            "total_messages": msg_count,
            "active_conversations": len([c for c in conversations if c.status == "active"])
        }
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в get_conversation_stats: {e}")
        return {"total_conversations": 0, "total_messages": 0, "active_conversations": 0}
