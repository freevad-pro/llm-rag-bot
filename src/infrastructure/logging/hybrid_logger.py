"""
Гибридная система логирования согласно @vision.md
- DEBUG → файлы (опционально)
- ERROR, WARNING → PostgreSQL  
- CRITICAL → PostgreSQL + Telegram алерт
- BUSINESS события → PostgreSQL для аналитики
"""
import logging
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.models import SystemLog
from src.config.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class HybridLogger:
    """Гибридная система логирования"""
    
    def __init__(self):
        self._setup_file_logger()
    
    def _setup_file_logger(self) -> None:
        """Настройка консольного логгера"""
        self.file_logger = logging.getLogger("llm_bot")
        self.file_logger.setLevel(logging.DEBUG)
        
        # Консольный handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        # Проверяем, что handler еще не добавлен
        if not self.file_logger.handlers:
            self.file_logger.addHandler(console_handler)
    
    async def log(
        self, 
        level: str, 
        message: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Основной метод логирования"""
        level_upper = level.upper()
        
        # Всегда в консоль
        log_level = getattr(logging, level_upper, logging.INFO)
        self.file_logger.log(log_level, message)
        
        # В БД для ERROR и выше
        if level_upper in ['ERROR', 'WARNING', 'CRITICAL', 'BUSINESS']:
            await self._save_to_db(level_upper, message, metadata)
        
        # TODO: В будущих итерациях добавить Telegram алерты для CRITICAL
    
    async def _save_to_db(
        self, 
        level: str, 
        message: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Сохранение в PostgreSQL"""
        try:
            from ..database.connection import get_session
            async for session in get_session():
                log_entry = SystemLog(
                    level=level,
                    message=message,
                    metadata=json.dumps(metadata) if metadata else None
                )
                session.add(log_entry)
                await session.commit()
                break
        except Exception as e:
            # Не падаем при ошибке логирования
            self.file_logger.error(f"Ошибка сохранения лога в БД: {e}")
    
    async def error(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Логирование ошибок"""
        await self.log("ERROR", message, metadata)
    
    async def warning(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Логирование предупреждений"""
        await self.log("WARNING", message, metadata)
    
    async def critical(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Логирование критических ошибок"""
        await self.log("CRITICAL", message, metadata)
    
    async def business(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Логирование бизнес-событий"""
        await self.log("BUSINESS", message, metadata)
    
    async def info(self, message: str) -> None:
        """Информационное логирование (только в консоль)"""
        self.file_logger.info(message)
    
    async def debug(self, message: str) -> None:
        """Отладочное логирование (только в консоль)"""
        self.file_logger.debug(message)


# Глобальный экземпляр логгера
hybrid_logger = HybridLogger()
