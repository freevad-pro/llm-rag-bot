#!/usr/bin/env python3
"""
Скрипт для проверки структуры таблицы conversations
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_conversations_table():
    """Проверяем структуру таблицы conversations"""
    
    # Получаем URL базы данных из переменных окружения
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL не установлен")
        return
    
    print(f"🔍 Подключаемся к базе данных")
    
    try:
        engine = create_async_engine(database_url)
        
        async with engine.begin() as conn:
            # Проверяем существует ли таблица conversations
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'conversations'
                );
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                print("❌ Таблица 'conversations' не существует")
                return
            
            print("✅ Таблица 'conversations' существует")
            
            # Получаем структуру таблицы
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'conversations' 
                ORDER BY ordinal_position;
            """))
            
            columns = result.fetchall()
            
            print("\n📋 Структура таблицы 'conversations':")
            for col in columns:
                print(f"  - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
            
            # Проверяем есть ли поле started_at или created_at
            column_names = [col[0] for col in columns]
            
            if 'started_at' in column_names:
                print("\n⚠️  ПРОБЛЕМА: В таблице есть поле 'started_at', но должно быть 'created_at'")
                print("   Нужно применить миграцию 008_rename_started_at_to_created_at")
            elif 'created_at' in column_names:
                print("\n✅ Поле 'created_at' присутствует - структура корректна")
            else:
                print("\n❌ Ни 'started_at', ни 'created_at' не найдены!")
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_conversations_table())
