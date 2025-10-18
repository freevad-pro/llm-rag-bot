# 🚀 Инструкция по обновлению бота на VPS

Подробное руководство по обновлению Telegram бота на VPS сервере. Все команды можно копировать и вставлять в терминал.

**⚠️ ВАЖНО:** Эта инструкция включает обновление кода, Docker образов и **миграций базы данных**.

---

## ⚡ TL;DR - Быстрое обновление

**Для большинства случаев достаточно одной команды:**

```bash
# Подключитесь к серверу
ssh root@ваш-сервер.ru

# Запустите автоматическое обновление
cd /opt/llm-bot && ./scripts/update.sh
```

**Скрипт автоматически:**
- ✅ Создаст backup
- ✅ Обновит код из Git
- ✅ Применит миграции БД
- ✅ Пересоберет Docker образы
- ✅ Откатится при ошибках

**Ваш `.env` файл не будет затронут** - все ваши ключи и настройки сохранятся.

**Читайте дальше**, если нужны детали или возникли проблемы.

---

## 📋 Содержание

1. [Быстрая проверка статуса](#быстрая-проверка-статуса)
2. [Вариант 1: Автоматическое обновление (РЕКОМЕНДУЕТСЯ)](#вариант-1-автоматическое-обновление-рекомендуется)
3. [Вариант 2: Ручное обычное обновление](#вариант-2-ручное-обычное-обновление)
4. [Вариант 3: Жесткое обновление (перезапись всех файлов)](#вариант-3-жесткое-обновление)
5. [Обновление конфигурации (.env файл)](#обновление-конфигурации-env-файл)
6. [Проверка после обновления](#проверка-после-обновления)
7. [Устранение проблем](#устранение-проблем)

---

## 🔍 Быстрая проверка статуса

Подключитесь к VPS и проверьте текущий статус:

```bash
# Подключение к VPS (замените на ваши данные)
ssh root@ваш-сервер.ru

# Переход в директорию проекта
cd /opt/llm-bot/app

# Проверка статуса контейнеров
docker-compose -f docker-compose.prod.yml ps

# Проверка последних логов бота
docker-compose -f docker-compose.prod.yml logs bot --tail=20
```

**🟢 Все работает если:**
- Контейнер `bot` в статусе `Up`
- В логах есть записи о запуске бота и нет критических ошибок

---

## 🤖 Вариант 1: Автоматическое обновление (РЕКОМЕНДУЕТСЯ)

**Когда использовать:** Всегда, когда нужно обновить бот с минимальными рисками.

**Что делает скрипт:**
- ✅ Автоматически создает backup перед обновлением
- ✅ Проверяет наличие обновлений в Git
- ✅ Применяет миграции базы данных (Alembic)
- ✅ Пересобирает Docker образы при необходимости
- ✅ Проверяет работоспособность после обновления
- ✅ **Автоматически откатывается** при ошибках

### 🚀 Простое обновление (безопасное)

```bash
# Подключаемся к серверу
ssh root@ваш-сервер.ru

# Переходим в директорию скриптов
cd /opt/llm-bot

# Запускаем автоматическое обновление
./scripts/update.sh
```

**Что происходит:**
1. Скрипт проверит наличие новых коммитов
2. Если обновлений нет - сообщит об этом и завершится
3. Если есть обновления - покажет список изменений
4. При наличии локальных изменений - остановится и попросит подтверждения

### 🔨 Принудительное обновление (с сохранением локальных изменений)

```bash
# Использовать если есть локальные изменения, которые нужно сохранить
./scripts/update.sh --force
```

**Что происходит:**
- Локальные изменения сохраняются в Git stash
- Применяются обновления с GitHub
- Локальные изменения можно восстановить позже через `git stash pop`

### ⚡ Полная перезапись (игнорировать локальные изменения)

```bash
# ВНИМАНИЕ: Удалит ВСЕ локальные изменения!
./scripts/update.sh --force-overwrite
```

**Используйте только если:**
- Локальные изменения не нужны
- Нужна точная копия из репозитория
- После критических ошибок

### 📋 Что делает скрипт обновления

Скрипт `update.sh` выполняет следующие шаги:

1. **Backup:** Создает резервную копию данных
2. **Git:** Получает обновления из репозитория
3. **Docker:** Пересобирает образы при изменении зависимостей
4. **Миграции:** Применяет изменения схемы базы данных (`alembic upgrade head`)
5. **Проверка:** Тестирует health endpoint и подключение к БД
6. **Откат:** При ошибках автоматически возвращается к предыдущей версии

### ✅ Проверка результата

После завершения скрипт покажет:
```
=== РЕЗУЛЬТАТ ОБНОВЛЕНИЯ ===
📝 Предыдущая версия: abc1234
📝 Новая версия: def5678
🏗️ Образ пересобран: Да
⏱️  Время обновления: 2025-10-18 15:30:00

=== ИЗМЕНЕНИЯ ===
def5678 Добавлена новая функция
...

🎉 Обновление завершено успешно!
```

---

## 🔧 Вариант 2: Ручное обычное обновление

**Когда использовать:** Если автоматический скрипт не работает или нужен особый контроль.

### Шаг 1: Проверка изменений

```bash
cd /opt/llm-bot/app
git status
```

**Если есть изменения** - решите:
- Сохранить их → используйте `git stash` перед обновлением
- Удалить их → переходите к [Варианту 3](#вариант-3-жесткое-обновление)

### Шаг 2: Загрузка обновлений

```bash
# Загрузка обновлений с GitHub
git fetch origin main

# Проверка что будет обновлено
git log HEAD..origin/main --oneline

# Применение обновлений
git pull origin main
```

**Если возникла ошибка слияния:**
```bash
# Прервать слияние и перейти к варианту 3
git merge --abort
```

### Шаг 3: Применение миграций БД

```bash
# ВАЖНО: Применяем миграции базы данных
docker-compose -f docker-compose.prod.yml exec app python -m alembic upgrade head

# Проверяем текущую версию схемы БД
docker-compose -f docker-compose.prod.yml exec app python -m alembic current
```

### Шаг 4: Перезапуск контейнеров

```bash
# Если были изменения только в коде Python
docker-compose -f docker-compose.prod.yml restart app bot

# Если менялись зависимости или Dockerfile
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

**Используйте полную пересборку если:**
- Обновлялись зависимости (pyproject.toml)
- Менялся Dockerfile
- Добавлялись новые системные пакеты

---

## 🔥 Вариант 3: Жесткое обновление

**Когда использовать:** Когда есть конфликты, нужна точная копия репозитория или после критических изменений.

### Шаг 1: Остановка контейнеров

```bash
cd /opt/llm-bot/app

# Полная остановка всех контейнеров
docker-compose -f docker-compose.prod.yml down
```

### Шаг 2: Жесткая перезапись файлов

```bash
# ВНИМАНИЕ: Удалит ВСЕ локальные изменения!
git reset --hard HEAD
git clean -fd
git pull origin main --force
```

### Шаг 3: Полная пересборка

```bash
# Пересборка всех контейнеров
docker-compose -f docker-compose.prod.yml build --no-cache

# Запуск контейнеров
docker-compose -f docker-compose.prod.yml up -d
```

### Шаг 4: Применение миграций БД

```bash
# Ждем пока контейнеры запустятся (30-60 секунд)
sleep 30

# Применяем миграции базы данных
docker-compose -f docker-compose.prod.yml exec app python -m alembic upgrade head

# Проверяем статус
docker-compose -f docker-compose.prod.yml exec app python -m alembic current
```

---

## 🔧 Обновление конфигурации (.env файл)

### Когда обновлять .env файл

**✅ МОЖНО ОСТАВИТЬ СТАРЫЙ `.env` если:**
- Бот работает нормально
- Все ключи API актуальны
- Нет новых критичных настроек

**⚠️ НУЖНО ОБНОВИТЬ `.env` если:**
- Добавились новые обязательные переменные
- Изменились значения по умолчанию
- Нужны новые функции (например, AI Cost Control)

### Проверка новых переменных

```bash
# Сравнить текущий .env с новым шаблоном
cd /opt/llm-bot/app
diff /opt/llm-bot/config/.env env.production

# Или посмотреть только добавленные переменные
comm -13 <(grep -E '^[A-Z_]+=' /opt/llm-bot/config/.env | sort) \
         <(grep -E '^[A-Z_]+=' env.production | sort)
```

### Добавление новых переменных

**Вариант 1: Ручное добавление (РЕКОМЕНДУЕТСЯ)**

```bash
# Открываем существующий .env
nano /opt/llm-bot/config/.env

# Добавляем новые переменные из env.production
# Например, для AI Cost Control:
# MONTHLY_TOKEN_LIMIT=500000
# MONTHLY_COST_LIMIT_USD=50.00
# COST_ALERT_THRESHOLD=0.8
# AUTO_DISABLE_ON_LIMIT=true
# COST_ALERT_ENABLED=true
# WEEKLY_USAGE_REPORT=true
```

**Вариант 2: Полная замена (если структура сильно изменилась)**

```bash
# ВНИМАНИЕ: Сохраните старый файл!
cp /opt/llm-bot/config/.env /opt/llm-bot/config/.env.backup

# Скопируйте новый шаблон
cp /opt/llm-bot/app/env.production /opt/llm-bot/config/.env

# Восстановите свои значения из backup
nano /opt/llm-bot/config/.env
```

### Применение изменений .env

```bash
# После изменения .env перезапустите контейнеры
cd /opt/llm-bot/app
docker-compose -f docker-compose.prod.yml restart app bot
```

### Новые переменные в последних версиях

**AI Cost Control (добавлены недавно):**
```env
MONTHLY_TOKEN_LIMIT=500000
MONTHLY_COST_LIMIT_USD=50.00
COST_ALERT_THRESHOLD=0.8
AUTO_DISABLE_ON_LIMIT=true
COST_ALERT_ENABLED=true
WEEKLY_USAGE_REPORT=true
```

**Модели AI (если используете новые модели):**
```env
OPENAI_DEFAULT_MODEL=gpt-4o-mini
OPENAI_AVAILABLE_MODELS=gpt-4o-mini,gpt-4o
YANDEX_DEFAULT_MODEL=yandexgpt-lite
YANDEX_AVAILABLE_MODELS=yandexgpt-lite,yandexgpt
```

---

## ✅ Проверка после обновления

### 1. Проверка статуса контейнеров

```bash
# Статус всех контейнеров
docker-compose -f docker-compose.prod.yml ps

# Ожидаемый результат:
# ✅ app: Up (порт 8000)
# ✅ bot: Up  
# ✅ postgres: Up (healthy)
```

### 2. Проверка миграций базы данных

```bash
# Проверяем текущую версию схемы БД
docker-compose -f docker-compose.prod.yml exec app python -m alembic current

# Должно показать последнюю примененную миграцию, например:
# 8bd76168eb7e (head)

# Проверяем историю миграций
docker-compose -f docker-compose.prod.yml exec app python -m alembic history

# Должен показать список всех миграций с отметкой (current) на последней
```

**🟢 Норма:**
- Текущая миграция помечена как `(head)`
- Нет ошибок при выполнении команд
- В истории видны все миграции

**🔴 Проблемы - если:**
```
# Миграция не на последней версии
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
abc123 (не head)

# Решение: применить миграции
docker-compose -f docker-compose.prod.yml exec app python -m alembic upgrade head
```

### 3. Проверка логов приложения

```bash
# Последние 30 записей логов app (FastAPI)
docker-compose -f docker-compose.prod.yml logs app --tail=30

# Последние 30 записей логов bot (Telegram)
docker-compose -f docker-compose.prod.yml logs bot --tail=30 -f
```

**🟢 Норма - должно быть:**
```
✅ Запуск Telegram бота...
✅ База данных инициализирована  
✅ Бот запущен: @ваш_бот
✅ Dispatcher настроен с поддержкой поиска, LLM...
✅ Запущен монитор неактивных пользователей
```

**🔴 Ошибки - НЕ должно быть:**
```
❌ BOT_TOKEN не настроен!
❌ TelegramConflictError: terminated by other getUpdates
❌ Failed to connect to database
❌ alembic.util.exc.CommandError: Can't locate revision
❌ Critical error in...
```

### 4. Проверка работы бота

Отправьте боту в Telegram:
```
/start
```

**Ожидаемый результат:**
- Бот отвечает приветственным сообщением
- Показывается меню с кнопками
- В логах появляется `Новый чат: XXXXX`

### 4. Проверка health endpoint

```bash
# Проверка API
curl -s http://localhost:8000/health | jq
```

**Ожидаемый результат:**
```json
{
  "status": "healthy",
  "database": "connected",
  "bot": "running"
}
```

---

## 🚨 Устранение проблем

### Проблема: Ошибки миграций базы данных

**Симптомы:**
- `alembic.util.exc.CommandError: Can't locate revision`
- `Target database is not up to date`
- Ошибки при запуске приложения связанные с отсутствующими колонками/таблицами

**Диагностика:**
```bash
# Проверяем текущую версию миграций
docker-compose -f docker-compose.prod.yml exec app python -m alembic current

# Проверяем историю
docker-compose -f docker-compose.prod.yml exec app python -m alembic history

# Смотрим логи приложения
docker-compose -f docker-compose.prod.yml logs app --tail=50 | grep -i alembic
```

**Решение 1: Применить недостающие миграции**
```bash
# Применяем все миграции до последней
docker-compose -f docker-compose.prod.yml exec app python -m alembic upgrade head

# Перезапускаем приложение
docker-compose -f docker-compose.prod.yml restart app bot
```

**Решение 2: Сбросить миграции (ОПАСНО! Только если БД пустая или тестовая)**
```bash
# ВНИМАНИЕ: Это удалит все данные!
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d postgres
sleep 10
docker-compose -f docker-compose.prod.yml up -d app
sleep 10
docker-compose -f docker-compose.prod.yml exec app python -m alembic upgrade head
docker-compose -f docker-compose.prod.yml up -d bot
```

**Решение 3: Откат к предыдущей версии кода**
```bash
# Если миграции сломали БД - откатываемся
cd /opt/llm-bot/app
git log --oneline -5
git reset --hard ПРЕДЫДУЩИЙ_КОММИТ

# Откатываем миграции
docker-compose -f docker-compose.prod.yml exec app python -m alembic downgrade -1

# Перезапускаем
docker-compose -f docker-compose.prod.yml restart app bot
```

### Проблема: Бот не отвечает

**Диагностика:**
```bash
# Проверка статуса контейнера
docker-compose -f docker-compose.prod.yml ps bot

# Детальные логи
docker-compose -f docker-compose.prod.yml logs bot --tail=50
```

**Решение:**
```bash
# Перезапуск бота
docker-compose -f docker-compose.prod.yml restart bot

# Если не помогло - полная пересборка
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache bot
docker-compose -f docker-compose.prod.yml up -d bot
```

### Проблема: Ошибки базы данных

**Диагностика:**
```bash
# Проверка статуса PostgreSQL
docker-compose -f docker-compose.prod.yml ps postgres
docker-compose -f docker-compose.prod.yml logs postgres --tail=20

# Проверка подключения
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d catalog_db -c "SELECT 1;"
```

**Решение:**
```bash
# Перезапуск базы данных
docker-compose -f docker-compose.prod.yml restart postgres

# Ждем 10 секунд, затем перезапускаем приложение
sleep 10
docker-compose -f docker-compose.prod.yml restart app bot
```

### Проблема: Конфликт экземпляров бота

**Симптомы:** В логах `TelegramConflictError: terminated by other getUpdates`

**Решение:**
```bash
# Убить все процессы Python
pkill -f "main.py"

# Остановить все контейнеры с ботом
docker stop $(docker ps -q --filter "name=bot")

# Запустить только production версию
cd /opt/llm-bot/app
docker-compose -f docker-compose.prod.yml up -d bot
```

### Проблема: Нет места на диске

**Диагностика:**
```bash
df -h
docker system df
```

**Решение:**
```bash
# Очистка Docker кэша
docker system prune -f

# Удаление старых образов
docker image prune -a -f

# Очистка логов
docker-compose -f docker-compose.prod.yml logs --tail=0 > /dev/null
```

---

## 📞 Экстренные контакты

**При критических проблемах:**

1. **Быстрый откат:**
   ```bash
   cd /opt/llm-bot/app
   git log --oneline -5
   git reset --hard ПРЕДЫДУЩИЙ_КОММИТ
   docker-compose -f docker-compose.prod.yml restart bot
   ```

2. **Полная остановка:**
   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```

3. **Проверка ресурсов:**
   ```bash
   htop
   df -h
   free -h
   ```

---

## 💡 Полезные команды

```bash
# Мониторинг логов в реальном времени
docker-compose -f docker-compose.prod.yml logs bot -f

# Вход в контейнер бота для отладки
docker-compose -f docker-compose.prod.yml exec bot bash

# Проверка переменных окружения
docker-compose -f docker-compose.prod.yml exec bot env | grep BOT

# Просмотр текущей версии кода
git log --oneline -3

# Размер логов Docker
docker-compose -f docker-compose.prod.yml logs bot 2>/dev/null | wc -l
```

---

## ⚡ Чек-лист быстрого обновления

### Вариант А: Автоматическое (рекомендуется)

- [ ] `ssh root@ваш-сервер.ru`
- [ ] `cd /opt/llm-bot`
- [ ] `./scripts/update.sh` (или `--force` если нужно)
- [ ] Дождаться завершения скрипта
- [ ] Проверить что показано: `🎉 Обновление завершено успешно!`
- [ ] Тест `/start` в Telegram
- [ ] ✅ Готово!

### Вариант Б: Ручное (для особых случаев)

- [ ] `ssh root@ваш-сервер.ru`
- [ ] `cd /opt/llm-bot/app`
- [ ] `git pull origin main`
- [ ] `docker-compose -f docker-compose.prod.yml exec app python -m alembic upgrade head`
- [ ] `docker-compose -f docker-compose.prod.yml restart app bot`
- [ ] `docker-compose -f docker-compose.prod.yml exec app python -m alembic current` - проверить (head)
- [ ] `docker-compose -f docker-compose.prod.yml logs bot --tail=10`
- [ ] Тест `/start` в Telegram
- [ ] ✅ Готово!

---

## 📝 Полный чек-лист для мажорного обновления

**Перед обновлением:**
- [ ] Создан backup (автоматически через `update.sh` или вручную)
- [ ] Проверен текущий статус: все контейнеры работают
- [ ] Известны текущие версии: `git log --oneline -1` и `alembic current`

**Процесс обновления:**
- [ ] Обновлен код из Git
- [ ] Применены миграции БД (`alembic upgrade head`)
- [ ] Пересобраны Docker образы (если нужно)
- [ ] Обновлен `.env` файл (если добавились новые переменные)
- [ ] Перезапущены контейнеры

**После обновления:**
- [ ] Все контейнеры в статусе `Up`
- [ ] Миграции на версии `(head)`: `alembic current`
- [ ] Health check проходит: `curl localhost:8000/health`
- [ ] Нет ошибок в логах: `docker-compose logs --tail=20`
- [ ] Бот отвечает на `/start` в Telegram
- [ ] Основные функции работают (поиск товаров, создание лидов)

**При проблемах:**
- [ ] Проверить логи: `docker-compose logs app bot`
- [ ] Проверить миграции: `alembic current` и `alembic history`
- [ ] При необходимости откатиться: `git reset --hard PREV_COMMIT`
- [ ] Восстановить из backup если критично

---

*Создано: 2025-09-14*  
*Обновлено: 2025-10-18*  
*Версия: 2.0 - Добавлены миграции БД и управление .env*
