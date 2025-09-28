#!/usr/bin/env python3
"""
Скрипт для тестирования функционала загрузки каталога.
Создает тестовый Excel файл и проверяет загрузку через API.
"""

import os
import sys
import pandas as pd
import requests
import time
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8000"
TEST_DATA_DIR = Path("data/test_uploads")
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

def create_test_excel():
    """Создает тестовый Excel файл с каталогом товаров"""
    print("📝 Создаю тестовый Excel файл...")
    
    # Тестовые данные согласно @product_idea.md
    test_products = [
        {
            "id": 1,
            "product name": "Болт М12x50 DIN 933",
            "description": "Болт с шестигранной головкой, полная резьба, сталь оцинкованная",
            "category 1": "Крепеж",
            "category 2": "Болты",
            "category 3": "Шестигранные",
            "article": "BOLT-M12-50-933",
            "photo_url": "https://example.com/bolt-m12.jpg",
            "page_url": "https://example.com/products/bolt-m12-50"
        },
        {
            "id": 2,
            "product name": "Гайка М12 DIN 934",
            "description": "Гайка шестигранная, сталь оцинкованная, класс прочности 8",
            "category 1": "Крепеж",
            "category 2": "Гайки",
            "category 3": "Шестигранные",
            "article": "NUT-M12-934",
            "photo_url": "https://example.com/nut-m12.jpg",
            "page_url": ""
        },
        {
            "id": 3,
            "product name": "Шайба М12 DIN 125",
            "description": "Шайба плоская, сталь оцинкованная",
            "category 1": "Крепеж",
            "category 2": "Шайбы",
            "category 3": "Плоские",
            "article": "WASHER-M12-125",
            "photo_url": "",
            "page_url": "https://example.com/products/washer-m12"
        },
        {
            "id": 4,
            "product name": "Винт М8x25 DIN 7991",
            "description": "Винт с потайной головкой под шестигранник, сталь нержавеющая A2",
            "category 1": "Крепеж",
            "category 2": "Винты",
            "category 3": "Потайные",
            "article": "SCREW-M8-25-7991",
            "photo_url": "https://example.com/screw-m8.jpg",
            "page_url": "https://example.com/products/screw-m8-25"
        },
        {
            "id": 5,
            "product name": "Подшипник 6205-2RS",
            "description": "Подшипник шариковый радиальный однорядный с защитными шайбами",
            "category 1": "Подшипники",
            "category 2": "Шариковые",
            "category 3": "Радиальные",
            "article": "BEARING-6205-2RS",
            "photo_url": "https://example.com/bearing-6205.jpg",
            "page_url": "https://example.com/products/bearing-6205"
        }
    ]
    
    # Создаем DataFrame
    df = pd.DataFrame(test_products)
    
    # Сохраняем в Excel
    test_file = TEST_DATA_DIR / "test_catalog_small.xlsx"
    df.to_excel(test_file, index=False)
    
    print(f"✅ Создан тестовый файл: {test_file}")
    print(f"   Товаров: {len(test_products)}")
    print(f"   Размер: {test_file.stat().st_size / 1024:.1f} KB")
    
    return test_file

def create_admin_user():
    """Создает тестового администратора"""
    print("👤 Создаю тестового администратора...")
    
    # Используем существующий скрипт
    script_path = Path("scripts/init_admin_users.py")
    if script_path.exists():
        os.system(f"python {script_path}")
        print("✅ Администратор создан")
    else:
        print("⚠️  Скрипт создания администратора не найден")

def login_admin():
    """Авторизуется в админ-панели"""
    print("🔐 Авторизуюсь в админ-панели...")
    
    session = requests.Session()
    
    # Получаем страницу входа
    login_page = session.get(f"{BASE_URL}/admin/login")
    if login_page.status_code != 200:
        print(f"❌ Ошибка получения страницы входа: {login_page.status_code}")
        return None
    
    # Авторизуемся
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    login_response = session.post(f"{BASE_URL}/admin/login", data=login_data)
    
    if login_response.status_code == 200 and "/admin/" in login_response.url:
        print("✅ Успешная авторизация")
        return session
    else:
        print(f"❌ Ошибка авторизации: {login_response.status_code}")
        print(f"   URL: {login_response.url}")
        return None

def test_catalog_upload_page(session):
    """Тестирует доступность страницы загрузки каталога"""
    print("📄 Проверяю страницу загрузки каталога...")
    
    response = session.get(f"{BASE_URL}/admin/catalog/upload")
    
    if response.status_code == 200:
        print("✅ Страница загрузки доступна")
        
        # Проверяем наличие ключевых элементов
        content = response.text
        checks = [
            ("форма загрузки", 'enctype="multipart/form-data"' in content),
            ("поле файла", 'type="file"' in content),
            ("валидация", 'accept=".xlsx,.xls"' in content),
            ("требования", "Обязательные колонки" in content)
        ]
        
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"   {status} {check_name}")
        
        return True
    else:
        print(f"❌ Ошибка доступа к странице: {response.status_code}")
        return False

