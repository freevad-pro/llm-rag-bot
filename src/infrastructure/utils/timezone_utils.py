"""
Утилиты для работы с временными зонами.
Обеспечивает единообразное отображение московского времени на всех страницах.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union
from .datetime_config import (
    DEFAULT_TIMEZONE, 
    TIMEZONE_LABEL, 
    get_datetime_format,
    get_timezone_label
)

# Используем настройки из конфигурации
MOSCOW_TZ = DEFAULT_TIMEZONE

def to_moscow_time(dt: Optional[Union[datetime, str]]) -> Optional[datetime]:
    """
    Преобразует datetime в московское время.
    
    Args:
        dt: Datetime объект, строка ISO формата или None
        
    Returns:
        Datetime в московском времени или None
    """
    if dt is None:
        return None
    
    # Если получили строку, парсим её
    if isinstance(dt, str):
        try:
            # Пытаемся распарсить ISO формат
            if 'T' in dt:
                # Формат 2025-09-28T09:34:19.387118
                if '.' in dt:
                    dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                else:
                    dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            else:
                # Другие форматы
                dt = datetime.fromisoformat(dt)
        except (ValueError, AttributeError):
            return None
    
    # Если datetime без timezone, считаем что это UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Преобразуем в московское время
    moscow_dt = dt.astimezone(MOSCOW_TZ)
    return moscow_dt

def format_moscow_datetime(dt: Optional[Union[datetime, str]], include_seconds: bool = False) -> str:
    """
    Форматирует datetime в московское время с подписью.
    
    Args:
        dt: Datetime объект
        include_seconds: Включать ли секунды в формат
        
    Returns:
        Отформатированная строка времени с подписью "мск"
    """
    if dt is None:
        return "Не указано"
    
    moscow_dt = to_moscow_time(dt)
    if moscow_dt is None:
        return "Не указано"
    
    if include_seconds:
        time_format = get_datetime_format("full_datetime_seconds")
    else:
        time_format = get_datetime_format("full_datetime")
    
    formatted_time = moscow_dt.strftime(time_format)
    timezone_label = get_timezone_label()
    return f"{formatted_time} {timezone_label}"

def format_moscow_date(dt: Optional[Union[datetime, str]]) -> str:
    """
    Форматирует только дату в московском времени.
    
    Args:
        dt: Datetime объект
        
    Returns:
        Отформатированная дата
    """
    if dt is None:
        return "Не указано"
    
    moscow_dt = to_moscow_time(dt)
    if moscow_dt is None:
        return "Не указано"
    
    date_format = get_datetime_format("date_only")
    return moscow_dt.strftime(date_format)

def format_moscow_time_only(dt: Optional[Union[datetime, str]]) -> str:
    """
    Форматирует только время в московской зоне.
    
    Args:
        dt: Datetime объект
        
    Returns:
        Отформатированное время с подписью "мск"
    """
    if dt is None:
        return "Не указано"
    
    moscow_dt = to_moscow_time(dt)
    if moscow_dt is None:
        return "Не указано"
    
    time_format = get_datetime_format("time_only")
    formatted_time = moscow_dt.strftime(time_format)
    timezone_label = get_timezone_label()
    return f"{formatted_time} {timezone_label}"

def get_current_moscow_time() -> datetime:
    """
    Возвращает текущее московское время.
    
    Returns:
        Текущий datetime в московской зоне
    """
    return datetime.now(MOSCOW_TZ)
