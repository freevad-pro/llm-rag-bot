#!/usr/bin/env python3
"""
Скрипт для создания первых админ-пользователей.
Запускается один раз для инициализации системы.
"""
import asyncio
import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.infrastructure.database.connection import get_async_session
from src.infrastructure.database.models import AdminUser as AdminUserModel
from src.infrastructure.logging.hybrid_logger import hybrid_logger


async def create_initial_admin_users():
    """
    Создает первых администраторов из переменных окружения.
    """
    # Получаем Telegram IDs из переменных окружения
    admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "")
    manager_ids_str = os.getenv("MANAGER_TELEGRAM_IDS", "")
    
    if not admin_ids_str and not manager_ids_str:
        print("⚠️  Переменные ADMIN_TELEGRAM_IDS и MANAGER_TELEGRAM_IDS не настроены")
        print("   Установите переменные окружения:")
        print("   ADMIN_TELEGRAM_IDS=123456789,987654321")
        print("   MANAGER_TELEGRAM_IDS=111111111,222222222")
        return False
    
    admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()] if admin_ids_str else []
    manager_ids = [int(x.strip()) for x in manager_ids_str.split(",") if x.strip()] if manager_ids_str else []
    
    async for session in get_async_session():
        try:
            created_count = 0
            
            # Создаем администраторов
            for telegram_id in admin_ids:
                # Проверяем, существует ли уже
                stmt = select(AdminUserModel).where(AdminUserModel.telegram_id == telegram_id)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    print(f"✓ Администратор {telegram_id} уже существует")
                    continue
                
                admin_user = AdminUserModel(
                    telegram_id=telegram_id,
                    role="ADMIN",
                    is_active=True
                )
                session.add(admin_user)
                created_count += 1
                print(f"✓ Создан администратор: {telegram_id}")
            
            # Создаем менеджеров
            for telegram_id in manager_ids:
                # Проверяем, существует ли уже
                stmt = select(AdminUserModel).where(AdminUserModel.telegram_id == telegram_id)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    print(f"✓ Менеджер {telegram_id} уже существует")
                    continue
                
                manager_user = AdminUserModel(
                    telegram_id=telegram_id,
                    role="MANAGER",
                    is_active=True
                )
                session.add(manager_user)
                created_count += 1
                print(f"✓ Создан менеджер: {telegram_id}")
            
            if created_count > 0:
                await session.commit()
                print(f"\n🎉 Создано {created_count} новых пользователей")
                await hybrid_logger.info(f"Инициализированы админ-пользователи: {created_count} новых")
            else:
                print("\n✓ Все пользователи уже существуют")
            
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Ошибка при создании пользователей: {e}")
            await hybrid_logger.error(f"Ошибка инициализации админ-пользователей: {e}")
            return False


async def list_admin_users():
    """
    Показывает список всех админ-пользователей.
    """
    async for session in get_async_session():
        try:
            stmt = select(AdminUserModel).order_by(AdminUserModel.created_at)
            result = await session.execute(stmt)
            users = result.scalars().all()
            
            if not users:
                print("📭 Нет админ-пользователей")
                return
            
            print(f"\n👥 Админ-пользователи ({len(users)}):")
            print("-" * 60)
            
            for user in users:
                status = "🟢 Активен" if user.is_active else "🔴 Заблокирован"
                role_icon = "👑" if user.role == "ADMIN" else "👤"
                
                print(f"{role_icon} {user.telegram_id} | {user.role} | {status}")
                if user.telegram_username:
                    print(f"   @{user.telegram_username}")
                if user.first_name or user.last_name:
                    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                    print(f"   {name}")
                if user.last_login:
                    print(f"   Последний вход: {user.last_login.strftime('%d.%m.%Y %H:%M')}")
                print()
                
        except Exception as e:
            print(f"❌ Ошибка при получении списка: {e}")


async def main():
    """Главная функция"""
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        await list_admin_users()
    else:
        print("🚀 Инициализация админ-пользователей...")
        success = await create_initial_admin_users()
        
        if success:
            print("\n📋 Текущие пользователи:")
            await list_admin_users()
            
            print("\n💡 Инструкции:")
            print("1. Теперь вы можете войти в админ-панель по адресу: /admin/")
            print("2. Используйте Telegram для авторизации")
            print("3. Только указанные Telegram ID будут иметь доступ")
        else:
            print("\n❌ Инициализация не удалась")
            sys.exit(1)


if __name__ == "__main__":
    # Загружаем переменные окружения из .env файла если есть
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    asyncio.run(main())


