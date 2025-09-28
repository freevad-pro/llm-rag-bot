"""
Domain entity для услуг компании
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from .service_category import ServiceCategory


@dataclass
class CompanyService:
    """Сущность услуги компании"""
    id: Optional[int]
    name: str
    description: str
    category_id: Optional[int] = None
    category: Optional[ServiceCategory] = None  # Объект категории
    keywords: Optional[str] = None  # Ключевые слова через запятую
    price_info: Optional[str] = None  # Информация о цене
    is_active: bool = True
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def keywords_list(self) -> List[str]:
        """Возвращает список ключевых слов"""
        if not self.keywords:
            return []
        return [kw.strip() for kw in self.keywords.split(',') if kw.strip()]
    
    @property
    def category_display(self) -> str:
        """Отображаемое название категории"""
        if self.category:
            return self.category.display_name
        return "Без категории"
    
    @property
    def category_badge_color(self) -> str:
        """Цвет badge для категории"""
        if self.category:
            return self.category.badge_color
        return "secondary"
    
    @property
    def category_icon(self) -> str:
        """Иконка категории"""
        if self.category:
            return self.category.icon_class
        return "bi bi-question-circle"
    
    @property
    def short_description(self) -> str:
        """Краткое описание (первые 100 символов)"""
        if len(self.description) <= 100:
            return self.description
        return self.description[:97] + "..."
    
    @property
    def has_price_info(self) -> bool:
        """Есть ли информация о цене"""
        return bool(self.price_info and self.price_info.strip())
    
    def matches_search(self, search_term: str) -> bool:
        """Проверяет соответствие поисковому запросу"""
        if not search_term:
            return True
            
        search_lower = search_term.lower()
        
        # Поиск в названии
        if search_lower in self.name.lower():
            return True
            
        # Поиск в описании
        if search_lower in self.description.lower():
            return True
            
        # Поиск в ключевых словах
        if self.keywords and search_lower in self.keywords.lower():
            return True
            
        # Поиск в информации о цене
        if self.price_info and search_lower in self.price_info.lower():
            return True
            
        return False
