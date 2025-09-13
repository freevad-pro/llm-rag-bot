"""
Настройки приложения через переменные окружения
"""
import os
from typing import List


class Settings:
    """Основные настройки приложения"""
    
    def __init__(self):
        # Основные
        self.database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@postgres:5432/catalog_db")
        self.bot_token: str = os.getenv("BOT_TOKEN", "")
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        
        # LLM
        self.default_llm_provider: str = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.yandex_api_key: str = os.getenv("YANDEX_API_KEY", "")
        self.yandex_folder_id: str = os.getenv("YANDEX_FOLDER_ID", "")
        
        # CRM
        self.zoho_token_endpoint: str = os.getenv("ZOHO_TOKEN_ENDPOINT", "")
        
        # Уведомления
        self.manager_telegram_chat_id: str = os.getenv("MANAGER_TELEGRAM_CHAT_ID", "")
        self.admin_telegram_ids: str = os.getenv("ADMIN_TELEGRAM_IDS", "")
        
        # Поиск и эмбеддинги
        self.embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "openai")  # openai or sentence-transformers
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
        
        # Пути
        self.chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "/app/data/chroma")
        self.upload_dir: str = os.getenv("UPLOAD_DIR", "/app/data/uploads")
        
        # Web
        self.webhook_secret: str = os.getenv("WEBHOOK_SECRET", "")
        self.admin_secret_key: str = os.getenv("ADMIN_SECRET_KEY", "")
        
        # SMTP (опционально)
        self.smtp_host: str = os.getenv("SMTP_HOST", "")
        self.smtp_user: str = os.getenv("SMTP_USER", "")
        self.smtp_password: str = os.getenv("SMTP_PASSWORD", "")
        self.manager_emails: str = os.getenv("MANAGER_EMAILS", "")
    
    @property
    def admin_telegram_ids_list(self) -> List[int]:
        """Список ID админов в Telegram"""
        if not self.admin_telegram_ids:
            return []
        return [int(x.strip()) for x in self.admin_telegram_ids.split(",") if x.strip()]
    
    @property
    def manager_emails_list(self) -> List[str]:
        """Список email менеджеров"""
        if not self.manager_emails:
            return []
        return [x.strip() for x in self.manager_emails.split(",") if x.strip()]


# Глобальный экземпляр настроек (lazy initialization)
_settings_instance = None

def get_settings() -> Settings:
    """Получить экземпляр настроек (создается при первом обращении)"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance

# Для обратной совместимости
settings = get_settings()
