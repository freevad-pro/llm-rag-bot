"""
Сервис поиска по каталогу товаров с использованием Chroma DB.
Реализует CatalogSearchProtocol согласно @vision.md
"""

import logging
import hashlib
import warnings
import gc
import psutil
import time
import asyncio
from pathlib import Path
from typing import Optional

# Подавляем предупреждения телеметрии ChromaDB
warnings.filterwarnings("ignore", message=".*telemetry.*")
warnings.filterwarnings("ignore", message=".*posthog.*")

import chromadb
from chromadb.config import Settings

# Дополнительное подавление ошибок телеметрии через monkey patching
def _silence_telemetry():
    """Подавляет сообщения об ошибках телеметрии ChromaDB"""
    try:
        # Подавляем на уровне posthog модуля
        import chromadb.telemetry.posthog as posthog_module
        original_capture = getattr(posthog_module, 'capture', None)
        if original_capture:
            def silent_capture(*args, **kwargs):
                pass
            posthog_module.capture = silent_capture
            
        # Подавляем на уровне логгера
        import chromadb.telemetry
        telemetry_logger = logging.getLogger('chromadb.telemetry')
        telemetry_logger.setLevel(logging.CRITICAL + 1)  # Выше CRITICAL
        
        # Дополнительное подавление через stdout перехват
        import sys
        class TelemetryFilter:
            def __init__(self, stream):
                self.stream = stream
                
            def write(self, data):
                if 'Failed to send telemetry event' not in str(data) and 'telemetry' not in str(data).lower():
                    self.stream.write(data)
                    
            def flush(self):
                self.stream.flush()
                
        # Применяем фильтр только если еще не применен
        if not hasattr(sys.stderr, '_telemetry_filtered'):
            sys.stderr = TelemetryFilter(sys.stderr)
            sys.stderr._telemetry_filtered = True
            
    except (ImportError, AttributeError):
        pass

# Вызываем функцию подавления
_silence_telemetry()

from ...domain.entities.product import Product, SearchResult
from ...domain.interfaces.search import CatalogSearchProtocol, BaseSearchService
from ...config.settings import settings
from .excel_loader import ExcelCatalogLoader
from .openai_embeddings import OpenAIEmbeddingFunction
from .sentence_transformers_embeddings import SentenceTransformersEmbeddingFunction

logger = logging.getLogger(__name__)


