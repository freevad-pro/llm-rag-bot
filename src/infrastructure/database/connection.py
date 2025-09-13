"""
Подключение к PostgreSQL и инициализация БД
"""
from sqlalchemy.ext.asyncio import AsyncEngine
from src.infrastructure.database.models import Base
from src.config.database import engine
import logging

logger = logging.getLogger(__name__)


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
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        return False


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
