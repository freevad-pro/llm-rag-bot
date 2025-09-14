"""
Настройки приложения через переменные окружения
"""
import os
from typing import List

# Отключаем телеметрию ChromaDB через переменные окружения
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
os.environ.setdefault("ALLOW_RESET", "true")
# Дополнительное отключение posthog (система телеметрии ChromaDB)
os.environ.setdefault("POSTHOG_DISABLED", "true")
os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "true")


class Settings:
    """Основные настройки приложения"""
    
    def __init__(self):
        # Основные
        self.database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@postgres:5432/catalog_db")
        self.bot_token: str = os.getenv("BOT_TOKEN", "")
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        
        # Режим работы контейнеров
        self.disable_telegram_bot: bool = os.getenv("DISABLE_TELEGRAM_BOT", "false").lower() == "true"
        
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
        self.embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "sentence-transformers")  # openai or sentence-transformers
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        self.embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
        
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
        
        # Настройки поиска
        self.search_min_score: float = float(os.getenv("SEARCH_MIN_SCORE", "0.3"))
        self.search_name_boost: float = float(os.getenv("SEARCH_NAME_BOOST", "0.2"))
        self.search_article_boost: float = float(os.getenv("SEARCH_ARTICLE_BOOST", "0.3"))
        self.search_max_results: int = int(os.getenv("SEARCH_MAX_RESULTS", "10"))
    
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
