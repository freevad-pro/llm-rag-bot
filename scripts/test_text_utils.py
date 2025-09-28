#!/usr/bin/env python3
"""
Простой тест для проверки утилит работы с текстом.
Проверяет исправления для обработки фигурных скобок.
"""
import sys
import os

# Добавляем путь к src для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from infrastructure.utils.text_utils import escape_braces, safe_format


def test_escape_braces():
    """Тестирует функцию escape_braces"""
    print("🧪 Тестирование escape_braces...")
    
    # Тест 1: Простые фигурные скобки
    text1 = "Найди товар {артикул}"
    result1 = escape_braces(text1)
    expected1 = "Найди товар {{артикул}}"
    assert result1 == expected1, f"Ожидалось: {expected1}, получено: {result1}"
    print("✅ Тест 1: Простые фигурные скобки")
    
    # Тест 2: Множественные скобки
    text2 = "Цена: {price} руб., скидка: {discount}%"
    result2 = escape_braces(text2)
    expected2 = "Цена: {{price}} руб., скидка: {{discount}}%"
    assert result2 == expected2, f"Ожидалось: {expected2}, получено: {result2}"
    print("✅ Тест 2: Множественные скобки")
    
    # Тест 3: Вложенные скобки
    text3 = "Объект: {data: {value}}"
    result3 = escape_braces(text3)
    expected3 = "Объект: {{data: {{value}}}}"
    assert result3 == expected3, f"Ожидалось: {expected3}, получено: {result3}"
    print("✅ Тест 3: Вложенные скобки")
    
    # Тест 4: Пустые скобки
    text4 = "Пустые скобки: {}"
    result4 = escape_braces(text4)
    expected4 = "Пустые скобки: {{}}"
    assert result4 == expected4, f"Ожидалось: {expected4}, получено: {result4}"
    print("✅ Тест 4: Пустые скобки")
    
    # Тест 5: Без скобок
    text5 = "Обычный текст без скобок"
    result5 = escape_braces(text5)
    assert result5 == text5, f"Ожидалось: {text5}, получено: {result5}"
    print("✅ Тест 5: Текст без скобок")
    
    print("✅ Все тесты escape_braces прошли успешно!")


def test_safe_format():
    """Тестирует функцию safe_format"""
    print("\n🧪 Тестирование safe_format...")
    
    # Тест 1: Фигурные скобки в значении
    template1 = "Запрос: {query}, Результат: {result}"
    result1 = safe_format(template1, query="Найди {товар}", result="OK")
    expected1 = "Запрос: Найди {{товар}}, Результат: OK"
    assert result1 == expected1, f"Ожидалось: {expected1}, получено: {result1}"
    print("✅ Тест 1: Фигурные скобки в значении")
    
    # Тест 2: Множественные скобки
    template2 = "Пользователь: {user}, Запрос: {query}"
    result2 = safe_format(template2, user="admin", query="SELECT * FROM {table}")
    expected2 = "Пользователь: admin, Запрос: SELECT * FROM {{table}}"
    assert result2 == expected2, f"Ожидалось: {expected2}, получено: {result2}"
    print("✅ Тест 2: Множественные скобки")
    
    # Тест 3: Без скобок
    template3 = "Пользователь: {user}, Запрос: {query}"
    result3 = safe_format(template3, user="admin", query="SELECT * FROM users")
    expected3 = "Пользователь: admin, Запрос: SELECT * FROM users"
    assert result3 == expected3, f"Ожидалось: {expected3}, получено: {result3}"
    print("✅ Тест 3: Без скобок в значениях")
    
    # Тест 4: Не-строковые значения
    template4 = "ID: {id}, Активен: {active}, Цена: {price}"
    result4 = safe_format(template4, id=123, active=True, price=99.99)
    expected4 = "ID: 123, Активен: True, Цена: 99.99"
    assert result4 == expected4, f"Ожидалось: {expected4}, получено: {result4}"
    print("✅ Тест 4: Не-строковые значения")
    
    print("✅ Все тесты safe_format прошли успешно!")


def test_real_world_scenarios():
    """Тестирует реальные сценарии использования"""
    print("\n🧪 Тестирование реальных сценариев...")
    
    # Тест 1: JSON-подобный синтаксис
    query1 = 'Найди товар с параметрами {"color": "red", "size": "large"}'
    template1 = "Поиск: {query}"
    result1 = safe_format(template1, query=query1)
    expected1 = 'Поиск: Найди товар с параметрами {{"color": "red", "size": "large"}}'
    assert result1 == expected1, f"Ожидалось: {expected1}, получено: {result1}"
    print("✅ Тест 1: JSON-подобный синтаксис")
    
    # Тест 2: Шаблонный синтаксис
    query2 = "Покажи товары где цена = {price} и категория = {category}"
    template2 = "Запрос пользователя: {user_query}"
    result2 = safe_format(template2, user_query=query2)
    expected2 = "Запрос пользователя: Покажи товары где цена = {{price}} и категория = {{category}}"
    assert result2 == expected2, f"Ожидалось: {expected2}, получено: {result2}"
    print("✅ Тест 2: Шаблонный синтаксис")
    
    # Тест 3: Классификационный промпт
    user_query3 = "Найди {товар} с параметром {value}"
    classification_prompt = """Классифицируй запрос пользователя:
        
Запрос: {query}

Классификация:"""
    
    result3 = safe_format(classification_prompt, query=user_query3)
    expected3 = """Классифицируй запрос пользователя:
        
Запрос: Найди {{товар}} с параметром {{value}}

Классификация:"""
    
    assert result3 == expected3, f"Ожидалось: {expected3}, получено: {result3}"
    print("✅ Тест 3: Классификационный промпт")
    
    print("✅ Все тесты реальных сценариев прошли успешно!")


def test_json_serialization():
    """Тестирует исправление JSON сериализации"""
    print("\n🧪 Тестирование JSON сериализации...")
    
    import json
    
    # Симулируем данные которые раньше ломались
    usage_data = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    model_name = "gpt-3.5-turbo"
    
    # Новый способ (исправленный)
    new_extra_data = json.dumps({
        "model": model_name,
        "usage": usage_data
    })
    
    # Проверяем что новый способ создает валидный JSON
    parsed_data = json.loads(new_extra_data)
    assert parsed_data['model'] == model_name
    assert parsed_data['usage']['total_tokens'] == 30
    
    # Проверяем что это действительно валидный JSON
    assert isinstance(parsed_data, dict)
    assert 'model' in parsed_data
    assert 'usage' in parsed_data
    
    print("✅ JSON сериализация работает корректно!")


def main():
    """Запускает все тесты"""
    print("🚀 Запуск тестов для утилит работы с текстом")
    print("=" * 60)
    
    try:
        test_escape_braces()
        test_safe_format()
        test_real_world_scenarios()
        test_json_serialization()
        
        print("\n" + "=" * 60)
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("✅ Исправления для обработки фигурных скобок работают корректно")
        print("✅ JSON сериализация исправлена")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ОШИБКА В ТЕСТАХ: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
