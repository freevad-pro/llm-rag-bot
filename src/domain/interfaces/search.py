"""
Протоколы и интерфейсы для поиска по каталогу.
Определяет контракты для поисковых сервисов согласно Clean Architecture.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Optional

from ..entities.product import Product, SearchResult


class CatalogSearchProtocol(Protocol):
    """
    Протокол для поиска товаров в каталоге.
    Определяет интерфейс векторного поиска через Chroma DB.
    """
    
    async def index_catalog(self, excel_path: str) -> None:
        """
        Индексирует каталог товаров из Excel файла.
        
        Args:
            excel_path: Путь к Excel файлу с товарами
            
        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если структура файла некорректна
        """
        ...
    
    async def search_products(
        self, 
        query: str, 
        category: Optional[str] = None,
        k: int = 10
    ) -> list[SearchResult]:
        """
        Выполняет семантический поиск товаров.
        
        Args:
            query: Поисковый запрос пользователя
            category: Опциональный фильтр по категории  
            k: Максимальное количество результатов
            
        Returns:
            Список результатов поиска с оценками релевантности
        """
        ...
    
    async def get_categories(self) -> list[str]:
        """
        Возвращает список всех доступных категорий.
        
        Returns:
            Список уникальных категорий из каталога
        """
        ...
        
    async def is_indexed(self) -> bool:
        """
        Проверяет, проиндексирован ли каталог.
        
        Returns:
            True если каталог готов к поиску, False иначе
        """
        ...


class ExcelLoaderProtocol(Protocol):
    """
    Протокол для загрузки данных из Excel файлов.
    """
    
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
        ...
    
    def validate_excel_structure(self, excel_path: str) -> dict[str, bool]:
        """
        Валидирует структуру Excel файла.
        
        Args:
            excel_path: Путь к Excel файлу
            
        Returns:
            Словарь с результатами валидации обязательных полей
        """
        ...


class SearchIndexProtocol(Protocol):
    """
    Протокол для работы с поисковым индексом.
    """
    
    async def create_index(self, products: list[Product]) -> None:
        """
        Создает векторный индекс для списка товаров.
        
        Args:
            products: Список товаров для индексации
        """
        ...
    
    async def search(
        self, 
        query: str, 
        filter_metadata: Optional[dict] = None,
        k: int = 10
    ) -> list[SearchResult]:
        """
        Выполняет поиск в индексе.
        
        Args:
            query: Поисковый запрос
            filter_metadata: Опциональные фильтры
            k: Количество результатов
            
        Returns:
            Результаты поиска
        """
        ...
    
    async def clear_index(self) -> None:
        """Очищает существующий индекс."""
        ...


class SearchRepositoryProtocol(Protocol):
    """
    Протокол для репозитория поисковых данных.
    Может использоваться для кэширования и метаданных.
    """
    
    async def save_search_metadata(
        self, 
        catalog_hash: str, 
        indexed_at: str,
        products_count: int
    ) -> None:
        """
        Сохраняет метаданные индексации.
        
        Args:
            catalog_hash: Хэш каталога для проверки изменений
            indexed_at: Время индексации  
            products_count: Количество проиндексированных товаров
        """
        ...
    
    async def get_search_metadata(self) -> Optional[dict]:
        """
        Получает метаданные последней индексации.
        
        Returns:
            Словарь с метаданными или None
        """
        ...


# Абстрактные базовые классы для имплементации

class BaseSearchService(ABC):
    """
    Базовый класс для поисковых сервисов.
    Реализует общую логику согласно @vision.md
    """
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Проверка работоспособности сервиса."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> dict:
        """Получение статистики работы сервиса."""
        pass
