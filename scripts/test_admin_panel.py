#!/usr/bin/env python3
"""
Скрипт для тестирования админ-панели локально.
Подготавливает тестовые данные и проверяет работоспособность.
"""
import asyncio
import sys
import os
import requests
import time
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from src.infrastructure.database.connection import get_async_session
from src.infrastructure.database.models import AdminUser as AdminUserModel, User, Conversation, Message
from src.infrastructure.logging.hybrid_logger import hybrid_logger


async def create_test_admin_users():
    """Создает тестовых админ-пользователей"""
    print("📝 Создание тестовых админ-пользователей...")
    
    test_users = [
        {"telegram_id": 123456789, "role": "ADMIN", "username": "test_admin", "first_name": "Test", "last_name": "Admin"},
        {"telegram_id": 111111111, "role": "MANAGER", "username": "test_manager", "first_name": "Test", "last_name": "Manager"},
    ]
    
    async for session in get_async_session():
        try:
            created_count = 0
            
            for user_data in test_users:
                # Проверяем существование
                stmt = select(AdminUserModel).where(AdminUserModel.telegram_id == user_data["telegram_id"])
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    print(f"✓ {user_data['role']} {user_data['telegram_id']} уже существует")
                    continue
                
                admin_user = AdminUserModel(
                    telegram_id=user_data["telegram_id"],
                    telegram_username=user_data["username"],
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    role=user_data["role"],
                    is_active=True
                )
                session.add(admin_user)
                created_count += 1
                print(f"✓ Создан {user_data['role']}: {user_data['telegram_id']} (@{user_data['username']})")
            
            if created_count > 0:
                await session.commit()
                print(f"🎉 Создано {created_count} тестовых админ-пользователей")
            
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Ошибка создания тестовых пользователей: {e}")
            return False


async def create_test_data():
    """Создает тестовые данные для демонстрации"""
    print("📊 Создание тестовых данных...")
    
    async for session in get_async_session():
        try:
            # Создаем тестового пользователя бота
            stmt = select(User).where(User.chat_id == 999999999)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                test_user = User(
                    chat_id=999999999,
                    telegram_user_id=999999999,
                    username="test_bot_user",
                    first_name="Test",
                    last_name="User"
                )
                session.add(test_user)
                await session.flush()
                
                # Создаем тестовый диалог
                test_conversation = Conversation(
                    chat_id=999999999,
                    user_id=test_user.id,
                    platform="telegram",
                    status="active"
                )
                session.add(test_conversation)
                await session.flush()
                
                # Создаем тестовые сообщения
                test_messages = [
                    {"role": "user", "content": "Привет! Расскажи о ваших услугах"},
                    {"role": "assistant", "content": "Здравствуйте! Мы занимаемся поставками оборудования из Китая. Чем могу помочь?"},
                    {"role": "user", "content": "Нужны болты М12"},
                    {"role": "assistant", "content": "Понял! Болты М12. Уточните пожалуйста количество и требования к материалу."},
                ]
                
                for msg_data in test_messages:
                    message = Message(
                        conversation_id=test_conversation.id,
                        role=msg_data["role"],
                        content=msg_data["content"]
                    )
                    session.add(message)
                
                await session.commit()
                print("✓ Созданы тестовые данные: пользователь, диалог, сообщения")
            else:
                print("✓ Тестовые данные уже существуют")
            
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Ошибка создания тестовых данных: {e}")
            return False


async def check_database_connection():
    """Проверяет подключение к базе данных"""
    print("🗄️  Проверка подключения к базе данных...")
    
    try:
        async for session in get_async_session():
            # Простой запрос для проверки соединения
            result = await session.execute(text("SELECT 1"))
            result.fetchone()
            print("✓ База данных доступна")
            
            # Проверяем таблицы
            tables_to_check = ["users", "admin_users", "conversations", "messages", "prompts"]
            for table in tables_to_check:
                try:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"✓ Таблица {table}: {count} записей")
                except Exception as e:
                    print(f"❌ Таблица {table}: {e}")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False


