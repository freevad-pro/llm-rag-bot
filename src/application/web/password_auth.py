"""
Сервис классической авторизации через username/password.
Замена для Telegram авторизации.
"""
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from ...domain.entities.admin_user import AdminUser, AdminRole
from ...infrastructure.database.models import AdminUser as AdminUserModel
from ...infrastructure.logging.hybrid_logger import hybrid_logger
from ...infrastructure.notifications.email_service import email_service
from ...config.settings import settings


class PasswordAuthService:
    """Сервис для работы с классической авторизацией"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Хеширование пароля"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Проверка пароля"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    @staticmethod
    def generate_reset_token() -> str:
        """Генерация токена для сброса пароля"""
        return secrets.token_urlsafe(32)
    
    async def authenticate_user(self, session: AsyncSession, username: str, password: str) -> Optional[AdminUser]:
        """Аутентификация пользователя"""
        try:
            # Ищем пользователя по username
            result = await session.execute(
                select(AdminUserModel).where(AdminUserModel.username == username)
            )
            user_model = result.scalar_one_or_none()
            
            if not user_model:
                await hybrid_logger.warning(f"Попытка входа с несуществующим username: {username}")
                return None
            
            if not user_model.is_active:
                await hybrid_logger.warning(f"Попытка входа с деактивированным аккаунтом: {username}")
                return None
            
            # Проверяем пароль
            if not self.verify_password(password, user_model.password_hash):
                await hybrid_logger.warning(f"Неверный пароль для пользователя: {username}")
                return None
            
            # Обновляем время последнего входа
            user_model.last_login = datetime.utcnow()
            session.add(user_model)
            await session.commit()
            
            # Конвертируем в доменную сущность
            return AdminUser(
                id=user_model.id,
                username=user_model.username,
                email=user_model.email,
                role=AdminRole(user_model.role),
                first_name=user_model.first_name,
                last_name=user_model.last_name,
                is_active=user_model.is_active,
                created_at=user_model.created_at,
                last_login=user_model.last_login,
                reset_token=user_model.reset_token,
                reset_token_expires=user_model.reset_token_expires
            )
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка аутентификации: {e}")
            return None
    
    async def get_user_by_id(self, session: AsyncSession, user_id: int) -> Optional[AdminUser]:
        """Получение пользователя по ID"""
        try:
            result = await session.execute(
                select(AdminUserModel).where(AdminUserModel.id == user_id)
            )
            user_model = result.scalar_one_or_none()
            
            if not user_model:
                return None
            
            return AdminUser(
                id=user_model.id,
                username=user_model.username,
                email=user_model.email,
                role=AdminRole(user_model.role),
                first_name=user_model.first_name,
                last_name=user_model.last_name,
                is_active=user_model.is_active,
                created_at=user_model.created_at,
                last_login=user_model.last_login,
                reset_token=user_model.reset_token,
                reset_token_expires=user_model.reset_token_expires
            )
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка получения пользователя: {e}")
            return None
    
    async def change_password(self, session: AsyncSession, user_id: int, new_password: str) -> bool:
        """Смена пароля"""
        try:
            result = await session.execute(
                select(AdminUserModel).where(AdminUserModel.id == user_id)
            )
            user_model = result.scalar_one_or_none()
            
            if not user_model:
                return False
            
            user_model.password_hash = self.hash_password(new_password)
            session.add(user_model)
            await session.commit()
            
            await hybrid_logger.info(f"Пароль изменен для пользователя: {user_model.username}")
            return True
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка смены пароля: {e}")
            return False
    
    async def initiate_password_reset(self, session: AsyncSession, email: str) -> bool:
        """Инициирование сброса пароля"""
        try:
            result = await session.execute(
                select(AdminUserModel).where(AdminUserModel.email == email)
            )
            user_model = result.scalar_one_or_none()
            
            if not user_model:
                # Не сообщаем что email не найден (безопасность)
                await hybrid_logger.warning(f"Попытка сброса пароля для несуществующего email: {email}")
                return True
            
            # Генерируем токен
            reset_token = self.generate_reset_token()
            user_model.reset_token = reset_token
            user_model.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            
            session.add(user_model)
            await session.commit()
            
            # Отправляем email
            await email_service.send_password_reset_email(user_model.email, reset_token)
            
            await hybrid_logger.info(f"Инициирован сброс пароля для: {email}")
            return True
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка инициирования сброса пароля: {e}")
            return False
    
    async def reset_password(self, session: AsyncSession, token: str, new_password: str) -> bool:
        """Сброс пароля по токену"""
        try:
            result = await session.execute(
                select(AdminUserModel).where(AdminUserModel.reset_token == token)
            )
            user_model = result.scalar_one_or_none()
            
            if not user_model:
                return False
            
            # Проверяем срок действия токена
            if not user_model.reset_token_expires or user_model.reset_token_expires < datetime.utcnow():
                await hybrid_logger.warning(f"Попытка использования просроченного токена сброса")
                return False
            
            # Обновляем пароль и очищаем токен
            user_model.password_hash = self.hash_password(new_password)
            user_model.reset_token = None
            user_model.reset_token_expires = None
            
            session.add(user_model)
            await session.commit()
            
            await hybrid_logger.info(f"Пароль сброшен для пользователя: {user_model.username}")
            return True
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка сброса пароля: {e}")
            return False
    
    async def update_profile(self, session: AsyncSession, user_id: int, email: str, first_name: str = None, last_name: str = None) -> bool:
        """Обновление профиля пользователя"""
        try:
            result = await session.execute(
                select(AdminUserModel).where(AdminUserModel.id == user_id)
            )
            user_model = result.scalar_one_or_none()
            
            if not user_model:
                return False
            
            # Проверяем уникальность email (если email изменился)
            if user_model.email != email:
                existing_user = await session.execute(
                    select(AdminUserModel).where(AdminUserModel.email == email)
                )
                if existing_user.scalar_one_or_none():
                    await hybrid_logger.warning(f"Попытка изменения email на уже существующий: {email}")
                    return False
            
            # Обновляем поля
            user_model.email = email
            user_model.first_name = first_name
            user_model.last_name = last_name
            
            session.add(user_model)
            await session.commit()
            
            await hybrid_logger.info(f"Профиль обновлен для пользователя: {user_model.username}")
            return True
            
        except Exception as e:
            await hybrid_logger.error(f"Ошибка обновления профиля: {e}")
            return False
    


# Глобальный экземпляр сервиса
password_auth_service = PasswordAuthService()
