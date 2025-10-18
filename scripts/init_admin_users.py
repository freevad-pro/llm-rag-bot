#!/usr/bin/env python3
"""
Скрипт для создания первых админ-пользователей.
Запускается один раз для инициализации системы.
"""
import asyncio
import sys
import os
from pathlib import Path
import bcrypt

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from src.infrastructure.database.connection import get_session
from src.infrastructure.database.models import AdminUser as AdminUserModel
from src.infrastructure.logging.hybrid_logger import hybrid_logger


async def create_initial_admin_users():
    """
    Создает первых администраторов с классической авторизацией.
    """
    async for session in get_session():
        try:
            created_count = 0
            
            # Проверяем, есть ли уже админы
            result = await session.execute(select(AdminUserModel))
            existing_admin = result.scalar_one_or_none()
            
            if existing_admin:
                print(f"✓ Администратор уже существует: {existing_admin.username}")
                return True
            
            # Создаем администратора
            username = "admin"
            password = "admin123"
            email = "admin@example.com"
            
            # Хешируем пароль
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            admin_user = AdminUserModel(
                username=username,
                email=email,
                password_hash=password_hash,
                role="ADMIN",
                is_active=True,
                first_name="Администратор",
                last_name="Системы"
            )
            
            session.add(admin_user)
            await session.commit()
            created_count += 1
            
            print(f"✓ Создан администратор: {username}")
            print(f"  Логин: {username}")
            print(f"  Пароль: {password}")
            print(f"  Email: {email}")
            
            if created_count > 0:
                print(f"\n🎉 Создано {created_count} новых пользователей")
                await hybrid_logger.info(f"Инициализирован админ-пользователь: {username}")
            
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
    async for session in get_session():
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
                
                print(f"{role_icon} {user.username} | {user.role} | {status}")
                print(f"   Email: {user.email}")
                if user.first_name or user.last_name:
                    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                    print(f"   Имя: {name}")
                print(f"   Создан: {user.created_at.strftime('%d.%m.%Y %H:%M')}")
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
            print("2. Используйте логин 'admin' и пароль 'admin123'")
            print("3. ⚠️  ВАЖНО: Смените пароль после первого входа!")
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


