"""
Сервис для работы с пользователями в Telegram боте
Согласно @vision.md: chat_id - основной идентификатор
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.infrastructure.database.models import User
from src.infrastructure.logging.hybrid_logger import hybrid_logger


async def ensure_user_exists(
    session: AsyncSession,
    chat_id: int,
    telegram_user_id: Optional[int] = None,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> User:
    """
    Создает пользователя если его нет, или обновляет данные
    chat_id - основной идентификатор согласно @vision.md
    """
    try:
        # Ищем пользователя по chat_id
        result = await session.execute(
            select(User).where(User.chat_id == chat_id)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            # Создаем нового пользователя
            user = User(
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            session.add(user)
            await session.flush()  # Получаем ID
            
            await hybrid_logger.business(
                f"Новый пользователь создан: {chat_id}",
                {
                    "chat_id": chat_id,
                    "username": username,
                    "first_name": first_name
                }
            )
        else:
            # Обновляем существующего пользователя если есть новые данные
            updated = False
            
            if telegram_user_id and user.telegram_user_id != telegram_user_id:
                user.telegram_user_id = telegram_user_id
                updated = True
                
            if username and user.username != username:
                user.username = username
                updated = True
                
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
                
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updated = True
            
            if updated:
                await hybrid_logger.business(
                    f"Пользователь обновлен: {chat_id}",
                    {"chat_id": chat_id, "fields_updated": True}
                )
        
        return user
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в ensure_user_exists: {e}")
        raise


async def get_user_by_chat_id(session: AsyncSession, chat_id: int) -> Optional[User]:
    """Получить пользователя по chat_id"""
    try:
        result = await session.execute(
            select(User).where(User.chat_id == chat_id)
        )
        return result.scalar_one_or_none()
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в get_user_by_chat_id: {e}")
        return None


async def update_user_contact(
    session: AsyncSession, 
    chat_id: int, 
    phone: Optional[str] = None,
    email: Optional[str] = None
) -> bool:
    """Обновить контактные данные пользователя"""
    try:
        user = await get_user_by_chat_id(session, chat_id)
        if not user:
            return False
            
        updated = False
        
        if phone and user.phone != phone:
            user.phone = phone
            updated = True
            
        if email and user.email != email:
            user.email = email
            updated = True
        
        if updated:
            await hybrid_logger.business(
                f"Контакты пользователя обновлены: {chat_id}",
                {"chat_id": chat_id, "phone": bool(phone), "email": bool(email)}
            )
            
        return updated
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка в update_user_contact: {e}")
        return False
