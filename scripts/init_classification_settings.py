#!/usr/bin/env python3
"""
Скрипт для инициализации дефолтных настроек классификации в БД.
Запускается после создания таблицы classification_settings.
"""

import asyncio
import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.connection import get_session
from src.infrastructure.services.classification_settings_service import classification_settings_service


async def init_default_classification_settings():
    """Инициализирует дефолтные настройки классификации в БД."""
    print("🚀 Инициализация дефолтных настроек классификации...")
    
    async with get_session() as session:
        try:
            # Проверяем, есть ли уже активные настройки
            existing_settings = await classification_settings_service.get_active_settings(session)
            
            if existing_settings and existing_settings.get("id"):
                print(f"✅ Настройки классификации уже существуют (ID: {existing_settings['id']})")
                print("   Пропускаем инициализацию.")
                return
            
            print("📝 Создаем дефолтные настройки классификации...")
            
            # Создаем дефолтные настройки
            default_settings = await classification_settings_service.create_settings(
                session=session,
                enable_fast_classification=True,
                enable_llm_classification=True,
                product_keywords=[
                    "товар", "product", "оборудование", "equipment", 
                    "запчасть", "part", "spare", "деталь", "detail",
                    "артикул", "article", "sku", "модель", "model"
                ],
                contact_keywords=[
                    "менеджер", "manager", "связаться", "contact", 
                    "позвонить", "call", "заказать", "order", 
                    "купить", "buy", "цена", "price", "консультация", 
                    "consultation", "помощь менеджера", "manager help"
                ],
                company_keywords=[
                    "компания", "company", "о вас", "about you", 
                    "адрес", "address", "контакты", "contacts", 
                    "история", "history", "местоположение", "location"
                ],
                availability_phrases=[
                    "есть ли у вас", "do you have", "продаете ли", "do you sell",
                    "найдется ли", "can be found", "имеется ли", "is available",
                    "у вас есть", "you have", "в наличии", "in stock",
                    "есть в наличии", "available in stock", "можно ли купить", 
                    "can I buy", "можно ли заказать", "can I order"
                ],
                search_words=[
                    "найти", "find", "искать", "search", "нужен", "need", 
                    "требуется", "required", "looking for", "ищу"
                ],
                specific_products=[
                    "сверло", "drill", "bit", "керн", "core",
                    "болт", "винт", "гайка", "шайба", "nut", "bolt", "screw", "washer",
                    "подшипник", "bearing", "фильтр", "filter", "масло", "oil",
                    "ремень", "belt", "насос", "pump", "двигатель", "motor", "engine",
                    "компрессор", "compressor", "клапан", "valve", "шланг", "hose",
                    "кабель", "cable", "wire", "провод", "провода"
                ],
                description="Дефолтные настройки классификации (автоматически созданы)",
                created_by_admin_id=1,  # Предполагаем, что admin с ID=1 существует
                is_active=True
            )
            
            print(f"✅ Дефолтные настройки классификации созданы успешно!")
            print(f"   ID: {default_settings.id}")
            print(f"   Активны: {default_settings.is_active}")
            print(f"   Быстрая классификация: {default_settings.enable_fast_classification}")
            print(f"   LLM классификация: {default_settings.enable_llm_classification}")
            print(f"   Количество конкретных товаров: {len(default_settings.specific_products.split(','))}")
            
        except Exception as e:
            print(f"❌ Ошибка при создании дефолтных настроек: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(init_default_classification_settings())
