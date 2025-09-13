# Стратегия деплоя ИИ-бота на VPS

**Дата создания:** 13 сентября 2025  
**Цель:** Безопасный деплой с сохранением данных при обновлениях  
**Принцип:** Zero-downtime deployment + Data persistence

---

## 🎯 Основные принципы деплоя

### 1. **Разделение данных и кода**
- **Код бота:** В Docker контейнере (пересоздается)
- **База данных:** В отдельном volume (сохраняется)
- **Логи:** В отдельном volume (сохраняются)
- **Конфигурация:** В .env файле (сохраняется)
- **Chroma данные:** В отдельном volume (сохраняются)

### 2. **Структура папок на VPS**
```
/opt/llm-bot/
├── app/                    # Код приложения (git repo)
├── data/                   # Постоянные данные
│   ├── postgres/          # База данных PostgreSQL
│   ├── chroma/            # Векторная база Chroma
│   ├── uploads/           # Загруженные каталоги
│   └── logs/              # Логи приложения
├── config/                # Конфигурационные файлы
│   ├── .env              # Переменные окружения
│   └── nginx.conf        # Конфигурация nginx (опционально)
└── scripts/               # Скрипты деплоя
    ├── deploy.sh         # Основной скрипт деплоя
    ├── update.sh         # Скрипт обновления
    └── backup.sh         # Скрипт резервного копирования
```

### 3. **Lifecycle компонентов**
- **При обновлении ПЕРЕСОЗДАЮТСЯ:** app контейнер
- **При обновлении СОХРАНЯЮТСЯ:** postgres, данные Chroma, логи, .env

---

## 🗂️ Детальная структура данных

### Volumes mapping:
```yaml
volumes:
  # Постоянные данные (НИКОГДА не удаляются)
  - /opt/llm-bot/data/postgres:/var/lib/postgresql/data     # БД
  - /opt/llm-bot/data/chroma:/app/data/chroma              # Векторная БД
  - /opt/llm-bot/data/uploads:/app/data/uploads            # Каталоги
  - /opt/llm-bot/data/logs:/app/logs                       # Логи приложения
  
  # Конфигурация
  - /opt/llm-bot/config/.env:/app/.env:ro                  # Переменные (read-only)
```

### Что сохраняется между обновлениями:
- ✅ **PostgreSQL данные** - пользователи, лиды, сообщения, настройки
- ✅ **Chroma векторы** - индексированный каталог товаров
- ✅ **Логи** - полная история работы бота
- ✅ **Загруженные файлы** - Excel каталоги в uploads/
- ✅ **Конфигурация** - все переменные окружения в .env

### Что обновляется:
- 🔄 **Код приложения** - новая версия бота
- 🔄 **Docker образ** - обновленные зависимости
- 🔄 **Миграции БД** - автоматически при запуске

---

## 🔧 Production Docker Compose

### Отличия от development версии:
1. **Убираем hot reload** - нет volume для /app/src
2. **Внешние volumes** - данные на хосте, не в Docker volumes
3. **Переменные из файла** - загрузка .env
4. **Restart policies** - автозапуск при перезагрузке сервера
5. **Healthchecks** - проверка здоровья сервисов

```yaml
# docker-compose.prod.yml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - /opt/llm-bot/config/.env
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      # Только данные, БЕЗ кода!
      - /opt/llm-bot/data/chroma:/app/data/chroma
      - /opt/llm-bot/data/uploads:/app/data/uploads
      - /opt/llm-bot/data/logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: catalog_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - /opt/llm-bot/data/postgres:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
```

---

## 🚀 Процесс первичного деплоя

### Шаг 1: Подготовка сервера
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo systemctl enable docker

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Создание структуры папок
sudo mkdir -p /opt/llm-bot/{app,data/{postgres,chroma,uploads,logs},config,scripts}
sudo chown -R $USER:$USER /opt/llm-bot
```

### Шаг 2: Клонирование проекта
```bash
cd /opt/llm-bot/app
git clone YOUR_REPOSITORY_URL .

# Создание production конфигурации
cp docker-compose.yml docker-compose.prod.yml
# Ручная настройка docker-compose.prod.yml по образцу выше
```

### Шаг 3: Настройка переменных окружения
```bash
# Копируем пример и настраиваем
cp /opt/llm-bot/app/env.example /opt/llm-bot/config/.env

