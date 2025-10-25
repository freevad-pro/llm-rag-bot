"""
Конфигурация для infrastructure слоя.
Перенаправляет импорты на основной config модуль.
"""

# Перенаправляем все импорты на основной config модуль
from ...config.settings import settings
from ...config.database import engine, get_db

__all__ = [
    "settings",
    "engine", 
    "get_db"
]
