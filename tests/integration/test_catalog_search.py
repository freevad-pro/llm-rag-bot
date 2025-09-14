"""
Интеграционные тесты для поиска в каталоге

Эти тесты проверяют:
1. Корректность загрузки каталога из Excel
2. Точность поиска на русском и английском языках  
3. Релевантность результатов
4. Производительность индексации
5. Обработку ошибок и граничных случаев
"""
import pytest
import os
import tempfile
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch
import pandas as pd

from src.infrastructure.search.catalog_service import CatalogSearchService
from src.infrastructure.search.excel_loader import ExcelCatalogLoader
from src.domain.entities.product import Product, SearchResult
from src.config.settings import settings


@pytest.mark.integration
@pytest.mark.search
class TestCatalogSearch:
    """Тесты системы поиска в каталоге"""

    async def _index_test_products(self, catalog_service, products):
        """Вспомогательный метод для индексации тестовых товаров"""
        import pandas as pd
        import tempfile
        import os
        
        # Конвертируем Product объекты в данные для Excel
        excel_data = []
        for product in products:
            excel_data.append({
                'id': product.id,
                'section name 1': product.section_name_1,
                'section name 2': product.section_name_2,
                'product name': product.product_name,
                'description': product.description,
                'category 1': product.category_1,
                'category 2': product.category_2,
                'category 3': product.category_3,
                'article': product.article,
                'photo_url': product.photo_url,
                'page_url': product.page_url
            })
        
        df = pd.DataFrame(excel_data)
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df.to_excel(tmp_file.name, index=False)
            excel_path = tmp_file.name
        
        try:
            # Индексируем каталог
            await catalog_service.index_catalog(excel_path)
        finally:
            # Очистка
            if os.path.exists(excel_path):
                os.unlink(excel_path)

    @pytest.fixture
    async def catalog_service(self):
        """Создает сервис каталога для тестов"""
        # Используем test настройки для Chroma (временная БД)
        service = CatalogSearchService(
            persist_dir="data/test_chroma"
        )
        yield service
        
        # Очистка после теста
        try:
            if hasattr(service, '_collection') and service._collection:
                service._client.delete_collection("test_catalog")
        except Exception:
            pass  # Игнорируем ошибки очистки

    @pytest.fixture
    def sample_products(self) -> List[Product]:
        """Расширенный набор тестовых товаров для качественного тестирования"""
        return [
            # Компьютерная техника
            Product(
                id="1",
                section_name_1="Компьютеры",
                section_name_2="Ноутбуки",
                product_name="Ноутбук ASUS VivoBook для работы и учебы",
                description="Высокопроизводительный ноутбук с процессором Intel i5, 8GB RAM, SSD 256GB для офисной работы, программирования и обучения",
                category_1="Электроника",
                category_2="Компьютеры", 
                category_3="Ноутбуки",
                article="ASUS-VB-001",
                photo_url="https://example.com/asus.jpg",
                page_url="https://example.com/products/asus001"
            ),
            Product(
                id="2",
                section_name_1="Компьютеры", 
                section_name_2="Принтеры",
                product_name="Принтер лазерный HP LaserJet Pro",
                description="Черно-белый лазерный принтер для офиса, скорость печати 20 стр/мин, Wi-Fi",
                category_1="Электроника",
                category_2="Офисная техника", 
                category_3="Принтеры",
                article="HP-LJ-001",
                photo_url="https://example.com/hp-printer.jpg",
                page_url="https://example.com/products/hp001"
            ),
            
            # Измерительные приборы
            Product(
                id="3", 
                section_name_1="Инструменты",
                section_name_2="Измерительные приборы",
                product_name="Digital measuring device DMM-100",
                description="Precision digital multimeter for electrical measurements, voltage, current, resistance",
                category_1="Инструменты",
                category_2="Измерительные", 
                category_3="Приборы",
                article="DMM-100",
                photo_url="https://example.com/dmm.jpg",
                page_url="https://example.com/products/dmm100"
            ),
            Product(
                id="4",
                section_name_1="Инструменты",
                section_name_2="Измерительные приборы", 
                product_name="Штангенциркуль цифровой 150мм",
                description="Цифровой штангенциркуль высокой точности для измерения внешних и внутренних размеров",
                category_1="Инструменты",
                category_2="Измерительные", 
                category_3="Приборы",
                article="CALIPER-150",
                photo_url="",
                page_url=""
            ),
            
            # Крепежные изделия
            Product(
                id="5",
                section_name_1="Крепеж",
                section_name_2="Болты",
                product_name="Болт крепежный M8x20 оцинкованный",
                description="Оцинкованный болт с шестигранной головкой для крепления металлических конструкций",
                category_1="Материалы",
                category_2="Крепеж", 
                category_3="Метизы",
                article="BOLT-M8-20",
                photo_url="",
                page_url=""
            ),
            Product(
                id="6",
                section_name_1="Крепеж",
                section_name_2="Гайки",
                product_name="Гайка шестигранная M8 оцинкованная",
                description="Шестигранная гайка М8 с цинковым покрытием для болтового соединения",
                category_1="Материалы",
                category_2="Крепеж", 
                category_3="Метизы", 
                article="NUT-M8",
                photo_url="",
                page_url=""
            ),
            
            # Электроинструменты
            Product(
                id="7",
                section_name_1="Инструменты",
                section_name_2="Электроинструменты",
                product_name="Дрель электрическая Makita 750W",
                description="Профессиональная ударная дрель с функцией сверления по бетону, металлу и дереву",
                category_1="Инструменты",
                category_2="Электроинструменты", 
                category_3="Дрели",
                article="MAKITA-750",
                photo_url="https://example.com/makita.jpg",
                page_url="https://example.com/products/makita750"
            ),
            
            # Специальные символы и сложные названия
            Product(
                id="8",
                section_name_1="Химия",
                section_name_2="Растворители",
                product_name="Ацетон технический 99.5% (CH₃COCH₃)",
                description="Органический растворитель высокой чистоты для обезжиривания и очистки поверхностей",
                category_1="Материалы",
                category_2="Химия", 
                category_3="Растворители",
                article="ACETONE-995",
                photo_url="",
                page_url=""
            )
        ]

    @pytest.mark.asyncio
    async def test_catalog_service_initialization(self, catalog_service):
        """Тест инициализации сервиса каталога"""
        assert catalog_service is not None
        assert catalog_service.embedding_provider == "sentence-transformers"
        assert "paraphrase-multilingual-MiniLM-L12-v2" in catalog_service.embedding_model

    @pytest.mark.asyncio
    async def test_index_products(self, catalog_service, sample_products):
        """Тест индексации товаров через Excel"""
        # Создаем временный Excel файл с тестовыми товарами
        import pandas as pd
        import tempfile
        import os
        
        # Конвертируем Product объекты в данные для Excel
        excel_data = []
        for product in sample_products:
            excel_data.append({
                'id': product.id,
                'section name 1': product.section_name_1,
                'section name 2': product.section_name_2,
                'product name': product.product_name,
                'description': product.description,
                'category 1': product.category_1,
                'category 2': product.category_2,
                'category 3': product.category_3,
                'article': product.article,
                'photo_url': product.photo_url,
                'page_url': product.page_url
            })
        
        df = pd.DataFrame(excel_data)
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df.to_excel(tmp_file.name, index=False)
            excel_path = tmp_file.name
        
        try:
            # Индексируем каталог
            await catalog_service.index_catalog(excel_path)
            
            # Проверяем что каталог проиндексирован
            is_indexed = await catalog_service.is_indexed()
            assert is_indexed, "Каталог должен быть проиндексирован"
            
        finally:
            # Очистка
            if os.path.exists(excel_path):
                os.unlink(excel_path)

    @pytest.mark.asyncio
    async def test_search_exact_product_name_russian(self, catalog_service, sample_products):
        """Тест точного поиска по названию товара на русском"""
        await self._index_test_products(catalog_service, sample_products)
        
        # Точный поиск ноутбука
        results = await catalog_service.search_products("ноутбук ASUS", k=5)
        
        assert len(results) > 0, "Должен найти ноутбук ASUS"
        
        # Проверяем что первый результат действительно релевантный
        top_result = results[0]
        assert isinstance(top_result, SearchResult)
        assert top_result.score > 0.3, f"Score слишком низкий: {top_result.score}"
        
        # Проверяем что найден именно ноутбук
        product_name_lower = top_result.product.product_name.lower()
        assert ("ноутбук" in product_name_lower or "asus" in product_name_lower), \
            f"Найденный товар не соответствует запросу: {top_result.product.product_name}"

    @pytest.mark.asyncio
    async def test_search_semantic_similarity_russian(self, catalog_service, sample_products):
        """Тест семантического поиска на русском языке"""
        await self._index_test_products(catalog_service, sample_products)
        
        # Семантический поиск компьютера (должен найти ноутбук)
        results = await catalog_service.search_products("компьютер для работы", k=3)
        
        assert len(results) > 0, "Должен найти компьютерную технику"
        
        # Проверяем что нашли компьютерную технику
        found_computer = any("компьютер" in r.product.get_full_category().lower() or 
                           "ноутбук" in r.product.product_name.lower() 
                           for r in results)
        assert found_computer, "Не найдена компьютерная техника при поиске 'компьютер для работы'"

    @pytest.mark.asyncio 
    async def test_search_english_query(self, catalog_service, sample_products):
        """Тест поиска на английском языке"""
        await self._index_test_products(catalog_service, sample_products)
        
        # Поиск измерительного прибора
        results = await catalog_service.search_products("measuring device", k=3)
        
        assert len(results) > 0, "Должен найти измерительные приборы"
        
        # Проверяем релевантность
        top_result = results[0]
        assert top_result.score > 0.3, f"Score слишком низкий для английского запроса: {top_result.score}"
        
        # Проверяем что найден именно измерительный прибор
        found_measuring = any("measuring" in r.product.product_name.lower() or 
                            "измерительн" in r.product.get_full_category().lower() or
                            "dmm" in r.product.product_name.lower()
                            for r in results)
        assert found_measuring, "Не найдены измерительные приборы при поиске 'measuring device'"

    @pytest.mark.asyncio
    async def test_search_by_article_number(self, catalog_service, sample_products):
        """Тест поиска по артикулу"""
        await self._index_test_products(catalog_service, sample_products)
        
        # Поиск по артикулу
        results = await catalog_service.search_products("ASUS-VB-001", k=3)
        
        assert len(results) > 0, "Должен найти товар по артикулу"
        
        # Первый результат должен быть с этим артикулом
        found_article = any(r.product.article == "ASUS-VB-001" for r in results)
        assert found_article, "Не найден товар с артикулом ASUS-VB-001"

    @pytest.mark.asyncio
    async def test_search_by_category_comprehensive(self, catalog_service, sample_products):
        """Подробный тест поиска по категориям"""
        await self._index_test_products(catalog_service, sample_products)
        
        # Тестируем различные категории
        test_cases = [
            ("компьютерная техника", ["компьютер", "ноутбук"]),
            ("измерительные приборы", ["измерительн", "штангенциркуль", "dmm"]),
            ("крепеж", ["болт", "гайка", "крепеж"]),
            ("электроинструменты", ["дрель", "makita"])
        ]
        
        for query, expected_keywords in test_cases:
            results = await catalog_service.search_products(query, k=5)
            
            assert len(results) > 0, f"Не найдено товаров для категории '{query}'"
            
            # Проверяем что найдены релевантные товары
            found_relevant = False
            for result in results:
                text_to_check = (result.product.product_name + " " + result.product.get_full_category() + " " + result.product.description).lower()
                if any(keyword in text_to_check for keyword in expected_keywords):
                    found_relevant = True
                    break
            
            assert found_relevant, f"Не найдены релевантные товары для '{query}'. Найдено: {[r.product.product_name for r in results[:2]]}"

    @pytest.mark.asyncio
    async def test_search_mixed_language_query(self, catalog_service, sample_products):
        """Тест поиска со смешанными языками"""
        await self._index_test_products(catalog_service, sample_products)
        
        # Поиск крепежа
        results = await catalog_service.search_products("болт крепежный", k=3)
        
        assert len(results) > 0
        assert "болт" in results[0].product.product_name.lower()

    @pytest.mark.asyncio
    async def test_search_by_category(self, catalog_service, sample_products):
        """Тест поиска по категории"""
        await self._index_test_products(catalog_service, sample_products)
        
        results = await catalog_service.search_products("компьютерная техника", k=5)
        
        # Должны найти товары из категории "Компьютеры"
        assert len(results) > 0
        computer_related = [r for r in results if "компьютер" in r.product.get_full_category().lower() or "ноутбук" in r.product.product_name.lower()]
        assert len(computer_related) > 0

    @pytest.mark.asyncio
    async def test_search_no_results(self, catalog_service, sample_products):
        """Тест поиска без результатов"""
        await self._index_test_products(catalog_service, sample_products)
        
        results = await catalog_service.search_products("совершенно несуществующий товар xyz123", k=3)
        
        # Может вернуть результаты с очень низким score или пустой список
        if results:
            assert all(r.score < 0.4 for r in results)  # Низкий score для нерелевантных результатов

    @pytest.mark.asyncio
    async def test_search_limit(self, catalog_service, sample_products):
        """Тест ограничения количества результатов"""
        await self._index_test_products(catalog_service, sample_products)
        
        results = await catalog_service.search_products("товар", k=2)
        
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_search_score_ordering(self, catalog_service, sample_products):
        """Тест сортировки результатов по релевантности"""
        await self._index_test_products(catalog_service, sample_products)
        
        results = await catalog_service.search_products("ноутбук", k=5)
        
        if len(results) > 1:
            # Результаты должны быть отсортированы по убыванию score
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True), f"Scores not sorted: {scores}"