# Редактируем конфигурацию
nano /opt/llm-bot/config/.env
```

### Шаг 4: Первый запуск
```bash
cd /opt/llm-bot/app
docker-compose -f docker-compose.prod.yml up -d

# Проверка статуса
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 🔄 Процесс обновления (Zero-downtime)

### Скрипт автоматического обновления:
```bash
#!/bin/bash
# /opt/llm-bot/scripts/update.sh

set -e  # Выход при ошибке

echo "🚀 Начинаем обновление ИИ-бота..."

cd /opt/llm-bot/app

# 1. Создаем backup перед обновлением
echo "📦 Создаем backup..."
./scripts/backup.sh

# 2. Получаем новый код
echo "📥 Получаем обновления из Git..."
git fetch origin
git pull origin main

# 3. Собираем новый образ
echo "🏗️ Собираем новый Docker образ..."
docker-compose -f docker-compose.prod.yml build app

# 4. Останавливаем только app, БД остается работать
echo "⏹️ Останавливаем приложение..."
docker-compose -f docker-compose.prod.yml stop app

# 5. Запускаем новую версию
echo "▶️ Запускаем новую версию..."
docker-compose -f docker-compose.prod.yml up -d app

# 6. Ждем готовности и проверяем health
echo "🔍 Проверяем готовность..."
sleep 10
docker-compose -f docker-compose.prod.yml ps

# 7. Проверяем health endpoint
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Обновление завершено успешно!"
else
    echo "❌ Ошибка! Откатываем изменения..."
    # Здесь можно добавить логику отката
    exit 1
fi

# 8. Очищаем старые образы
echo "🧹 Очищаем старые Docker образы..."
docker image prune -f

echo "🎉 Обновление завершено!"
```

---

## 💾 Система резервного копирования

### Автоматический backup скрипт:
```bash
#!/bin/bash
# /opt/llm-bot/scripts/backup.sh

BACKUP_DIR="/opt/llm-bot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$DATE"

mkdir -p $BACKUP_PATH

echo "📦 Создаем backup $DATE..."

# 1. Backup PostgreSQL
echo "📊 Backup базы данных..."
docker-compose -f /opt/llm-bot/app/docker-compose.prod.yml exec -T postgres \
    pg_dump -U postgres catalog_db > $BACKUP_PATH/database.sql

# 2. Backup Chroma данных
echo "🧠 Backup векторной базы..."
cp -r /opt/llm-bot/data/chroma $BACKUP_PATH/

# 3. Backup конфигурации
echo "⚙️ Backup конфигурации..."
cp /opt/llm-bot/config/.env $BACKUP_PATH/

# 4. Backup логов (последние 7 дней)
echo "📋 Backup логов..."
find /opt/llm-bot/data/logs -name "*.log" -mtime -7 -exec cp {} $BACKUP_PATH/ \;

# 5. Архивируем
echo "🗜️ Создаем архив..."
cd $BACKUP_DIR
tar -czf "${DATE}.tar.gz" $DATE/
rm -rf $DATE/

# 6. Удаляем старые backup'ы (старше 30 дней)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "✅ Backup завершен: ${DATE}.tar.gz"
```

---

## 🔐 Управление конфигурацией

### Пример production .env:
```env
# === PRODUCTION КОНФИГУРАЦИЯ ===

# Основные
DATABASE_URL=postgresql+asyncpg://postgres:STRONG_PASSWORD@postgres:5432/catalog_db
BOT_TOKEN=1234567890:AAEhBOweJhfuelfUHBOULUFGBOFG
POSTGRES_PASSWORD=STRONG_PASSWORD_FOR_DB

# LLM (выберите один)
DEFAULT_LLM_PROVIDER=yandex
YANDEX_API_KEY=your_yandex_api_key
YANDEX_FOLDER_ID=your_folder_id
# Или для OpenAI:
# DEFAULT_LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your_openai_key

# CRM
ZOHO_TOKEN_ENDPOINT=https://accounts.zoho.com/oauth/v2/token

# Уведомления
MANAGER_TELEGRAM_CHAT_ID=-1001234567890
ADMIN_TELEGRAM_IDS=123456789,987654321

# Пути (НЕ ИЗМЕНЯЙТЕ!)
CHROMA_PERSIST_DIR=/app/data/chroma
UPLOAD_DIR=/app/data/uploads

# Production режим
DEBUG=false
LOG_LEVEL=INFO

# Безопасность
WEBHOOK_SECRET=super_secret_webhook_key
ADMIN_SECRET_KEY=super_secret_admin_key

# SMTP (опционально)
SMTP_HOST=smtp.gmail.com
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
MANAGER_EMAILS=manager@company.com

# Embeddings (после оптимизации)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_BATCH_SIZE=100
```

