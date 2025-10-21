"""
Конфигурация базы данных
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.config.settings import settings


# Создание асинхронного движка с правильным connection pool
engine = create_async_engine(
    settings.database_url,
    # QueuePool с разумными настройками для production
    pool_size=10,  # Базовый размер пула (10 постоянных подключений)
    max_overflow=20,  # Дополнительно до 20 подключений при пиковой нагрузке
    pool_pre_ping=True,  # Проверять подключение перед использованием
    pool_recycle=3600,  # Пересоздавать подключения каждый час
    echo=settings.debug,
)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Dependency для получения сессии БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


from contextlib import asynccontextmanager

@asynccontextmanager
async def get_session():
    """Контекстный менеджер для получения сессии БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()