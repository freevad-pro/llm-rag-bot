"""
Unit тесты для компонентов каталога (быстрые, без внешних зависимостей)
"""
import pytest
import tempfile
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from src.domain.entities.product import Product
from src.infrastructure.search.excel_loader import ExcelCatalogLoader


@pytest.mark.unit
@pytest.mark.search
class TestProductEntity:
    """Unit тесты для сущности Product"""
    
    def test_product_creation(self):
        """Тест создания продукта с обязательными полями"""
        product = Product(
            id="TEST-001",
            section_name_1="Тест",
            section_name_2="Категория",
            product_name="Тестовый товар",
            description="Описание",
            category_1="Тест",
                category_2="Категория", 
                category_3="Подкатегория",
            article="ART-001",
            photo_url="",
            page_url=""
        )
        
        assert product.id == "TEST-001"
        assert product.product_name == "Тестовый товар"
        assert product.category_1 == "Тест"
        assert product.article == "ART-001"
    
    def test_product_search_text(self):
        """Тест генерации текста для поиска"""
        product = Product(
            id="1",
            section_name_1="Компьютеры",
            section_name_2="Ноутбуки",
            product_name="Ноутбук ASUS",
            description="Современный ноутбук",
            category_1="Электроника",
                category_2="Компьютеры", 
                category_3="Общие",
            article="ASUS-001",
            photo_url="",
            page_url=""
        )
        
        search_text = product.get_search_text()
        
        # Проверяем что все важные поля включены
        assert "Ноутбук ASUS" in search_text
        assert "Современный ноутбук" in search_text
        assert "Компьютеры" in search_text
        assert "Ноутбуки" in search_text
        assert "Общие" in search_text
        assert "ASUS-001" in search_text
    
    def test_product_display_name(self):
        """Тест получения названия для отображения"""
        product = Product(
            id="1",
            section_name_1="Тест",
            section_name_2="Тест",
            product_name="Тестовый товар для отображения",
            description="",
            category_1="Тест",
            category_2="Категория",
            category_3="Подкатегория",
            article="",
            photo_url="",
            page_url=""
        )
        
        assert product.get_display_name() == "Тестовый товар для отображения"
    
    def test_product_full_category(self):
        """Тест формирования полного пути категории"""
        product = Product(
            id="1",
            section_name_1="Электроника",
            section_name_2="Компьютеры",
            product_name="Товар",
            description="",
            category_1="Электроника",
                category_2="Компьютеры", 
                category_3="Ноутбуки",
            article="",
            photo_url="",
            page_url=""
        )
        
        full_category = product.get_full_category()
        assert full_category == "Электроника > Компьютеры > Ноутбуки"


