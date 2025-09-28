"""
Фильтры для Jinja2 шаблонов.
Обеспечивает единообразное форматирование времени и других данных.
"""

from datetime import datetime
from ..infrastructure.utils.timezone_utils import (
    format_moscow_datetime,
    format_moscow_date,
    format_moscow_time_only
)

def moscow_datetime(dt, include_seconds=False):
    """
    Фильтр для форматирования datetime в московское время.
    Использование: {{ created_at | moscow_datetime }}
    """
    return format_moscow_datetime(dt, include_seconds=include_seconds)

def moscow_date(dt):
    """
    Фильтр для форматирования только даты.
    Использование: {{ created_at | moscow_date }}
    """
    return format_moscow_date(dt)

def moscow_time(dt):
    """
    Фильтр для форматирования только времени.
    Использование: {{ created_at | moscow_time }}
    """
    return format_moscow_time_only(dt)

def filesize(bytes_size):
    """
    Фильтр для форматирования размера файла.
    Использование: {{ file_size | filesize }}
    """
    if not bytes_size:
        return "0 Б"
    
    try:
        size = float(bytes_size)
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size < 1024.0:
                if unit == 'Б':
                    return f"{int(size)} {unit}"
                else:
                    return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} ТБ"
    except (ValueError, TypeError):
        return "0 Б"

def number_format(number):
    """
    Фильтр для форматирования чисел с разделителями тысяч.
    Использование: {{ products_count | number_format }}
    """
    if number is None:
        return "0"
    
    try:
        return f"{int(number):,}".replace(',', ' ')
    except (ValueError, TypeError):
        return str(number)

# Словарь всех фильтров для регистрации в приложении
TEMPLATE_FILTERS = {
    'moscow_datetime': moscow_datetime,
    'moscow_date': moscow_date,
    'moscow_time': moscow_time,
    'filesize': filesize,
    'number_format': number_format,
}
