#!/usr/bin/env python3
"""
Простой тест загрузки Excel файла
"""
import requests
import pandas as pd
from pathlib import Path

BASE_URL = "http://localhost:8000"

def create_simple_excel():
    """Создает простой тестовый Excel файл"""
    data = [
        {
            "id": 1,
            "product name": "Тестовый товар 1",
            "description": "Описание тестового товара",
            "category 1": "Тест",
            "category 2": "Категория",
            "category 3": "Подкатегория",
            "article": "TEST-001"
        }
    ]
    
    df = pd.DataFrame(data)
    test_file = Path("test_simple.xlsx")
    df.to_excel(test_file, index=False)
    return test_file

def test_upload():
    """Тестирует загрузку файла"""
    session = requests.Session()
    
    # Авторизуемся
    login_data = {"username": "admin", "password": "admin123"}
    login_response = session.post(f"{BASE_URL}/admin/login", data=login_data)
    
    if login_response.status_code != 200:
        print("❌ Ошибка авторизации")
        return False
    
    # Создаем тестовый файл
    test_file = create_simple_excel()
    print(f"📝 Создан тестовый файл: {test_file}")
    
    # Загружаем файл
    with open(test_file, 'rb') as f:
        files = {'file': (test_file.name, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        data = {'schedule_type': 'immediate'}
        
        response = session.post(f"{BASE_URL}/admin/catalog/upload", files=files, data=data)
    
    print(f"📤 Загрузка файла: {response.status_code}")
    
    if response.status_code == 200:
        if "успешно" in response.text or "загружен" in response.text:
            print("✅ Файл загружен успешно")
            
            # Проверяем статус
            status_response = session.get(f"{BASE_URL}/admin/catalog/status/api")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"📊 Статус: {status_data.get('status', 'unknown')}")
                print(f"📊 Прогресс: {status_data.get('progress', 0)}%")
                return True
        else:
            print("⚠️  Нет подтверждения загрузки")
            print(f"Ответ: {response.text[:300]}...")
    else:
        print(f"❌ Ошибка загрузки: {response.status_code}")
        print(f"Ответ: {response.text[:300]}...")
    
    # Удаляем тестовый файл
    test_file.unlink()
    return False

if __name__ == "__main__":
    success = test_upload()
    print(f"\n{'✅ Тест пройден' if success else '❌ Тест не пройден'}")
