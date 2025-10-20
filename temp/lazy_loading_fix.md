# Исправление: Ленивая загрузка модели SentenceTransformers

## Проблема

После внедрения системы управления моделью через веб-интерфейс обнаружилась проблема:

**При старте приложения модель всё равно пыталась загрузиться** из-за вызова `_initialize_model()` в `__init__` класса `SentenceTransformersEmbeddingFunction`.

### Симптомы:
```
app-1  | '(ReadTimeoutError(...))' thrown while requesting HEAD https://huggingface.co/...
app-1  | Retrying in 1s [Retry 1/5].
```

### Последовательность событий:
1. `main.py` запускается
2. Создаётся экземпляр `CatalogSearchService` (даже если не используется)
3. В `CatalogSearchService.__init__()` создаётся `SentenceTransformersEmbeddingFunction`
4. В `SentenceTransformersEmbeddingFunction.__init__()` вызывался `self._initialize_model()`
5. Модель пыталась загрузиться из HuggingFace → таймаут

## Решение

Убрал **преждевременную загрузку** модели из `__init__`:

### Было:
```python
def __init__(self, model_name: str = "...", batch_size: int = 32):
    self.model_name = model_name
    self.batch_size = batch_size
    self._model = None
    self._logger = logging.getLogger(...)
    
    # ❌ ЗАГРУЖАЛО МОДЕЛЬ СРАЗУ
    self._initialize_model()
```

### Стало:
```python
def __init__(self, model_name: str = "...", batch_size: int = 32):
    self.model_name = model_name
    self.batch_size = batch_size
    self._model = None
    self._logger = logging.getLogger(...)
    
    # ✅ НЕ загружаем модель при инициализации
    # Модель загрузится при первом вызове __call__
```

### Как работает ленивая загрузка:

Модель загружается **только при первом использовании** в методе `__call__`:

```python
def __call__(self, input: Documents) -> List[List[float]]:
    # ✅ Проверяем и загружаем только если нужно
    if not self._model:
        self._initialize_model()
    
    # Используем модель...
```

## Результат

### До исправления:
- ❌ Приложение при старте пыталось загрузить модель
- ❌ Таймауты на старте если модель не скачана
- ❌ Задержка запуска даже когда модель не нужна

### После исправления:
- ✅ Приложение стартует быстро
- ✅ Модель загружается только когда действительно нужна (при индексации)
- ✅ Если модель не скачана - приложение всё равно работает (просто нельзя индексировать)

## Файлы

**Изменён:** `src/infrastructure/search/sentence_transformers_embeddings.py`
- Строка 46: Закомментирован вызов `self._initialize_model()`
- Добавлен комментарий о ленивой загрузке

## Тестирование

Проверить что приложение стартует без попыток загрузки модели:

```bash
docker compose -f docker-compose.prod.yml restart app
docker compose -f docker-compose.prod.yml logs app --tail=50 | grep -i "huggingface\|sentence"
```

Должно быть пусто или только при **фактической индексации**.

---

**Дата:** 20.10.2025
**Статус:** Исправлено

