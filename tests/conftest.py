"""
Общие fixtures для всех тестов
"""
import asyncio
import os
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient
from fastapi.testclient import TestClient

# Импорты из нашего приложения
from src.main import app
from src.config.settings import Settings
from src.infrastructure.database.models import Base
from src.config.database import get_db

# Тестовые настройки
# Используем реальную PostgreSQL тестовую БД для интеграционных тестов
# В Docker используем имя сервиса вместо localhost
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_pass@postgres-test:5432/test_catalog_db"

class TestSettings(Settings):
    """Настройки для тестирования"""
    debug: bool = True
    database_url: str = TEST_DATABASE_URL
    bot_token: str = "test_token"
    default_llm_provider: str = "test"
    
    # Отключаем внешние сервисы в тестах
    manager_telegram_chat_id: str = ""
    admin_telegram_ids: str = ""

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Создает event loop для всей сессии тестов"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """Создает тестовый движок базы данных"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    
    # Создаем все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Очищаем после тестов
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def test_session(test_engine) -> AsyncSession:
    """Создает тестовую сессию БД для каждого теста"""
    async_session = async_sessionmaker(
        test_engine, 
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        # Начинаем транзакцию
        transaction = await session.begin()
        
        try:
            yield session
        finally:
            # Пробуем сделать rollback, игнорируем ошибку если транзакция уже закрыта
            try:
                await transaction.rollback()
            except Exception:
                pass
            
            # Закрываем сессию
            try:
                await session.close()
            except Exception:
                pass

@pytest.fixture
def override_get_db(test_session):
    """Переопределяет зависимость get_db для тестов"""
    async def _override_get_db():
        yield test_session
    return _override_get_db

@pytest.fixture
def test_client(override_get_db) -> TestClient:
    """Создает тестовый клиент FastAPI"""
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture
async def async_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Создает асинхронный тестовый клиент"""
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture
def test_settings() -> TestSettings:
    """Возвращает тестовые настройки"""
    return TestSettings()

# Фикстуры для быстрого доступа к маркерам
@pytest.fixture
def mark_unit():
    """Маркер для unit тестов"""
    return pytest.mark.unit

@pytest.fixture  
def mark_integration():
    """Маркер для интеграционных тестов"""
    return pytest.mark.integration

@pytest.fixture
def mark_e2e():
    """Маркер для E2E тестов"""
    return pytest.mark.e2e

@pytest.fixture
def mark_slow():
    """Маркер для медленных тестов"""
    return pytest.mark.slow

# Автоматическое применение маркеров
def pytest_collection_modifyitems(config, items):
    """Автоматически применяет маркеры к тестам"""
    for item in items:
        # Определяем тип теста по пути к файлу
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)
        
        # Добавляем специфичные маркеры
        if "db" in str(item.fspath) or "database" in str(item.fspath):
            item.add_marker(pytest.mark.db)
        if "api" in str(item.fspath):
            item.add_marker(pytest.mark.api)
        if "telegram" in str(item.fspath):
            item.add_marker(pytest.mark.telegram)
        if "llm" in str(item.fspath):
            item.add_marker(pytest.mark.llm)
        if "search" in str(item.fspath):
            item.add_marker(pytest.mark.search)
        if "lead" in str(item.fspath):
            item.add_marker(pytest.mark.leads)
