# Исправление: Правильный путь к кэшу HuggingFace

## Проблема

Код искал модель в неправильной директории:
```
❌ /root/.cache/torch/sentence_transformers/sentence-transformers_paraphrase-multilingual-MiniLM-L12-v2/
```

Но модель фактически находится здесь:
```
✅ /root/.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2/
```

## Причина

С версии **transformers 4.x** и **sentence-transformers 2.x** изменился механизм кэширования:

**Старый путь (до 2023):**
- `/root/.cache/torch/sentence_transformers/`
- Формат: `org_model` → `sentence-transformers_paraphrase-multilingual-MiniLM-L12-v2`

**Новый путь (с 2023):**
- `/root/.cache/huggingface/hub/`
- Формат: `models--org--model` → `models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2`

## Как обнаружили

1. Модель работала (тест прошёл успешно)
2. Но директория "не существовала" при проверке
3. Нашли реальный путь через Python:
   ```python
   import subprocess
   result = subprocess.run(['find', '/root/.cache', '-name', '*paraphrase*', '-type', 'd'])
   ```

## Что исправлено

### 1. `src/application/web/routes/model_management.py`

**Было:**
```python
cache_dir = Path.home() / ".cache" / "torch" / "sentence_transformers"
model_name = settings.embedding_model.replace("/", "_")
model_dir = cache_dir / model_name
```

**Стало:**
```python
cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
model_name = settings.embedding_model.replace("/", "--")
model_dir = cache_dir / f"models--{model_name}"
```

### 2. `src/application/web/routes/catalog.py`

Обновлены обе проверки (в GET и POST) на правильный путь.

### 3. `docs/model_management_guide.md`

Обновлены все команды проверки и документация.

### 4. `scripts/check_model.sh`

Обновлён скрипт для проверки в правильной директории.

## Формат преобразования имени

```python
# Старый формат
"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  ↓ .replace("/", "_")
"sentence-transformers_paraphrase-multilingual-MiniLM-L12-v2"

# Новый формат HuggingFace Hub
"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  ↓ .replace("/", "--") + добавить "models--"
"models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2"
```

## Проверка после исправления

На сервере:
```bash
docker compose -f docker-compose.prod.yml exec app \
  du -sh /root/.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2
```

Должно показать ~400-500 MB если модель загружена полностью.

Или через обновлённый скрипт:
```bash
bash scripts/check_model.sh
```

## Теперь работает корректно

- ✅ Страница `/admin/model/` показывает правильный статус
- ✅ Отображается размер модели
- ✅ Проверка перед загрузкой каталога работает
- ✅ Кнопка "Удалить модель" удалит правильную директорию

## Объяснение быстрой "загрузки"

**15 секунд для "загрузки"** объясняется тем, что:
1. Модель уже была в кэше HuggingFace (частично загружена ранее)
2. `SentenceTransformer()` просто проверил наличие и загрузил в память
3. Реальная загрузка с интернета заняла бы 5-10 минут

**Откуда была модель в кэше?**
- При предыдущих попытках запуска (до исправления ленивой загрузки)
- Приложение пыталось загрузить модель при старте
- Частично успело скачать или полностью скачало до таймаута

---

**Дата:** 20.10.2025  
**Статус:** Исправлено

