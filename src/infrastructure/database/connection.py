"""
Подключение к PostgreSQL и инициализация БД
"""
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from src.infrastructure.database.models import Base
from src.config.database import engine
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Создаем фабрику сессий
async_session_factory = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def create_tables() -> None:
    """Создание всех таблиц в БД"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise


async def check_db_connection() -> bool:
    """Проверка подключения к БД"""
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        return False


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для получения сессии базы данных.
    Используется в FastAPI через Depends.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Альтернативная функция для получения сессии.
    Используется в скриптах и сервисах.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_health() -> dict:
    """Информация о состоянии БД для health check"""
    try:
        is_connected = await check_db_connection()
        return {
            "database": "connected" if is_connected else "disconnected",
            "engine": str(engine.url).replace(engine.url.password or "", "***")
        }
    except Exception as e:
        return {
            "database": "error",
            "error": str(e)
        }
