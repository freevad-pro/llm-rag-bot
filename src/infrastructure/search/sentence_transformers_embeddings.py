"""
Sentence-Transformers Embeddings для Chroma DB.
Локальные эмбеддинги без зависимости от внешних API.
"""
import logging
from typing import Optional, List
import numpy as np
from chromadb.api.types import EmbeddingFunction, Documents

logger = logging.getLogger(__name__)


class SentenceTransformersEmbeddingFunction(EmbeddingFunction):
    """
    Функция эмбеддингов через Sentence-Transformers для Chroma DB.
    
    Преимущества:
    - Работает offline без API ключей
    - Поддержка русского и английского языков
    - Быстрая инициализация
    - Стабильная работа без rate limits
    
    Недостатки:
    - +~350MB к размеру Docker образа
    - Требует больше RAM и CPU
    """
    
    def __init__(
        self, 
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        batch_size: int = 32
    ):
        """
        Инициализация Sentence-Transformers эмбеддингов.
        
        Args:
            model_name: Название модели (по умолчанию многоязычная)
            batch_size: Размер батча для обработки
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Ленивая инициализация модели
        self._initialize_model()
    
    def _initialize_model(self):
        """Инициализация модели Sentence-Transformers с обработкой сетевых ошибок."""
        try:
            from sentence_transformers import SentenceTransformer
            
            self._logger.info(f"Загрузка модели Sentence-Transformers: {self.model_name}")
            
            # Устанавливаем более короткий таймаут для избежания долгих зависаний
            import os
            os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '30'  # 30 секунд вместо дефолтных 10 минут
            
            self._model = SentenceTransformer(self.model_name)
            self._logger.info("Модель Sentence-Transformers загружена успешно")
            
        except ImportError as e:
            self._logger.error("sentence-transformers не установлен. Установите: pip install sentence-transformers")
            raise ImportError("sentence-transformers required for local embeddings") from e
        except Exception as e:
            error_msg = f"Ошибка загрузки модели {self.model_name}: {e}"
            self._logger.error(error_msg)
            
            # Проверяем, не сетевая ли это ошибка
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['timeout', 'connection', 'network', 'huggingface']):
                raise RuntimeError(
                    f"Не удалось загрузить модель {self.model_name} из-за проблем с сетью. "
                    f"Убедитесь что модель предзагружена в Docker образ или доступен HuggingFace. "
                    f"Оригинальная ошибка: {e}"
                ) from e
            raise
    
    def __call__(self, input: Documents) -> List[List[float]]:
        """
        Создание эмбеддингов для текстов.
        
        Args:
            input: Список текстов для обработки
            
        Returns:
            Список эмбеддингов
        """
        if not self._model:
            self._initialize_model()
        
        try:
            # Обрабатываем батчами для экономии памяти
            embeddings = []
            
            for i in range(0, len(input), self.batch_size):
                batch = input[i:i + self.batch_size]
                
                # Получаем эмбеддинги для батча
                batch_embeddings = self._model.encode(
                    batch,
                    convert_to_tensor=False,  # Возвращаем numpy arrays
                    normalize_embeddings=True,  # Нормализация для лучшего поиска
                    show_progress_bar=False  # Отключаем прогресс-бар
                )
                
                # Конвертируем в список списков
                embeddings.extend(batch_embeddings.tolist())
            
            self._logger.debug(f"Создано {len(embeddings)} эмбеддингов размерности {len(embeddings[0])}")
            return embeddings
            
        except Exception as e:
            self._logger.error(f"Ошибка создания эмбеддингов: {e}")
            raise
    
    def get_model_info(self) -> dict:
        """
        Информация о модели.
        
        Returns:
            Словарь с информацией о модели
        """
        if not self._model:
            return {
                "model_name": self.model_name,
                "status": "not_loaded",
                "embedding_dim": "unknown"
            }
        
        # Получаем размерность эмбеддинга
        test_embedding = self._model.encode(["test"], convert_to_tensor=False)
        
        return {
            "model_name": self.model_name,
            "status": "loaded",
            "embedding_dim": test_embedding.shape[1],
            "batch_size": self.batch_size,
            "max_seq_length": getattr(self._model, 'max_seq_length', 'unknown')
        }


# Фабрика для создания embedding функций
def create_sentence_transformers_embeddings(
    model_name: Optional[str] = None,
    batch_size: int = 32
) -> SentenceTransformersEmbeddingFunction:
    """
    Создает Sentence-Transformers embedding функцию.
    
    Args:
        model_name: Название модели (если None, используется по умолчанию)
        batch_size: Размер батча
        
    Returns:
        Настроенная embedding функция
    """
    if model_name is None:
        # Многоязычная модель по умолчанию (поддерживает русский)
        model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    return SentenceTransformersEmbeddingFunction(
        model_name=model_name,
        batch_size=batch_size
    )


# Альтернативные модели для разных задач
RECOMMENDED_MODELS = {
    "multilingual": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # Русский + английский
    "english": "sentence-transformers/all-MiniLM-L6-v2",  # Только английский, быстрая
    "russian": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",  # Лучше для русского
    "small": "sentence-transformers/all-MiniLM-L6-v2",  # Самая компактная
    "large": "sentence-transformers/all-mpnet-base-v2"  # Лучшее качество
}
