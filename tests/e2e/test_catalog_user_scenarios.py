"""
E2E тесты для полных пользовательских сценариев с каталогом
"""
import pytest
import asyncio
import tempfile
import pandas as pd
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.infrastructure.search.catalog_service import CatalogSearchService
from src.domain.entities.product import Product


@pytest.mark.e2e
@pytest.mark.search
@pytest.mark.slow
class TestCatalogUserJourney:
    """E2E тесты полного пути пользователя с каталогом"""
    
    @pytest.fixture
    def sample_catalog_data(self):
        """Фикстура с данными полного каталога для E2E тестов"""
        return [
            {
                'id': '1',
                'section name 1': 'Компьютеры',
                'section name 2': 'Ноутбуки',
                'product name': 'Ноутбук ASUS VivoBook для работы',
                'description': 'Современный ноутбук с процессором Intel i5, 8GB RAM, SSD 256GB для офисной работы и программирования',
                'category 1': 'Электроника',
                'category 2': 'Компьютеры',
                'category 3': 'Ноутбуки',
                'article': 'ASUS-VB-001',
                'photo_url': 'https://example.com/asus.jpg',
                'page_url': 'https://example.com/products/asus'
            },
            {
                'id': '2',
                'section name 1': 'Компьютеры',
                'section name 2': 'Принтеры',
                'product name': 'Принтер лазерный HP LaserJet Pro',
                'description': 'Черно-белый лазерный принтер для офиса, скорость 20 стр/мин, Wi-Fi',
                'category 1': 'Электроника',
                'category 2': 'Офисная техника',
                'category 3': 'Принтеры',
                'article': 'HP-LJ-001',
                'photo_url': 'https://example.com/hp.jpg',
                'page_url': 'https://example.com/products/hp'
            },
            {
                'id': '3',
                'section name 1': 'Инструменты',
                'section name 2': 'Измерительные',
                'product name': 'Digital measuring device DMM-100',
                'description': 'Precision digital multimeter for electrical measurements',
                'category 1': 'Инструменты',
                'category 2': 'Измерительные',
                'category 3': 'Приборы',
                'article': 'DMM-100',
                'photo_url': '',
                'page_url': ''
            },
            {
                'id': '4',
                'section name 1': 'Крепеж',
                'section name 2': 'Болты',
                'product name': 'Болт крепежный M8x20 оцинкованный',
                'description': 'Оцинкованный болт с шестигранной головкой для металлических конструкций',
                'category 1': 'Материалы',
                'category 2': 'Крепеж',
                'category 3': 'Метизы',
                'article': 'BOLT-M8-20',
                'photo_url': '',
                'page_url': ''
            },
            {
                'id': '5',
                'section name 1': 'Электроинструменты',
                'section name 2': 'Дрели',
                'product name': 'Дрель электрическая Makita 750W',
                'description': 'Профессиональная ударная дрель для сверления по бетону, металлу и дереву',
                'category 1': 'Инструменты',
                'category 2': 'Электроинструменты',
                'category 3': 'Дрели',
                'article': 'MAKITA-750',
                'photo_url': 'https://example.com/makita.jpg',
                'page_url': 'https://example.com/products/makita'
            }
        ]
    
    def create_catalog_excel(self, data: list) -> str:
        """Создает Excel файл с каталогом"""
        df = pd.DataFrame(data)
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df.to_excel(tmp_file.name, index=False)
            return tmp_file.name
    
    @pytest.fixture
    async def catalog_service(self):
        """Фикстура сервиса каталога для E2E тестов"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        service = CatalogSearchService(
            persist_dir=f"data/test_e2e_catalog_{unique_id}"
        )
        yield service
        
        # Очистка после теста
        try:
            import shutil
            import os
            test_dir = Path(f"data/test_e2e_catalog_{unique_id}")
            if test_dir.exists():
                shutil.rmtree(test_dir)
        except Exception:
            pass  # Игнорируем ошибки очистки
    
    @pytest.mark.asyncio
    async def test_complete_catalog_workflow(self, catalog_service, sample_catalog_data):
        """
        E2E тест: Полный рабочий процесс каталога
        1. Загрузка каталога из Excel
        2. Поиск товаров на разных языках
        3. Проверка качества результатов
        """
        # 1. Подготовка данных
        excel_file = self.create_catalog_excel(sample_catalog_data)
        
        try:
            # 2. Загрузка каталога
            await catalog_service.index_catalog(excel_file)
            
            # Проверяем что каталог загружен
            is_indexed = await catalog_service.is_indexed()
            assert is_indexed, "Каталог должен быть проиндексирован"
            
            # 3. Тестируем различные типы поиска
            
            # 3.1 Поиск по точному названию (русский)
            results = await catalog_service.search_products("ноутбук ASUS")
            assert len(results) > 0, "Должен найти ноутбук ASUS"
            
            top_result = results[0]
            assert "asus" in top_result.product.product_name.lower()
            assert top_result.score > 0.4, f"Score слишком низкий: {top_result.score}"
            
            # 3.2 Семантический поиск (русский)
            results = await catalog_service.search_products("компьютер для офиса")
            assert len(results) > 0, "Должен найти компьютерную технику"
            
            # Проверяем что нашли релевантные товары
            found_computer_related = any(
                "компьютер" in r.product.get_full_category().lower() or 
                "ноутбук" in r.product.product_name.lower() or
                "принтер" in r.product.product_name.lower()
                for r in results
            )
            assert found_computer_related, "Должен найти компьютерную технику"
            
            # 3.3 Поиск на английском языке
            results = await catalog_service.search_products("digital measuring device")
            assert len(results) > 0, "Должен найти измерительные приборы"
            
            found_measuring = any(
                "measuring" in r.product.product_name.lower() or
                "dmm" in r.product.product_name.lower()
                for r in results
            )
            assert found_measuring, "Должен найти измерительный прибор"
            
            # 3.4 Поиск по артикулу
            results = await catalog_service.search_products("MAKITA-750")
            assert len(results) > 0, "Должен найти товар по артикулу"
            
            found_by_article = any(
                r.product.article == "MAKITA-750" for r in results
            )
            assert found_by_article, "Должен найти товар с артикулом MAKITA-750"
            
            # 3.5 Поиск по категории
            results = await catalog_service.search_products("электроинструменты")
            assert len(results) > 0, "Должен найти электроинструменты"
            
            found_tools = any(
                "электроинструмент" in r.product.get_full_category().lower() or
                "дрель" in r.product.product_name.lower()
                for r in results
            )
            assert found_tools, "Должен найти электроинструменты"
            
            # 4. Проверяем качество сортировки результатов
            results = await catalog_service.search_products("ноутбук")
            if len(results) > 1:
                scores = [r.score for r in results]
                assert scores == sorted(scores, reverse=True), "Результаты должны быть отсортированы по убыванию score"
            
        finally:
            # Очистка
            import os
            if os.path.exists(excel_file):
                os.unlink(excel_file)
    
    @pytest.mark.asyncio
    async def test_catalog_reindexing_scenario(self, catalog_service, sample_catalog_data):
        """
        E2E тест: Сценарий переиндексации каталога (Blue-Green deployment)
        """
        # 1. Загружаем первый каталог
        excel_file_1 = self.create_catalog_excel(sample_catalog_data[:3])  # Первые 3 товара
        excel_file_2 = None  # Инициализируем переменную
        
        try:
            await catalog_service.index_catalog(excel_file_1)
            
            # Проверяем что товары загружены
            results_1 = await catalog_service.search_products("ноутбук")
            assert len(results_1) > 0, "Должен найти товары из первого каталога"
            
            # 2. Загружаем обновленный каталог (все товары)
            excel_file_2 = self.create_catalog_excel(sample_catalog_data)  # Все товары
            
            await catalog_service.index_catalog(excel_file_2)
            
            # 3. Проверяем что новые товары доступны
            results_2 = await catalog_service.search_products("дрель makita")
            assert len(results_2) > 0, "Должен найти товары из обновленного каталога"
            
            found_drill = any(
                "makita" in r.product.product_name.lower() for r in results_2
            )
            assert found_drill, "Должен найти дрель Makita из обновленного каталога"
            
            # 4. Проверяем что старые товары все еще доступны
            results_3 = await catalog_service.search_products("ноутбук")
            assert len(results_3) > 0, "Старые товары должны быть доступны после переиндексации"
            
        finally:
            import os
            for file in [excel_file_1, excel_file_2]:
                if file and os.path.exists(file):
                    os.unlink(file)
    
    @pytest.mark.asyncio
    async def test_multilingual_search_quality(self, catalog_service, sample_catalog_data):
        """
        E2E тест: Качество многоязычного поиска
        """
        excel_file = self.create_catalog_excel(sample_catalog_data)
        
        try:
            await catalog_service.index_catalog(excel_file)
            
            # Тестируем качество поиска на разных языках
            # С учетом нового порога SEARCH_MIN_SCORE=0.45
            test_cases = [
                # (запрос, ожидаемые ключевые слова в результатах, минимальный score)
                ("ноутбук для работы", ["ноутбук", "asus", "компьютер"], 0.45),
                ("болт крепежный", ["болт", "крепеж", "метиз"], 0.45),
                ("дрель makita", ["дрель", "makita", "электроинструмент"], 0.45),
            ]
            
            for query, expected_keywords, min_score in test_cases:
                results = await catalog_service.search_products(query, k=3)
                
                assert len(results) > 0, f"Не найдено результатов для запроса: {query}"
                
                # Проверяем минимальный score
                top_score = results[0].score
                assert top_score >= min_score, f"Score {top_score:.3f} слишком низкий для '{query}' (мин: {min_score})"
                
                # Проверяем релевантность
                found_relevant = False
                for result in results:
                    text_to_check = (
                        result.product.product_name + " " + 
                        result.product.description + " " + 
                        result.product.get_full_category()
                    ).lower()
                    
                    if any(keyword.lower() in text_to_check for keyword in expected_keywords):
                        found_relevant = True
                        break
                
                assert found_relevant, f"Не найдены релевантные результаты для '{query}'. Найдено: {[r.product.product_name for r in results[:2]]}"
        
        finally:
            import os
            if os.path.exists(excel_file):
                os.unlink(excel_file)


@pytest.mark.e2e
@pytest.mark.search
@pytest.mark.slow
class TestCatalogPerformance:
    """E2E тесты производительности каталога"""
    
    @pytest.mark.asyncio
    async def test_large_catalog_performance(self):
        """
        E2E тест: Производительность с большим каталогом
        (Тест пропускается если нет реального большого каталога)
        """
        real_catalog_path = Path("data/uploads/test_catalog.xlsx")
        
        if not real_catalog_path.exists():
            pytest.skip("Большой тестовый каталог не найден")
        
        service = CatalogSearchService(persist_dir="data/test_performance")
        
        try:
            import time
            
            # Тест загрузки
            start_time = time.time()
            await service.index_catalog(str(real_catalog_path))
            indexing_time = time.time() - start_time
            
            # Производительность должна быть разумной
            assert indexing_time < 60, f"Индексация слишком медленная: {indexing_time:.1f} сек"
            
            # Тест поиска - используем запросы которые точно найдут результаты
            search_queries = ["DL001", "FL002", "BT003"]
            
            total_search_time = 0
            for query in search_queries:
                start_time = time.time()
                results = await service.search_products(query, k=5)
                search_time = time.time() - start_time
                total_search_time += search_time
                
                # Каждый поиск должен быть быстрым
                assert search_time < 2.0, f"Поиск '{query}' слишком медленный: {search_time:.3f} сек"
                assert len(results) > 0, f"Нет результатов для '{query}'"
            
            avg_search_time = total_search_time / len(search_queries)
            assert avg_search_time < 1.0, f"Средний поиск слишком медленный: {avg_search_time:.3f} сек"
            
        finally:
            # Очистка
            try:
                import shutil
                test_dir = Path("data/test_performance")
                if test_dir.exists():
                    shutil.rmtree(test_dir)
            except Exception:
                pass
