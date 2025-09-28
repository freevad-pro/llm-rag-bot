#!/usr/bin/env python3
"""
Тест истории версий каталога
"""
import requests

BASE_URL = "http://localhost:8000"

def test_history():
    """Тестирует историю версий"""
    session = requests.Session()
    
    # Авторизуемся
    login_data = {"username": "admin", "password": "admin123"}
    session.post(f"{BASE_URL}/admin/login", data=login_data)
    
    # Проверяем историю
    response = session.get(f"{BASE_URL}/admin/catalog/history")
    
    print(f"📚 История версий: {response.status_code}")
    
    if response.status_code == 200:
        if "test_simple.xlsx" in response.text:
            print("✅ Загруженный файл найден в истории")
            
            # Проверяем статус
            if "processing" in response.text:
                print("📊 Статус: processing")
            elif "completed" in response.text:
                print("📊 Статус: completed")
            elif "failed" in response.text:
                print("📊 Статус: failed")
            else:
                print("📊 Статус: unknown")
            
            return True
        else:
            print("❌ Файл не найден в истории")
    else:
        print(f"❌ Ошибка доступа к истории: {response.status_code}")
    
    return False

if __name__ == "__main__":
    success = test_history()
    print(f"\n{'✅ Тест пройден' if success else '❌ Тест не пройден'}")


