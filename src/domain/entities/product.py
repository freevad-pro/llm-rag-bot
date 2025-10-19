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
