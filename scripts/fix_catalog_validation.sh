#!/bin/bash
# Скрипт для исправления валидации каталога - делаем category_2, category_3 и description опциональными
# Использование: ./scripts/fix_catalog_validation.sh

set -e

# Цвета для вывода
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

log "Начинаем исправление валидации каталога..."

# Переходим в рабочую директорию
cd /opt/llm-bot/app

# Проверяем, что мы в правильной директории
if [ ! -f "docker-compose.prod.yml" ]; then
    error "Файл docker-compose.prod.yml не найден. Убедитесь, что вы находитесь в правильной директории."
    exit 1
fi

log "Останавливаем приложение..."
docker-compose -f docker-compose.prod.yml stop app

log "Создаем backup текущего кода..."
cp -r src src_backup_$(date +%Y%m%d_%H%M%S)

log "Применяем исправления валидации..."

# Создаем исправленные файлы
cat > src/infrastructure/search/excel_loader.py << 'EOF'
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
    - Обязательные поля: id, product name, category 1, article
    - Опциональные поля: description, category 2, category 3, photo_url, page_url
    - Любые другие колонки игнорируются
    """
    
    # Маппинг колонок Excel в атрибуты Product
    REQUIRED_COLUMNS = {
        'id': 'id',
        'product name': 'product_name',
        'category 1': 'category_1',
        'article': 'article'
    }
    
    OPTIONAL_COLUMNS = {
        'description': 'description',
        'category 2': 'category_2',
        'category 3': 'category_3',
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
            Список объектов Product
            
        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если структура файла некорректна
        """
        try:
            self._logger.info(f"Начинаю загрузку товаров из {excel_path}")
            
            # Читаем Excel файл
            df = pd.read_excel(excel_path)
            self._logger.info(f"Загружено {len(df)} строк из Excel файла")
            
            # Валидируем структуру
            validation_result = self.validate_excel_structure(excel_path)
            missing_required = [col for col, exists in validation_result.items() if not exists]
            
            if missing_required:
                raise ValueError(f"Отсутствуют обязательные колонки: {', '.join(missing_required)}")
            
            # Преобразуем строки в объекты Product
            products = []
            errors_count = 0
            
            for index, row in df.iterrows():
                try:
                    product = self._row_to_product(row)
                    products.append(product)
                except Exception as e:
                    errors_count += 1
                    self._logger.warning(f"Ошибка обработки строки {index + 1}: {e}")
                    # Продолжаем обработку остальных строк
                    continue
            
            self._logger.info(f"Успешно загружено {len(products)} товаров, ошибок: {errors_count}")
            
            if len(products) == 0:
                raise ValueError("Не удалось загрузить ни одного товара из файла")
            
            return products
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Файл {excel_path} не найден")
        except Exception as e:
            self._logger.error(f"Ошибка загрузки товаров из {excel_path}: {e}")
            raise ValueError(f"Ошибка обработки Excel файла: {e}")
    
    def validate_excel_structure(self, excel_path: str) -> dict[str, bool]:
        """
        Валидирует структуру Excel файла.
        
        Args:
            excel_path: Путь к Excel файлу
            
        Returns:
            Словарь с результатами валидации обязательных полей
        """
        try:
            # Читаем только заголовки
            df_headers = pd.read_excel(excel_path, nrows=0)
            available_columns = [col.lower().strip() for col in df_headers.columns]
            
            self._logger.debug(f"Найденные колонки: {available_columns}")
            
            # Проверяем наличие обязательных колонок
            validation_result = {}
            for required_col in self.REQUIRED_COLUMNS.keys():
                validation_result[required_col] = required_col.lower() in available_columns
            
            return validation_result
            
        except Exception as e:
            self._logger.error(f"Ошибка валидации структуры Excel: {e}")
            return {col: False for col in self.REQUIRED_COLUMNS.keys()}
    
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
            # Получаем значения обязательных полей
            product_data = {}
            
            for excel_col, product_attr in self.REQUIRED_COLUMNS.items():
                value = self._get_column_value(row, excel_col)
                if not value.strip():
                    raise ValueError(f"Обязательное поле '{excel_col}' пустое")
                product_data[product_attr] = value.strip()
            
            # Получаем значения опциональных полей
            for excel_col, product_attr in self.OPTIONAL_COLUMNS.items():
                value = self._get_column_value(row, excel_col)
                product_data[product_attr] = value.strip() if value.strip() else None
            
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
EOF

cat > src/domain/entities/product.py << 'EOF'
"""
Сущности товаров для каталога.
Модуль содержит dataclass для представления товаров согласно @product_idea.md
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Product:
    """
    Сущность товара из каталога.
    
    Поля соответствуют структуре Excel файла из @product_idea.md:
    - Обязательные: id, product_name, category_1, article
    - Опциональные: description, category_2, category_3, photo_url, page_url
    """
    
    # Обязательные поля
    id: str
    product_name: str    # наименование товара
    category_1: str      # категория 1-го уровня
    article: str         # артикул
    
    # Опциональные поля
    description: Optional[str] = None  # описание
    category_2: Optional[str] = None   # категория 2-го уровня
    category_3: Optional[str] = None   # категория 3-го уровня
    photo_url: Optional[str] = None    # ссылка на фото товара
    page_url: Optional[str] = None     # ссылка на страницу товара на сайте
    
    def get_search_text(self) -> str:
        """
        Формирует текст для индексации в векторной БД.
        Объединяет все текстовые поля для лучшего поиска.
        """
        search_parts = [
            self.product_name,
            self.description or "",
            self.category_1,
            self.category_2 or "",
            self.category_3 or "",
            self.article
        ]
        return " ".join(part for part in search_parts if part.strip())
    
    def get_display_name(self) -> str:
        """Возвращает название для отображения пользователю."""
        return self.product_name
    
    def get_full_category(self) -> str:
        """
        Возвращает полный путь категорий.
        Например: "Электроника > Компьютеры > Ноутбуки"
        """
        categories = [self.category_1, self.category_2 or "", self.category_3 or ""]
        return " > ".join(cat for cat in categories if cat.strip())


@dataclass 
class SearchResult:
    """
    Результат поиска товара с метрикой релевантности.
    """
    
    product: Product
    score: float  # оценка релевантности (0.0 - 1.0)
    
    def __post_init__(self) -> None:
        """Валидация оценки релевантности."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score должен быть между 0.0 и 1.0, получен: {self.score}")
EOF

success "Исправления применены!"

log "Перезапускаем приложение..."
docker-compose -f docker-compose.prod.yml up -d app

log "Ожидаем запуска приложения..."
sleep 10

log "Проверяем статус приложения..."
if docker-compose -f docker-compose.prod.yml ps app | grep -q "Up"; then
    success "Приложение успешно запущено!"
    
    log "Проверяем логи на наличие ошибок..."
    if docker-compose -f docker-compose.prod.yml logs --tail=20 app | grep -q "ERROR"; then
        warning "Обнаружены ошибки в логах. Проверьте: docker-compose logs app"
    else
        success "Ошибок в логах не обнаружено!"
    fi
    
    success "Исправление валидации каталога завершено!"
    log "Теперь можно перезапустить обработку каталога через админ-панель"
    
else
    error "Приложение не запустилось. Проверьте логи: docker-compose logs app"
    exit 1
fi
