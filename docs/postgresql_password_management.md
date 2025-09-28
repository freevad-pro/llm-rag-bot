# Управление паролем PostgreSQL в ИИ-боте

**Дата создания:** 13 сентября 2025  
**Цель:** Понимание и настройка паролей PostgreSQL для development и production  
**Архитектура:** Production использует 3 контейнера (app, bot, postgres)

---

## 🔍 Текущее состояние паролей

### Development окружение:
- **Пароль:** `password` (слабый, только для разработки)
- **Где задан:** В `docker-compose.yml` и `env.example`
- **Безопасность:** ❌ НЕ подходит для production

### Production окружение:
- **Пароль:** Задается в `/opt/llm-bot/config/.env`
- **Где используется:** В `docker-compose.prod.yml` через переменную `${POSTGRES_PASSWORD}`
- **Безопасность:** ✅ Настраивается пользователем

---

## 📋 Где хранятся пароли

### 1. **Development (docker-compose.yml):**
```yaml
# Строка 25 в docker-compose.yml
POSTGRES_PASSWORD: password

# Строка 9 в docker-compose.yml  
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/catalog_db
```

### 2. **Development пример (env.example):**
```env
# Строка 2 в env.example
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/catalog_db
```

### 3. **Production (docker-compose.prod.yml):**
```yaml
# Строка 44 в docker-compose.prod.yml
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # Берется из .env файла
```

### 4. **Production конфигурация (env.production):**
```env
# В env.production (заполняется пользователем)
POSTGRES_PASSWORD=ЗАМЕНИТЕ_НА_СИЛЬНЫЙ_ПАРОЛЬ
DATABASE_URL=postgresql+asyncpg://postgres:ЗАМЕНИТЕ_НА_СИЛЬНЫЙ_ПАРОЛЬ@postgres:5432/catalog_db
```

---

## 🔧 Как установить пароль в production

### Шаг 1: Генерация сильного пароля
```bash
# Генерируем случайный пароль (32 символа)
openssl rand -base64 32

# Или через команду (если openssl недоступен)
head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32 ; echo ''

# Пример сгенерированного пароля:
# K8mN2pQwE4rT6yU9iO1aS3dF5gH7jK0l
```

### Шаг 2: Установка пароля в .env файле
```bash
# Редактируем конфигурацию на сервере
nano /opt/llm-bot/config/.env

# Заменяем эти строки:
POSTGRES_PASSWORD=K8mN2pQwE4rT6yU9iO1aS3dF5gH7jK0l
DATABASE_URL=postgresql+asyncpg://postgres:K8mN2pQwE4rT6yU9iO1aS3dF5gH7jK0l@postgres:5432/catalog_db
```

### Шаг 3: Применение изменений
```bash
cd /opt/llm-bot/app

# Пересоздаем контейнеры с новым паролем
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🔄 Как сменить пароль в работающей системе

### ⚠️ ВАЖНО: Backup перед сменой пароля!
```bash
# Создаем backup перед изменением пароля
/opt/llm-bot/scripts/backup.sh
```

### Метод 1: Полная пересборка (рекомендуется)

#### Шаг 1: Остановка сервисов
```bash
cd /opt/llm-bot/app
# Останавливаем все сервисы (app, bot, postgres)
docker-compose -f docker-compose.prod.yml down
```

#### Шаг 2: Изменение пароля в .env
```bash
# Редактируем файл
nano /opt/llm-bot/config/.env

# Меняем пароль в двух местах:
POSTGRES_PASSWORD=ВАШ_НОВЫЙ_СИЛЬНЫЙ_ПАРОЛЬ
DATABASE_URL=postgresql+asyncpg://postgres:ВАШ_НОВЫЙ_СИЛЬНЫЙ_ПАРОЛЬ@postgres:5432/catalog_db
```

#### Шаг 3: Пересоздание контейнеров
```bash
# Удаляем старые контейнеры и volumes (ДАННЫЕ СОХРАНЯТСЯ)
docker-compose -f docker-compose.prod.yml down -v

# Запускаем все сервисы с новым паролем (app, bot, postgres)
docker-compose -f docker-compose.prod.yml up -d
```

### Метод 2: Изменение пароля в работающей БД

#### Шаг 1: Подключение к PostgreSQL
```bash
# Подключаемся к контейнеру PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d catalog_db
```

#### Шаг 2: Смена пароля в БД
```sql
-- В консоли PostgreSQL выполняем:
ALTER USER postgres PASSWORD 'ВАШ_НОВЫЙ_СИЛЬНЫЙ_ПАРОЛЬ';

-- Выходим
\q
```

#### Шаг 3: Обновление .env файла
```bash
# Редактируем .env с новым паролем
nano /opt/llm-bot/config/.env

# ⚠️ ВАЖНО: Перезапускаем ОБА контейнера (app И bot)
# Оба используют БД и кешируют переменные окружения при старте
docker-compose -f docker-compose.prod.yml restart app bot
```

---

## 🧪 Проверка подключения с новым паролем

### Тест подключения из приложения:
```bash
# Смотрим логи FastAPI сервера на ошибки подключения
docker-compose -f docker-compose.prod.yml logs app | grep -i "database\|postgres\|connection"

