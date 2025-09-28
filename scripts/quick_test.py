#!/usr/bin/env python3
"""
Быстрая проверка всех компонентов загрузки каталога
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def quick_test():
    """Быстрая проверка всех компонентов"""
    
    print("🧪 Быстрая проверка функционала загрузки каталога")
    print("=" * 50)
    
    # 1. Health check
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ Health check: {health.status_code}")
    except:
        print("❌ Health check: недоступен")
        return False
    
    # 2. Админ-панель
    try:
        admin = requests.get(f"{BASE_URL}/admin/", timeout=5)
        print(f"✅ Админ-панель: {admin.status_code}")
    except:
        print("❌ Админ-панель: недоступна")
        return False
    
    # 3. Авторизация
    session = requests.Session()
    try:
        login_data = {"username": "admin", "password": "admin123"}
        login = session.post(f"{BASE_URL}/admin/login", data=login_data, timeout=5)
        
        if login.status_code == 200 and "/admin/" in login.url:
            print("✅ Авторизация: успешна")
        else:
            print("❌ Авторизация: ошибка")
            return False
    except:
        print("❌ Авторизация: недоступна")
        return False
    
    # 4. Страница загрузки каталога
    try:
        catalog = session.get(f"{BASE_URL}/admin/catalog/upload", timeout=5)
        if catalog.status_code == 200:
            print("✅ Страница каталога: доступна")
        else:
            print(f"❌ Страница каталога: {catalog.status_code}")
            return False
    except:
        print("❌ Страница каталога: недоступна")
        return False
    
    # 5. API статуса
    try:
        status = session.get(f"{BASE_URL}/admin/catalog/status/api", timeout=5)
        if status.status_code == 200:
            data = status.json()
            print(f"✅ API статуса: работает (статус: {data.get('status', 'unknown')})")
        else:
            print(f"❌ API статуса: {status.status_code}")
            return False
    except:
        print("❌ API статуса: недоступен")
        return False
    
    # 6. История версий
    try:
        history = session.get(f"{BASE_URL}/admin/catalog/history", timeout=5)
        if history.status_code == 200:
            print("✅ История версий: доступна")
        else:
            print(f"❌ История версий: {history.status_code}")
            return False
    except:
        print("❌ История версий: недоступна")
        return False
    
    print("=" * 50)
    print("✅ Все компоненты работают корректно!")
    print("\n📋 Для ручной проверки:")
    print("   1. Откройте: http://localhost:8000/admin/")
    print("   2. Войдите: admin / admin123")
    print("   3. Загрузите: test_catalog_manual.xlsx")
    print("   4. Проверьте статус и историю")
    
    return True

if __name__ == "__main__":
    success = quick_test()
    if not success:
        print("\n❌ Обнаружены проблемы. Проверьте:")
        print("   - Запущены ли контейнеры: docker-compose ps")
        print("   - Доступность порта 8000")
        print("   - Логи приложения: docker-compose logs app")
