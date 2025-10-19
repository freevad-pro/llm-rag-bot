# Руководство по устранению проблем с миграциями Alembic в Docker

## 1. Описание ситуации (ошибки)

При попытке создать миграцию возникали следующие ошибки:

```bash
ERROR [alembic.util.messaging] Target database is not up to date.
FAILED: Target database is not up to date.

ERROR [alembic.util.messaging] Multiple head revisions are present
FAILED: Multiple heads are present; please specify the head revision
```

Дополнительные проблемы:
- При проверке `alembic heads` показывало две головные ревизии вместо одной
- При попытке `alembic upgrade head` - ошибка о множественных головах
- Таблицы в БД существовали, но `alembic_version` отсутствовала
- Файлы миграций продолжали появляться даже после удаления

## 2. Возможные причины создания такой ситуации

1. **Раздвоение истории миграций** - когда два разработчика создают миграции параллельно от одной точки
2. **Ручное изменение БД** - таблицы создавались не через миграции, а напрямую или через `Base.metadata.create_all()`
3. **Неполная очистка при сбросе миграций** - удаление файлов миграций без очистки таблицы `alembic_version`
4. **Конфликты при слиянии веток** в Git с разными миграциями

## 3. Причины ошибки в данном случае

### Основная причина
Старые файлы миграций были **встроены в Docker образ** при сборке, поэтому:
- Удаление файлов на хосте не помогало
- После перезапуска контейнера файлы возвращались
- Alembic видел историю миграций с "раздвоением" (009 → 010 и 009 → 8bd76168eb7e)

### Дополнительные проблемы
1. **Приложение создавало таблицы при старте** - логи показывали "База данных инициализирована", что означало создание таблиц через SQLAlchemy напрямую
2. **Отсутствие таблицы alembic_version** - Alembic не мог определить текущую версию БД
3. **Ошибка в alembic.ini** - параметр `version_num_format = %04d` вызывал `InterpolationSyntaxError` (нужно `%%04d`)
4. **Volume mounting** - код монтировался с хоста, но при этом образ содержал старые версии файлов

## 4. Как исправить ошибку (пошаговое руководство)

### Шаг 1: Полная очистка БД и миграций

```bash
# 1. Остановить все контейнеры
docker-compose -f docker-compose.prod.yml down

# 2. Удалить данные PostgreSQL (ВСЕ ДАННЫЕ БУДУТ ПОТЕРЯНЫ!)
rm -rf /opt/llm-bot/data/postgres/*

# 3. Удалить старые файлы миграций на хосте
rm -rf /opt/llm-bot/app/src/infrastructure/database/migrations/versions/*.py

# 4. Проверить что папка пустая
ls -la /opt/llm-bot/app/src/infrastructure/database/migrations/versions/
```

### Шаг 2: Создать правильный alembic.ini

```bash
cd /opt/llm-bot/app

cat > alembic.ini << 'EOF'
[alembic]
script_location = src/infrastructure/database/migrations
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql+asyncpg://postgres:password@postgres:5432/catalog_db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
EOF
```

**Важно:** Если хотите числовые версии файлов (0001, 0002 вместо хешей), добавьте строку:
```ini
version_num_format = %%04d
```
(именно два процента!)

### Шаг 3: Закоммитить изменения в Git

```bash
# Настроить git (если не настроен)
git config --global user.email "admin@server.com"
git config --global user.name "Server Admin"

# Закоммитить удаление
git add -A
git commit -m "Clean up migration files and fix alembic.ini"

# Проверить
git status
```

### Шаг 4: Пересобрать Docker образ

```bash
# Пересобрать БЕЗ кеша (важно!)
docker-compose -f docker-compose.prod.yml build --no-cache app

# Запустить контейнеры
docker-compose -f docker-compose.prod.yml up -d

# Подождать запуска PostgreSQL
sleep 15

# Проверить что всё запустилось
docker-compose -f docker-compose.prod.yml ps
```

### Шаг 5: Проверить чистоту миграций

```bash
# Проверить что папка versions пустая
docker-compose -f docker-compose.prod.yml exec app ls -la src/infrastructure/database/migrations/versions/

# Проверить что alembic.ini правильный
docker-compose -f docker-compose.prod.yml exec app cat /app/alembic.ini | head -10

# Проверить что нет heads
docker-compose -f docker-compose.prod.yml exec app alembic heads
# Должно быть пусто или ошибка
```

### Шаг 6: Создать первую миграцию

```bash
# Создать пустую начальную миграцию
docker-compose -f docker-compose.prod.yml exec app alembic revision -m "initial"

# Проверить что создалась
docker-compose -f docker-compose.prod.yml exec app alembic heads
# Должен показать один head с хешом

# Пометить БД этой версией (таблицы уже существуют)
docker-compose -f docker-compose.prod.yml exec app alembic stamp head

# Проверить статус
docker-compose -f docker-compose.prod.yml exec app alembic current
```

### Шаг 7: Проверить результат

```bash
# Проверить таблицу alembic_version
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d catalog_db -c "SELECT * FROM alembic_version;"

# Проверить все таблицы
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d catalog_db -c "\dt"

# Проверить историю миграций
docker-compose -f docker-compose.prod.yml exec app alembic history
```

## 5. Профилактика ошибок

### Правила работы с миграциями

1. **Всегда используйте миграции** - не создавайте таблицы через `Base.metadata.create_all()` в production
2. **Коммитьте файлы миграций** - они должны быть в Git
3. **Один разработчик - одна миграция** - избегайте параллельных миграций
4. **Пересобирайте образ** после изменения миграций

### Настройка приложения

Если в коде есть автоматическое создание таблиц:

```python
# ПЛОХО - не использовать в production
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)

# ХОРОШО - использовать только миграции
# Удалить create_all из кода продакшена
```

### Структура проекта

```
/opt/llm-bot/app/
├── alembic.ini                    # Конфигурация Alembic
├── src/
│   └── infrastructure/
│       └── database/
│           ├── models.py          # Модели SQLAlchemy
│           └── migrations/        # Папка миграций
│               ├── env.py         # Настройка окружения
│               ├── script.py.mako # Шаблон миграций
│               └── versions/      # Файлы миграций
│                   └── [hash]_description.py
```

## 6. Правильный workflow миграций

### Создание новой миграции

```bash
# 1. Изменить models.py на хосте
# Например, добавить новое поле в модель

# 2. Создать миграцию с autogenerate
docker-compose -f docker-compose.prod.yml exec app alembic revision --autogenerate -m "add_user_email_field"

# 3. Проверить созданный файл миграции
# Файл появится в src/infrastructure/database/migrations/versions/
cat src/infrastructure/database/migrations/versions/*_add_user_email_field.py

# 4. При необходимости отредактировать миграцию вручную
# Alembic не всегда корректно определяет все изменения

# 5. Применить миграцию
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# 6. Проверить результат
docker-compose -f docker-compose.prod.yml exec app alembic current
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d catalog_db -c "\d+ table_name"
```

### Откат миграции

```bash
# Откат на одну миграцию назад
docker-compose -f docker-compose.prod.yml exec app alembic downgrade -1

# Откат до конкретной ревизии
docker-compose -f docker-compose.prod.yml exec app alembic downgrade <revision_hash>

# Проверить текущую версию
docker-compose -f docker-compose.prod.yml exec app alembic current
```

### Слияние веток с миграциями

Если в Git появились две головы после мерджа:

```bash
# 1. Проверить головы
docker-compose -f docker-compose.prod.yml exec app alembic heads

# 2. Создать merge миграцию
docker-compose -f docker-compose.prod.yml exec app alembic merge -m "merge_branches" <rev1> <rev2>

# 3. Применить
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

### Деплой на продакшен

```bash
# 1. Обновить код из Git
cd /opt/llm-bot/app
git pull origin main

# 2. Пересобрать образ если изменились зависимости
docker-compose -f docker-compose.prod.yml build app

# 3. Остановить контейнеры
docker-compose -f docker-compose.prod.yml down

# 4. Запустить
docker-compose -f docker-compose.prod.yml up -d

# 5. Применить миграции
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# 6. Проверить
docker-compose -f docker-compose.prod.yml exec app alembic current
```

## 7. Нужно ли исправить код

### Проверьте код приложения

Найдите и удалите/закомментируйте автоматическое создание таблиц:

```python
# src/infrastructure/database/connection.py или аналогичный файл

# ❌ УДАЛИТЬ или закомментировать:
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # Это создаёт таблицы

# ✅ Правильно - создание через миграции:
async def init_db():
    # Подключение к БД есть
    # Таблицы создаются через alembic upgrade head
    pass
```

### Что оставить в коде

Создание админа и другую инициализацию данных можно оставить:

```python
async def init_db():
    # ✅ Это нормально - работа с данными, не схемой
    async with AsyncSession(engine) as session:
        existing_admin = await session.scalar(
            select(AdminUser).where(AdminUser.username == "admin")
        )
        if not existing_admin:
            # Создать первого админа
            pass
```

## 8. Важные замечания

### ⚠️ Критические моменты

1. **Volume mounting** - когда код монтируется с хоста, старые файлы в образе могут конфликтовать. Всегда пересобирайте образ после изменения структуры проекта.

2. **Git и миграции** - файлы миграций ОБЯЗАТЕЛЬНО должны быть в Git. Они часть кода приложения.

3. **Формат версий** - если используете `version_num_format`, обязательно экранируйте: `%%04d` (два процента!)

4. **База данных** - `alembic_version` - служебная таблица. НЕ удаляйте её вручную, НЕ изменяйте значения.

5. **PostgreSQL и пароль** - в примерах используется `password`. В продакшене используйте надёжные пароли из переменных окружения.

### 💡 Лучшие практики

1. **Проверяйте миграции** - всегда просматривайте сгенерированный файл миграции перед применением
2. **Тестируйте откаты** - убедитесь что `downgrade` работает
3. **Бэкапы** - делайте бэкап БД перед применением миграций в продакшене
4. **Логирование** - храните логи выполнения миграций
5. **CI/CD** - автоматизируйте проверку миграций в pipeline

### 📝 Полезные команды

```bash
# Посмотреть текущую версию
alembic current

# Посмотреть все головы
alembic heads

# Посмотреть историю
alembic history

# Показать конкретную миграцию
alembic show <revision>

# Создать SQL-скрипт миграции (без применения)
alembic upgrade head --sql

# Проверить что будет применено
alembic upgrade head --sql > migration.sql
```

### 🔧 Troubleshooting

**Проблема:** "Target database is not up to date"
- **Решение:** Проверьте `alembic_version`, используйте `alembic stamp head`

**Проблема:** "Multiple heads"
- **Решение:** Создайте merge миграцию или полная очистка (как в разделе 4)

**Проблема:** Миграция не создаётся
- **Решение:** Проверьте что `target_metadata = Base.metadata` правильно настроено в `env.py`

**Проблема:** Изменения в models.py не попадают в миграцию
- **Решение:** Убедитесь что модель импортируется в `models.py` и `Base` знает о ней

---

**Дата создания:** 19.10.2025  
**Версия:** 1.0  
**Статус:** Протестировано и работает