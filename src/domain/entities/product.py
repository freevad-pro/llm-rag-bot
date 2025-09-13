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
    - Обязательные: id, section_name_1, section_name_2, product_name, description, category, article
    - Опциональные: photo_url, page_url
    """
    
    # Обязательные поля
    id: str
    section_name_1: str  # наименование раздела
    section_name_2: str  # наименование подраздела  
    product_name: str    # наименование товара
    description: str     # описание
    category: str        # категория
    article: str         # артикул
    
    # Опциональные поля
    photo_url: Optional[str] = None    # ссылка на фото товара
    page_url: Optional[str] = None     # ссылка на страницу товара на сайте
    
    def get_search_text(self) -> str:
        """
        Формирует текст для индексации в векторной БД.
        Объединяет все текстовые поля для лучшего поиска.
        """
        search_parts = [
            self.product_name,
            self.description,
            self.section_name_1,
            self.section_name_2,
            self.category,
            self.article
        ]
        return " ".join(part for part in search_parts if part.strip())
    
    def get_display_name(self) -> str:
        """Возвращает название для отображения пользователю."""
        return self.product_name
    
    def get_full_category(self) -> str:
        """Возвращает полный путь категории: раздел > подраздел > категория."""
        return f"{self.section_name_1} > {self.section_name_2} > {self.category}"


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
