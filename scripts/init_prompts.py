#!/usr/bin/env python3
"""
Скрипт для инициализации дефолтных промптов в базе данных.
Выполняет метод initialize_default_prompts из PromptManagementService.
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.connection import get_session
from src.domain.services.prompt_management import prompt_management_service


async def main():
    """Инициализирует дефолтные промпты в базе данных"""
    print("🚀 Начинаем инициализацию дефолтных промптов...")
    
    try:
        async for session in get_session():
            await prompt_management_service.initialize_default_prompts(session)
            print("✅ Промпты успешно инициализированы!")
            print("\n📋 Инициализированные промпты:")
            
            # Получаем список промптов для проверки
            prompts = await prompt_management_service.get_all_prompts(session)
            for prompt in prompts:
                print(f"  - {prompt.name} ({prompt.display_name})")
            
            break
            
    except Exception as e:
        print(f"❌ Ошибка инициализации промптов: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

