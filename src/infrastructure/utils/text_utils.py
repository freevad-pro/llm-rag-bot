"""
Утилиты для работы с текстом.
Включает функции для безопасной обработки пользовательского ввода.
"""


def escape_braces(text: str) -> str:
    """
    Экранирует фигурные скобки в тексте для безопасного использования с str.format().
    
    Заменяет:
    - { на {{
    - } на }}
    
    Args:
        text: Исходный текст
        
    Returns:
        Текст с экранированными фигурными скобками
        
    Example:
        >>> escape_braces("Найди товар {артикул}")
        'Найди товар {{артикул}}'
        
        >>> escape_braces("Цена: {price} руб.")
        'Цена: {{price}} руб.'
    """
    if not isinstance(text, str):
        return str(text)
    
    return text.replace("{", "{{").replace("}", "}}")


def safe_format(template: str, **kwargs) -> str:
    """
    Безопасное форматирование строки с автоматическим экранированием пользовательских данных.
    
    Экранирует фигурные скобки во всех переданных значениях перед форматированием.
    
    Args:
        template: Шаблон строки с плейсхолдерами
        **kwargs: Значения для подстановки
        
    Returns:
        Отформатированная строка
        
    Example:
        >>> template = "Запрос: {query}, Результат: {result}"
        >>> safe_format(template, query="Найди {товар}", result="OK")
        'Запрос: Найди {{товар}}, Результат: OK'
    """
    # Экранируем все значения
    escaped_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, str):
            escaped_kwargs[key] = escape_braces(value)
        else:
            escaped_kwargs[key] = value
    
    return template.format(**escaped_kwargs)
