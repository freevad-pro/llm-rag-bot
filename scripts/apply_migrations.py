#!/usr/bin/env python3
"""
Скрипт для применения миграций Alembic
"""
import asyncio
import subprocess
import sys
import os

async def apply_migrations():
    """Применяем миграции Alembic"""
    
    print("🔧 Применяем миграции Alembic...")
    
    try:
        # Применяем все миграции до последней
        result = subprocess.run([
            "alembic", "upgrade", "head"
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            print("✅ Миграции успешно применены")
            print("📋 Вывод:")
            print(result.stdout)
        else:
            print("❌ Ошибка при применении миграций")
            print("📋 Ошибка:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(apply_migrations())
    if success:
        print("\n🎉 Миграции применены успешно!")
        print("Теперь ошибка с started_at должна исчезнуть")
    else:
        print("\n❌ Не удалось применить миграции")
        print("Проверьте подключение к базе данных")
