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
    - Все поля опциональные: id, product_name, description, category_1, category_2, category_3, article, photo_url, page_url
    - Если поле пустое, используется значение по умолчанию
    """
    
    # Все поля опциональные
    id: str = ""
    product_name: str = ""
    description: str = ""
    category_1: str = ""
    category_2: str = ""
    category_3: str = ""
    article: str = ""
    photo_url: Optional[str] = None
    page_url: Optional[str] = None
    
    def get_search_text(self) -> str:
        """
        Формирует текст для индексации в векторной БД.
        
        ВАЖНО: Артикул и название в начале для лучшего поиска!
        Embedding модели придают больше веса началу текста.
        Критично для sentence-transformers с лимитом 128 токенов.
        """
        parts = []
        
        # 1. Артикул (самый важный для точного поиска)
        if self.article and self.article.strip():
            parts.append(f"[{self.article}]")  # В квадратных скобках для выделения
        
        # 2. Название товара
        if self.product_name and self.product_name.strip():
            parts.append(self.product_name)
        
        # 3. Категории (для контекста)
        categories = [self.category_1, self.category_2 or "", self.category_3 or ""]
        category_path = " > ".join(c for c in categories if c.strip())
        if category_path:
            parts.append(category_path)
        
        # 4. Описание (в конце, может быть обрезано при лимите токенов)
        if self.description and self.description.strip():
            parts.append(self.description)
        
        return " | ".join(parts)
    
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
