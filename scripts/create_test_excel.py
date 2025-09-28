#!/usr/bin/env python3
"""
Создание тестового Excel файла для проверки загрузки каталога
"""
import pandas as pd
from pathlib import Path

def create_test_catalog():
    """Создает тестовый каталог согласно требованиям @product_idea.md"""
    
    # Тестовые товары с обязательными полями
    products = [
        {
            "id": 1,
            "product name": "Болт М12x50 DIN 933",
            "description": "Болт с шестигранной головкой, полная резьба, сталь оцинкованная",
            "category 1": "Крепеж",
            "category 2": "Болты", 
            "category 3": "Шестигранные",
            "article": "BOLT-M12-50-933",
            "photo_url": "https://example.com/bolt-m12.jpg"
        },
        {
            "id": 2,
            "product name": "Гайка М12 DIN 934",
            "description": "Гайка шестигранная, сталь оцинкованная, класс прочности 8",
            "category 1": "Крепеж",
            "category 2": "Гайки",
            "category 3": "Шестигранные", 
            "article": "NUT-M12-934",
            "photo_url": ""
        },
        {
            "id": 3,
            "product name": "Подшипник 6205-2RS",
            "description": "Подшипник шариковый радиальный однорядный с защитными шайбами",
            "category 1": "Подшипники",
            "category 2": "Шариковые",
            "category 3": "Радиальные",
            "article": "BEARING-6205-2RS",
            "photo_url": "https://example.com/bearing-6205.jpg"
        }
    ]
    
    # Создаем DataFrame
    df = pd.DataFrame(products)
    
    # Сохраняем в Excel
    output_file = Path("test_catalog_manual.xlsx")
    df.to_excel(output_file, index=False)
    
    print(f"✅ Создан тестовый каталог: {output_file}")
    print(f"   Товаров: {len(products)}")
    print(f"   Размер: {output_file.stat().st_size / 1024:.1f} KB")
    
    return output_file

if __name__ == "__main__":
    create_test_catalog()