class CatalogSearchService(BaseSearchService):
    """
    Сервис поиска товаров через Chroma DB.
    
    Использует:
    - OpenAI Embeddings API: text-embedding-3-small (оптимизация после MVP)
    - Chroma persist_directory: /app/data/chroma
    - Blue-green deployment при переиндексации
    
    Преимущества OpenAI embeddings:
    - Экономия ~350MB в Docker образе
    - Лучшее качество поиска для коммерческих каталогов
    - Оптимизация для CPU-серверов
    """
    
    COLLECTION_NAME = "products_catalog"
    
    def __init__(self, persist_dir: Optional[str] = None) -> None:
        """
        Инициализация сервиса поиска.
        
        Args:
            persist_dir: Директория для персистентного хранения Chroma DB
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._persist_dir = Path(persist_dir or settings.chroma_persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Настройки из конфигурации
        self.embedding_model = settings.embedding_model
        self.embedding_provider = settings.embedding_provider
        
        # Инициализация Chroma клиента с полным отключением телеметрии
        chroma_settings = Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
        self._client = chromadb.PersistentClient(
            path=str(self._persist_dir),
            settings=chroma_settings
        )
        
        # Инициализация функции эмбеддингов
        if self.embedding_provider == "openai":
            self._embedding_function = OpenAIEmbeddingFunction(
                model=self.embedding_model,
                batch_size=settings.embedding_batch_size
            )
        elif self.embedding_provider == "sentence-transformers":
            # Пытаемся использовать глобальный singleton если доступен
            from .sentence_transformers_embeddings import get_global_embedding_instance
            
            global_instance = get_global_embedding_instance()
            
            if global_instance is not None and global_instance.model_name == self.embedding_model:
                # Используем готовый singleton с загруженной моделью
                self._embedding_function = global_instance
                self._logger.info(f"Используется глобальный singleton embeddings: {self.embedding_model} (модель уже в памяти)")
            else:
                # Создаём новый экземпляр с lazy loading
                self._embedding_function = SentenceTransformersEmbeddingFunction(
                    model_name=self.embedding_model,
                    batch_size=settings.embedding_batch_size
                )
                self._logger.info(f"Создан новый экземпляр embeddings: {self.embedding_model} (модель будет загружена при первом использовании)")
        else:
            raise ValueError(f"Неподдерживаемый embedding provider: {self.embedding_provider}. "
                           f"Поддерживаются: openai, sentence-transformers")
        
        self._logger.info(f"Используется {self.embedding_provider} embeddings: {self.embedding_model}")
        
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
            
            # Создаем временную коллекцию с cosine similarity
            temp_collection = self._client.create_collection(
                name=temp_collection_name,
                embedding_function=self._embedding_function,
                metadata={"hnsw:space": "cosine"}  # Используем cosine similarity
            )
            
            # Индексируем товары в временную коллекцию
            await self._index_products_to_collection(temp_collection, products)
            
            # Атомарно переключаемся: удаляем старую, переименовываем временную
            try:
                self._client.delete_collection(self.COLLECTION_NAME)
            except Exception:
                pass  # Основная коллекция не существует
            
            # Пересоздаем основную коллекцию с cosine similarity
            main_collection = self._client.create_collection(
                name=self.COLLECTION_NAME,
                embedding_function=self._embedding_function,
                metadata={"hnsw:space": "cosine"}  # Используем cosine similarity
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
        Выполняет гибридный поиск товаров: точный/префиксный по артикулу + семантический.
        
        Алгоритм:
        1. Пытается точный поиск по артикулу в метаданных
        2. Пытается префиксный поиск по артикулу
        3. Выполняет семантический поиск через эмбеддинги
        4. Объединяет и ранжирует результаты
        
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
            query_lower = query.strip().lower()
            
            # Шаг 1: Точный поиск по артикулу (приоритет)
            exact_matches = await self._search_by_article_exact(collection, query_lower, category)
            
            # Шаг 2: Префиксный поиск по артикулу
            prefix_matches = await self._search_by_article_prefix(collection, query_lower, category)
            
            # Шаг 3: Семантический поиск через эмбеддинги
            semantic_results = await self._semantic_search(collection, query, category, k)
            
            # Шаг 4: Объединяем результаты (убираем дубликаты, сохраняем лучший score)
            merged_results = self._merge_search_results(exact_matches, prefix_matches, semantic_results)
            
            self._logger.debug(
                f"Гибридный поиск '{query}': "
                f"exact={len(exact_matches)}, prefix={len(prefix_matches)}, "
                f"semantic={len(semantic_results)}, merged={len(merged_results)}"
            )
            
            # Применяем улучшения: boost и фильтрацию
            improved_results = self._improve_search_results(merged_results, query)
            
            self._logger.debug(f"После улучшений: {len(improved_results)} результатов")
            return improved_results
            
        except Exception as e:
            self._logger.error(f"Ошибка поиска: {e}")
            return []
    
    async def _search_by_article_exact(
        self, 
        collection, 
        query: str,
        category: Optional[str] = None
    ) -> list[SearchResult]:
        """
        Точный поиск по артикулу в метаданных (без учета регистра).
        
        Args:
            collection: Коллекция Chroma
            query: Поисковый запрос (уже в нижнем регистре)
            category: Опциональный фильтр по категории
            
        Returns:
            Список результатов с максимальным score=1.0
        """
        try:
            # КРИТИЧНО: Получаем ВСЕ документы (по умолчанию limit=10!)
            # Получаем количество документов сначала
            total_count = collection.count()
            if total_count == 0:
                return []
            
            # Получаем все документы с явным limit
            all_results = collection.get(limit=total_count)
            
            exact_matches = []
            if all_results["metadatas"]:
                for metadata in all_results["metadatas"]:
                    article = (metadata.get("article") or "").lower()
                    
                    # Проверяем точное совпадение
                    if article == query:
                        # Проверяем фильтр категории если нужен
                        if category and metadata.get("category_1") != category:
                            continue
                        
                        # Создаем Product из метаданных
                        product = Product(
                            id=metadata.get("id", ""),
                            product_name=metadata.get("product_name", ""),
                            description=metadata.get("description", ""),
                            category_1=metadata.get("category_1", ""),
                            category_2=metadata.get("category_2", ""),
                            category_3=metadata.get("category_3", ""),
                            article=metadata.get("article", ""),
                            photo_url=metadata.get("photo_url"),
                            page_url=metadata.get("page_url")
                        )
                        
                        # Точное совпадение артикула = максимальный score
                        exact_matches.append(SearchResult(product=product, score=1.0))
            
            if exact_matches:
                self._logger.debug(f"Найдено {len(exact_matches)} точных совпадений по артикулу '{query}'")
            
            return exact_matches
            
        except Exception as e:
            self._logger.warning(f"Ошибка точного поиска по артикулу: {e}")
            return []
    
    async def _search_by_article_prefix(
        self, 
        collection, 
        query: str,
        category: Optional[str] = None
    ) -> list[SearchResult]:
        """
        Префиксный поиск по артикулу в метаданных.
        Находит артикулы начинающиеся с запроса, например "PG-R" найдет "PG-R-23600"
        
        Args:
            collection: Коллекция Chroma
            query: Поисковый запрос (уже в нижнем регистре)
            category: Опциональный фильтр по категории
            
        Returns:
            Список результатов с высоким score=0.9
        """
        try:
            # Пропускаем если запрос слишком короткий (менее 2 символов)
            if len(query) < 2:
                return []
            
            # КРИТИЧНО: Получаем ВСЕ документы
            total_count = collection.count()
            if total_count == 0:
                return []
            
            all_results = collection.get(limit=total_count)
            
            prefix_matches = []
            if all_results["metadatas"]:
                for metadata in all_results["metadatas"]:
                    article = (metadata.get("article") or "").lower()
                    
                    # Проверяем префикс (но не точное совпадение - оно уже обработано)
                    if article.startswith(query) and article != query:
                        # Проверяем фильтр категории если нужен
                        if category and metadata.get("category_1") != category:
                            continue
                        
                        # Создаем Product из метаданных
                        product = Product(
                            id=metadata.get("id", ""),
                            product_name=metadata.get("product_name", ""),
                            description=metadata.get("description", ""),
                            category_1=metadata.get("category_1", ""),
                            category_2=metadata.get("category_2", ""),
                            category_3=metadata.get("category_3", ""),
                            article=metadata.get("article", ""),
                            photo_url=metadata.get("photo_url"),
                            page_url=metadata.get("page_url")
                        )
                        
                        # Префикс артикула = высокий score (0.9)
                        prefix_matches.append(SearchResult(product=product, score=0.9))
            
            if prefix_matches:
                self._logger.debug(f"Найдено {len(prefix_matches)} префиксных совпадений по артикулу '{query}'")
            
            return prefix_matches
            
        except Exception as e:
            self._logger.warning(f"Ошибка префиксного поиска по артикулу: {e}")
            return []
    
    async def _semantic_search(
        self, 
        collection, 
        query: str,
        category: Optional[str] = None,
        k: int = 10
    ) -> list[SearchResult]:
        """
        Семантический поиск через эмбеддинги.
        
        Args:
            collection: Коллекция Chroma
            query: Поисковый запрос (исходный, не lowercase)
            category: Опциональный фильтр по категории
            k: Количество результатов
            
        Returns:
            Список результатов поиска
        """
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
                        
                        # Преобразуем cosine distance в score 
                        # Для cosine: distance = 1 - similarity, поэтому score = 1 - distance
                        score = max(0.0, 1.0 - distance)
                        
                        # Создаем объект Product из метаданных
                        product = Product(
                            id=metadata.get("id", ""),
                            product_name=metadata.get("product_name", ""),
                            description=metadata.get("description", ""),
                            category_1=metadata.get("category_1", ""),
                            category_2=metadata.get("category_2", ""),
                            category_3=metadata.get("category_3", ""),
                            article=metadata.get("article", ""),
                            photo_url=metadata.get("photo_url"),
                            page_url=metadata.get("page_url")
                        )
                        
                        search_results.append(SearchResult(product=product, score=score))
                        
                    except Exception as e:
                        self._logger.warning(f"Ошибка обработки результата поиска: {e}")
                        continue
            
            return search_results
            
        except Exception as e:
            self._logger.error(f"Ошибка семантического поиска: {e}")
            return []
    
    def _merge_search_results(
        self, 
        exact_matches: list[SearchResult],
        prefix_matches: list[SearchResult],
        semantic_results: list[SearchResult]
    ) -> list[SearchResult]:
        """
        Объединяет результаты разных типов поиска, убирая дубликаты.
        
        При дубликатах сохраняется результат с максимальным score.
        Приоритет: exact > prefix > semantic
        
        Args:
            exact_matches: Точные совпадения по артикулу
            prefix_matches: Префиксные совпадения
            semantic_results: Семантический поиск
            
        Returns:
            Объединенный список результатов
        """
        # Словарь для хранения лучших результатов по product.id
        best_results = {}
        
        # Добавляем все результаты, сохраняя лучший score для каждого товара
        for results_list in [exact_matches, prefix_matches, semantic_results]:
            for result in results_list:
                product_id = result.product.id
                
                if product_id not in best_results or result.score > best_results[product_id].score:
                    best_results[product_id] = result
        
        # Преобразуем обратно в список и сортируем по score
        merged = list(best_results.values())
        merged.sort(key=lambda x: x.score, reverse=True)
        
        return merged
    
    def _improve_search_results(self, results: list[SearchResult], query: str) -> list[SearchResult]:
        """
        Улучшает результаты поиска: добавляет boost за совпадения в названии и фильтрует по score.
        
        Args:
            results: Исходные результаты поиска
            query: Поисковый запрос
            
        Returns:
            Улучшенные и отфильтрованные результаты
        """
        if not results:
            return results
            
        improved_results = []
        query_words = set(word.lower().strip() for word in query.split() if len(word.strip()) > 1)
        
        for result in results:
            # Применяем boost за совпадения в названии
            boosted_score = self._calculate_name_boost(result, query_words)
            
            # Применяем фильтр по минимальному score
            if boosted_score >= settings.search_min_score:
                # Создаем новый результат с улучшенным score
                improved_result = SearchResult(
                    product=result.product,
                    score=boosted_score
                )
                improved_results.append(improved_result)
        
        # Сортируем по убыванию score
        improved_results.sort(key=lambda x: x.score, reverse=True)
        
        # Ограничиваем количество результатов согласно настройкам
        max_results = settings.search_max_results
        if len(improved_results) > max_results:
            improved_results = improved_results[:max_results]
            self._logger.debug(f"Ограничено до {max_results} результатов")
        
        return improved_results
    
    def _calculate_name_boost(self, result: SearchResult, query_words: set[str]) -> float:
        """
        Рассчитывает boost за совпадения слов запроса в названии и артикуле товара.
        
        Использует поиск подстрок вместо точного совпадения слов для лучшего результата.
        Например: "винт" найдет "Винт М6", "PG-R" найдет "PG-R-23600"
        
        Args:
            result: Результат поиска
            query_words: Слова поискового запроса (в нижнем регистре)
            
        Returns:
            Улучшенный score
        """
        base_score = result.score
        product_name = result.product.product_name.lower()
        product_article = result.product.article.lower() if result.product.article else ""
        
        total_boost = 0.0
        
        # 1. Boost за совпадения в названии товара (поиск подстрок)
        name_matches = 0
        name_exact_matches = 0  # Для точных совпадений слов
        
        for word in query_words:
            if word in product_name:
                name_matches += 1
                # Проверяем точное совпадение слова (word boundary)
                import re
                if re.search(rf'\b{re.escape(word)}\b', product_name):
                    name_exact_matches += 1
        
        if name_matches > 0 and len(query_words) > 0:
            # Базовый boost за подстроку
            name_boost_factor = name_matches / len(query_words)
            name_boost = settings.search_name_boost * name_boost_factor
            
            # Дополнительный boost за точное совпадение слова
            if name_exact_matches > 0:
                exact_boost_factor = name_exact_matches / len(query_words)
                name_boost += settings.search_name_boost * 0.5 * exact_boost_factor
            
            total_boost += name_boost
            
            self._logger.debug(
                f"Name boost для '{result.product.product_name}': "
                f"+{name_boost:.3f} ({name_matches}/{len(query_words)} подстрок, "
                f"{name_exact_matches} точных совпадений)"
            )
        
        # 2. Boost за совпадения в артикуле (более высокий приоритет)
        if product_article:
            article_matches = 0
            article_prefix_match = False
            
            for word in query_words:
                if word in product_article:
                    article_matches += 1
                    # Проверяем начинается ли артикул с этого слова (префикс)
                    if product_article.startswith(word):
                        article_prefix_match = True
            
            if article_matches > 0 and len(query_words) > 0:
                article_boost_factor = article_matches / len(query_words)
                article_boost = settings.search_article_boost * article_boost_factor
                
                # Дополнительный boost за префикс (критично для артикулов типа "PG-R")
                if article_prefix_match:
                    article_boost += settings.search_article_boost * 0.5
                
                total_boost += article_boost
                
                self._logger.debug(
                    f"Article boost для '{result.product.article}': "
                    f"+{article_boost:.3f} ({article_matches}/{len(query_words)} совпадений, "
                    f"prefix={article_prefix_match})"
                )
        
        if total_boost > 0:
            # Ограничиваем итоговый score значением 1.0
            boosted_score = min(1.0, base_score + total_boost)
            
            self._logger.debug(
                f"Итоговый boost для '{result.product.product_name}': "
                f"{base_score:.3f} + {total_boost:.3f} = {boosted_score:.3f}"
            )
            
            return boosted_score
        
        return base_score
    
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
            # КРИТИЧНО: Получаем ВСЕ документы (по умолчанию limit=10!)
            total_count = collection.count()
            if total_count == 0:
                return []
            
            results = collection.get(limit=total_count)
            
            if not results["metadatas"]:
                return []
            
            # Извлекаем уникальные категории (из всех трех уровней)
            categories = set()
            for metadata in results["metadatas"]:
                for level in ["category_1", "category_2", "category_3"]:
                    category = metadata.get(level)
                    if category and category.strip():
                        categories.add(category.strip())
            
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
            if not test_embedding or len(test_embedding) == 0:
                return False
            
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
                "embedding_model": self.embedding_model,
                "embedding_provider": "OpenAI",
                "collection_name": self.COLLECTION_NAME,
                "optimization": "CPU-optimized (no sentence-transformers)"
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
                    "product_name": product.product_name,
                    "description": product.description,
                    "category_1": product.category_1,
                    "category_2": product.category_2,
                    "category_3": product.category_3,
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
    
    async def _copy_collection_data(self, source_collection, target_collection, progress_callback=None) -> None:
        """
        Копирует данные из одной коллекции в другую батчами.
        
        Это предотвращает зависание при копировании больших коллекций (40K+ товаров)
        и снижает потребление памяти.
        """
        try:
            # Получаем общее количество документов
            total_count = source_collection.count()
            if total_count == 0:
                self._logger.info("Исходная коллекция пуста, копирование не требуется")
                return
            
            self._logger.info(f"Начинаю копирование {total_count} документов батчами...")
            
            # Размер батча - баланс между памятью и производительностью
            batch_size = 1000
            offset = 0
            copied_count = 0
            
            while offset < total_count:
                # Получаем батч данных
                batch_data = source_collection.get(
                    limit=batch_size,
                    offset=offset
                )
                
                if not batch_data["ids"]:
                    break
                
                # Копируем батч в целевую коллекцию
                target_collection.add(
                    ids=batch_data["ids"],
                    documents=batch_data["documents"],
                    metadatas=batch_data["metadatas"]
                )
                
                copied_count += len(batch_data["ids"])
                offset += batch_size
                
                # Логируем прогресс каждые 5000 документов
                if copied_count % 5000 == 0:
                    progress = (copied_count / total_count) * 100
                    self._logger.info(f"Скопировано {copied_count}/{total_count} документов ({progress:.1f}%)")
                    # Сообщаем наружу о прогрессе копирования
                    if progress_callback is not None:
                        try:
                            await progress_callback(progress, copied_count, total_count)
                        except Exception as cb_err:
                            # Не прерываем копирование при ошибке колбэка
                            self._logger.warning(f"Ошибка колбэка прогресса копирования: {cb_err}")
                
                # Даем системе передохнуть между батчами
                await asyncio.sleep(0.01)  # 10ms пауза
            
            self._logger.info(f"Копирование завершено: {copied_count} документов")
            
        except Exception as e:
            self._logger.error(f"Ошибка копирования данных коллекции: {e}")
            raise e
    
    # Методы для blue-green deployment
    
    async def create_collection(self, collection_name: str) -> None:
        """
        Создает новую коллекцию для blue-green deployment.
        
        Args:
            collection_name: Имя коллекции
        """
        try:
            collection = self._client.create_collection(
                name=collection_name,
                embedding_function=self._embedding_function
            )
            self._logger.info(f"Создана коллекция: {collection_name}")
            
        except Exception as e:
            # Если коллекция уже существует, удаляем и создаем заново
            try:
                self._client.delete_collection(collection_name)
                collection = self._client.create_collection(
                    name=collection_name,
                    embedding_function=self._embedding_function
                )
                self._logger.info(f"Пересоздана коллекция: {collection_name}")
            except Exception as create_error:
                self._logger.error(f"Ошибка создания коллекции {collection_name}: {create_error}")
                raise create_error
    
    async def index_products_batch(self, products: list, collection_name: str) -> None:
        """
        Индексирует батч товаров в указанную коллекцию с оптимизацией памяти.
        
        Args:
            products: Список товаров для индексации
            collection_name: Имя коллекции
        """
        try:
            collection = self._client.get_collection(
                name=collection_name,
                embedding_function=self._embedding_function
            )
            
            # Подготавливаем данные для индексации
            ids = []
            documents = []
            metadatas = []
            
            for product in products:
                # Создаем уникальный ID
                product_id = f"product_{product.id}"
                ids.append(product_id)
                
                # Создаем документ для поиска
                document = self._create_search_document(product)
                documents.append(document)
                
                # Создаем метаданные
                metadata = self._create_product_metadata(product)
                metadatas.append(metadata)
            
            # Добавляем в коллекцию
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            # Агрессивная очистка памяти
            del ids, documents, metadatas
            gc.collect()
            
            # Дополнительная пауза для стабилизации
            await asyncio.sleep(0.2)
            
            self._logger.debug(f"Проиндексировано {len(products)} товаров в коллекцию {collection_name}")
            
        except Exception as e:
            self._logger.error(f"Ошибка индексации батча в коллекцию {collection_name}: {e}")
            raise e
    
    async def get_collection(self, collection_name: str):
        """
        Получает коллекцию по имени.
        
        Args:
            collection_name: Имя коллекции
            
        Returns:
            Collection object или None если не существует
        """
        try:
            if not await self.collection_exists(collection_name):
                return None
            
            return self._client.get_collection(
                name=collection_name,
                embedding_function=self._embedding_function
            )
        except Exception as e:
            self._logger.error(f"Ошибка получения коллекции {collection_name}: {e}")
            return None
    
    async def collection_exists(self, collection_name: str) -> bool:
        """
        Проверяет существование коллекции.
        
        Args:
            collection_name: Имя коллекции
            
        Returns:
            True если коллекция существует, False иначе
        """
        try:
            collections = self._client.list_collections()
            collection_names = [c.name for c in collections]
            return collection_name in collection_names
        except Exception as e:
            self._logger.error(f"Ошибка проверки существования коллекции {collection_name}: {e}")
            return False
    
    async def rename_collection(self, old_name: str, new_name: str, progress_callback=None) -> None:
        """
        Переименовывает коллекцию (через копирование данных батчами).
        
        Args:
            old_name: Старое имя коллекции
            new_name: Новое имя коллекции
        """
        try:
            # Проверяем существование старой коллекции
            if not await self.collection_exists(old_name):
                raise ValueError(f"Коллекция {old_name} не существует")
            
            self._logger.info(f"Начинаю переименование коллекции: {old_name} -> {new_name}")
            
            # Получаем старую коллекцию
            old_collection = self._client.get_collection(
                name=old_name,
                embedding_function=self._embedding_function
            )
            
            # Проверяем размер коллекции
            total_count = old_collection.count()
            self._logger.info(f"Размер коллекции {old_name}: {total_count} документов")
            
            # Создаем новую коллекцию
            await self.create_collection(new_name)
            new_collection = self._client.get_collection(
                name=new_name,
                embedding_function=self._embedding_function
            )
            
            # Копируем данные батчами (это предотвращает зависание)
            await self._copy_collection_data(old_collection, new_collection, progress_callback)
            
            # Проверяем что копирование прошло успешно
            new_count = new_collection.count()
            if new_count != total_count:
                raise ValueError(f"Ошибка копирования: {new_count} != {total_count}")
            
            # Удаляем старую коллекцию только после успешного копирования
            self._client.delete_collection(old_name)
            
            # КРИТИЧНО: Очищаем кэш коллекции при переименовании активной коллекции
            if old_name == self.COLLECTION_NAME:
                self._logger.info("Очищаю кэш коллекции после переименования активной коллекции")
                self._collection = None
            
            self._logger.info(f"Коллекция успешно переименована: {old_name} -> {new_name} ({total_count} документов)")
            
        except Exception as e:
            self._logger.error(f"Ошибка переименования коллекции {old_name} -> {new_name}: {e}")
            # Пытаемся очистить новую коллекцию при ошибке
            try:
                if await self.collection_exists(new_name):
                    self._client.delete_collection(new_name)
                    self._logger.info(f"Очищена коллекция {new_name} после ошибки")
            except:
                pass
            raise e
    
    async def delete_collection(self, collection_name: str) -> None:
        """
        Удаляет коллекцию и физически удаляет её файлы с диска.
        
        Args:
            collection_name: Имя коллекции для удаления
        """
        try:
            # Сначала удаляем коллекцию из ChromaDB
            self._client.delete_collection(collection_name)
            
            # КРИТИЧНО: Очищаем кэш коллекции при удалении активной коллекции
            if collection_name == self.COLLECTION_NAME:
                self._logger.info("Очищаю кэш коллекции после удаления активной коллекции")
                self._collection = None
            
            # Физически удаляем файлы коллекции с диска
            await self._delete_collection_files(collection_name)
            
            self._logger.info(f"Удалена коллекция и её файлы: {collection_name}")
            
        except Exception as e:
            self._logger.warning(f"Ошибка удаления коллекции {collection_name}: {e}")
            # Не поднимаем исключение, так как коллекция может не существовать
    
    async def _delete_collection_files(self, collection_name: str) -> None:
        """
        Физически удаляет файлы коллекции с диска.
        
        Args:
            collection_name: Имя коллекции для удаления файлов
        """
        try:
            # Получаем UUID коллекции из ChromaDB
            collections = self._client.list_collections()
            collection_uuid = None
            
            for collection in collections:
                if collection.name == collection_name:
                    collection_uuid = collection.id
                    break
            
            if not collection_uuid:
                self._logger.warning(f"UUID коллекции {collection_name} не найден")
                return
            
            # Путь к файлам коллекции
            collection_dir = self._persist_dir / collection_uuid
            
            if collection_dir.exists():
                # Подсчитываем размер перед удалением
                size_before = sum(f.stat().st_size for f in collection_dir.rglob('*') if f.is_file())
                size_mb = size_before / (1024 * 1024)
                
                # Удаляем директорию с файлами
                import shutil
                shutil.rmtree(collection_dir)
                
                self._logger.info(f"Физически удалены файлы коллекции {collection_name}: {size_mb:.2f} MB")
            else:
                self._logger.warning(f"Директория коллекции {collection_name} не найдена: {collection_dir}")
                
        except Exception as e:
            self._logger.error(f"Ошибка физического удаления файлов коллекции {collection_name}: {e}")
            # Не поднимаем исключение, чтобы не нарушить основной процесс удаления
    
    def _create_search_document(self, product: Product) -> str:
        """
        Создает текстовый документ для поиска из товара.
        
        Args:
            product: Товар
            
        Returns:
            Текстовый документ для индексации
        """
        # Собираем все текстовые поля товара
        parts = []
        
        if product.product_name:
            parts.append(product.product_name)
        
        if product.description:
            parts.append(product.description)
        
        if product.article:
            parts.append(f"Артикул: {product.article}")
        
        if product.category_1:
            parts.append(f"Категория: {product.category_1}")
        
        if product.category_2:
            parts.append(f"Подкатегория: {product.category_2}")
        
        if product.category_3:
            parts.append(f"Тип: {product.category_3}")
        
        return " | ".join(parts)
    
    def _create_product_metadata(self, product: Product) -> dict:
        """
        Создает метаданные товара для Chroma.
        
        Args:
            product: Товар
            
        Returns:
            Словарь с метаданными
        """
        return {
            "id": str(product.id),
            "name": product.product_name or "",
            "article": product.article or "",
            "category_1": product.category_1 or "",
            "category_2": product.category_2 or "",
            "category_3": product.category_3 or "",
            "photo_url": product.photo_url or "",
            "page_url": product.page_url or ""
        }