"""
Тесты для утилит работы с текстом.
Проверяют корректное экранирование фигурных скобок.
"""
import pytest

from src.infrastructure.utils.text_utils import escape_braces, safe_format


class TestEscapeBraces:
    """Тесты для функции escape_braces."""
    
    def test_escape_single_braces(self):
        """Тест экранирования одиночных фигурных скобок."""
        text = "Найди товар {артикул}"
        result = escape_braces(text)
        assert result == "Найди товар {{артикул}}"
    
    def test_escape_multiple_braces(self):
        """Тест экранирования множественных фигурных скобок."""
        text = "Цена: {price} руб., скидка: {discount}%"
        result = escape_braces(text)
        assert result == "Цена: {{price}} руб., скидка: {{discount}}%"
    
    def test_escape_nested_braces(self):
        """Тест экранирования вложенных фигурных скобок."""
        text = "Объект: {data: {value}}"
        result = escape_braces(text)
        assert result == "Объект: {{data: {{value}}}}"
    
    def test_escape_empty_braces(self):
        """Тест экранирования пустых фигурных скобок."""
        text = "Пустые скобки: {}"
        result = escape_braces(text)
        assert result == "Пустые скобки: {{}}"
    
    def test_no_braces(self):
        """Тест текста без фигурных скобок."""
        text = "Обычный текст без скобок"
        result = escape_braces(text)
        assert result == text
    
    def test_empty_string(self):
        """Тест пустой строки."""
        result = escape_braces("")
        assert result == ""
    
    def test_non_string_input(self):
        """Тест обработки не-строковых значений."""
        result = escape_braces(123)
        assert result == "123"
        
        result = escape_braces(None)
        assert result == "None"


class TestSafeFormat:
    """Тесты для функции safe_format."""
    
    def test_safe_format_with_braces_in_value(self):
        """Тест безопасного форматирования с фигурными скобками в значении."""
        template = "Запрос: {query}, Результат: {result}"
        result = safe_format(template, query="Найди {товар}", result="OK")
        assert result == "Запрос: Найди {{товар}}, Результат: OK"
    
    def test_safe_format_multiple_braces(self):
        """Тест с множественными фигурными скобками."""
        template = "Пользователь: {user}, Запрос: {query}"
        result = safe_format(template, user="admin", query="SELECT * FROM {table}")
        assert result == "Пользователь: admin, Запрос: SELECT * FROM {{table}}"
    
    def test_safe_format_no_braces(self):
        """Тест без фигурных скобок в значениях."""
        template = "Пользователь: {user}, Запрос: {query}"
        result = safe_format(template, user="admin", query="SELECT * FROM users")
        assert result == "Пользователь: admin, Запрос: SELECT * FROM users"
    
    def test_safe_format_non_string_values(self):
        """Тест с не-строковыми значениями."""
        template = "ID: {id}, Активен: {active}, Цена: {price}"
        result = safe_format(template, id=123, active=True, price=99.99)
        assert result == "ID: 123, Активен: True, Цена: 99.99"
    
    def test_safe_format_mixed_values(self):
        """Тест со смешанными типами значений."""
        template = "Товар: {name}, Цена: {price}, Описание: {desc}"
        result = safe_format(
            template, 
            name="Товар {премиум}", 
            price=1000, 
            desc="Описание с {параметрами}"
        )
        assert result == "Товар: Товар {{премиум}}, Цена: 1000, Описание: Описание с {{параметрами}}"


class TestRealWorldScenarios:
    """Тесты реальных сценариев использования."""
    
    def test_user_query_with_json_like_syntax(self):
        """Тест пользовательского запроса с JSON-подобным синтаксисом."""
        query = 'Найди товар с параметрами {"color": "red", "size": "large"}'
        escaped = escape_braces(query)
        
        template = "Поиск: {query}"
        result = safe_format(template, query=query)
        
        expected = 'Поиск: Найди товар с параметрами {{"color": "red", "size": "large"}}'
        assert result == expected
    
    def test_user_query_with_template_syntax(self):
        """Тест пользовательского запроса с синтаксисом шаблонов."""
        query = "Покажи товары где цена = {price} и категория = {category}"
        
        template = "Запрос пользователя: {user_query}"
        result = safe_format(template, user_query=query)
        
        expected = "Запрос пользователя: Покажи товары где цена = {{price}} и категория = {{category}}"
        assert result == expected
    
    def test_classification_prompt_scenario(self):
        """Тест сценария классификации запроса."""
        user_query = "Найди {товар} с параметром {value}"
        
        classification_prompt = """Классифицируй запрос пользователя:
        
Запрос: {query}

Классификация:"""
        
        result = safe_format(classification_prompt, query=user_query)
        
        expected = """Классифицируй запрос пользователя:
        
Запрос: Найди {{товар}} с параметром {{value}}

Классификация:"""
        
        assert result == expected
    
    def test_product_search_prompt_scenario(self):
        """Тест сценария промпта поиска товаров."""
        user_query = "Найди насос {модель} для {применение}"
        search_results = "Найдено 3 товара"
        
        product_prompt = """Найденные товары: {search_results}
Запрос пользователя: {user_query}"""
        
        result = safe_format(
            product_prompt, 
            search_results=search_results, 
            user_query=user_query
        )
        
        expected = """Найденные товары: Найдено 3 товара
Запрос пользователя: Найди насос {{модель}} для {{применение}}"""
        
        assert result == expected
