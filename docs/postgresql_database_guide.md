# 📘 Руководство по работе с PostgreSQL на сервере

> **Для кого**: Администраторов и разработчиков, работающих с БД на production сервере  
> **Сложность**: Базовый уровень, все команды готовы для копирования

---

## 📑 Содержание

1. [Подключение к базе данных](#1-подключение-к-базе-данных)
2. [Просмотр структуры БД](#2-просмотр-структуры-бд)
3. [Просмотр данных](#3-просмотр-данных)
4. [Добавление записей (INSERT)](#4-добавление-записей-insert)
5. [Изменение записей (UPDATE)](#5-изменение-записей-update)
6. [Удаление записей (DELETE)](#6-удаление-записей-delete)
7. [Полезные запросы](#7-полезные-запросы)
8. [Безопасность и бэкапы](#8-безопасность-и-бэкапы)

---

## 1. Подключение к базе данных

### 1.1 Подключение к серверу по SSH

Сначала подключитесь к вашему VPS серверу:

```bash
ssh root@your-server-ip
```

После подключения перейдите в директорию проекта:

```bash
cd /opt/llm-bot/app
```

### 1.2 Подключение к PostgreSQL через Docker

PostgreSQL работает в Docker контейнере. Есть два способа подключения:

#### Способ А: Через Docker exec (рекомендуется)

```bash
docker exec -it llm-rag-bot-postgres-1 psql -U postgres -d catalog_db
```

**Что здесь происходит:**
- `docker exec` - выполнить команду в контейнере
- `-it` - интерактивный режим с терминалом
- `llm-rag-bot-postgres-1` - имя контейнера PostgreSQL
- `psql` - клиент PostgreSQL
- `-U postgres` - имя пользователя
- `-d catalog_db` - имя базы данных

#### Способ Б: Узнать имя контейнера, если команда выше не работает

Сначала посмотрите список контейнеров:

```bash
docker ps
```

Найдите контейнер с postgres в названии (например, `llm-rag-bot-postgres-1`), затем:

```bash
docker exec -it CONTAINER_NAME psql -U postgres -d catalog_db
```

### 1.3 Успешное подключение

Если всё прошло успешно, вы увидите приглашение:

```
catalog_db=#
```

**Готово! Вы в PostgreSQL консоли.**

### 1.4 Выход из PostgreSQL

Чтобы выйти из консоли PostgreSQL:

```sql
\q
```

Или нажмите `Ctrl + D`

---

## 2. Просмотр структуры БД

### 2.1 Список всех таблиц

```sql
\dt
```

**Результат:**
```
 Schema |       Name              | Type  |  Owner   
--------+-------------------------+-------+----------
 public | admin_users             | table | postgres
 public | alembic_version         | table | postgres
 public | catalog_versions        | table | postgres
 public | company_info            | table | postgres
 public | company_services        | table | postgres
 public | conversations           | table | postgres
 public | lead_interactions       | table | postgres
 public | leads                   | table | postgres
 public | llm_settings            | table | postgres
 public | messages                | table | postgres
 public | prompts                 | table | postgres
 public | system_logs             | table | postgres
 public | usage_statistics        | table | postgres
 public | users                   | table | postgres
```

### 2.2 Подробная информация о таблице

Чтобы увидеть структуру конкретной таблицы (колонки, типы данных, ограничения):

```sql
\d users
```

**Результат покажет:**
- Названия колонок
- Типы данных
- Ограничения (NOT NULL, PRIMARY KEY и т.д.)
- Индексы

### 2.3 Описание всех таблиц (расширенное)

Для получения подробной информации обо всех таблицах:

```sql
\d+
```

### 2.4 Список колонок конкретной таблицы

Альтернативный способ через SQL запрос:

```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position;
```

---

## 3. Просмотр данных

### 3.1 Просмотр всех записей в таблице

**⚠️ ВНИМАНИЕ:** Если таблица большая, это может занять время!

```sql
SELECT * FROM users;
```

### 3.2 Просмотр первых N записей

Безопаснее ограничить количество записей:

```sql
-- Первые 10 записей
SELECT * FROM users LIMIT 10;
```

### 3.3 Просмотр конкретных колонок

Выбрать только нужные поля:

```sql
SELECT id, chat_id, username, created_at FROM users LIMIT 10;
```

### 3.4 Поиск конкретной записи

По ID:

```sql
SELECT * FROM users WHERE id = 1;
```

По chat_id:

```sql
SELECT * FROM users WHERE chat_id = 123456789;
```

По частичному совпадению (например, в имени):

```sql
SELECT * FROM users WHERE first_name LIKE '%Иван%';
```

### 3.5 Сортировка результатов

По дате создания (новые сначала):

```sql
SELECT * FROM users ORDER BY created_at DESC LIMIT 10;
```

По имени (алфавитный порядок):

```sql
SELECT * FROM users ORDER BY username ASC LIMIT 10;
```

### 3.6 Подсчёт записей

Сколько всего записей в таблице:

```sql
SELECT COUNT(*) FROM users;
```

Сколько пользователей с заполненным email:

```sql
SELECT COUNT(*) FROM users WHERE email IS NOT NULL;
```

### 3.7 Объединение данных из нескольких таблиц

Пример: Пользователи и их лиды

```sql
SELECT 
    u.id, 
    u.username, 
    u.first_name,
    l.name AS lead_name,
    l.phone,
    l.status,
    l.created_at
FROM users u
LEFT JOIN leads l ON u.id = l.user_id
ORDER BY l.created_at DESC
LIMIT 20;
```

---

## 4. Добавление записей (INSERT)

### 4.1 Добавление одной записи

**Базовый синтаксис:**

```sql
INSERT INTO table_name (column1, column2, column3)
VALUES (value1, value2, value3);
```

### 4.2 Примеры добавления

#### Пример 1: Добавить пользователя

```sql
INSERT INTO users (chat_id, telegram_user_id, username, first_name, last_name, phone, email)
VALUES (987654321, 987654321, 'ivan_petrov', 'Иван', 'Петров', '+79001234567', 'ivan@example.com');
```

#### Пример 2: Добавить лид

```sql
INSERT INTO leads (user_id, name, phone, email, question, status, auto_created, lead_source)
VALUES (1, 'Иван Петров', '+79001234567', 'ivan@example.com', 'Интересует каталог товаров', 'pending_sync', false, 'telegram');
```

#### Пример 3: Добавить услугу компании

```sql
INSERT INTO company_services (title, description, category, active)
VALUES ('Консультация по выбору', 'Помощь в подборе товаров из каталога', 'Консультации', true);
```

#### Пример 4: Добавить промпт

```sql
INSERT INTO prompts (name, content, version, active, role)
VALUES ('greeting', 'Здравствуйте! Я помогу вам найти нужные товары.', 1, true, 'system');
```

### 4.3 Добавление с возвратом ID

Если нужно узнать ID новой записи:

```sql
INSERT INTO users (chat_id, username, first_name)
VALUES (111222333, 'test_user', 'Тест')
RETURNING id;
```

### 4.4 Добавление нескольких записей сразу

```sql
INSERT INTO company_services (title, description, category, active)
VALUES 
    ('Доставка', 'Быстрая доставка по городу', 'Логистика', true),
    ('Установка', 'Профессиональная установка оборудования', 'Сервис', true),
    ('Гарантия', 'Расширенная гарантия на 3 года', 'Сервис', true);
```

---

## 5. Изменение записей (UPDATE)

### 5.1 Изменение одной записи

**⚠️ ВАЖНО:** Всегда используйте WHERE! Иначе изменятся ВСЕ записи!

**Базовый синтаксис:**

```sql
UPDATE table_name
SET column1 = value1, column2 = value2
WHERE condition;
```

### 5.2 Примеры изменения

#### Пример 1: Обновить телефон пользователя

```sql
UPDATE users
SET phone = '+79009998877'
WHERE id = 1;
```

#### Пример 2: Изменить статус лида

```sql
UPDATE leads
SET status = 'synced', sync_attempts = 1
WHERE id = 5;
```

#### Пример 3: Обновить несколько полей

```sql
UPDATE users
SET 
    first_name = 'Иван',
    last_name = 'Иванов',
    phone = '+79001112233',
    email = 'newemail@example.com'
WHERE chat_id = 123456789;
```

#### Пример 4: Изменить по условию

Активировать все услуги определённой категории:

```sql
UPDATE company_services
SET active = true
WHERE category = 'Консультации';
```

#### Пример 5: Деактивировать старый промпт и активировать новый

```sql
-- Сначала деактивируем старый
UPDATE prompts
SET active = false
WHERE name = 'greeting' AND version = 1;

-- Затем активируем новый
UPDATE prompts
SET active = true
WHERE name = 'greeting' AND version = 2;
```

### 5.3 Обновление с проверкой результата

```sql
UPDATE users
SET phone = '+79991234567'
WHERE id = 10
RETURNING id, username, phone;
```

### 5.4 Массовое обновление (с осторожностью!)

Добавить email всем пользователям без email (пример):

```sql
UPDATE users
SET email = username || '@example.com'
WHERE email IS NULL;
```

---

## 6. Удаление записей (DELETE)

### 6.1 Удаление записи

**⚠️ КРИТИЧЕСКИ ВАЖНО:** Всегда используйте WHERE! Иначе удалятся ВСЕ записи!

**Базовый синтаксис:**

```sql
DELETE FROM table_name
WHERE condition;
```

### 6.2 Примеры удаления

#### Пример 1: Удалить конкретного пользователя

```sql
DELETE FROM users
WHERE id = 999;
```

#### Пример 2: Удалить лид по chat_id

```sql
DELETE FROM leads
WHERE user_id = (SELECT id FROM users WHERE chat_id = 123456789);
```

#### Пример 3: Удалить неактивные услуги

```sql
DELETE FROM company_services
WHERE active = false;
```

#### Пример 4: Удалить старые логи

Удалить логи старше 30 дней:

```sql
DELETE FROM system_logs
WHERE created_at < NOW() - INTERVAL '30 days';
```

#### Пример 5: Удалить тестовые данные

```sql
DELETE FROM users
WHERE username LIKE 'test_%';
```

### 6.3 Удаление с возвратом удалённых данных

```sql
DELETE FROM leads
WHERE status = 'failed' AND sync_attempts >= 2
RETURNING id, name, phone, created_at;
```

### 6.4 Удаление всех записей из таблицы

**⚠️ ОПАСНО! Удалит ВСЕ данные:**

```sql
DELETE FROM table_name;
```

**Более безопасный вариант с подтверждением:**

```sql
TRUNCATE TABLE table_name;
```

---

## 7. Полезные запросы

### 7.1 Статистика по таблицам

Размер каждой таблицы:

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 7.2 Последние добавленные пользователи

```sql
SELECT id, chat_id, username, first_name, last_name, created_at
FROM users
ORDER BY created_at DESC
LIMIT 10;
```

### 7.3 Все лиды с ошибками синхронизации

```sql
SELECT 
    l.id,
    l.name,
    l.phone,
    l.email,
    l.status,
    l.sync_attempts,
    l.last_sync_attempt,
    u.username
FROM leads l
LEFT JOIN users u ON l.user_id = u.id
WHERE l.status = 'failed' OR l.sync_attempts > 1
ORDER BY l.last_sync_attempt DESC;
```

### 7.4 Активные настройки LLM

```sql
SELECT provider, is_active, config
FROM llm_settings
WHERE is_active = true;
```

### 7.5 Все активные промпты

```sql
SELECT name, version, role, updated_at
FROM prompts
WHERE active = true
ORDER BY name, version DESC;
```

### 7.6 Статистика по лидам

```sql
SELECT 
    status,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
FROM leads
GROUP BY status
ORDER BY count DESC;
```

### 7.7 Последние сообщения в диалогах

```sql
SELECT 
    m.id,
    c.chat_id,
    m.role,
    LEFT(m.content, 100) as content_preview,
    m.created_at
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
ORDER BY m.created_at DESC
LIMIT 20;
```

### 7.8 Проверка версий каталога

```sql
SELECT 
    id,
    version_name,
    status,
    total_rows,
    indexed_rows,
    created_at,
    completed_at
FROM catalog_versions
ORDER BY created_at DESC
LIMIT 5;
```

### 7.9 Использование AI (токены и расходы)

```sql
SELECT 
    provider,
    model,
    year,
    month,
    total_tokens,
    price_per_1k_tokens,
    currency,
    (total_tokens::float / 1000 * price_per_1k_tokens) as total_cost
FROM usage_statistics
ORDER BY year DESC, month DESC;
```

### 7.10 Системные ошибки за последние 24 часа

```sql
SELECT level, message, created_at
FROM system_logs
WHERE level IN ('ERROR', 'CRITICAL')
  AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

---

## 8. Безопасность и бэкапы

### 8.1 Создание резервной копии БД

**На сервере (через Docker):**

```bash
docker exec llm-rag-bot-postgres-1 pg_dump -U postgres catalog_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Сохранить в папку бэкапов:**

```bash
docker exec llm-rag-bot-postgres-1 pg_dump -U postgres catalog_db > /opt/llm-bot/backups/db_backup_$(date +%Y%m%d_%H%M%S).sql
```

### 8.2 Восстановление из резервной копии

**⚠️ ОПАСНО! Это удалит все текущие данные!**

```bash
# Сначала удалить существующую БД
docker exec llm-rag-bot-postgres-1 psql -U postgres -c "DROP DATABASE catalog_db;"

# Создать новую
docker exec llm-rag-bot-postgres-1 psql -U postgres -c "CREATE DATABASE catalog_db;"

# Восстановить из бэкапа
cat backup_20250119_120000.sql | docker exec -i llm-rag-bot-postgres-1 psql -U postgres -d catalog_db
```

### 8.3 Экспорт таблицы в CSV

```sql
\copy (SELECT * FROM users) TO '/tmp/users_export.csv' WITH CSV HEADER;
```

**Или через Docker:**

```bash
docker exec llm-rag-bot-postgres-1 psql -U postgres -d catalog_db -c "\COPY users TO '/tmp/users.csv' WITH CSV HEADER"
```

### 8.4 Проверка целостности данных

Проверить, что нет лидов без пользователей:

```sql
SELECT COUNT(*) 
FROM leads l
LEFT JOIN users u ON l.user_id = u.id
WHERE u.id IS NULL;
```

### 8.5 Проверка связей между таблицами

```sql
-- Пользователи с количеством лидов
SELECT 
    u.id,
    u.username,
    u.first_name,
    COUNT(l.id) as leads_count
FROM users u
LEFT JOIN leads l ON u.id = l.user_id
GROUP BY u.id, u.username, u.first_name
ORDER BY leads_count DESC;
```

---

## 9. Транзакции (безопасные изменения)

### 9.1 Что такое транзакция?

Транзакция - это группа команд, которые либо выполняются все вместе, либо не выполняются вообще. Это защита от ошибок.

### 9.2 Использование транзакций

```sql
-- Начать транзакцию
BEGIN;

-- Выполнить изменения
UPDATE users SET email = 'new@example.com' WHERE id = 1;
UPDATE leads SET phone = '+79001234567' WHERE user_id = 1;

-- Проверить результат
SELECT * FROM users WHERE id = 1;

-- Если всё правильно - сохранить
COMMIT;

-- Если что-то не так - отменить
-- ROLLBACK;
```

### 9.3 Безопасное удаление

```sql
BEGIN;

-- Показать что будет удалено
SELECT * FROM leads WHERE status = 'failed' AND sync_attempts > 2;

-- Если всё правильно, раскомментировать:
-- DELETE FROM leads WHERE status = 'failed' AND sync_attempts > 2;

-- Проверить
-- SELECT COUNT(*) FROM leads WHERE status = 'failed';

-- Если всё ок - сохранить
COMMIT;

-- Если передумали - отменить
-- ROLLBACK;
```

---

## 10. Быстрая справка по командам

### PostgreSQL консольные команды (начинаются с \)

| Команда | Описание |
|---------|----------|
| `\l` | Список всех баз данных |
| `\dt` | Список всех таблиц |
| `\d table_name` | Структура таблицы |
| `\du` | Список пользователей |
| `\q` | Выход из PostgreSQL |
| `\h` | Справка по SQL командам |
| `\?` | Справка по консольным командам |
| `\timing on` | Включить отображение времени выполнения |

### SQL команды (заканчиваются на ;)

| Команда | Описание |
|---------|----------|
| `SELECT * FROM table` | Выбрать все записи |
| `INSERT INTO table VALUES (...)` | Добавить запись |
| `UPDATE table SET ... WHERE ...` | Обновить запись |
| `DELETE FROM table WHERE ...` | Удалить запись |
| `COUNT(*)` | Подсчитать записи |
| `LIMIT N` | Ограничить количество результатов |
| `ORDER BY column` | Сортировка |
| `WHERE condition` | Фильтрация |

---

## 11. Таблицы проекта (справка)

### Основные таблицы

| Таблица | Назначение |
|---------|------------|
| `users` | Пользователи Telegram бота |
| `leads` | Лиды (потенциальные клиенты) |
| `lead_interactions` | Взаимодействия с лидами |
| `conversations` | Диалоги пользователей |
| `messages` | Сообщения в диалогах |
| `company_services` | Услуги компании |
| `company_info` | Информация о компании |
| `prompts` | Промпты для LLM |
| `llm_settings` | Настройки LLM провайдеров |
| `usage_statistics` | Статистика использования AI |
| `catalog_versions` | Версии каталога товаров |
| `admin_users` | Администраторы системы |
| `system_logs` | Системные логи |

### Ключевые поля

**users:**
- `chat_id` - основной идентификатор (НЕ telegram_user_id!)
- `telegram_user_id` - ID пользователя в Telegram
- `username`, `first_name`, `last_name` - данные из Telegram
- `phone`, `email` - контактные данные

**leads:**
- `user_id` - связь с таблицей users
- `name`, `phone`, `email` - контактная информация
- `status` - статус: pending_sync, synced, failed
- `sync_attempts` - количество попыток синхронизации с CRM
- `zoho_lead_id` - ID лида в Zoho CRM

**messages:**
- `conversation_id` - связь с диалогом
- `role` - роль: user, assistant, system
- `content` - текст сообщения

---

## 12. Примеры реальных задач

### Задача 1: Найти пользователя и его лиды

```sql
-- Найти пользователя по username
SELECT * FROM users WHERE username = 'ivan_petrov';

-- Найти его лиды (подставить ID из предыдущего запроса)
SELECT * FROM leads WHERE user_id = 123;
```

### Задача 2: Исправить статус лида

```sql
-- Найти лид
SELECT id, name, status, sync_attempts FROM leads WHERE phone = '+79001234567';

-- Исправить статус
UPDATE leads 
SET status = 'pending_sync', sync_attempts = 0
WHERE id = 456;
```

### Задача 3: Добавить новую услугу

```sql
INSERT INTO company_services (title, description, category, active)
VALUES ('Новая услуга', 'Описание услуги', 'Категория', true)
RETURNING id;
```

### Задача 4: Посмотреть последние диалоги

```sql
SELECT 
    c.id as conversation_id,
    c.chat_id,
    u.username,
    c.started_at,
    COUNT(m.id) as messages_count
FROM conversations c
LEFT JOIN users u ON c.user_id = u.id
LEFT JOIN messages m ON c.id = m.conversation_id
GROUP BY c.id, c.chat_id, u.username, c.started_at
ORDER BY c.started_at DESC
LIMIT 10;
```

### Задача 5: Очистить тестовые данные

```sql
BEGIN;

-- Показать что будет удалено
SELECT * FROM users WHERE username LIKE 'test_%';

-- Удалить (раскомментировать после проверки)
-- DELETE FROM users WHERE username LIKE 'test_%';

COMMIT;
```

---

## ⚠️ Важные предупреждения

1. **Всегда делайте бэкап** перед массовыми изменениями!
2. **Используйте транзакции** (BEGIN/COMMIT) для важных операций
3. **Проверяйте WHERE** условия перед UPDATE и DELETE
4. **Тестируйте на малых данных** перед массовыми операциями
5. **Не удаляйте данные** без крайней необходимости
6. **Храните бэкапы** в безопасном месте вне сервера

---

## 🆘 Что делать если что-то пошло не так

### Если случайно изменили/удалили данные

1. **НЕ ПАНИКУЙТЕ!**
2. Немедленно выйдите из PostgreSQL (`\q`)
3. Восстановите из последнего бэкапа
4. Если бэкапа нет - обратитесь к администратору

### Если команда "зависла"

1. Нажмите `Ctrl + C` для отмены
2. Проверьте синтаксис команды
3. Попробуйте упростить запрос

### Если забыли пароль от PostgreSQL

Пароль находится в файле:

```bash
cat /opt/llm-bot/config/.env | grep POSTGRES_PASSWORD
```

---

## 📚 Дополнительные ресурсы

- **Официальная документация PostgreSQL**: https://www.postgresql.org/docs/
- **SQL Tutorial**: https://www.w3schools.com/sql/
- **Описание таблиц проекта**: `doc/vision.md` раздел 5
- **Модели SQLAlchemy**: `src/infrastructure/database/models.py`

---

**Автор**: AI LLM-RAG Bot Team  
**Дата создания**: 19.01.2025  
**Версия**: 1.0

