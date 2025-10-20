# Исправление: Неправильный repo_id модели

## Проблема

Ошибка 401 при загрузке модели:
```
Repository Not Found for url: https://huggingface.co/api/models/paraphrase-multilingual-MiniLM-L12-v2/revision/main
```

## Причина

В переменной окружения `EMBEDDING_MODEL` не указан префикс организации.

**Было:**
```env
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
```

**Должно быть:**
```env
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

## Исправление на сервере

### 1. Обновить `.env` на сервере

```bash
ssh user@server
cd /opt/llm-bot/config

# Открыть .env и исправить строку
nano .env
```

Найти:
```env
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
```

Заменить на:
```env
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Сохранить: `Ctrl+O`, `Enter`, `Ctrl+X`

### 2. Перезапустить приложение

```bash
cd /opt/llm-bot/app
docker compose -f docker-compose.prod.yml restart app
```

### 3. Попробовать загрузить модель снова

Через веб-интерфейс: `/admin/model/` → "Скачать модель"

## Что исправлено в репозитории

Обновлены все файлы с переменными окружения:
- ✅ `env.production`
- ✅ `env.example`  
- ✅ `env.test`

## Правильный формат repo_id

HuggingFace требует полный путь: `{organization}/{model-name}`

Примеры:
- ✅ `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- ✅ `openai/gpt-3.5-turbo`
- ✅ `meta-llama/Llama-2-7b`
- ❌ `paraphrase-multilingual-MiniLM-L12-v2` (без организации)

---

**Дата:** 20.10.2025  
**Статус:** Исправлено в репозитории, требуется обновление на сервере

