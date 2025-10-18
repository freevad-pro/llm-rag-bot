# Исправление ошибки "started_at does not exist"

## Проблема

Каждые 10 минут в логах появляется ошибка:
```
Ошибка поиска неактивных пользователей: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) 
<class 'asyncpg.exceptions.UndefinedColumnError'>: column conversations.started_at does not exist
```

## Причина

Проблема возникает из-за рассогласования между кодом и базой данных:
- **В коде** используется `Conversation.created_at` 
- **В базе данных** (на сервере) все еще ищется поле `started_at`

Это происходит потому что:
1. На сервере запущена старая версия кода
2. Python использует закэшированные .pyc файлы
3. Контейнер не перезапущен после обновления

## Решения

### Решение 1: Быстрое исправление (рекомендуется)

Очистка кэша и перезапуск контейнера:

```bash
# На production сервере
cd /opt/llm-bot/app
./scripts/quick_fix_started_at.sh
```

Или вручную:

```bash
# Очистить Python кэш
docker-compose -f docker-compose.prod.yml exec web find . -type d -name __pycache__ -exec rm -rf {} +
docker-compose -f docker-compose.prod.yml exec web find . -type f -name "*.pyc" -delete

# Перезапустить контейнер
docker-compose -f docker-compose.prod.yml restart web
```

### Решение 2: Полное обновление кода

Если быстрое исправление не помогло, нужно обновить код:

```bash
# На production сервере
cd /opt/llm-bot/app
./scripts/fix_started_at_error.sh
```

Или вручную:

```bash
cd /opt/llm-bot/app

# Остановить контейнеры
docker-compose -f docker-compose.prod.yml down

# Обновить код
git fetch origin main
git reset --hard origin/main

# Удалить кэш
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Пересобрать образ
docker-compose -f docker-compose.prod.yml build web

# Запустить
docker-compose -f docker-compose.prod.yml up -d
```

### Решение 3: Проверка версии кода

Проверить какая версия кода запущена на сервере:

```bash
# На production сервере
cd /opt/llm-bot/app
./scripts/check_server_code_version.sh
```

## Проверка результата

После применения решения подождите 10-15 минут и проверьте логи:

```bash
# Следим за логами в реальном времени
docker-compose -f docker-compose.prod.yml logs -f web

# Или проверяем последние записи
docker-compose -f docker-compose.prod.yml logs --tail=100 web | grep -i "started_at"
```

Если ошибка **не появляется** - проблема решена! ✅

Если ошибка **появляется снова** - переходим к Решению 2 или 3.

## Техническая информация

### Что произошло

1. В ранней версии проекта таблица `conversations` имела поле `started_at`
2. Была создана миграция `008_rename_started_at_to_created_at.py` для переименования
3. Код был обновлен для использования `created_at`
4. На сервере осталась старая версия кода или закэшированные .pyc файлы

### Как это работает

Монитор неактивных пользователей (`InactiveUsersMonitor`) запускается каждые 10 минут и вызывает метод `LeadService.find_inactive_users()`, который:
1. Ищет последнюю активность пользователей в таблице `conversations`
2. Использует поле `created_at` для определения времени последнего сообщения
3. Если в коде используется старое имя `started_at` - возникает ошибка

### Файлы, которые изменились

- `src/infrastructure/database/models.py` - модель Conversation использует `created_at`
- `src/application/telegram/services/lead_service.py` - метод find_inactive_users использует `Conversation.created_at`
- `src/infrastructure/database/migrations/versions/008_rename_started_at_to_created_at.py` - миграция переименования

## Предотвращение проблемы в будущем

1. **Всегда перезапускайте контейнеры** после обновления кода:
   ```bash
   docker-compose -f docker-compose.prod.yml restart web
   ```

2. **Очищайте кэш** при значительных изменениях:
   ```bash
   docker-compose -f docker-compose.prod.yml exec web find . -type d -name __pycache__ -exec rm -rf {} +
   ```

3. **Используйте скрипты обновления** из `scripts/`:
   - `update_safe.sh` - безопасное обновление с бэкапом
   - `update_force.sh` - форсированное обновление
   - `quick_update_prompts.py` - быстрое обновление промптов

## Связанные документы

- [QUICK_UPDATE_GUIDE.md](QUICK_UPDATE_GUIDE.md) - Быстрое обновление сервера
- [vps_update_guide.md](vps_update_guide.md) - Полное руководство по обновлению VPS
- [deployment_strategy.md](deployment_strategy.md) - Стратегия деплоя

