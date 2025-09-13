#!/usr/bin/env python3
"""
Скрипт для обновления промптов в базе данных ИИ-бота.
Использует улучшенные промпты из improved_prompts.py
"""
import asyncio
import sys
import os
from pathlib import Path

# Добавляем корень проекта в путь для импортов
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    # Импортируем компоненты проекта
    from src.infrastructure.llm.services.prompt_manager import prompt_manager
    from src.infrastructure.llm.services.improved_prompts import get_all_improved_prompts
    from src.config.settings import Settings
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь что запускаете скрипт из корневой директории проекта")
    print("Пример: python scripts/update_prompts.py update")
    sys.exit(1)


async def update_all_prompts():
    """Обновляет все промпты в базе данных."""
    
    print("🚀 Обновление промптов ИИ-бота KeTai Consulting")
    print("=" * 50)
    
    # Загружаем настройки
    settings = Settings()
    
    # Создаем движок базы данных
    engine = create_async_engine(
        settings.database_url,
        echo=False  # Отключаем лишние логи
    )
    
    # Создаем сессию
    AsyncSessionLocal = sessionmaker(
        bind=engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    try:
        async with AsyncSessionLocal() as session:
            # Получаем все улучшенные промпты
            improved_prompts = get_all_improved_prompts()
            
            print(f"📋 Найдено {len(improved_prompts)} улучшенных промптов")
            print()
            
            success_count = 0
            error_count = 0
            
            for prompt_name, prompt_content in improved_prompts.items():
                try:
                    print(f"🔄 Обновляю промпт: {prompt_name}")
                    
                    # Обновляем промпт в БД
                    success = await prompt_manager.update_prompt(
                        name=prompt_name,
                        content=prompt_content,
                        session=session
                    )
                    
                    if success:
                        print(f"✅ Промпт '{prompt_name}' успешно обновлен")
                        success_count += 1
                    else:
                        print(f"❌ Ошибка обновления промпта '{prompt_name}'")
                        error_count += 1
                        
                except Exception as e:
                    print(f"❌ Исключение при обновлении '{prompt_name}': {e}")
                    error_count += 1
                
                print()
            
            # Очищаем кэш промптов для применения изменений
            prompt_manager.clear_cache()
            print("🧹 Кэш промптов очищен")
            print()
            
            # Итоговая статистика
            print("📊 Результаты обновления:")
            print(f"✅ Успешно обновлено: {success_count}")
            print(f"❌ Ошибок: {error_count}")
            print(f"📝 Всего промптов: {len(improved_prompts)}")
            
            if error_count == 0:
                print("\n🎉 Все промпты успешно обновлены!")
            else:
                print(f"\n⚠️  Обновление завершено с {error_count} ошибками")
            
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        return False
    
    finally:
        await engine.dispose()
    
    return error_count == 0


async def list_current_prompts():
    """Показывает текущие промпты в базе данных."""
    
    print("📋 Текущие промпты в базе данных")
    print("=" * 40)
    
    # Загружаем настройки
    settings = Settings()
    
    # Создаем движок базы данных
    engine = create_async_engine(
        settings.database_url,
        echo=False
    )
    
    # Создаем сессию
    AsyncSessionLocal = sessionmaker(
        bind=engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    try:
        async with AsyncSessionLocal() as session:
            # Получаем список промптов
            prompts_info = await prompt_manager.list_prompts(session)
            
            if not prompts_info:
                print("❌ Промпты в базе данных не найдены")
                return
            
            for prompt_name, info in prompts_info.items():
                print(f"📝 {prompt_name}")
                print(f"   Версия: {info['version']}")
                print(f"   Активен: {info['active']}")
                print(f"   Обновлен: {info['updated_at'] or 'Не указано'}")
                print(f"   Превью: {info['content_preview']}")
                print()
    
    except Exception as e:
        print(f"💥 Ошибка получения промптов: {e}")
    
    finally:
        await engine.dispose()


async def show_prompt_diff(prompt_name: str):
    """Показывает разницу между текущим и улучшенным промптом."""
    
    print(f"🔍 Сравнение промпта: {prompt_name}")
    print("=" * 50)
    
    # Получаем улучшенный промпт
    improved_prompts = get_all_improved_prompts()
    if prompt_name not in improved_prompts:
        print(f"❌ Улучшенный промпт '{prompt_name}' не найден")
        return
    
    new_prompt = improved_prompts[prompt_name]
    
    # Загружаем настройки
    settings = Settings()
    
    # Создаем движок базы данных
    engine = create_async_engine(
        settings.database_url,
        echo=False
    )
    
    # Создаем сессию
    AsyncSessionLocal = sessionmaker(
        bind=engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    try:
        async with AsyncSessionLocal() as session:
            # Получаем текущий промпт
            current_prompt = await prompt_manager.get_prompt(prompt_name, session)
            
            print("📄 ТЕКУЩИЙ ПРОМПТ:")
            print("-" * 30)
            print(current_prompt[:500] + ("..." if len(current_prompt) > 500 else ""))
            print()
            
            print("✨ УЛУЧШЕННЫЙ ПРОМПТ:")
            print("-" * 30)
            print(new_prompt[:500] + ("..." if len(new_prompt) > 500 else ""))
            print()
            
            print(f"📊 Статистика:")
            print(f"   Текущая длина: {len(current_prompt)} символов")
            print(f"   Новая длина: {len(new_prompt)} символов")
            print(f"   Изменение: {len(new_prompt) - len(current_prompt):+d} символов")
    
    except Exception as e:
        print(f"💥 Ошибка сравнения промпта: {e}")
    
    finally:
        await engine.dispose()


def print_help():
    """Показывает справку по использованию скрипта."""
    print("""
🤖 Скрипт обновления промптов ИИ-бота KeTai Consulting

Использование:
    python scripts/update_prompts.py [команда] [параметры]

Команды:
    update          Обновить все промпты в базе данных
    list           Показать текущие промпты в БД
    diff <name>    Показать разницу для конкретного промпта
    help           Показать эту справку

Примеры:
    python scripts/update_prompts.py update
    python scripts/update_prompts.py list
    python scripts/update_prompts.py diff system_prompt

Доступные промпты для обновления:
    - system_prompt (основной системный промпт)
    - product_search_prompt (поиск товаров)
    - pricing_inquiry_prompt (запросы о ценах)
    - welcome_prompt (приветствие)
    - technical_clarification_prompt (технические уточнения)
    - objection_handling_prompt (работа с возражениями)
    - lead_qualification_prompt (квалификация лидов)
    - service_answer_prompt (ответы об услугах)
    - general_conversation_prompt (общий диалог)
    - company_info_prompt (информация о компании)
    - error_handling_prompt (обработка ошибок)
    - conversation_closing_prompt (завершение диалога)

Перед запуском убедитесь:
    - База данных запущена
    - Переменные окружения настроены
    - Находитесь в корневой директории проекта
""")


async def main():
    """Главная функция скрипта."""
    
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "update":
        await update_all_prompts()
    elif command == "list":
        await list_current_prompts()
    elif command == "diff":
        if len(sys.argv) < 3:
            print("❌ Укажите название промпта для сравнения")
            print("Пример: python scripts/update_prompts.py diff system_prompt")
            return
        prompt_name = sys.argv[2]
        await show_prompt_diff(prompt_name)
    elif command == "help":
        print_help()
    else:
        print(f"❌ Неизвестная команда: {command}")
        print("Используйте 'help' для справки")


if __name__ == "__main__":
    # Проверяем что мы в правильной директории
    if not Path("src").exists() or not Path("scripts").exists():
        print("❌ Запустите скрипт из корневой директории проекта")
        print("Пример: python scripts/update_prompts.py update")
        sys.exit(1)
    
    # Запускаем основную функцию
    asyncio.run(main())
