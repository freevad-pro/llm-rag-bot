"""
Конфигурация для infrastructure слоя.
Перенаправляет импорты на основной config модуль.
"""

# Используем абсолютные импорты вместо относительных
from src.config.settings import settings
from src.config.database import engine, get_db

__all__ = [
    "settings",
    "engine", 
    "get_db"
]
