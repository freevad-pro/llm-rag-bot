"""
Domain entity для категорий услуг компании
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ServiceCategory:
    """Сущность категории услуг"""
    id: Optional[int]
    name: str  # Техническое имя (например: development)
    display_name: str  # Отображаемое название (например: Разработка)
    description: Optional[str] = None
    color: Optional[str] = None  # Цвет в формате hex (#FF5733)
    icon: Optional[str] = None  # Иконка Bootstrap Icons (например: gear)
    is_active: bool = True
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def css_color_class(self) -> str:
        """Возвращает CSS класс для цвета"""
        if not self.color:
            return "text-secondary"
        return f"text-{self.color}" if not self.color.startswith('#') else ""
    
    @property
    def badge_color(self) -> str:
        """Возвращает цвет для badge"""
        color_map = {
            "#007bff": "primary",
            "#28a745": "success", 
            "#dc3545": "danger",
            "#ffc107": "warning",
            "#17a2b8": "info",
            "#6c757d": "secondary",
            "#343a40": "dark"
        }
        return color_map.get(self.color, "secondary")
    
    @property
    def icon_class(self) -> str:
        """Возвращает полный класс иконки"""
        if not self.icon:
            return "bi bi-gear"
        return f"bi bi-{self.icon}" if not self.icon.startswith('bi-') else f"bi {self.icon}"
    
    def __str__(self) -> str:
        return self.display_name
    
    def __repr__(self) -> str:
        return f"ServiceCategory(id={self.id}, name='{self.name}', display_name='{self.display_name}')"





