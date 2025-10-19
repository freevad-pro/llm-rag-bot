"""
Сервис загрузки каталога товаров из Excel файлов.
Реализует ExcelLoaderProtocol согласно требованиям из @product_idea.md
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from pandas import DataFrame

from ...domain.entities.product import Product
from ...domain.interfaces.search import ExcelLoaderProtocol

logger = logging.getLogger(__name__)


class ExcelCatalogLoader:
    """
    Загрузчик каталога товаров из Excel файлов.
    
    Поддерживает структуру из @product_idea.md:
    - Все поля опциональные: id, product name, description, category 1, category 2, category 3, article, photo_url, page_url
    - Если поле пустое, используется значение по умолчанию (None или пустая строка)
    - Любые другие колонки игнорируются
    """
    
    # Маппинг колонок Excel в атрибуты Product
    # Все поля теперь опциональные - если поле пустое, используется значение по умолчанию
    COLUMN_MAPPING = {
        'id': 'id',
        'product name': 'product_name',
        'description': 'description',
        'category 1': 'category_1',
        'category 2': 'category_2',
        'category 3': 'category_3',
        'article': 'article',
        'photo_url': 'photo_url',
        'page_url': 'page_url'
    }
    
    def __init__(self) -> None:
        """Инициализация загрузчика."""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def load_products(self, excel_path: str) -> list[Product]:
        """
        Загружает товары из Excel файла.
        
        Args:
            excel_path: Путь к Excel файлу
            
        Returns:
            Список товаров
            
        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если структура файла некорректна
        """
        self._logger.info(f"Начинаю загрузку каталога из {excel_path}")
        
        # Проверяем существование файла
        file_path = Path(excel_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Excel файл не найден: {excel_path}")
        
        # Валидируем структуру файла (все поля опциональные, поэтому проверка не критична)
        validation_result = self.validate_excel_structure(excel_path)
        
        # Логируем найденные поля для информации
        found_columns = [col for col, exists in validation_result.items() if exists]
        self._logger.info(f"Найдены поля в Excel файле: {found_columns}")
        
        # Загружаем данные
        try:
            df = pd.read_excel(excel_path, dtype=str)
            df = df.fillna("")  # Заменяем NaN на пустые строки
            
            self._logger.info(f"Загружено {len(df)} строк из Excel файла")
            
            # Преобразуем в объекты Product
            products = []
            for idx, row in df.iterrows():
                try:
                    product = self._row_to_product(row)
                    products.append(product)
                except Exception as e:
                    self._logger.warning(f"Ошибка обработки строки {idx + 1}: {e}")
                    continue
            
            self._logger.info(f"Успешно загружено {len(products)} товаров")
            return products
            
        except Exception as e:
            self._logger.error(f"Ошибка чтения Excel файла: {e}")
            raise ValueError(f"Ошибка обработки Excel файла: {e}")
    
    def validate_excel_structure(self, excel_path: str) -> dict[str, bool]:
        """
        Валидирует структуру Excel файла.
        
        Args:
            excel_path: Путь к Excel файлу
            
        Returns:
            Словарь с результатами валидации полей (всегда True, так как все поля опциональные)
        """
        try:
            # Читаем только заголовки
            df_headers = pd.read_excel(excel_path, nrows=0)
            available_columns = [col.lower().strip() for col in df_headers.columns]
            
            self._logger.debug(f"Найденные колонки: {available_columns}")
            
            # Все поля опциональные, поэтому всегда возвращаем True
            validation_result = {}
            for col in self.COLUMN_MAPPING.keys():
                validation_result[col] = True  # Все поля опциональные
            
            return validation_result
            
        except Exception as e:
            self._logger.error(f"Ошибка валидации структуры Excel: {e}")
            return {col: True for col in self.COLUMN_MAPPING.keys()}  # Все поля опциональные
    
    def _row_to_product(self, row: pd.Series) -> Product:
        """
        Преобразует строку DataFrame в объект Product.
        
        Args:
            row: Строка данных из DataFrame
            
        Returns:
            Объект Product
            
        Raises:
            ValueError: Если не удается создать продукт
        """
        try:
            # Получаем значения всех полей (все опциональные)
            product_data = {}
            
            for excel_col, product_attr in self.COLUMN_MAPPING.items():
                value = self._get_column_value(row, excel_col)
                # Если поле пустое, используем значение по умолчанию
                if value.strip():
                    product_data[product_attr] = value.strip()
                else:
                    # Для строковых полей используем пустую строку, для остальных None
                    if product_attr in ['id', 'product_name', 'description', 'category_1', 'category_2', 'category_3', 'article']:
                        product_data[product_attr] = ""
                    else:
                        product_data[product_attr] = None
            
            return Product(**product_data)
            
        except Exception as e:
            raise ValueError(f"Ошибка создания продукта: {e}")
    
    def _get_column_value(self, row: pd.Series, column_name: str) -> str:
        """
        Получает значение колонки по имени (регистронезависимо).
        
        Args:
            row: Строка данных
            column_name: Имя колонки
            
        Returns:
            Значение колонки или пустая строка
        """
        # Ищем колонку по имени (регистронезависимо)
        for col in row.index:
            if col.lower().strip() == column_name.lower():
                value = row[col]
                return str(value) if pd.notna(value) else ""
        
        return ""
    
    def get_file_stats(self, excel_path: str) -> dict:
        """
        Получает статистику Excel файла.
        
        Args:
            excel_path: Путь к файлу
            
        Returns:
            Словарь со статистикой
        """
        try:
            file_path = Path(excel_path)
            df = pd.read_excel(excel_path, nrows=1)  # Читаем только для получения колонок
            
            return {
                "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
                "columns_count": len(df.columns), 
                "available_columns": list(df.columns),
                "required_columns_present": list(self.validate_excel_structure(excel_path).keys()),
                "file_exists": True
            }
            
        except Exception as e:
            self._logger.error(f"Ошибка получения статистики файла: {e}")
            return {
                "file_size_mb": 0,
                "columns_count": 0,
                "available_columns": [],
                "required_columns_present": [],
                "file_exists": False,
                "error": str(e)
            }
