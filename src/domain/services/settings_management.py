"""
Сервис управления настройками системы.
Работает с переменными окружения (.env) и настройками БД.
"""
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from ...infrastructure.database.models import LLMSetting, Prompt, CompanyService, ServiceCategory
from ...config.settings import Settings


class SettingsCategory:
    """Категория настроек с метаданными"""
    
    def __init__(self, name: str, title: str, icon: str, description: str):
        self.name = name
        self.title = title
        self.icon = icon
        self.description = description


class SettingItem:
    """Элемент настройки с метаданными"""
    
    def __init__(
        self,
        key: str,
        value: Any,
        title: str,
        description: str = "",
        setting_type: str = "text",  # text, password, number, boolean, select
        source: str = "env",  # env, db
        restart_required: bool = False,
        is_sensitive: bool = False,
        options: Optional[List[str]] = None,
        validation_pattern: Optional[str] = None
    ):
        self.key = key
        self.value = value
        self.title = title
        self.description = description
        self.setting_type = setting_type
        self.source = source
        self.restart_required = restart_required
        self.is_sensitive = is_sensitive
        self.options = options or []
        self.validation_pattern = validation_pattern


class SettingsManagementService:
    """
    Сервис управления настройками системы.
    Объединяет настройки из .env файлов и базы данных.
    """
    
    def __init__(self):
        self.settings = Settings()
        self._env_file_path = Path(".env")
        
        # Определение категорий настроек
        self.categories = {
            "system": SettingsCategory(
                "system", "🔧 Системные настройки", "bi-gear",
                "Основные параметры системы и режим работы"
            ),
            "llm": SettingsCategory(
                "llm", "🤖 LLM и AI", "bi-robot",
                "Настройки языковых моделей и искусственного интеллекта"
            ),
            "search": SettingsCategory(
                "search", "🔍 Поиск и индексация", "bi-search",
                "Параметры поиска по каталогу и векторных вычислений"
            ),
            "notifications": SettingsCategory(
                "notifications", "📧 Уведомления", "bi-bell",
                "Настройки Telegram и email уведомлений"
            ),
            "integrations": SettingsCategory(
                "integrations", "🔗 Интеграции", "bi-link-45deg",
                "Подключения к внешним сервисам и API"
            ),
            "storage": SettingsCategory(
                "storage", "📁 Пути и хранилище", "bi-folder",
                "Настройки путей к файлам и директориям"
            ),
            "security": SettingsCategory(
                "security", "🛡️ Безопасность", "bi-shield-lock",
                "Ключи доступа, токены и секреты"
            ),
            "cost_control": SettingsCategory(
                "cost_control", "💰 Управление расходами на AI", "bi-cash-coin",
                "Лимиты токенов, контроль расходов и алерты"
            )
        }
    
    def get_environment(self) -> Tuple[str, str]:
        """
        Определяет текущую среду выполнения.
        
        Returns:
            Tuple[env_name, env_color] - название среды и цвет для UI
        """
        env = os.getenv("ENVIRONMENT", "").lower()
        
        if env in ["development", "dev"]:
            return "Development", "success"
        elif env in ["testing", "test"]:
            return "Testing", "warning"
        elif env in ["production", "prod"]:
            return "Production", "danger"
        else:
            # Определяем по другим признакам
            if self.settings.debug:
                return "Development", "success"
            elif "test" in self.settings.database_url.lower():
                return "Testing", "warning"
            else:
                return "Production", "danger"
    
    async def get_all_settings(self, session: AsyncSession) -> Dict[str, List[SettingItem]]:
        """
        Получает все настройки системы, сгруппированные по категориям.
        
        Args:
            session: Сессия базы данных
            
        Returns:
            Словарь настроек по категориям
        """
        settings_by_category = {}
        
        # Системные настройки
        settings_by_category["system"] = [
            SettingItem(
                "DATABASE_URL", self.settings.database_url,
                "URL базы данных", "Строка подключения к PostgreSQL",
                "text", "env", True, True
            ),
            SettingItem(
                "DEBUG", self.settings.debug,
                "Режим отладки", "Включает детальное логирование",
                "boolean", "env", True
            ),
            SettingItem(
                "LOG_LEVEL", self.settings.log_level,
                "Уровень логирования", "Минимальный уровень записываемых логов",
                "select", "env", True, False, ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            ),
            SettingItem(
                "DISABLE_TELEGRAM_BOT", self.settings.disable_telegram_bot,
                "Отключить Telegram бота", "Запускать только веб-интерфейс",
                "boolean", "env", True
            )
        ]
        
        # LLM настройки
        llm_settings = await self._get_llm_settings(session)
        settings_by_category["llm"] = [
            SettingItem(
                "DEFAULT_LLM_PROVIDER", self.settings.default_llm_provider,
                "LLM провайдер по умолчанию", "Используется при отсутствии настроек в БД",
                "select", "env", True, False, ["openai", "yandexgpt"]
            ),
            SettingItem(
                "OPENAI_API_KEY", self.settings.openai_api_key,
                "OpenAI API ключ", "Ключ для доступа к GPT моделям",
                "password", "env", True, True
            ),
            SettingItem(
                "YANDEX_API_KEY", self.settings.yandex_api_key,
                "Yandex API ключ", "Ключ для доступа к YandexGPT",
                "password", "env", True, True
            ),
            SettingItem(
                "YANDEX_FOLDER_ID", self.settings.yandex_folder_id,
                "Yandex Folder ID", "ID папки в Yandex Cloud",
                "text", "env", True, True
            ),
            SettingItem(
                "OPENAI_DEFAULT_MODEL", self.settings.openai_default_model,
                "OpenAI модель по умолчанию", "Модель OpenAI для генерации ответов",
                "select", "env", True, False, self.settings.openai_available_models
            ),
            SettingItem(
                "YANDEX_DEFAULT_MODEL", self.settings.yandex_default_model,
                "YandexGPT модель по умолчанию", "Модель YandexGPT для генерации ответов",
                "select", "env", True, False, self.settings.yandex_available_models
            )
        ] + llm_settings
        
        # Поиск и индексация
        settings_by_category["search"] = [
            SettingItem(
                "EMBEDDING_PROVIDER", self.settings.embedding_provider,
                "Провайдер эмбеддингов", "Сервис для векторизации текста",
                "select", "env", True, False, ["openai", "sentence-transformers"]
            ),
            SettingItem(
                "EMBEDDING_MODEL", self.settings.embedding_model,
                "Модель эмбеддингов", "Конкретная модель для векторизации",
                "text", "env", True
            ),
            SettingItem(
                "EMBEDDING_BATCH_SIZE", self.settings.embedding_batch_size,
                "Размер батча эмбеддингов", "Количество текстов для обработки за раз",
                "number", "env", True
            ),
            SettingItem(
                "SEARCH_MIN_SCORE", self.settings.search_min_score,
                "Минимальный score поиска", "Порог релевантности результатов (0.0-1.0)",
                "number", "env", False
            ),
            SettingItem(
                "SEARCH_NAME_BOOST", self.settings.search_name_boost,
                "Boost названия товара", "Дополнительный вес совпадений в названии",
                "number", "env", False
            ),
            SettingItem(
                "SEARCH_ARTICLE_BOOST", self.settings.search_article_boost,
                "Boost артикула", "Дополнительный вес совпадений в артикуле",
                "number", "env", False
            ),
            SettingItem(
                "SEARCH_MAX_RESULTS", self.settings.search_max_results,
                "Максимум результатов", "Максимальное количество результатов поиска",
                "number", "env", False
            )
        ]
        
        # Уведомления
        settings_by_category["notifications"] = [
            SettingItem(
                "BOT_TOKEN", self.settings.bot_token,
                "Telegram Bot Token", "Токен для работы с Telegram API",
                "password", "env", True, True
            ),
            SettingItem(
                "MANAGER_TELEGRAM_CHAT_ID", self.settings.manager_telegram_chat_id,
                "Chat ID менеджеров", "ID чата для уведомлений о лидах",
                "text", "env", False, True
            ),
            SettingItem(
                "ADMIN_TELEGRAM_IDS", self.settings.admin_telegram_ids,
                "ID администраторов", "Список ID администраторов через запятую",
                "text", "env", False, True
            ),
            SettingItem(
                "SMTP_HOST", self.settings.smtp_host,
                "SMTP сервер", "Адрес SMTP сервера для отправки email",
                "text", "env", False
            ),
            SettingItem(
                "SMTP_USER", self.settings.smtp_user,
                "SMTP пользователь", "Логин для SMTP аутентификации",
                "text", "env", False
            ),
            SettingItem(
                "SMTP_PASSWORD", self.settings.smtp_password,
                "SMTP пароль", "Пароль для SMTP аутентификации",
                "password", "env", False, True
            ),
            SettingItem(
                "MANAGER_EMAILS", self.settings.manager_emails,
                "Email менеджеров", "Список email для уведомлений через запятую",
                "text", "env", False
            )
        ]
        
        # Интеграции
        settings_by_category["integrations"] = [
            SettingItem(
                "ZOHO_TOKEN_ENDPOINT", self.settings.zoho_token_endpoint,
                "Zoho Token Endpoint", "URL для получения токенов Zoho API",
                "text", "env", False
            )
        ]
        
        # Пути и хранилище
        settings_by_category["storage"] = [
            SettingItem(
                "CHROMA_PERSIST_DIR", self.settings.chroma_persist_dir,
                "Директория Chroma DB", "Путь для хранения векторной базы данных",
                "text", "env", True
            ),
            SettingItem(
                "UPLOAD_DIR", self.settings.upload_dir,
                "Директория загрузок", "Путь для сохранения загруженных файлов",
                "text", "env", True
            )
        ]
        
        # Безопасность
        settings_by_category["security"] = [
            SettingItem(
                "WEBHOOK_SECRET", self.settings.webhook_secret,
                "Webhook Secret", "Секретный ключ для защиты webhook'ов от внешних сервисов (необязательно)",
                "password", "env", True, True
            ),
            SettingItem(
                "ADMIN_SECRET_KEY", self.settings.admin_secret_key,
                "Admin Secret Key", "Ключ для шифрования сессий админ-панели (генерируется автоматически)",
                "password", "env", True, True
            )
        ]
        
        # Управление расходами на AI
        settings_by_category["cost_control"] = [
            SettingItem(
                "MONTHLY_TOKEN_LIMIT", str(self.settings.monthly_token_limit),
                "Месячный лимит токенов", "Максимальное количество токенов в месяц",
                "number", "env", True, False
            ),
            SettingItem(
                "MONTHLY_COST_LIMIT_USD", str(self.settings.monthly_cost_limit_usd),
                "Месячный лимит расходов (USD)", "Максимальная сумма расходов в месяц",
                "number", "env", True, False
            ),
            SettingItem(
                "COST_ALERT_THRESHOLD", str(self.settings.cost_alert_threshold),
                "Порог алерта", "При каком проценте лимита отправлять алерт (0.1-1.0)",
                "number", "env", True, False
            ),
            SettingItem(
                "AUTO_DISABLE_ON_LIMIT", str(self.settings.auto_disable_on_limit).lower(),
                "Автоотключение при превышении", "Отключать бота при превышении лимитов",
                "boolean", "env", True, False, ["true", "false"]
            ),
            SettingItem(
                "COST_ALERT_ENABLED", str(self.settings.cost_alert_enabled).lower(),
                "Алерты включены", "Отправлять уведомления о расходах",
                "boolean", "env", True, False, ["true", "false"]
            ),
            SettingItem(
                "WEEKLY_USAGE_REPORT", str(self.settings.weekly_usage_report).lower(),
                "Еженедельные отчеты", "Отправлять еженедельную статистику использования",
                "boolean", "env", True, False, ["true", "false"]
            )
        ]
        
        return settings_by_category
    
    async def _get_llm_settings(self, session: AsyncSession) -> List[SettingItem]:
        """Получает настройки LLM из базы данных"""
        query = select(LLMSetting).order_by(LLMSetting.created_at.desc())
        result = await session.execute(query)
        llm_settings = result.scalars().all()
        
        settings_list = []
        for setting in llm_settings:
            settings_list.append(SettingItem(
                f"llm_setting_{setting.id}",
                f"{setting.provider} ({'активен' if setting.is_active else 'неактивен'})",
                f"LLM настройка: {setting.provider}",
                f"Конфигурация провайдера {setting.provider}",
                "text", "db", False
            ))
        
        return settings_list
    
    def mask_sensitive_value(self, value: str) -> str:
        """
        Маскирует чувствительные данные для отображения.
        
        Args:
            value: Исходное значение
            
        Returns:
            Замаскированное значение
        """
        if not value or len(value) < 4:
            return "••••••••"
        
        # Показываем первые 4 символа и маскируем остальное
        return value[:4] + "•" * (len(value) - 4)
    
    async def update_env_setting(self, key: str, value: str) -> bool:
        """
        Обновляет настройку в .env файле.
        
        Args:
            key: Ключ настройки
            value: Новое значение
            
        Returns:
            True если успешно обновлено
        """
        try:
            if not self._env_file_path.exists():
                # Создаем .env файл если его нет
                self._env_file_path.touch()
            
            # Читаем текущий .env файл
            lines = []
            if self._env_file_path.exists():
                with open(self._env_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            
            # Ищем существующую настройку
            key_found = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    key_found = True
                    break
            
            # Если настройка не найдена, добавляем в конец
            if not key_found:
                lines.append(f"{key}={value}\n")
            
            # Записываем обратно в файл
            with open(self._env_file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return True
            
        except Exception as e:
            print(f"Ошибка обновления .env: {e}")
            return False
    
    def validate_setting(self, key: str, value: str, setting_type: str) -> Tuple[bool, str]:
        """
        Валидирует значение настройки.
        
        Args:
            key: Ключ настройки
            value: Значение для валидации
            setting_type: Тип настройки
            
        Returns:
            Tuple[is_valid, error_message]
        """
        if setting_type == "boolean":
            if value.lower() not in ["true", "false", "1", "0", "yes", "no"]:
                return False, "Значение должно быть true/false"
        
        elif setting_type == "number":
            try:
                float(value)
            except ValueError:
                return False, "Значение должно быть числом"
        
        elif key == "DATABASE_URL":
            if not value.startswith(("postgresql://", "postgresql+asyncpg://")):
                return False, "URL должен начинаться с postgresql:// или postgresql+asyncpg://"
        
        elif key == "SEARCH_MIN_SCORE":
            try:
                score = float(value)
                if not 0.0 <= score <= 1.0:
                    return False, "Значение должно быть от 0.0 до 1.0"
            except ValueError:
                return False, "Значение должно быть числом от 0.0 до 1.0"
        
        return True, ""
