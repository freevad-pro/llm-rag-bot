"""
Smoke tests для проверки работоспособности системы на VPS.
Быстрые проверки критических компонентов с обязательной очисткой данных.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from sqlalchemy.exc import SQLAlchemyError

from src.config.database import get_async_session
from src.infrastructure.database.models import User, Conversation, Message, Lead as LeadModel
from src.infrastructure.llm.factory import create_llm_provider
from src.infrastructure.search.catalog_service import CatalogService
from src.application.telegram.services.user_service import ensure_user_exists
from src.application.telegram.services.message_service import get_or_create_conversation, save_message
from src.infrastructure.logging.hybrid_logger import hybrid_logger


class SmokeTestError(Exception):
    """Исключение для ошибок smoke тестов"""
    pass


class SmokeTestRunner:
    """Запускает быстрые проверки системы на VPS"""
    
    # Константы для тестовых данных
    TEST_USER_PREFIX = "smoke_test_"
    TEST_CHAT_ID_BASE = 999000000  # Вне диапазона реальных пользователей
    TEST_CONVERSATION_PREFIX = "smoke_test_conversation_"
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.test_data_created = []  # Отслеживаем созданные тестовые данные
        
    async def run_all_smoke_tests(self) -> Dict[str, Any]:
        """
        Запускает все smoke tests и возвращает результаты.
        
        Returns:
            Dict с результатами всех тестов
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "tests": {}
        }
        
        tests = [
            ("database", self.test_database_connection),
            ("llm_provider", self.test_llm_provider),
            ("catalog_search", self.test_catalog_search), 
            ("user_creation", self.test_user_creation),
            ("api_health", self.test_api_health)
        ]
        
        self.logger.info("🔥 Запуск smoke tests...")
        
        for test_name, test_func in tests:
            results["total_tests"] += 1
            
            try:
                start_time = datetime.utcnow()
                await test_func()
                end_time = datetime.utcnow()
                
                duration = (end_time - start_time).total_seconds()
                
                results["tests"][test_name] = {
                    "status": "PASSED",
                    "duration_seconds": duration,
                    "error": None
                }
                results["passed"] += 1
                
                self.logger.info(f"✅ {test_name}: PASSED ({duration:.2f}s)")
                
            except Exception as e:
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                results["tests"][test_name] = {
                    "status": "FAILED", 
                    "duration_seconds": duration,
                    "error": str(e)
                }
                results["failed"] += 1
                
                self.logger.error(f"❌ {test_name}: FAILED - {e}")
        
        # Обязательная очистка данных
        await self.cleanup_all_test_data()
        
        success_rate = (results["passed"] / results["total_tests"]) * 100
        self.logger.info(f"🏁 Smoke tests завершены: {results['passed']}/{results['total_tests']} ({success_rate:.1f}%)")
        
        return results
    
    async def test_database_connection(self):
        """Тест подключения к базе данных"""
        async with get_async_session() as session:
            # Простой SELECT запрос
            result = await session.execute(text("SELECT 1 as test_value"))
            value = result.scalar()
            
            if value != 1:
                raise SmokeTestError(f"Database returned {value}, expected 1")
            
            # Проверка записи/чтения
            test_user = User(
                chat_id=self.TEST_CHAT_ID_BASE + 1,
                telegram_user_id=self.TEST_CHAT_ID_BASE + 1,
                username=f"{self.TEST_USER_PREFIX}db_test",
                first_name="Test",
                last_name="User"
            )
            
            session.add(test_user)
            await session.flush()
            
            # Проверяем что ID присвоен
            if not test_user.id:
                raise SmokeTestError("User ID not assigned after flush")
            
            self.test_data_created.append(('user', test_user.id))
            
            # Откатываем транзакцию (данные не сохранятся)
            await session.rollback()
    
    async def test_llm_provider(self):
        """Тест работы LLM провайдера"""
        try:
            llm_provider = await create_llm_provider()
            
            # Простой тестовый запрос
            test_prompt = "Скажи одно слово: привет"
            response = await llm_provider.generate_response(
                messages=[{"role": "user", "content": test_prompt}],
                max_tokens=10
            )
            
            if not response or len(response.strip()) == 0:
                raise SmokeTestError("LLM returned empty response")
            
            if len(response) > 100:
                raise SmokeTestError(f"LLM response too long: {len(response)} chars")
                
        except Exception as e:
            raise SmokeTestError(f"LLM provider failed: {e}")
    
    async def test_catalog_search(self):
        """Тест поиска по каталогу"""
        try:
            catalog_service = CatalogService()
            
            # Поиск по популярному запросу
            results = await catalog_service.search("насос", limit=5)
            
            if not results:
                raise SmokeTestError("Catalog search returned no results")
                
            if len(results) == 0:
                raise SmokeTestError("Empty search results")
            
            # Проверяем структуру результата
            first_result = results[0]
            required_fields = ['title', 'description']
            
            for field in required_fields:
                if not hasattr(first_result, field):
                    raise SmokeTestError(f"Search result missing field: {field}")
                    
        except Exception as e:
            raise SmokeTestError(f"Catalog search failed: {e}")
    
    async def test_user_creation(self):
        """Тест создания пользователя через сервис"""
        async with get_async_session() as session:
            try:
                test_chat_id = self.TEST_CHAT_ID_BASE + 2
                test_telegram_id = self.TEST_CHAT_ID_BASE + 2
                
                # Создаем пользователя через сервис
                user = await ensure_user_exists(
                    session=session,
                    chat_id=test_chat_id,
                    telegram_user_id=test_telegram_id,
                    username=f"{self.TEST_USER_PREFIX}service_test",
                    first_name="Smoke",
                    last_name="Test"
                )
                
                if not user or not user.id:
                    raise SmokeTestError("User creation failed")
                
                self.test_data_created.append(('user', user.id))
                
                # Создаем тестовый диалог
                conversation = await get_or_create_conversation(
                    session=session,
                    chat_id=test_chat_id
                )
                
                if not conversation or not conversation.id:
                    raise SmokeTestError("Conversation creation failed")
                
                self.test_data_created.append(('conversation', conversation.id))
                
                # Создаем тестовое сообщение
                message = await save_message(
                    session=session,
                    chat_id=test_chat_id,
                    role="user",
                    content="Тестовое сообщение smoke test"
                )
                
                if not message or not message.id:
                    raise SmokeTestError("Message creation failed")
                
                self.test_data_created.append(('message', message.id))
                
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                raise SmokeTestError(f"User creation test failed: {e}")
    
    async def test_api_health(self):
        """Тест доступности API endpoints (базовый)"""
        # Этот тест можно расширить с помощью httpx для реальных HTTP запросов
        # Пока проверяем что основные модули импортируются
        try:
            from src.application.web import app  # Если есть FastAPI app
            from src.application.telegram.bot import dp  # Если есть Telegram dispatcher
            
            # Простая проверка что модули загружаются
            if not app and not dp:
                raise SmokeTestError("API modules not loaded")
                
        except ImportError as e:
            raise SmokeTestError(f"API modules import failed: {e}")
    
    async def cleanup_all_test_data(self):
        """Очищает все тестовые данные созданные в процессе тестирования"""
        async with get_async_session() as session:
            try:
                cleaned_count = 0
                
                # Удаляем в обратном порядке создания (из-за foreign keys)
                for data_type, data_id in reversed(self.test_data_created):
                    try:
                        if data_type == 'message':
                            await session.execute(delete(Message).where(Message.id == data_id))
                        elif data_type == 'conversation':
                            await session.execute(delete(Conversation).where(Conversation.id == data_id))
                        elif data_type == 'lead':
                            await session.execute(delete(LeadModel).where(LeadModel.id == data_id))
                        elif data_type == 'user':
                            await session.execute(delete(User).where(User.id == data_id))
                        
                        cleaned_count += 1
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to cleanup {data_type} {data_id}: {e}")
                
                # Дополнительная очистка по префиксам (на случай если что-то пропустили)
                await self.cleanup_test_data_by_prefix(session)
                
                await session.commit()
                
                if cleaned_count > 0:
                    self.logger.info(f"🧹 Очищено {cleaned_count} тестовых записей")
                
                self.test_data_created.clear()
                
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Ошибка очистки тестовых данных: {e}")
    
    async def cleanup_test_data_by_prefix(self, session: AsyncSession):
        """Очищает тестовые данные по префиксам (дополнительная защита)"""
        try:
            # Удаляем пользователей с тестовыми именами
            await session.execute(
                delete(User).where(User.username.like(f"{self.TEST_USER_PREFIX}%"))
            )
            
            # Удаляем тестовые диалоги 
            await session.execute(
                delete(Conversation).where(
                    Conversation.chat_id >= self.TEST_CHAT_ID_BASE
                )
            )
            
            # Удаляем старые тестовые данные (> 1 часа)
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            await session.execute(
                delete(User).where(
                    User.username.like(f"{self.TEST_USER_PREFIX}%") &
                    User.created_at < cutoff_time
                )
            )
            
        except Exception as e:
            self.logger.warning(f"Ошибка дополнительной очистки: {e}")


