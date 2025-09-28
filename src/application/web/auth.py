"""
Система авторизации админ-панели через Telegram.
Согласно @vision.md: авторизация через Telegram ID с проверкой ролей.
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import unquote

from fastapi import HTTPException, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ...config.settings import settings
from ...domain.entities.admin_user import AdminUser, AdminRole
from ...infrastructure.database.models import AdminUser as AdminUserModel
from ...infrastructure.database.connection import get_session
from ...infrastructure.logging.hybrid_logger import hybrid_logger


security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


class TelegramAuth:
    """
    Авторизация через Telegram Login Widget.
    Проверяет подпись данных от Telegram и создает сессию.
    """
    
    def __init__(self):
        self.bot_token = settings.bot_token
        if not self.bot_token:
            raise ValueError("BOT_TOKEN не настроен для авторизации")
    
    def verify_telegram_data(self, auth_data: Dict[str, Any]) -> bool:
        """
        Проверяет подлинность данных от Telegram Login Widget.
        
        Args:
            auth_data: Данные от Telegram (id, first_name, username, hash, etc.)
            
        Returns:
            True если данные подлинные
        """
        if 'hash' not in auth_data:
            return False
        
        # Извлекаем hash и остальные данные
        received_hash = auth_data.pop('hash')
        
        # Создаем строку для проверки
        data_check_string = '\n'.join([
            f"{key}={value}" 
            for key, value in sorted(auth_data.items())
            if value is not None
        ])
        
        # Создаем секретный ключ из токена бота
        secret_key = hashlib.sha256(self.bot_token.encode()).digest()
        
        # Вычисляем HMAC
        calculated_hash = hmac.new(
            secret_key, 
            data_check_string.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(calculated_hash, received_hash)
    
    def parse_telegram_data(self, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Парсит и валидирует данные от Telegram.
        
        Returns:
            Очищенные данные пользователя
        """
        required_fields = ['id']
        for field in required_fields:
            if field not in auth_data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        # Проверяем время авторизации (не старше 24 часов)
        auth_date = auth_data.get('auth_date')
        if auth_date:
            auth_time = datetime.fromtimestamp(int(auth_date))
            if datetime.now() - auth_time > timedelta(hours=24):
                raise ValueError("Токен авторизации устарел")
        
        return {
            'telegram_id': int(auth_data['id']),
            'telegram_username': auth_data.get('username'),
            'first_name': auth_data.get('first_name'),
            'last_name': auth_data.get('last_name'),
        }


class AdminAuthService:
    """
    Сервис управления авторизацией администраторов.
    """
    
    def __init__(self):
        self.telegram_auth = TelegramAuth()
    
    async def authenticate_telegram_user(
        self, 
        auth_data: Dict[str, Any], 
        session: AsyncSession
    ) -> Optional[AdminUser]:
        """
        Аутентификация пользователя через Telegram данные.
        
        Args:
            auth_data: Данные от Telegram Login Widget
            session: Сессия базы данных
            
        Returns:
            AdminUser если авторизация успешна, None если пользователь не найден
            
        Raises:
            ValueError: Если данные невалидны
            HTTPException: Если пользователь заблокирован
        """
        # Проверяем подпись Telegram
        if not self.telegram_auth.verify_telegram_data(auth_data.copy()):
            raise ValueError("Неверная подпись Telegram")
        
        # Парсим данные
        user_data = self.telegram_auth.parse_telegram_data(auth_data)
        telegram_id = user_data['telegram_id']
        
        # Ищем пользователя в БД
        stmt = select(AdminUserModel).where(AdminUserModel.telegram_id == telegram_id)
        result = await session.execute(stmt)
        admin_user_model = result.scalar_one_or_none()
        
        if not admin_user_model:
            await hybrid_logger.warning(
                f"Попытка входа неавторизованного пользователя: {telegram_id}",
                extra_data={"telegram_id": telegram_id, **user_data}
            )
            return None
        
        # Проверяем активность
        if not admin_user_model.is_active:
            await hybrid_logger.warning(
                f"Попытка входа заблокированного пользователя: {telegram_id}",
                extra_data={"telegram_id": telegram_id, "admin_id": admin_user_model.id}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Аккаунт заблокирован"
            )
        
        # Обновляем время последнего входа
        await session.execute(
            update(AdminUserModel)
            .where(AdminUserModel.id == admin_user_model.id)
            .values(last_login=datetime.utcnow())
        )
        await session.commit()
        
        # Логируем успешный вход
        await hybrid_logger.info(
            f"Успешный вход в админ-панель: {admin_user_model.telegram_username or telegram_id}",
            extra_data={
                "admin_id": admin_user_model.id,
                "telegram_id": telegram_id,
                "role": admin_user_model.role
            }
        )
        
        # Конвертируем в доменную сущность
        return AdminUser(
            id=admin_user_model.id,
            telegram_id=admin_user_model.telegram_id,
            telegram_username=admin_user_model.telegram_username,
            first_name=admin_user_model.first_name,
            last_name=admin_user_model.last_name,
            role=AdminRole(admin_user_model.role),
            is_active=admin_user_model.is_active,
            created_at=admin_user_model.created_at,
            last_login=admin_user_model.last_login,
        )
    
    async def get_user_by_telegram_id(
        self, 
        telegram_id: int, 
        session: AsyncSession
    ) -> Optional[AdminUser]:
        """
        Получает пользователя по Telegram ID.
        """
        stmt = select(AdminUserModel).where(
            AdminUserModel.telegram_id == telegram_id,
            AdminUserModel.is_active == True
        )
        result = await session.execute(stmt)
        admin_user_model = result.scalar_one_or_none()
        
        if not admin_user_model:
            return None
        
        return AdminUser(
            id=admin_user_model.id,
            telegram_id=admin_user_model.telegram_id,
            telegram_username=admin_user_model.telegram_username,
            first_name=admin_user_model.first_name,
            last_name=admin_user_model.last_name,
            role=AdminRole(admin_user_model.role),
            is_active=admin_user_model.is_active,
            created_at=admin_user_model.created_at,
            last_login=admin_user_model.last_login,
        )


# Глобальный экземпляр сервиса авторизации
admin_auth_service = AdminAuthService()


async def get_current_admin_user(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> Optional[AdminUser]:
    """
    Dependency для получения текущего авторизованного администратора.
    Проверяет сессию или токен авторизации.
    """
    # Проверяем сессию
    admin_id = request.session.get('admin_id')
    if admin_id:
        telegram_id = request.session.get('telegram_id')
        if telegram_id:
            return await admin_auth_service.get_user_by_telegram_id(telegram_id, session)
    
    return None


async def require_admin_user(
    current_user: Optional[AdminUser] = Depends(get_current_admin_user)
) -> AdminUser:
    """
    Dependency для требования авторизации.
    Возвращает авторизованного пользователя или 401 ошибку.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация"
        )
    return current_user


async def require_admin_role(
    current_user: AdminUser = Depends(require_admin_user)
) -> AdminUser:
    """
    Dependency для требования роли администратора.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )
    return current_user


async def require_manager_or_admin(
    current_user: AdminUser = Depends(require_admin_user)
) -> AdminUser:
    """
    Dependency для требования роли менеджера или администратора.
    """
    if not (current_user.is_manager or current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    return current_user


