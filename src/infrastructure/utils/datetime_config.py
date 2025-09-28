"""
Централизованная конфигурация форматирования даты и времени.
Позволяет легко изменять форматы отображения времени во всем приложении.
"""

from datetime import timezone, timedelta

# Конфигурация временной зоны
DEFAULT_TIMEZONE = timezone(timedelta(hours=3))  # Московское время UTC+3
TIMEZONE_LABEL = "мск"

# Форматы отображения времени
# Эти форматы можно легко изменить для всего приложения
DATETIME_FORMATS = {
    # Полные форматы даты и времени
    "full_datetime": "%d.%m.%Y %H:%M",        # 28.09.2025 12:34
    "full_datetime_seconds": "%d.%m.%Y %H:%M:%S",  # 28.09.2025 12:34:56
    
    # Только дата
    "date_only": "%d.%m.%Y",                  # 28.09.2025
    "date_short": "%d.%m",                    # 28.09
    
    # Только время
    "time_only": "%H:%M",                     # 12:34
    "time_seconds": "%H:%M:%S",               # 12:34:56
    
    # Специальные форматы
    "month_year": "%m.%Y",                    # 09.2025
    "day_month": "%d %B",                     # 28 сентября
}

# Альтернативные конфигурации для будущего использования
ALTERNATIVE_CONFIGS = {
    "iso_format": {
        "full_datetime": "%Y-%m-%d %H:%M",
        "date_only": "%Y-%m-%d",
        "time_only": "%H:%M",
        "timezone_label": "UTC+3"
    },
    
    "us_format": {
        "full_datetime": "%m/%d/%Y %I:%M %p",
        "date_only": "%m/%d/%Y",
        "time_only": "%I:%M %p",
        "timezone_label": "MSK"
    },
    
    "european_format": {
        "full_datetime": "%d.%m.%Y %H:%M",
        "date_only": "%d.%m.%Y",
        "time_only": "%H:%M",
        "timezone_label": "мск"
    }
}

def get_datetime_format(format_type: str = "full_datetime") -> str:
    """
    Получает формат даты/времени по типу.
    
    Args:
        format_type: Тип формата из DATETIME_FORMATS
        
    Returns:
        Строка формата для strftime
    """
    return DATETIME_FORMATS.get(format_type, DATETIME_FORMATS["full_datetime"])

def get_timezone_label() -> str:
    """
    Получает метку временной зоны.
    
    Returns:
        Строка с меткой временной зоны
    """
    return TIMEZONE_LABEL

def switch_config(config_name: str) -> bool:
    """
    Переключает на альтернативную конфигурацию.
    В будущем можно использовать для смены форматов.
    
    Args:
        config_name: Имя конфигурации из ALTERNATIVE_CONFIGS
        
    Returns:
        True если конфигурация переключена, False если не найдена
    """
    if config_name in ALTERNATIVE_CONFIGS:
        config = ALTERNATIVE_CONFIGS[config_name]
        # В будущем здесь можно обновлять глобальные переменные
        # или сохранять настройки в базе/конфиге
        return True
    return False

# FUTURE FEATURE: Пользовательское время
# ===========================================
# В будущем можно добавить функциональность для отображения времени
# в часовом поясе пользователя:
#
# 1. Сохранять timezone пользователя в браузере (JavaScript)
# 2. Передавать его в backend через HTTP заголовки
# 3. Использовать для форматирования времени вместо московского
# 
# Примерная структура:
# def format_user_datetime(dt, user_timezone='Europe/Moscow'):
#     user_tz = pytz.timezone(user_timezone)
#     user_dt = dt.astimezone(user_tz)
#     return user_dt.strftime(get_datetime_format())
# 
# JavaScript для получения timezone пользователя:
# const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
# 
# Это позволит показывать время в локальной зоне каждого пользователя
# без изменения основной архитектуры форматирования.