### Безопасное редактирование .env:
```bash
# Редактируем конфигурацию
sudo nano /opt/llm-bot/config/.env

# Применяем изменения без остановки БД
cd /opt/llm-bot/app
docker-compose -f docker-compose.prod.yml up -d app
```

---

## 📊 Мониторинг и логи

### Просмотр логов:
```bash
# Все логи
docker-compose -f docker-compose.prod.yml logs -f

# Логи конкретного сервиса
docker-compose -f docker-compose.prod.yml logs -f app
docker-compose -f docker-compose.prod.yml logs -f postgres

# Логи приложения на диске
tail -f /opt/llm-bot/data/logs/app.log
```

### Проверка состояния:
```bash
# Статус сервисов
docker-compose -f docker-compose.prod.yml ps

# Использование ресурсов
docker stats

# Health check
curl http://localhost:8000/health

# Проверка БД
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d catalog_db -c "SELECT version();"
```

---

## ⚙️ Cron задачи

### Автоматический backup (ежедневно в 3:00):
```bash
# Добавляем в crontab
crontab -e

# Добавляем строку:
0 3 * * * /opt/llm-bot/scripts/backup.sh >> /opt/llm-bot/data/logs/backup.log 2>&1
```

### Мониторинг места на диске:
```bash
# Добавляем в crontab (каждые 6 часов)
0 */6 * * * df -h /opt/llm-bot | grep -E '9[0-9]%|100%' && echo "WARNING: Disk space low" | mail -s "LLM Bot Disk Alert" admin@company.com
```

---

## 🛡️ Безопасность

### 1. Firewall настройки:
```bash
# Разрешаем только необходимые порты
sudo ufw allow ssh
sudo ufw allow 8000    # FastAPI
sudo ufw allow 80     # HTTP (если используете nginx)
sudo ufw allow 443    # HTTPS (если используете nginx)
sudo ufw enable
```

### 2. Регулярные обновления:
```bash
# Автоматические обновления безопасности
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

### 3. Мониторинг логов на атаки:
```bash
# Установка fail2ban
sudo apt install fail2ban

# Конфигурация для защиты SSH
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## 🚨 План действий при сбоях

### 1. Если не запускается app:
```bash
# Проверяем логи
docker-compose -f docker-compose.prod.yml logs app

# Проверяем конфигурацию
docker-compose -f docker-compose.prod.yml config

# Пересобираем образ
docker-compose -f docker-compose.prod.yml build app
docker-compose -f docker-compose.prod.yml up -d app
```

### 2. Если проблемы с БД:
```bash
# Проверяем состояние PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U postgres

# Восстанавливаем из backup
cat /opt/llm-bot/backups/YYYYMMDD_HHMMSS/database.sql | \
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres catalog_db
```

### 3. Полный откат:
```bash
# Откат к предыдущей версии кода
git reset --hard HEAD~1

# Пересборка и запуск
docker-compose -f docker-compose.prod.yml build app
docker-compose -f docker-compose.prod.yml up -d app
```

---

## 📋 Checklist готовности к production

### Перед первым деплоем:
- [ ] VPS создан с нужными характеристиками
- [ ] Docker и Docker Compose установлены
- [ ] Структура папок создана
- [ ] .env файл настроен с production параметрами
- [ ] docker-compose.prod.yml создан
- [ ] Скрипты backup'а и обновления созданы
- [ ] Cron задачи настроены
- [ ] Firewall настроен
- [ ] SSL сертификат получен (если нужен HTTPS)

### После каждого обновления:
- [ ] Backup создан
- [ ] Логи проверены на ошибки
- [ ] Health check проходит
- [ ] Telegram бот отвечает
- [ ] Поиск по каталогу работает
- [ ] Старые Docker образы очищены

---

## 🎯 Следующие шаги

1. **✅ Стратегия создана** ← (текущий шаг)
2. **⏭️ Создание production файлов** (docker-compose.prod.yml, скрипты)
3. **⏭️ Инструкция по первичному деплою**
4. **⏭️ Инструкция по обновлениям**

---

**💬 Важно:** Эта стратегия обеспечивает сохранение всех данных (логи, БД, настройки) при любых обновлениях кода!