@pytest.mark.integration
@pytest.mark.search 
@pytest.mark.slow
class TestExcelCatalogLoader:
    """Тесты загрузки каталога из Excel"""

    @pytest.fixture
    def excel_loader(self):
        """Создает загрузчик Excel"""
        return ExcelCatalogLoader()

    @pytest.fixture
    def create_test_excel(self) -> str:
        """Создает тестовый Excel файл"""
        test_data = [
            {
                'id': '1',
                'section name 1': 'Тест категория 1',
                'section name 2': 'Тест подкатегория 1',
                'product name': 'Тестовый товар 1',
                'description': 'Описание тестового товара номер один',
                'category 1': 'Тестовая',
                'category 2': 'Категория',
                'category 3': 'Уровень1',
                'article': 'TEST-001',
                'photo_url': 'https://example.com/photo1.jpg',
                'page_url': 'https://example.com/product1'
            },
            {
                'id': '2',
                'section name 1': 'Test Category 2',
                'section name 2': 'Test Subcategory 2',
                'product name': 'Test Product with English Name',
                'description': 'English description for testing multilingual support',
                'category 1': 'Test',
                'category 2': 'Equipment',
                'category 3': 'Level2',
                'article': 'TEST-002',
                'photo_url': '',
                'page_url': ''
            },
            {
                'id': '3',
                'section name 1': 'Специальные символы',
                'section name 2': 'Химия & Физика',
                'product name': 'H₂SO₄ - Серная кислота 98%',
                'description': 'Концентрированная серная кислота для лабораторных работ (опасно!)',
                'category 1': 'Материалы',
                'category 2': 'Химия',
                'category 3': 'Кислоты',
                'article': 'CHEM-H2SO4',
                'photo_url': '',
                'page_url': ''
            }
        ]
        
        # Создаем временный Excel файл
        df = pd.DataFrame(test_data)
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df.to_excel(tmp_file.name, index=False)
            return tmp_file.name

    def test_excel_loader_initialization(self, excel_loader):
        """Тест инициализации загрузчика"""
        assert excel_loader is not None
        assert hasattr(excel_loader, 'load_products')

    @pytest.mark.asyncio
    async def test_load_custom_excel_catalog(self, excel_loader, create_test_excel):
        """Тест загрузки созданного тестового каталога"""
        excel_file = create_test_excel
        
        try:
            products = await excel_loader.load_products(excel_file)
            
            # Базовые проверки
            assert len(products) == 3, f"Ожидалось 3 товара, получено {len(products)}"
            assert all(isinstance(p, Product) for p in products), "Все объекты должны быть Product"
            
            # Проверяем обязательные поля
            for product in products:
                assert product.id, f"ID не должен быть пустым: {product}"
                assert product.product_name, f"Название товара не должно быть пустым: {product}"
                assert product.get_full_category(), f"Категория не должна быть пустой: {product}"
                assert product.article, f"Артикул не должен быть пустым: {product}"
            
            # Проверяем конкретные значения
            product_1 = next(p for p in products if p.id == "1")
            assert product_1.product_name == "Тестовый товар 1"
            assert product_1.get_full_category() == "Тестовая > Категория > Уровень1"
            assert product_1.article == "TEST-001"
            
            # Проверяем английский товар
            product_2 = next(p for p in products if p.id == "2")
            assert "English" in product_2.product_name
            assert product_2.article == "TEST-002"
            
            # Проверяем товар со специальными символами
            product_3 = next(p for p in products if p.id == "3")
            assert "H₂SO₄" in product_3.product_name
            assert "CHEM-H2SO4" == product_3.article
            
        finally:
            # Очистка временного файла
            if os.path.exists(excel_file):
                os.unlink(excel_file)

    @pytest.mark.asyncio
    async def test_load_real_test_catalog_if_exists(self, excel_loader):
        """Тест загрузки реального тестового каталога если он существует"""
        test_file = Path("data/uploads/test_catalog.xlsx")
        
        if test_file.exists():
            products = await excel_loader.load_products(str(test_file))
            
            assert len(products) > 0, "Реальный тестовый каталог должен содержать товары"
            assert all(isinstance(p, Product) for p in products), "Все объекты должны быть Product"
            
            # Проверяем структуру товаров
            for product in products:
                assert product.id, "ID обязателен"
                assert product.product_name, "Название товара обязательно"
                assert product.get_full_category(), "Категория обязательна"
                assert product.article, "Артикул обязателен"
                
            print(f"✅ Загружен реальный каталог: {len(products)} товаров")
            
            # Показываем примеры товаров
            for i, product in enumerate(products[:3], 1):
                print(f"  {i}. {product.product_name} ({product.get_full_category()})")
                
        else:
            pytest.skip("Реальный тестовый каталог не найден: data/uploads/test_catalog.xlsx")

    @pytest.mark.asyncio
    async def test_excel_loader_error_handling(self, excel_loader):
        """Тест обработки ошибок в загрузчике Excel"""
        
        # Тест несуществующего файла
        with pytest.raises(Exception):  # Может быть FileNotFoundError или другая ошибка
            await excel_loader.load_products("nonexistent_file.xlsx")
        
        # Тест некорректного формата файла
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(b"This is not an Excel file")
            tmp_file.flush()
            
            try:
                with pytest.raises(Exception):  # Ожидаем ошибку формата
                    await excel_loader.load_products(tmp_file.name)
            finally:
                os.unlink(tmp_file.name)


