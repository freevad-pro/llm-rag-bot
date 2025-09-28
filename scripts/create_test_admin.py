#!/usr/bin/env python3
"""
Скрипт для создания тестовых администраторов с классическим логином/паролем.
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


async def create_test_admin_users():
    """
    Создает тестовых администраторов с классическим логином/паролем.
    """
    # Создаем тестовых пользователей для разработки
    test_users = [
        {
            "username": "admin",
            "email": "admin@example.com",
            "password": "admin123",
            "role": "ADMIN",
            "full_name": "Системный администратор"
        },
        {
            "username": "manager",
            "email": "manager@example.com", 
            "password": "manager123",
            "role": "MANAGER",
            "full_name": "Менеджер по продажам"
        }
    ]
    
    async for session in get_async_session():
        try:
            created_count = 0
            
            for user_data in test_users:
                # Проверяем, существует ли уже
                stmt = select(AdminUserModel).where(AdminUserModel.username == user_data["username"])
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if not existing:
                    # Импортируем сервис для хеширования пароля
                    from src.application.web.password_auth import password_auth_service
                    
                    hashed_password = password_auth_service.hash_password(user_data["password"])
                    
                    admin_user = AdminUserModel(
                        username=user_data["username"],
                        email=user_data["email"],
                        password_hash=hashed_password,
                        role=user_data["role"],
                        full_name=user_data["full_name"],
                        is_active=True
                    )
                    session.add(admin_user)
                    created_count += 1
                    print(f"✅ Создан пользователь: {user_data['username']} ({user_data['role']})")
                else:
                    print(f"ℹ️  Пользователь уже существует: {user_data['username']}")
            
            if created_count > 0:
                await session.commit()
                print(f"✅ Создано пользователей: {created_count}")
                print("\n📋 Данные для входа:")
                print("   Администратор: admin / admin123")
                print("   Менеджер: manager / manager123")
            else:
                print("ℹ️  Все пользователи уже существуют")
            
            return True
            
        except Exception as e:
            await session.rollback()
            await hybrid_logger.error(f"Ошибка при создании пользователей: {e}")
            print(f"❌ Ошибка при создании пользователей: {e}")
            return False


async def main():
    """Основная функция"""
    print("🚀 Создание тестовых администраторов...")
    
    try:
        success = await create_test_admin_users()
        
        if success:
            print("✅ Инициализация завершена успешно")
        else:
            print("❌ Инициализация не удалась")
            
        return success
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

