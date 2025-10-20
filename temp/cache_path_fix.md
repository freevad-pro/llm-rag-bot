# Исправление: Неправильный путь к кэшу модели

## Проблема

Модель успешно загрузилась, но страница показывала "Не загружена".

### Логи показали:
```
Модель успешно загружена. 
Путь: /root/.cache/huggingface/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2/snapshots/...
```

### Код искал в:
```python
cache_dir = Path.home() / ".cache" / "huggingface" / "hub"  # ❌ hub/
```

### Реальный путь:
```
/root/.cache/huggingface/  # ✅ БЕЗ hub/
```

## Причина

`snapshot_download()` при параметре `cache_dir` добавляет свою структуру, а не использует `hub/` подпапку.

## Исправлено

### 1. `src/application/web/routes/model_management.py`

```python
# Было
cache_dir = Path.home() / ".cache" / "huggingface" / "hub"

# Стало
cache_dir = Path.home() / ".cache" / "huggingface"
```

### 2. `src/application/web/routes/catalog.py`

Обновлены обе проверки (GET и POST) с `hub/` на без `hub/`.

### 3. Документация и скрипты

- `docs/model_management_guide.md` - обновлены пути
- `scripts/check_model.sh` - обновлён путь проверки

## Структура кэша HuggingFace

```
/root/.cache/
└── huggingface/
    ├── models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2/
    │   ├── snapshots/
    │   │   └── 86741b4e3f5cb7765a600d3a3d55a0f6a6cb443d/
    │   │       ├── tf_model.h5 (471 MB)
    │   │       ├── config.json
    │   │       └── ... (28 files total)
    │   └── refs/
    │       └── main
    └── hub/  # ← Это другая структура (не используется)
```

## Время загрузки

По логам:
```
Fetching 28 files: 100% [00:39<00:00, 1.40s/it]
tf_model.h5: 100% 471M [00:10<00:00, 46.1MB/s]
```

**Реальное время:** ~40 секунд для 471 MB + метаданные  
**Скорость:** ~46 MB/s (отличная скорость!)

## Результат

После исправления:
- ✅ Страница `/admin/model/` корректно показывает "Загружена"
- ✅ Отображается размер модели
- ✅ Проверка перед загрузкой каталога работает
- ✅ Все пути синхронизированы

## Для деплоя на сервер

```bash
cd /opt/llm-bot/app
git pull
docker compose -f docker-compose.prod.yml restart app

# Проверка
docker compose -f docker-compose.prod.yml exec app du -sh /root/.cache/huggingface/models--*
```

Должно показать ~500 MB.

---

**Дата:** 20.10.2025  
**Статус:** Исправлено, готово к деплою