@pytest.mark.unit
@pytest.mark.search
class TestExcelLoader:
    """Unit тесты для ExcelCatalogLoader"""
    
    def test_excel_loader_initialization(self):
        """Тест инициализации загрузчика"""
        loader = ExcelCatalogLoader()
        assert loader is not None
        assert hasattr(loader, 'load_products')
    
    def create_test_excel(self, data: list) -> str:
        """Вспомогательный метод для создания тестового Excel файла"""
        df = pd.DataFrame(data)
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df.to_excel(tmp_file.name, index=False)
            return tmp_file.name
    
    @pytest.mark.asyncio
    async def test_load_valid_excel(self):
        """Тест загрузки корректного Excel файла"""
        test_data = [
            {
                'id': '1',
                'section name 1': 'Тест 1',
                'section name 2': 'Тест 2',
                'product name': 'Тестовый товар',
                'description': 'Описание товара',
                'category 1': 'Тест',
                'category 2': 'Категория',
                'category 3': 'Подкатегория',
                'article': 'TEST-001',
                'photo_url': '',
                'page_url': ''
            }
        ]
        
        excel_file = self.create_test_excel(test_data)
        
        try:
            loader = ExcelCatalogLoader()
            products = await loader.load_products(excel_file)
            
            assert len(products) == 1
            product = products[0]
            
            assert isinstance(product, Product)
            assert product.id == "1"
            assert product.product_name == "Тестовый товар"
            assert product.section_name_1 == "Тест 1"
            assert product.article == "TEST-001"
            
        finally:
            # Очистка
            import os
            if os.path.exists(excel_file):
                os.unlink(excel_file)
    
    @pytest.mark.asyncio
    async def test_load_excel_with_special_characters(self):
        """Тест загрузки Excel с специальными символами"""
        test_data = [
            {
                'id': '1',
                'section name 1': 'Химия & Физика',
                'section name 2': 'Реагенты',
                'product name': 'H₂SO₄ - Серная кислота 98%',
                'description': 'Концентрированная кислота (опасно!)',
                'category 1': 'Материалы',
                'category 2': 'Химия',
                'category 3': 'Кислоты',
                'article': 'CHEM-H2SO4',
                'photo_url': '',
                'page_url': ''
            }
        ]
        
        excel_file = self.create_test_excel(test_data)
        
        try:
            loader = ExcelCatalogLoader()
            products = await loader.load_products(excel_file)
            
            assert len(products) == 1
            product = products[0]
            
            assert "H₂SO₄" in product.product_name
            assert "Химия & Физика" in product.section_name_1
            assert "CHEM-H2SO4" == product.article
            
        finally:
            import os
            if os.path.exists(excel_file):
                os.unlink(excel_file)
    
    @pytest.mark.asyncio
    async def test_load_empty_excel(self):
        """Тест загрузки пустого Excel файла (ожидаем ошибку)"""
        test_data = []  # Пустые данные
        excel_file = self.create_test_excel(test_data)
        
        try:
            loader = ExcelCatalogLoader()
            
            # Ожидаем ошибку валидации для пустого файла
            with pytest.raises(ValueError, match="В Excel файле отсутствуют обязательные колонки"):
                await loader.load_products(excel_file)
            
        finally:
            import os
            if os.path.exists(excel_file):
                os.unlink(excel_file)
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self):
        """Тест загрузки несуществующего файла"""
        loader = ExcelCatalogLoader()
        
        with pytest.raises(Exception):  # Ожидаем любое исключение
            await loader.load_products("nonexistent_file.xlsx")


@pytest.mark.unit
@pytest.mark.search
class TestSentenceTransformersEmbedding:
    """Unit тесты для SentenceTransformersEmbeddingFunction (без загрузки модели)"""
    
    @patch('sentence_transformers.SentenceTransformer')
    def test_embedding_function_initialization(self, mock_sentence_transformer):
        """Тест инициализации функции эмбеддингов (с моком)"""
        from src.infrastructure.search.sentence_transformers_embeddings import SentenceTransformersEmbeddingFunction
        
        # Настраиваем мок
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model
        
        # Создаем функцию эмбеддингов
        embedding_func = SentenceTransformersEmbeddingFunction(
            model_name="test-model",
            batch_size=50
        )
        
        # Проверяем
        assert embedding_func.model_name == "test-model"
        assert embedding_func.batch_size == 50
        mock_sentence_transformer.assert_called_once_with("test-model")
    
    @patch('sentence_transformers.SentenceTransformer')
    def test_embedding_function_call(self, mock_sentence_transformer):
        """Тест вызова функции эмбеддингов (с моком)"""
        from src.infrastructure.search.sentence_transformers_embeddings import SentenceTransformersEmbeddingFunction
        import numpy as np
        
        # Настраиваем мок
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model
        
        # Создаем и вызываем функцию
        embedding_func = SentenceTransformersEmbeddingFunction()
        result = embedding_func(["text1", "text2"])
        
        # Проверяем
        assert len(result) == 2
        assert len(result[0]) == 3
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]
        
        # Проверяем что encode был вызван с правильными параметрами
        mock_model.encode.assert_called_once_with(
            ["text1", "text2"], 
            convert_to_tensor=False,
            normalize_embeddings=True,
            show_progress_bar=False
        )
