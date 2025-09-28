"""
Сервис управления пользователями админ-панели.
"""
import bcrypt
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.exc import IntegrityError

from ...infrastructure.database.models import AdminUser as AdminUserModel
from ..entities.admin_user import AdminUser, AdminRole


class UserManagementService:
    """Сервис для управления пользователями админ-панели"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_all_users(self) -> List[AdminUser]:
        """Получить всех пользователей"""
        query = select(AdminUserModel).order_by(AdminUserModel.created_at.desc())
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def get_user_by_id(self, user_id: int) -> Optional[AdminUser]:
        """Получить пользователя по ID"""
        query = select(AdminUserModel).where(AdminUserModel.id == user_id)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        if model:
            return self._model_to_entity(model)
        return None
    
    async def get_user_by_username(self, username: str) -> Optional[AdminUser]:
        """Получить пользователя по username"""
        query = select(AdminUserModel).where(AdminUserModel.username == username)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        if model:
            return self._model_to_entity(model)
        return None
    
    async def create_user(
        self,
        username: str,
        password: str,
        email: str,
        role: AdminRole,
        created_by: int,
        is_active: bool = True
    ) -> AdminUser:
        """Создать нового пользователя"""
        # Хешируем пароль
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        new_user = AdminUserModel(
            username=username,
            password_hash=password_hash,
            email=email,
            role=role.value,
            is_active=is_active
        )
        
        self.session.add(new_user)
        
        try:
            await self.session.commit()
            await self.session.refresh(new_user)
            return self._model_to_entity(new_user)
        except IntegrityError as e:
            await self.session.rollback()
            if "username" in str(e):
                raise ValueError("Пользователь с таким именем уже существует")
            elif "email" in str(e):
                raise ValueError("Пользователь с таким email уже существует")
            else:
                raise ValueError("Ошибка создания пользователя")
    
    async def update_user(
        self,
        user_id: int,
        updated_by: int,
        username: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[AdminRole] = None,
        is_active: Optional[bool] = None
    ) -> Optional[AdminUser]:
        """Обновить данные пользователя"""
        update_data = {}
        
        if username is not None:
            update_data["username"] = username
        if email is not None:
            update_data["email"] = email
        if role is not None:
            update_data["role"] = role.value
        if is_active is not None:
            update_data["is_active"] = is_active
        
        query = (
            update(AdminUserModel)
            .where(AdminUserModel.id == user_id)
            .values(**update_data)
        )
        
        try:
            result = await self.session.execute(query)
            await self.session.commit()
            
            if result.rowcount > 0:
                return await self.get_user_by_id(user_id)
            return None
        except IntegrityError as e:
            await self.session.rollback()
            if "username" in str(e):
                raise ValueError("Пользователь с таким именем уже существует")
            elif "email" in str(e):
                raise ValueError("Пользователь с таким email уже существует")
            else:
                raise ValueError("Ошибка обновления пользователя")
    
    async def change_user_password(
        self,
        user_id: int,
        new_password: str,
        updated_by: int
    ) -> bool:
        """Изменить пароль пользователя"""
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        query = (
            update(AdminUserModel)
            .where(AdminUserModel.id == user_id)
            .values(password_hash=password_hash)
        )
        
        result = await self.session.execute(query)
        await self.session.commit()
        
        return result.rowcount > 0
    
    async def toggle_user_status(
        self,
        user_id: int,
        updated_by: int
    ) -> Optional[AdminUser]:
        """Переключить статус пользователя (активный/заблокированный)"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        new_status = not user.is_active
        return await self.update_user(
            user_id=user_id,
            updated_by=updated_by,
            is_active=new_status
        )
    
    async def delete_user(self, user_id: int) -> bool:
        """Удалить пользователя"""
        query = delete(AdminUserModel).where(AdminUserModel.id == user_id)
        result = await self.session.execute(query)
        await self.session.commit()
        
        return result.rowcount > 0
    
    async def can_delete_user(self, user_id: int, current_user_id: int) -> tuple[bool, str]:
        """Проверить, можно ли удалить пользователя"""
        if user_id == current_user_id:
            return False, "Нельзя удалить самого себя"
        
        user = await self.get_user_by_id(user_id)
        if not user:
            return False, "Пользователь не найден"
        
        # Проверяем, есть ли другие администраторы
        if user.role == AdminRole.ADMIN:
            query = select(AdminUserModel).where(
                and_(
                    AdminUserModel.role == AdminRole.ADMIN.value,
                    AdminUserModel.id != user_id,
                    AdminUserModel.is_active == True
                )
            )
            result = await self.session.execute(query)
            other_admins = result.scalars().all()
            
            if len(other_admins) == 0:
                return False, "Нельзя удалить последнего администратора"
        
        return True, ""
    
    async def can_change_role(
        self,
        user_id: int,
        new_role: AdminRole,
        current_user_id: int
    ) -> tuple[bool, str]:
        """Проверить, можно ли изменить роль пользователя"""
        if user_id == current_user_id and new_role == AdminRole.MANAGER:
            return False, "Нельзя понизить свою роль с администратора"
        
        user = await self.get_user_by_id(user_id)
        if not user:
            return False, "Пользователь не найден"
        
        # Если понижаем админа до менеджера, проверяем наличие других админов
        if user.role == AdminRole.ADMIN and new_role == AdminRole.MANAGER:
            query = select(AdminUserModel).where(
                and_(
                    AdminUserModel.role == AdminRole.ADMIN.value,
                    AdminUserModel.id != user_id,
                    AdminUserModel.is_active == True
                )
            )
            result = await self.session.execute(query)
            other_admins = result.scalars().all()
            
            if len(other_admins) == 0:
                return False, "Нельзя понизить последнего администратора"
        
        return True, ""
    
    async def get_user_stats(self) -> dict:
        """Получить статистику пользователей"""
        # Общее количество
        total_query = select(AdminUserModel)
        total_result = await self.session.execute(total_query)
        total_count = len(total_result.scalars().all())
        
        # Активные пользователи
        active_query = select(AdminUserModel).where(AdminUserModel.is_active == True)
        active_result = await self.session.execute(active_query)
        active_count = len(active_result.scalars().all())
        
        # Администраторы
        admin_query = select(AdminUserModel).where(AdminUserModel.role == AdminRole.ADMIN.value)
        admin_result = await self.session.execute(admin_query)
        admin_count = len(admin_result.scalars().all())
        
        # Менеджеры
        manager_query = select(AdminUserModel).where(AdminUserModel.role == AdminRole.MANAGER.value)
        manager_result = await self.session.execute(manager_query)
        manager_count = len(manager_result.scalars().all())
        
        return {
            "total": total_count,
            "active": active_count,
            "blocked": total_count - active_count,
            "admins": admin_count,
            "managers": manager_count
        }
    
    def _model_to_entity(self, model: AdminUserModel) -> AdminUser:
        """Конвертировать модель в сущность"""
        return AdminUser(
            id=model.id,
            username=model.username,
            email=model.email,
            role=AdminRole(model.role),
            is_active=model.is_active,
            created_at=model.created_at,
            first_name=model.first_name,
            last_name=model.last_name,
            last_login=model.last_login,
            reset_token=model.reset_token,
            reset_token_expires=model.reset_token_expires
        )