@pytest.mark.integration 
@pytest.mark.search
@pytest.mark.slow
class TestFullCatalogWorkflow:
    """Полный тест рабочего процесса каталога"""

    @pytest.fixture
    async def full_catalog_service(self):
        """Сервис каталога для полного теста"""
        service = CatalogSearchService(
            persist_dir="data/test_chroma_full",
        )
        yield service
        
        # Очистка
        try:
            if hasattr(service, '_collection') and service._collection:
                service._client.delete_collection("test_catalog_full")
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_full_catalog_workflow(self, full_catalog_service):
        """Тест полного цикла: загрузка каталога + поиск"""
        test_file = Path("data/uploads/test_catalog.xlsx")
        
        if not test_file.exists():
            pytest.skip("Тестовый каталог не найден для полного теста")
        
        # 1. Загружаем каталог
        import time
        start_time = time.time()
        
        await full_catalog_service.index_catalog(str(test_file))
        
        indexing_time = time.time() - start_time
        
        # Проверяем что каталог был проиндексирован
        is_indexed = await full_catalog_service.is_indexed()
        assert is_indexed, "Каталог должен быть проиндексирован"
        
        # Проверяем что процесс прошел успешно
        assert indexing_time > 0, f"Время индексации должно быть положительным: {indexing_time}"
        
        print(f"✅ Каталог проиндексирован за {indexing_time:.2f} секунд")
        
        # 2. Тестируем различные типы поиска
        test_queries = [
            ("ноутбук", "русский поиск"),
            ("computer", "английский поиск"),
            ("принтер", "офисная техника"),
            ("measuring", "измерительные приборы"),
            ("болт", "крепежные изделия")
        ]
        
        for query, description in test_queries:
            results = await full_catalog_service.search_products(query, k=3)
            
            # Логируем результаты для отладки
            print(f"\n🔍 {description}: '{query}'")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.product.product_name} (score: {result.score:.3f})")
            
            # Базовые проверки
            assert isinstance(results, list)
            if results:
                assert all(isinstance(r, SearchResult) for r in results)
                assert all(0 <= r.score <= 1 for r in results)


# Маркеры для удобного запуска
pytestmark = [
    pytest.mark.integration,
    pytest.mark.search,
]

# Дополнительные маркеры для TestExcelCatalogLoader
pytest.mark.slow  # Медленные тесты с файловыми операциями