def test_catalog_upload(session, test_file):
    """Тестирует загрузку Excel файла"""
    print("📤 Тестирую загрузку Excel файла...")
    
    # Подготавливаем файл для загрузки
    with open(test_file, 'rb') as f:
        files = {'file': (test_file.name, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        data = {
            'schedule_type': 'immediate'
        }
        
        response = session.post(f"{BASE_URL}/admin/catalog/upload", files=files, data=data)
    
    if response.status_code == 200:
        print("✅ Файл успешно загружен")
        
        # Проверяем наличие сообщения об успехе
        if "Файл загружен" in response.text or "успешно" in response.text:
            print("✅ Получено подтверждение загрузки")
            return True
        else:
            print("⚠️  Нет подтверждения загрузки в ответе")
            return False
    else:
        print(f"❌ Ошибка загрузки файла: {response.status_code}")
        print(f"   Ответ: {response.text[:200]}...")
        return False

def test_catalog_status(session):
    """Проверяет статус индексации"""
    print("📊 Проверяю статус индексации...")
    
    # Проверяем страницу статуса
    response = session.get(f"{BASE_URL}/admin/catalog/status")
    
    if response.status_code == 200:
        print("✅ Страница статуса доступна")
        
        # Проверяем API статуса
        api_response = session.get(f"{BASE_URL}/admin/catalog/status/api")
        
        if api_response.status_code == 200:
            status_data = api_response.json()
            print(f"✅ API статуса работает")
            print(f"   Статус: {status_data.get('status', 'unknown')}")
            print(f"   Прогресс: {status_data.get('progress', 0)}%")
            print(f"   Товаров: {status_data.get('products_count', 0)}")
            
            return status_data
        else:
            print(f"❌ Ошибка API статуса: {api_response.status_code}")
            return None
    else:
        print(f"❌ Ошибка доступа к странице статуса: {response.status_code}")
        return None

def test_catalog_history(session):
    """Проверяет историю версий каталога"""
    print("📚 Проверяю историю версий каталога...")
    
    response = session.get(f"{BASE_URL}/admin/catalog/history")
    
    if response.status_code == 200:
        print("✅ Страница истории доступна")
        
        # Проверяем наличие загруженного файла в истории
        content = response.text
        if "test_catalog_small.xlsx" in content:
            print("✅ Загруженный файл найден в истории")
            return True
        else:
            print("⚠️  Загруженный файл не найден в истории")
            return False
    else:
        print(f"❌ Ошибка доступа к истории: {response.status_code}")
        return False

def wait_for_indexing(session, max_wait=60):
    """Ждет завершения индексации"""
    print("⏳ Жду завершения индексации...")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        status_data = test_catalog_status(session)
        
        if status_data:
            status = status_data.get('status', 'unknown')
            progress = status_data.get('progress', 0)
            
            if status == 'completed':
                print("✅ Индексация завершена успешно!")
                return True
            elif status == 'failed':
                print("❌ Индексация завершилась с ошибкой")
                return False
            elif status == 'processing':
                print(f"   Прогресс: {progress}%")
            
        time.sleep(2)
    
    print("⏰ Превышено время ожидания индексации")
    return False

def main():
    """Основная функция тестирования"""
    print("🧪 Начинаю тестирование функционала загрузки каталога")
    print("=" * 60)
    
    try:
        # 1. Создаем тестовый Excel файл
        test_file = create_test_excel()
        
        # 2. Создаем администратора (если нужно)
        create_admin_user()
        
        # 3. Авторизуемся
        session = login_admin()
        if not session:
            print("❌ Не удалось авторизоваться. Завершаю тестирование.")
            return False
        
        # 4. Тестируем страницу загрузки
        if not test_catalog_upload_page(session):
            print("❌ Страница загрузки недоступна. Завершаю тестирование.")
            return False
        
        # 5. Загружаем файл
        if not test_catalog_upload(session, test_file):
            print("❌ Не удалось загрузить файл. Завершаю тестирование.")
            return False
        
        # 6. Ждем завершения индексации
        if not wait_for_indexing(session):
            print("⚠️  Индексация не завершилась в ожидаемое время")
        
        # 7. Проверяем историю
        test_catalog_history(session)
        
        print("=" * 60)
        print("✅ Тестирование завершено успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка во время тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


