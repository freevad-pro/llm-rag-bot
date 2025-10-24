"""
Фабрика LLM провайдеров.
Создает провайдеров по настройкам из БД согласно @vision.md.
"""
import json
import logging
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database.models import LLMSetting
from .providers import LLMProvider, OpenAIProvider, YandexGPTProvider, LLMProviderError
from ...config.settings import settings


class LLMProviderFactory:
    """
    Фабрика для создания LLM провайдеров.
    Читает конфигурацию из БД и создает соответствующего провайдера.
    """
    
    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._providers_cache: Dict[str, LLMProvider] = {}
    
    async def get_active_provider(self, session: AsyncSession) -> LLMProvider:
        """
        Возвращает активного LLM провайдера из БД.
        
        Args:
            session: Сессия базы данных
            
        Returns:
            Активный LLM провайдер
            
        Raises:
            LLMProviderError: Если не найден активный провайдер
        """
        try:
            # Ищем активного провайдера в БД
            query = select(LLMSetting).where(LLMSetting.is_active == True)
            result = await session.execute(query)
            active_setting = result.scalar_one_or_none()
            
            if active_setting:
                # Если есть активный провайдер в БД, создаем его
                self._logger.info(f"Используем активного провайдера из БД: {active_setting.provider}")
                return await self._create_provider(
                    active_setting.provider, 
                    json.loads(active_setting.config)
                )
            else:
                # Иначе используем провайдера по умолчанию из переменных окружения
                self._logger.info(f"Используем провайдера по умолчанию: {settings.default_llm_provider}")
                return await self._create_default_provider()
                
        except Exception as e:
            self._logger.error(f"Ошибка получения активного провайдера: {e}")
            # Fallback на провайдера по умолчанию
            return await self._create_default_provider()
    
    async def _create_default_provider(self) -> LLMProvider:
        """
        Создает провайдера по умолчанию из переменных окружения.
        
        Returns:
            Провайдер по умолчанию
        """
        provider_name = settings.default_llm_provider.lower()
        
        if provider_name == "openai":
            config = {
                "api_key": settings.openai_api_key,
                "model": settings.openai_default_model,
                "timeout": 30
            }
        elif provider_name == "yandex":
            # Для YandexGPT нужны дополнительные переменные
            yandex_api_key = getattr(settings, 'yandex_api_key', '')
            yandex_folder_id = getattr(settings, 'yandex_folder_id', '')
            
            config = {
                "api_key": yandex_api_key,
                "folder_id": yandex_folder_id,
                "model": "yandexgpt",
                "timeout": 30
            }
        else:
            raise LLMProviderError(
                "factory", 
                f"Неподдерживаемый провайдер по умолчанию: {provider_name}"
            )
        
        return await self._create_provider(provider_name, config)
    
    async def _create_provider(self, provider_name: str, config: Dict[str, Any]) -> LLMProvider:
        """
        Создает провайдера по имени и конфигурации.
        
        Args:
            provider_name: Имя провайдера (openai, yandex)
            config: Конфигурация провайдера
            
        Returns:
            Созданный провайдер
        """
        cache_key = f"{provider_name}_{hash(str(sorted(config.items())))}"
        
        # Проверяем кэш
        if cache_key in self._providers_cache:
            self._logger.debug(f"Возвращаем провайдера из кэша: {provider_name}")
            return self._providers_cache[cache_key]
        
        # Создаем нового провайдера
        provider_name_lower = provider_name.lower()
        
        if provider_name_lower == "openai":
            provider = OpenAIProvider(config)
        elif provider_name_lower == "yandex":
            provider = YandexGPTProvider(config)
        else:
            raise LLMProviderError(
                "factory",
                f"Неподдерживаемый провайдер: {provider_name}"
            )
        
        # Кэшируем провайдера
        self._providers_cache[cache_key] = provider
        
        self._logger.info(f"Создан новый провайдер: {provider_name}")
        return provider
    
    async def get_provider_by_name(
        self, 
        provider_name: str, 
        session: AsyncSession
    ) -> Optional[LLMProvider]:
        """
        Возвращает провайдера по имени из БД.
        
        Args:
            provider_name: Имя провайдера
            session: Сессия базы данных
            
        Returns:
            Провайдер или None если не найден
        """
        try:
            query = select(LLMSetting).where(LLMSetting.provider == provider_name)
            result = await session.execute(query)
            setting = result.scalar_one_or_none()
            
            if setting:
                return await self._create_provider(
                    setting.provider,
                    json.loads(setting.config)
                )
            
            return None
            
        except Exception as e:
            self._logger.error(f"Ошибка получения провайдера {provider_name}: {e}")
            return None
    
    async def health_check_all_providers(self, session: AsyncSession) -> Dict[str, bool]:
        """
        Проверяет здоровье всех настроенных провайдеров.
        
        Args:
            session: Сессия базы данных
            
        Returns:
            Словарь {provider_name: is_healthy}
        """
        health_status = {}
        
        try:
            # Получаем всех провайдеров из БД
            query = select(LLMSetting)
            result = await session.execute(query)
            settings_list = result.scalars().all()
            
            for setting in settings_list:
                try:
                    provider = await self._create_provider(
                        setting.provider,
                        json.loads(setting.config)
                    )
                    
                    is_healthy = await provider.is_healthy()
                    health_status[setting.provider] = is_healthy
                    
                except Exception as e:
                    self._logger.error(f"Ошибка health check для {setting.provider}: {e}")
                    health_status[setting.provider] = False
            
            # Также проверяем провайдера по умолчанию
            try:
                default_provider = await self._create_default_provider()
                is_healthy = await default_provider.is_healthy()
                health_status[f"default_{settings.default_llm_provider}"] = is_healthy
            except Exception as e:
                self._logger.error(f"Ошибка health check для провайдера по умолчанию: {e}")
                health_status[f"default_{settings.default_llm_provider}"] = False
            
        except Exception as e:
            self._logger.error(f"Ошибка health check всех провайдеров: {e}")
        
        return health_status
    
    def clear_cache(self) -> None:
        """Очищает кэш провайдеров."""
        self._providers_cache.clear()
        self._logger.info("Кэш провайдеров очищен")


# Глобальный экземпляр фабрики
llm_factory = LLMProviderFactory()
