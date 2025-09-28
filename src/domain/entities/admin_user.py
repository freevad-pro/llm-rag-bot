"""
Доменная сущность административного пользователя.
Согласно @vision.md: dataclasses для сущностей без внешних зависимостей.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class AdminRole(Enum):
    """Роли администрирования согласно @vision.md"""
    MANAGER = "MANAGER"  # Базовые права: каталог, промпты, услуги, статистика
    ADMIN = "ADMIN"      # Полные права: + LLM настройки, логи, БД, деплой


@dataclass
class AdminUser:
    """
    Административный пользователь системы.
    Классическая авторизация через username/password.
    """
    username: str
    email: str
    role: AdminRole
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    reset_token: Optional[str] = None
    reset_token_expires: Optional[datetime] = None
    
    @property
    def display_name(self) -> str:
        """Отображаемое имя пользователя"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return self.username
    
    @property
    def is_manager(self) -> bool:
        """Проверка роли менеджера"""
        return self.role == AdminRole.MANAGER
    
    @property
    def is_admin(self) -> bool:
        """Проверка роли администратора"""
        return self.role == AdminRole.ADMIN
    
    def is_administrator(self) -> bool:
        """Проверка роли администратора (альтернативное название)"""
        return self.is_admin
    
    def can_access_logs(self) -> bool:
        """Может ли просматривать логи (только админы)"""
        return self.is_admin
    
    def can_manage_database(self) -> bool:
        """Может ли управлять БД (только админы)"""
        return self.is_admin
    
    def can_switch_llm_provider(self) -> bool:
        """Может ли переключать LLM провайдера (только админы)"""
        return self.is_admin
    
    def can_manage_catalog(self) -> bool:
        """Может ли управлять каталогом (менеджеры и админы)"""
        return self.is_active and (self.is_manager or self.is_admin)
    
    def can_edit_prompts(self) -> bool:
        """Может ли редактировать промпты (менеджеры и админы)"""
        return self.is_active and (self.is_manager or self.is_admin)
    
    def can_manage_services(self) -> bool:
        """Может ли управлять услугами (менеджеры и админы)"""
        return self.is_active and (self.is_manager or self.is_admin)
    
    def can_view_basic_stats(self) -> bool:
        """Может ли просматривать базовую статистику (менеджеры и админы)"""
        return self.is_active and (self.is_manager or self.is_admin)
    
    def can_view_full_stats(self) -> bool:
        """Может ли просматривать полную статистику (только админы)"""
        return self.is_active and self.is_admin
    
    def can_change_password(self) -> bool:
        """Может ли менять пароль (все активные пользователи)"""
        return self.is_active