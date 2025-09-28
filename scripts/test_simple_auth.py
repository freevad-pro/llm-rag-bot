#!/usr/bin/env python3
"""
Простой тест авторизации и доступа к каталогу
"""
import requests

BASE_URL = "http://localhost:8000"

def test_auth_and_catalog():
    """Тестирует авторизацию и доступ к каталогу"""
    
    session = requests.Session()
    
    print("🔐 Тестирую авторизацию...")
    
    # 1. Получаем страницу входа
    login_page = session.get(f"{BASE_URL}/admin/login")
    print(f"   Страница входа: {login_page.status_code}")
    
    # 2. Авторизуемся
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    login_response = session.post(f"{BASE_URL}/admin/login", data=login_data, allow_redirects=False)
    print(f"   Авторизация: {login_response.status_code}")
    print(f"   Location: {login_response.headers.get('location', 'Нет')}")
    
    # 3. Проверяем редирект
    if login_response.status_code == 302:
        print("✅ Успешная авторизация (редирект)")
        
        # Переходим по редиректу
        dashboard = session.get(f"{BASE_URL}/admin/")
        print(f"   Панель управления: {dashboard.status_code}")
        
        if dashboard.status_code == 200:
            print("✅ Доступ к панели управления")
            
            # 4. Тестируем страницу каталога
            catalog_page = session.get(f"{BASE_URL}/admin/catalog/upload")
            print(f"   Страница каталога: {catalog_page.status_code}")
            
            if catalog_page.status_code == 200:
                print("✅ Доступ к странице каталога")
                
                # Проверяем содержимое
                if "Загрузить новый каталог" in catalog_page.text:
                    print("✅ Страница каталога содержит форму загрузки")
                    return True
                else:
                    print("❌ Форма загрузки не найдена")
            else:
                print(f"❌ Нет доступа к странице каталога: {catalog_page.status_code}")
        else:
            print(f"❌ Нет доступа к панели: {dashboard.status_code}")
    else:
        print(f"❌ Ошибка авторизации: {login_response.status_code}")
        print(f"   Ответ: {login_response.text[:200]}...")
    
    return False

if __name__ == "__main__":
    success = test_auth_and_catalog()
    print(f"\n{'✅ Тест пройден' if success else '❌ Тест не пройден'}")