def check_web_server():
    """Проверяет работу веб-сервера"""
    print("🌐 Проверка веб-сервера...")
    
    base_url = "http://localhost:8000"
    
    endpoints_to_check = [
        ("/", "Корневой endpoint"),
        ("/health", "Health check"),
        ("/admin/login", "Страница авторизации админки"),
        ("/api/info", "API информация"),
    ]
    
    success_count = 0
    
    for endpoint, description in endpoints_to_check:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✓ {description}: HTTP {response.status_code}")
                success_count += 1
            else:
                print(f"⚠️  {description}: HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {description}: {e}")
    
    return success_count == len(endpoints_to_check)


def print_test_instructions():
    """Выводит инструкции для тестирования"""
    print("\n" + "="*60)
    print("🧪 ИНСТРУКЦИИ ПО ТЕСТИРОВАНИЮ АДМИН-ПАНЕЛИ")
    print("="*60)
    
    print("\n1. 🌐 Откройте браузер и перейдите по адресу:")
    print("   http://localhost:8000/admin/")
    
    print("\n2. 🔐 Для тестирования авторизации:")
    print("   - Страница покажет форму входа через Telegram")
    print("   - Для полного тестирования нужен реальный Telegram бот")
    print("   - Замените в env.test на ваши реальные Telegram ID")
    
    print("\n3. 🎛️  Доступные страницы (после авторизации):")
    print("   - /admin/           - Главная панель")
    print("   - /admin/profile    - Профиль пользователя")
    print("   - /admin/login      - Страница входа")
    
    print("\n4. 🧪 Тестовые пользователи созданы:")
    print("   - Админ: 123456789 (Test Admin)")
    print("   - Менеджер: 111111111 (Test Manager)")
    
    print("\n5. 📊 Проверьте работу:")
    print("   - Адаптивность интерфейса (измените размер окна)")
    print("   - Навигационное меню")
    print("   - Статистические карточки")
    print("   - Кнопки быстрых действий")
    
    print("\n6. 🔧 API endpoints для тестирования:")
    print("   - GET  /health         - Состояние системы")
    print("   - GET  /api/info       - Информация о системе")
    print("   - GET  /admin/api/user-info - Информация о пользователе (требует авторизации)")
    
    print("\n7. 🐛 При возникновении ошибок:")
    print("   - Проверьте логи: docker-compose logs app")
    print("   - Проверьте БД: docker-compose logs postgres")
    print("   - Перезапустите: docker-compose restart")
    
    print("\n" + "="*60)


async def main():
    """Главная функция тестирования"""
    print("🚀 ПОДГОТОВКА К ТЕСТИРОВАНИЮ АДМИН-ПАНЕЛИ")
    print("="*50)
    
    # Ждем запуска веб-сервера
    print("⏳ Ожидание запуска веб-сервера...")
    for i in range(30):  # 30 секунд максимум
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print("✓ Веб-сервер запущен!")
                break
        except:
            pass
        time.sleep(1)
        if i % 5 == 0:
            print(f"   Попытка {i+1}/30...")
    else:
        print("❌ Веб-сервер не запустился за 30 секунд")
        print("   Проверьте: docker-compose logs app")
        return False
    
    # Проверяем базу данных
    if not await check_database_connection():
        print("❌ Проблема с базой данных")
        return False
    
    # Создаем тестовых пользователей
    if not await create_test_admin_users():
        print("❌ Не удалось создать тестовых админ-пользователей")
        return False
    
    # Создаем тестовые данные
    if not await create_test_data():
        print("⚠️  Не удалось создать тестовые данные (не критично)")
    
    # Проверяем веб-сервер
    if not check_web_server():
        print("⚠️  Некоторые endpoints недоступны")
    
    print("\n✅ ПОДГОТОВКА ЗАВЕРШЕНА!")
    print_test_instructions()
    
    return True


if __name__ == "__main__":
    # Загружаем переменные из env.test
    import subprocess
    import shlex
    
    print("📝 Используем настройки из env.test")
    
    asyncio.run(main())