# Смотрим логи Telegram бота на ошибки подключения
docker-compose -f docker-compose.prod.yml logs bot | grep -i "database\|postgres\|connection"

# Если есть ошибки - проверяем пароль в .env
```

### Прямой тест подключения:
```bash
# Тестируем подключение напрямую
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d catalog_db -c "SELECT version();"

# Должно показать версию PostgreSQL
```

### Тест через приложение:
```bash
# Проверяем health endpoint
curl http://localhost:8000/health

# Должен вернуть {"status": "healthy"}
```

---

## 🔐 Требования к паролю PostgreSQL

### ✅ Сильный пароль должен содержать:
- **Минимум 16 символов** (рекомендуется 32)
- **Буквы разного регистра** (A-Z, a-z)
- **Цифры** (0-9)
- **Специальные символы** (но осторожно с URL encoding)

### ❌ Избегайте в пароле:
- **Специальные символы URL** (@, /, :, %, ? и т.д.)
- **Пробелы** и **табуляции**
- **Кавычки** (", ')
- **Символы bash** ($, `, \, |)

### 💡 Примеры хороших паролей:
```
K8mN2pQwE4rT6yU9iO1aS3dF5gH7jK0l
Xm4Bn7Rt9Ql2Vw8Zx5Cy3Pf6Ht1Nk4Js
P9rG2nM5qX8wE1tY4uI7oA6sD3fH0kL
```

---

## 🚨 Восстановление при забытом пароле

### Если забыли пароль и система не работает:

#### Вариант 1: Восстановление из backup
```bash
# Восстанавливаем данные из последнего backup
cd /opt/llm-bot
tar -xzf backups/latest.tar.gz

# Возвращаем старую конфигурацию
cp llm-bot-backup-*/. env config/.env

# Перезапускаем
cd app
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

#### Вариант 2: Сброс через временный контейнер
```bash
# Останавливаем сервисы
docker-compose -f docker-compose.prod.yml down

# Запускаем PostgreSQL с отключенной аутентификацией
docker run --rm -v /opt/llm-bot/data/postgres:/var/lib/postgresql/data \
  -e POSTGRES_HOST_AUTH_METHOD=trust \
  -p 5432:5432 \
  postgres:15

# В другом терминале подключаемся и меняем пароль
docker exec -it <container_id> psql -U postgres -c "ALTER USER postgres PASSWORD 'новый_пароль';"

# Останавливаем временный контейнер и запускаем обычные сервисы
```

---

## 📊 Безопасность паролей по окружениям

| Окружение | Текущий пароль | Безопасность | Рекомендация |
|-----------|----------------|--------------|--------------|
| **Development** | `password` | ❌ Слабый | Оставить как есть (только для разработки) |
| **Production** | Настраивается | ✅ Сильный | Обязательно сменить на сложный |
| **Staging** | Настраивается | ✅ Сильный | Использовать отдельный пароль |

---

## 📝 Checklist смены пароля

### Перед сменой:
- [ ] Создан backup системы
- [ ] Сгенерирован сильный пароль
- [ ] Проверена доступность системы
- [ ] Есть план отката

### Во время смены:
- [ ] Остановлены все сервисы (app, bot, postgres)
- [ ] Изменен пароль в .env файле (2 места)
- [ ] Перезапущены все контейнеры (app, bot, postgres)
- [ ] Проверено подключение из app и bot

### После смены:
- [ ] Health check проходит
- [ ] Приложение работает
- [ ] Telegram бот отвечает
- [ ] Новый пароль сохранен в безопасном месте

---

## 💡 Автоматизация

### Скрипт проверки пароля:
```bash
#!/bin/bash
# /opt/llm-bot/scripts/check_db_password.sh

echo "🔍 Проверяем подключение к PostgreSQL..."

# Проверяем прямое подключение к БД
if docker-compose -f /opt/llm-bot/app/docker-compose.prod.yml exec postgres psql -U postgres -d catalog_db -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ Прямое подключение к PostgreSQL работает"
else
    echo "❌ Ошибка прямого подключения к PostgreSQL"
    echo "Проверьте пароль в /opt/llm-bot/config/.env"
    exit 1
fi

# Проверяем что app и bot контейнеры запущены
echo "🔍 Проверяем статус контейнеров..."
if docker-compose -f /opt/llm-bot/app/docker-compose.prod.yml ps app bot | grep -q "Up"; then
    echo "✅ Контейнеры app и bot запущены"
else
    echo "⚠️ Один или оба контейнера (app/bot) не запущены"
    echo "Запустите: docker-compose -f docker-compose.prod.yml up -d app bot"
fi
```

### Скрипт генерации пароля:
```bash
#!/bin/bash
# /opt/llm-bot/scripts/generate_password.sh

echo "🔐 Генерируем новый пароль PostgreSQL:"
NEW_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
echo "Новый пароль: $NEW_PASSWORD"
echo ""
echo "Добавьте в /opt/llm-bot/config/.env:"
echo "POSTGRES_PASSWORD=$NEW_PASSWORD"
echo "DATABASE_URL=postgresql+asyncpg://postgres:$NEW_PASSWORD@postgres:5432/catalog_db"
```

---

**🔐 Помните: Сильный пароль PostgreSQL - основа безопасности всех данных вашего бота!**
