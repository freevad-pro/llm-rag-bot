"""
Middleware для Telegram бота
Обеспечивает подключение к базе данных для каждого запроса
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import AsyncSessionLocal
from src.infrastructure.logging.hybrid_logger import hybrid_logger


class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware для автоматического создания сессии БД
    для каждого обновления от Telegram
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Создает сессию БД и передает в handler"""
        async with AsyncSessionLocal() as session:
            try:
                # Добавляем сессию в данные для handler'а
                data["session"] = session
                
                # Вызываем handler
                result = await handler(event, data)
                
                # Коммитим изменения
                await session.commit()
                
                return result
                
            except Exception as e:
                # Откатываем изменения при ошибке
                await session.rollback()
                await hybrid_logger.error(f"Ошибка в DatabaseMiddleware: {e}")
                raise
            finally:
                # Сессия автоматически закроется через context manager
                pass
