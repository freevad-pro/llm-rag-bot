"""
Сервис поиска по каталогу товаров с использованием Chroma DB.
Реализует CatalogSearchProtocol согласно @vision.md
"""

import logging
import hashlib
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

from ...domain.entities.product import Product, SearchResult
from ...domain.interfaces.search import CatalogSearchProtocol, BaseSearchService
from .excel_loader import ExcelCatalogLoader

logger = logging.getLogger(__name__)


class CatalogSearchService(BaseSearchService):
    """
    Сервис поиска товаров через Chroma DB.
    
    Использует:
    - HuggingFaceEmbeddings: paraphrase-multilingual-MiniLM-L12-v2 (согласно @vision.md)
    - Chroma persist_directory: /app/data/chroma
    - Blue-green deployment при переиндексации
    """
    
    COLLECTION_NAME = "products_catalog"
    EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    
    def __init__(self, persist_dir: str = "/app/data/chroma") -> None:
        """
        Инициализация сервиса поиска.
        
        Args:
            persist_dir: Директория для персистентного хранения Chroma DB
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._persist_dir = Path(persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Инициализация Chroma клиента
        self._client = chromadb.PersistentClient(
            path=str(self._persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Инициализация функции эмбеддингов
        self._embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.EMBEDDING_MODEL
        )
        
        # Загрузчик Excel файлов
        self._excel_loader = ExcelCatalogLoader()
        
        # Кэш для коллекции
        self._collection = None
        
        self._logger.info(f"Инициализирован CatalogSearchService с persist_dir: {persist_dir}")
    
    async def index_catalog(self, excel_path: str) -> None:
        """
        Индексирует каталог товаров из Excel файла.
        Реализует blue-green deployment.
        
        Args:
            excel_path: Путь к Excel файлу с товарами
            
        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если структура файла некорректна
        """
        self._logger.info(f"Начинаю индексацию каталога из {excel_path}")
        
        try:
            # Загружаем товары из Excel
            products = await self._excel_loader.load_products(excel_path)
            
            if not products:
                raise ValueError("Не найдено товаров для индексации")
            
            # Blue-green deployment: создаем временную коллекцию
            temp_collection_name = f"{self.COLLECTION_NAME}_temp"
            
            # Удаляем временную коллекцию если существует
            try:
                self._client.delete_collection(temp_collection_name)
            except Exception:
                pass  # Коллекция не существует
            
            # Создаем временную коллекцию
            temp_collection = self._client.create_collection(
                name=temp_collection_name,
                embedding_function=self._embedding_function
            )
            
            # Индексируем товары в временную коллекцию
            await self._index_products_to_collection(temp_collection, products)
            
            # Атомарно переключаемся: удаляем старую, переименовываем временную
            try:
                self._client.delete_collection(self.COLLECTION_NAME)
            except Exception:
                pass  # Основная коллекция не существует
            
            # Пересоздаем основную коллекцию
            main_collection = self._client.create_collection(
                name=self.COLLECTION_NAME,
                embedding_function=self._embedding_function
            )
            
            # Копируем данные из временной в основную
            await self._copy_collection_data(temp_collection, main_collection)
            
            # Удаляем временную коллекцию
            self._client.delete_collection(temp_collection_name)
            
            # Обновляем кэш
            self._collection = main_collection
            
            self._logger.info(f"Успешно проиндексировано {len(products)} товаров")
            
        except Exception as e:
            self._logger.error(f"Ошибка индексации каталога: {e}")
            # Очищаем временную коллекцию в случае ошибки
            try:
                self._client.delete_collection(f"{self.COLLECTION_NAME}_temp")
            except Exception:
                pass
            raise
    
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
        if not query.strip():
            return []
        
        collection = await self._get_collection()
        if not collection:
            self._logger.warning("Коллекция не найдена, каталог не проиндексирован")
            return []
        
        try:
            # Подготавливаем фильтры
            where_filter = {}
            if category:
                where_filter["category"] = category
            
            # Выполняем поиск
            results = collection.query(
                query_texts=[query],
                n_results=min(k, 50),  # Ограничиваем максимум
                where=where_filter if where_filter else None
            )
            
            # Преобразуем результаты
            search_results = []
            
            if results["documents"] and results["documents"][0]:
                documents = results["documents"][0]
                metadatas = results["metadatas"][0] if results["metadatas"] else []
                distances = results["distances"][0] if results["distances"] else []
                
                for i in range(len(documents)):
                    try:
                        metadata = metadatas[i] if i < len(metadatas) else {}
                        distance = distances[i] if i < len(distances) else 1.0
                        
                        # Преобразуем distance в score (чем меньше distance, тем больше score)
                        score = max(0.0, 1.0 - distance)
                        
                        # Создаем объект Product из метаданных
                        product = Product(
                            id=metadata.get("id", ""),
                            section_name_1=metadata.get("section_name_1", ""),
                            section_name_2=metadata.get("section_name_2", ""),
                            product_name=metadata.get("product_name", ""),
                            description=metadata.get("description", ""),
                            category=metadata.get("category", ""),
                            article=metadata.get("article", ""),
                            photo_url=metadata.get("photo_url"),
                            page_url=metadata.get("page_url")
                        )
                        
                        search_results.append(SearchResult(product=product, score=score))
                        
                    except Exception as e:
                        self._logger.warning(f"Ошибка обработки результата поиска: {e}")
                        continue
            
            self._logger.debug(f"Найдено {len(search_results)} результатов для запроса: {query}")
            return search_results
            
        except Exception as e:
            self._logger.error(f"Ошибка поиска: {e}")
            return []
    
    async def get_categories(self) -> list[str]:
        """
        Возвращает список всех доступных категорий.
        
        Returns:
            Список уникальных категорий из каталога
        """
        collection = await self._get_collection()
        if not collection:
            return []
        
        try:
            # Получаем все документы
            results = collection.get()
            
            if not results["metadatas"]:
                return []
            
            # Извлекаем уникальные категории
            categories = set()
            for metadata in results["metadatas"]:
                category = metadata.get("category")
                if category:
                    categories.add(category)
            
            return sorted(list(categories))
            
        except Exception as e:
            self._logger.error(f"Ошибка получения категорий: {e}")
            return []
    
    async def is_indexed(self) -> bool:
        """
        Проверяет, проиндексирован ли каталог.
        
        Returns:
            True если каталог готов к поиску, False иначе
        """
        try:
            collection = await self._get_collection()
            if not collection:
                return False
            
            # Проверяем количество документов
            count = collection.count()
            return count > 0
            
        except Exception as e:
            self._logger.error(f"Ошибка проверки индекса: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Проверка работоспособности сервиса."""
        try:
            # Проверяем подключение к Chroma
            collections = self._client.list_collections()
            
            # Проверяем доступность модели эмбеддингов
            test_embedding = self._embedding_function(["test"])
            
            return True
            
        except Exception as e:
            self._logger.error(f"Health check failed: {e}")
            return False
    
    async def get_stats(self) -> dict:
        """Получение статистики работы сервиса."""
        try:
            collection = await self._get_collection()
            
            stats = {
                "indexed": await self.is_indexed(),
                "persist_dir": str(self._persist_dir),
                "embedding_model": self.EMBEDDING_MODEL,
                "collection_name": self.COLLECTION_NAME
            }
            
            if collection:
                stats["documents_count"] = collection.count()
                stats["categories_count"] = len(await self.get_categories())
            else:
                stats["documents_count"] = 0
                stats["categories_count"] = 0
            
            return stats
            
        except Exception as e:
            self._logger.error(f"Ошибка получения статистики: {e}")
            return {"error": str(e)}
    
    async def _get_collection(self):
        """Получает коллекцию Chroma (с кэшированием)."""
        if self._collection is None:
            try:
                self._collection = self._client.get_collection(
                    name=self.COLLECTION_NAME,
                    embedding_function=self._embedding_function
                )
            except Exception:
                # Коллекция не существует
                return None
        
        return self._collection
    
    async def _index_products_to_collection(self, collection, products: list[Product]) -> None:
        """Индексирует список товаров в указанную коллекцию."""
        batch_size = 100  # Обрабатываем порциями для больших каталогов
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            
            # Подготавливаем данные для batch insert
            ids = []
            documents = []
            metadatas = []
            
            for product in batch:
                ids.append(product.id)
                documents.append(product.get_search_text())
                
                # Подготавливаем метаданные
                metadata = {
                    "id": product.id,
                    "section_name_1": product.section_name_1,
                    "section_name_2": product.section_name_2,
                    "product_name": product.product_name,
                    "description": product.description,
                    "category": product.category,
                    "article": product.article
                }
                
                if product.photo_url:
                    metadata["photo_url"] = product.photo_url
                if product.page_url:
                    metadata["page_url"] = product.page_url
                
                metadatas.append(metadata)
            
            # Добавляем batch в коллекцию
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            self._logger.debug(f"Проиндексирована порция {i + 1}-{i + len(batch)} из {len(products)}")
    
    async def _copy_collection_data(self, source_collection, target_collection) -> None:
        """Копирует данные из одной коллекции в другую."""
        # Получаем все данные из источника
        source_data = source_collection.get()
        
        if source_data["ids"]:
            # Копируем данные в целевую коллекцию
            target_collection.add(
                ids=source_data["ids"],
                documents=source_data["documents"],
                metadatas=source_data["metadatas"]
            )
