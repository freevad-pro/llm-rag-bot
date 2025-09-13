"""
OpenAI Embeddings для Chroma DB.
Замена sentence-transformers для экономии ресурсов и улучшения качества.
"""
import logging
from typing import Optional, List
import httpx
import json
from chromadb.api.types import EmbeddingFunction, Documents

from src.config.settings import settings
from src.infrastructure.logging.hybrid_logger import hybrid_logger


class OpenAIEmbeddingFunction(EmbeddingFunction):
    """
    Функция эмбеддингов через OpenAI API для Chroma DB.
    
    Преимущества над sentence-transformers:
    - Экономия ~350MB в Docker образе
    - Лучшее качество для коммерческих каталогов
    - Оптимизация для CPU-серверов
    - Поддержка мультиязычности
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        batch_size: int = 100
    ) -> None:
        """
        Инициализация OpenAI embeddings.
        
        Args:
            api_key: OpenAI API ключ (берется из настроек если не указан)
            model: Модель эмбеддингов (text-embedding-3-small по умолчанию)
            batch_size: Размер batch для обработки
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model
        self.batch_size = batch_size
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        if not self.api_key:
            raise ValueError("OpenAI API key не настроен. Установите OPENAI_API_KEY")
        
        self._logger.info(f"Инициализирован OpenAI Embeddings с моделью {model}")
    
    def __call__(self, input: Documents) -> List[List[float]]:
        """
        Создает эмбеддинги для списка документов.
        
        Args:
            input: Список текстов для обработки
            
        Returns:
            Список векторов эмбеддингов
        """
        if not input:
            return []
        
        try:
            # Обрабатываем большие списки порциями
            all_embeddings = []
            
            for i in range(0, len(input), self.batch_size):
                batch = input[i:i + self.batch_size]
                batch_embeddings = self._get_embeddings_batch(batch)
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
            
        except Exception as e:
            self._logger.error(f"Ошибка создания эмбеддингов: {e}")
            raise
    
    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Получает эмбеддинги для порции текстов через OpenAI API.
        
        Args:
            texts: Список текстов для обработки
            
        Returns:
            Список векторов эмбеддингов
        """
        try:
            # Подготавливаем запрос
            payload = {
                "input": texts,
                "model": self.model,
                "encoding_format": "float"
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Отправляем запрос к OpenAI API
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    "https://api.openai.com/v1/embeddings",
                    json=payload,
                    headers=headers
                )
                
                response.raise_for_status()
                data = response.json()
            
            # Извлекаем эмбеддинги из ответа
            embeddings = []
            for item in data["data"]:
                embeddings.append(item["embedding"])
            
            self._logger.debug(f"Получено {len(embeddings)} эмбеддингов для {len(texts)} текстов")
            return embeddings
            
        except httpx.HTTPStatusError as e:
            self._logger.error(f"HTTP ошибка OpenAI API: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            self._logger.error(f"Ошибка соединения с OpenAI API: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Неожиданная ошибка при получении эмбеддингов: {e}")
            raise


async def test_openai_embeddings() -> bool:
    """
    Тестирует работу OpenAI embeddings.
    
    Returns:
        True если тест прошел успешно
    """
    try:
        embedding_func = OpenAIEmbeddingFunction()
        
        # Тестовые тексты
        test_texts = [
            "болт М12 нержавеющая сталь",
            "гайка шестигранная оцинкованная", 
            "шайба плоская DIN 125"
        ]
        
        # Получаем эмбеддинги
        embeddings = embedding_func(test_texts)
        
        # Проверяем результат
        if len(embeddings) != len(test_texts):
            return False
        
        # Проверяем размерность векторов
        for embedding in embeddings:
            if not isinstance(embedding, list) or len(embedding) == 0:
                return False
        
        await hybrid_logger.info(
            f"OpenAI embeddings тест пройден: "
            f"{len(embeddings)} векторов размерности {len(embeddings[0])}"
        )
        
        return True
        
    except Exception as e:
        await hybrid_logger.error(f"Ошибка теста OpenAI embeddings: {e}")
        return False
