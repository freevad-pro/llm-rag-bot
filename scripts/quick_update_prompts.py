#!/usr/bin/env python3
"""
Простой скрипт обновления промптов через Docker контейнер.
Обновляет промпты прямо в running приложении.
"""
import json
import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.llm.services.improved_prompts import IMPROVED_PROMPTS

def create_sql_script():
    """Создает SQL скрипт для обновления промптов."""
    
    sql_lines = [
        "-- Скрипт обновления промптов ИИ-бота KeTai Consulting",
        "-- Автоматически сгенерирован",
        "",
        "-- Деактивируем все старые промпты",
        "UPDATE prompts SET active = false;",
        "",
        "-- Добавляем новые улучшенные промпты",
    ]
    
    for prompt_name, prompt_content in IMPROVED_PROMPTS.items():
        # Экранируем одинарные кавычки для SQL
        escaped_content = prompt_content.replace("'", "''")
        
        sql_lines.extend([
            f"-- Промпт: {prompt_name}",
            f"INSERT INTO prompts (name, content, version, active, created_at, updated_at) VALUES (",
            f"    '{prompt_name}',",
            f"    '{escaped_content}',",
            f"    1,",
            f"    true,",
            f"    NOW(),",
            f"    NOW()",
            f");",
            ""
        ])
    
    return "\n".join(sql_lines)

def save_sql_script():
    """Сохраняет SQL скрипт в файл."""
    sql_content = create_sql_script()
    
    # Создаем временную папку если её нет
    temp_dir = project_root / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    sql_file = temp_dir / "update_prompts.sql"
    
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write(sql_content)
    
    return sql_file

def print_manual_instructions():
    """Выводит инструкции для ручного обновления."""
    print("""
🤖 Обновление промптов ИИ-бота KeTai Consulting

Способы обновления промптов:

1️⃣ Через Docker (рекомендуется):
   docker-compose exec postgres psql -U postgres -d catalog_db -f /tmp/update_prompts.sql

2️⃣ Через админку (веб-интерфейс):
   - Откройте http://localhost:8000
   - Перейдите в раздел "Промпты"
   - Обновите каждый промпт вручную

3️⃣ Ручное выполнение SQL:
   - Подключитесь к базе: docker-compose exec postgres psql -U postgres -d catalog_db
   - Выполните команды из сгенерированного файла

📋 Список промптов для обновления:
""")
    
    for i, prompt_name in enumerate(IMPROVED_PROMPTS.keys(), 1):
        print(f"   {i:2d}. {prompt_name}")
    
    print(f"""
📁 SQL скрипт сохранен в: temp/update_prompts.sql

💡 Для быстрого обновления через Docker:
   1. Скопируйте SQL файл в контейнер:
      docker cp temp/update_prompts.sql llm-rag-bot-postgres-1:/tmp/
   
   2. Выполните SQL скрипт:
      docker-compose exec postgres psql -U postgres -d catalog_db -f /tmp/update_prompts.sql

✅ После обновления перезапустите приложение:
   docker-compose restart app
""")

def main():
    """Главная функция."""
    
    print("🚀 Генерация скрипта обновления промптов...")
    
    try:
        # Создаем SQL скрипт
        sql_file = save_sql_script()
        print(f"✅ SQL скрипт создан: {sql_file}")
        
        # Выводим инструкции
        print_manual_instructions()
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания скрипта: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