# Удобные функции для использования в скриптах
async def run_smoke_tests() -> Dict[str, Any]:
    """Запускает все smoke tests и возвращает результаты"""
    runner = SmokeTestRunner()
    return await runner.run_all_smoke_tests()


async def run_single_smoke_test(test_name: str) -> Dict[str, Any]:
    """Запускает один конкретный smoke test"""
    runner = SmokeTestRunner()
    
    tests_map = {
        "database": runner.test_database_connection,
        "llm": runner.test_llm_provider,
        "search": runner.test_catalog_search,
        "user": runner.test_user_creation,
        "api": runner.test_api_health
    }
    
    if test_name not in tests_map:
        raise ValueError(f"Unknown test: {test_name}. Available: {list(tests_map.keys())}")
    
    start_time = datetime.utcnow()
    
    try:
        await tests_map[test_name]()
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            "test": test_name,
            "status": "PASSED",
            "duration_seconds": duration,
            "error": None
        }
        
    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            "test": test_name,
            "status": "FAILED",
            "duration_seconds": duration,
            "error": str(e)
        }
    
    finally:
        # Всегда очищаем данные
        await runner.cleanup_all_test_data()
    
    return result


if __name__ == "__main__":
    # Для тестирования модуля
    async def main():
        results = await run_smoke_tests()
        print(f"Results: {results}")
    
    asyncio.run(main())
