"""
Конфигурация Jinja2 шаблонов с фильтрами.
Централизованная настройка шаблонов для всего приложения.
"""

from fastapi.templating import Jinja2Templates
from .template_filters import TEMPLATE_FILTERS

def create_templates() -> Jinja2Templates:
    """
    Создает настроенный объект Jinja2Templates с фильтрами.
    
    Returns:
        Настроенный объект templates
    """
    templates = Jinja2Templates(directory="src/presentation/templates")
    
    # Регистрируем все фильтры
    for filter_name, filter_func in TEMPLATE_FILTERS.items():
        templates.env.filters[filter_name] = filter_func
    
    return templates

# Глобальный объект templates для использования во всех роутах
templates = create_templates()
