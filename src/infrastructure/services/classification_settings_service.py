"""
Сервис для управления настройками классификации запросов.
Позволяет гибко настраивать ключевые слова и логику классификации через админку.
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from sqlalchemy.orm import selectinload

from src.infrastructure.database.models import ClassificationSettings, AdminUser


class ClassificationSettingsService:
    """
    Сервис для управления настройками классификации.
    Поддерживает кеширование для мгновенного применения изменений.
    """
    
    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
    
    async def get_active_settings(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Получает активные настройки классификации с кешированием.
        
        Args:
            session: Сессия базы данных
            
        Returns:
            Словарь с настройками классификации
        """
        try:
            # Проверяем кеш
            if self._cache and self._cache_timestamp:
                # Кеш действителен 5 минут
                if (datetime.now() - self._cache_timestamp).seconds < 300:
                    return self._cache
            
            # Загружаем из БД
            query = select(ClassificationSettings).where(
                ClassificationSettings.is_active == True
            ).order_by(ClassificationSettings.created_at.desc()).limit(1)
            
            result = await session.execute(query)
            settings = result.scalar_one_or_none()
            
            if settings:
                settings_dict = self._settings_to_dict(settings)
            else:
                # Создаем настройки по умолчанию
                settings_dict = self._get_default_settings()
            
            # Обновляем кеш
            self._cache = settings_dict
            self._cache_timestamp = datetime.now()
            
            return settings_dict
            
        except Exception as e:
            self._logger.error(f"Ошибка получения настроек классификации: {e}")
            return self._get_default_settings()
    
    async def update_settings(
        self, 
        session: AsyncSession, 
        admin_user_id: int,
        settings_data: Dict[str, Any]
    ) -> bool:
        """
        Обновляет настройки классификации.
        
        Args:
            session: Сессия базы данных
            admin_user_id: ID администратора
            settings_data: Новые настройки
            
        Returns:
            True если обновление успешно
        """
        try:
            # Деактивируем старые настройки
            await session.execute(
                update(ClassificationSettings)
                .where(ClassificationSettings.is_active == True)
                .values(is_active=False)
            )
            
            # Создаем новые настройки
            new_settings = ClassificationSettings(
                enable_fast_classification=settings_data.get("enable_fast_classification", True),
                enable_llm_classification=settings_data.get("enable_llm_classification", True),
                product_keywords=json.dumps(settings_data.get("product_keywords", [])),
                contact_keywords=json.dumps(settings_data.get("contact_keywords", [])),
                company_keywords=json.dumps(settings_data.get("company_keywords", [])),
                availability_phrases=json.dumps(settings_data.get("availability_phrases", [])),
                search_words=json.dumps(settings_data.get("search_words", [])),
                specific_products=json.dumps(settings_data.get("specific_products", [])),
                description=settings_data.get("description", ""),
                created_by=admin_user_id
            )
            
            session.add(new_settings)
            await session.commit()
            
            # Очищаем кеш для принудительного обновления
            self._cache = None
            self._cache_timestamp = None
            
            self._logger.info(f"Настройки классификации обновлены администратором {admin_user_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Ошибка обновления настроек классификации: {e}")
            await session.rollback()
            return False
    
    async def get_settings_history(self, session: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает историю изменений настроек.
        
        Args:
            session: Сессия базы данных
            limit: Максимальное количество записей
            
        Returns:
            Список настроек с метаданными
        """
        try:
            query = select(ClassificationSettings).options(
                selectinload(ClassificationSettings.created_by_user)
            ).order_by(ClassificationSettings.created_at.desc()).limit(limit)
            
            result = await session.execute(query)
            settings_list = result.scalars().all()
            
            return [
                {
                    "id": settings.id,
                    "description": settings.description,
                    "is_active": settings.is_active,
                    "created_at": settings.created_at,
                    "created_by": settings.created_by_user.username if settings.created_by_user else "Unknown",
                    "settings": self._settings_to_dict(settings)
                }
                for settings in settings_list
            ]
            
        except Exception as e:
            self._logger.error(f"Ошибка получения истории настроек: {e}")
            return []
    
    def _settings_to_dict(self, settings: ClassificationSettings) -> Dict[str, Any]:
        """Преобразует модель в словарь."""
        return {
            "enable_fast_classification": settings.enable_fast_classification,
            "enable_llm_classification": settings.enable_llm_classification,
            "product_keywords": json.loads(settings.product_keywords) if settings.product_keywords else [],
            "contact_keywords": json.loads(settings.contact_keywords) if settings.contact_keywords else [],
            "company_keywords": json.loads(settings.company_keywords) if settings.company_keywords else [],
            "availability_phrases": json.loads(settings.availability_phrases) if settings.availability_phrases else [],
            "search_words": json.loads(settings.search_words) if settings.search_words else [],
            "specific_products": json.loads(settings.specific_products) if settings.specific_products else [],
        }
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Возвращает настройки по умолчанию."""
        from src.infrastructure.services.default_classification_settings import DEFAULT_CLASSIFICATION_SETTINGS
        return DEFAULT_CLASSIFICATION_SETTINGS.copy()
    
    def clear_cache(self):
        """Очищает кеш настроек."""
        self._cache = None
        self._cache_timestamp = None

    async def initialize_default_settings(self, session: AsyncSession, admin_user_id: int = 1) -> ClassificationSettings:
        """Инициализирует дефолтные настройки классификации если их нет."""
        # Проверяем, есть ли уже активные настройки
        existing_settings = await self.get_active_settings(session)
        
        if existing_settings and existing_settings.get("id"):
            self._logger.info(f"Настройки классификации уже существуют (ID: {existing_settings['id']})")
            return None
        
        self._logger.info("Создаем дефолтные настройки классификации...")
        
        # Получаем дефолтные настройки
        default_settings = self._get_default_settings()
        
        # Создаем новые настройки
        new_settings = await self.create_settings(
            session=session,
            enable_fast_classification=default_settings["enable_fast_classification"],
            enable_llm_classification=default_settings["enable_llm_classification"],
            product_keywords=default_settings["product_keywords"],
            contact_keywords=default_settings["contact_keywords"],
            company_keywords=default_settings["company_keywords"],
            availability_phrases=default_settings["availability_phrases"],
            search_words=default_settings["search_words"],
            specific_products=default_settings["specific_products"],
            description="Дефолтные настройки классификации (автоматически созданы)",
            created_by_admin_id=admin_user_id,
            is_active=True
        )
        
        self._logger.info(f"Дефолтные настройки классификации созданы (ID: {new_settings.id})")
        return new_settings


# Глобальный экземпляр сервиса
classification_settings_service = ClassificationSettingsService()
