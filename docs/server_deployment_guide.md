# Полная инструкция по деплою ИИ-бота на VPS

**Дата создания:** 13 сентября 2025  
**Для проекта:** AI Агент консультирования клиентов  
**Уровень:** Детальный (копируй-вставляй команды)

---

## 🎯 Что будем делать

1. **Подготовка сервера** - установка Docker, создание структуры папок
2. **Первичный деплой** - загрузка кода, настройка конфигурации
3. **Запуск бота** - старт всех сервисов
4. **Тестирование** - проверка работоспособности
5. **Настройка автоматизации** - backup'ы и обновления

---

## 📋 Предварительные требования

### ✅ Что должно быть готово:
- VPS создан и доступен по SSH
- Домен настроен (опционально)
- У вас есть:
  - Telegram Bot Token (от @BotFather)
  - YandexGPT API ключ ИЛИ OpenAI API ключ
  - Zoho CRM данные (опционально)

### 🔧 Технические требования:
- Ubuntu 22.04 LTS
- 4 vCPU, 8GB RAM, 60GB SSD (минимум: 2 vCPU, 4GB RAM)
- Открытые порты: 22 (SSH), 8000 (FastAPI)

---

## 🚀 Шаг 1: Подготовка сервера

### 1.1 Подключение к серверу
```bash
# Замените YOUR_SERVER_IP на реальный IP
ssh root@YOUR_SERVER_IP
```

### 1.2 Обновление системы
```bash
# Обновляем пакеты
apt update && apt upgrade -y

# Устанавливаем необходимые утилиты
apt install -y curl git htop nano ufw fail2ban
```

### 1.3 Создание пользователя для бота
```bash
# Создаем пользователя
useradd -m -s /bin/bash llmbot
usermod -aG sudo llmbot

# Переключаемся на нового пользователя
su - llmbot
```

### 1.3.1 Проверка и очистка окружения
```bash
# ⚠️ ВАЖНО: Проверяем нет ли конфликтных переменных окружения
echo "=== Проверка переменных окружения ==="
env | grep -E "(DEBUG|NODE_ENV|ENVIRONMENT)" || echo "✅ Конфликтных переменных нет"

# Если найдены конфликтные переменные - очищаем их
unset DEBUG NODE_ENV ENVIRONMENT

# Проверяем повторно
env | grep -E "(DEBUG|NODE_ENV|ENVIRONMENT)" || echo "✅ Окружение очищено"
```

> **🛡️ Принцип безопасности:** Системные переменные окружения могут перебивать настройки приложения. Поэтому перед деплоем всегда очищаем потенциально конфликтные переменные.

### 1.4 Установка Docker
```bash
# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER

# Перелогиниваемся для применения изменений
exit
su - llmbot

# Проверяем установку
docker --version
```

### 1.5 Установка Docker Compose
```bash
# Устанавливаем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверяем установку
docker-compose --version
```

### 1.6 Создание структуры папок
```bash
# Создаем основные директории
sudo mkdir -p /opt/llm-bot/{app,data/{postgres,chroma,uploads,logs},config,scripts,backups}

# Устанавливаем права доступа
sudo chown -R llmbot:llmbot /opt/llm-bot
chmod 755 /opt/llm-bot

# Переходим в рабочую директорию
cd /opt/llm-bot
```

---

## 📥 Шаг 2: Загрузка кода

### 2.1 Клонирование репозитория
```bash
# Клонируем репозиторий в текущую папку
cd /opt/llm-bot/app
git clone https://github.com/freevad-pro/llm-rag-bot.git .

# Проверяем, что файлы загружены
ls -la
```

### 2.2 Копирование production файлов
```bash
# Копируем шаблон конфигурации
cp env.production ../config/.env

# ⚠️ ВАЖНО: НЕ копируем docker-compose.yml поверх docker-compose.prod.yml!
# Файл docker-compose.prod.yml уже настроен для production с 3 контейнерами:
# - app (FastAPI сервер)
# - bot (Telegram бот) 
# - postgres (база данных)
```

---

## ⚙️ Шаг 3: Настройка конфигурации

### 3.1 Редактирование .env файла
```bash
# Редактируем конфигурацию
nano /opt/llm-bot/config/.env
```

### 3.2 Обязательные параметры для замены:

**Основные настройки:**
```env
# Замените на ваши реальные значения
BOT_TOKEN=1234567890:ВАША_СТРОКА_ОТ_BOTFATHER
POSTGRES_PASSWORD=ВАШ_СИЛЬНЫЙ_ПАРОЛЬ_ДЛЯ_БД
DATABASE_URL=postgresql+asyncpg://postgres:ВАШ_СИЛЬНЫЙ_ПАРОЛЬ_ДЛЯ_БД@postgres:5432/catalog_db
```

**Выбор LLM провайдера (один из вариантов):**

*Вариант A: OpenAI (по умолчанию, лучшее качество)*
```env
DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-ВАШ_OPENAI_KEY
```

*Вариант B: YandexGPT (для российских серверов)*
```env
DEFAULT_LLM_PROVIDER=yandex
YANDEX_API_KEY=ВАШ_YANDEX_API_KEY
YANDEX_FOLDER_ID=ВАШ_FOLDER_ID
```

**Уведомления:**
```env
# ID чата для уведомлений (создайте группу, добавьте бота, получите ID через @userinfobot)
MANAGER_TELEGRAM_CHAT_ID=-1001234567890

# Ваши Telegram ID через запятую (получите через @userinfobot)
ADMIN_TELEGRAM_IDS=123456789,987654321
```

**Безопасность:**
```env
# Сгенерируйте случайные строки
WEBHOOK_SECRET=your_random_32_char_string_here
ADMIN_SECRET_KEY=your_random_64_char_string_here
```

### 3.3 Проверка конфигурации
```bash
# Проверяем синтаксис Docker Compose
cd /opt/llm-bot/app
docker-compose -f docker-compose.prod.yml config
```

---

## 🚀 Шаг 4: Первичный запуск

### 4.1 Сборка образов
```bash
cd /opt/llm-bot/app

# Собираем Docker образы
docker-compose -f docker-compose.prod.yml build
```

### 4.2 Запуск PostgreSQL
```bash
# Запускаем только базу данных
docker-compose -f docker-compose.prod.yml up -d postgres

# Ждем готовности (может занять 30-60 секунд)
docker-compose -f docker-compose.prod.yml logs -f postgres
# Дождитесь сообщения "database system is ready to accept connections"
# Нажмите Ctrl+C для выхода из логов
```

### 4.3 Финальная проверка окружения
```bash
# ⚠️ КРИТИЧНО: Последняя проверка перед запуском
echo "=== Финальная проверка окружения ==="
env | grep -E "(DEBUG|NODE_ENV|ENVIRONMENT)" || echo "✅ Нет конфликтных переменных"

# Очищаем если есть
unset DEBUG NODE_ENV ENVIRONMENT
```

### 4.4 Запуск основного приложения
```bash
# Запускаем FastAPI сервер (API + админка)
docker-compose -f docker-compose.prod.yml up -d app

# Ждем готовности FastAPI (30-60 секунд)
docker-compose -f docker-compose.prod.yml logs -f app
# Дождитесь сообщения о готовности, затем Ctrl+C

# Запускаем Telegram бота (отдельный контейнер)
docker-compose -f docker-compose.prod.yml up -d bot

# Проверяем статус всех сервисов
docker-compose -f docker-compose.prod.yml ps

# Смотрим логи бота
docker-compose -f docker-compose.prod.yml logs -f bot
# Дождитесь сообщения "Bot started successfully", затем Ctrl+C
```

---

## 🧪 Шаг 5: Тестирование

### 5.1 Проверка health endpoint
```bash
# Проверяем health check
curl http://localhost:8000/health

# Должен вернуть что-то вроде: {"status": "healthy"}
```

### 5.2 Проверка веб-интерфейса
```bash
# Если health check прошел, откройте в браузере:
# http://YOUR_SERVER_IP:8000
```

### 5.3 Тестирование Telegram бота
1. Найдите вашего бота в Telegram
2. Отправьте команду `/start`
3. Бот должен ответить приветственным сообщением

### 5.4 Проверка логов
```bash
# Смотрим логи всех сервисов
docker-compose -f docker-compose.prod.yml logs

# Логи только приложения
docker-compose -f docker-compose.prod.yml logs app

# Логи в реальном времени
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 🔧 Шаг 6: Настройка автоматизации

### 6.1 Копирование скриптов управления
```bash
# Копируем скрипты
cp /opt/llm-bot/app/scripts/*.sh /opt/llm-bot/scripts/
chmod +x /opt/llm-bot/scripts/*.sh
```

### 6.2 Настройка автоматических backup'ов

> **О backup'ах:** У Timeweb есть снапшоты всего сервера, но наши backup'ы содержат только данные приложения и **переносимы между любыми хостингами**. Также создаются автоматически перед каждым обновлением.

```bash
# Редактируем crontab
crontab -e

# Добавляем строку (backup каждое воскресенье в 3:00 утра):
0 3 * * 0 /opt/llm-bot/scripts/backup.sh >> /opt/llm-bot/data/logs/backup.log 2>&1
```

### 6.3 Первый тестовый backup
```bash
# Создаем первый backup
/opt/llm-bot/scripts/backup.sh

# Проверяем, что backup создался
ls -la /opt/llm-bot/backups/
```

---

## 🛡️ Шаг 7: Настройка безопасности

### 7.1 Настройка firewall
```bash
# Включаем UFW
sudo ufw enable

# Разрешаем SSH
sudo ufw allow ssh

# Разрешаем порт приложения
sudo ufw allow 8000

# Проверяем статус
sudo ufw status
```

### 7.2 Настройка fail2ban
```bash
# Проверяем, что fail2ban запущен
sudo systemctl status fail2ban

# Если не запущен
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 7.3 Автоматические обновления безопасности (рекомендуется)
```bash
# Устанавливаем unattended-upgrades для автоматических патчей безопасности
sudo apt install unattended-upgrades

# Настраиваем (выберите "Yes" для автоматических обновлений безопасности)
sudo dpkg-reconfigure unattended-upgrades

# Проверяем конфигурацию
sudo systemctl status unattended-upgrades
```

> **Что это:** Автоматические обновления системных пакетов безопасности Ubuntu (например, исправления уязвимостей в SSH, ядре и т.д.). **НЕ затрагивает** наше приложение - только системные компоненты.

> **Зачем:** Защита от известных уязвимостей без ручного вмешательства. Обновления применяются только для критических пакетов безопасности.

---

## 📊 Шаг 8: Загрузка каталога (первичная настройка)

### 8.1 Доступ к админке
1. Откройте браузер: `http://YOUR_SERVER_IP:8000`
2. Перейдите в раздел "Загрузка каталога"
3. Загрузите Excel файл с товарами
4. Дождитесь завершения индексации

### 8.2 Проверка поиска
1. В Telegram боте введите запрос товара
2. Бот должен найти и показать релевантные товары
3. Проверьте различные типы запросов:
   - По названию: "ноутбук", "дрель"
   - По артикулу: "DL001", "FL002"
   - По категории: "электроника", "инструменты"

### 8.3 Настройка качества поиска (опционально)
Если результаты поиска неудовлетворительны, отредактируйте файл `/opt/llm-bot/config/.env`:

```bash
# Для более строгого отбора результатов
SEARCH_MIN_SCORE=0.6

# Для большего охвата результатов
SEARCH_MIN_SCORE=0.3

# Увеличение приоритета точных совпадений в артикуле
SEARCH_ARTICLE_BOOST=0.4
```

После изменения перезапустите бота:
```bash
cd /opt/llm-bot && ./scripts/prod_restart.sh
```

---

## 🔄 Обновление бота

### Автоматическое обновление:
```bash
# Переходим в директорию бота
cd /opt/llm-bot

# Запускаем скрипт обновления
./scripts/update.sh
```

### Принудительное обновление:
```bash
# Если нужно принудительно пересобрать образ
./scripts/update.sh --force
```

---

## 📋 Полезные команды

### Управление сервисами:
```bash
cd /opt/llm-bot/app

# Статус всех сервисов (app, bot, postgres)
docker-compose -f docker-compose.prod.yml ps

# Перезапуск только FastAPI сервера
docker-compose -f docker-compose.prod.yml restart app

# Перезапуск только Telegram бота
docker-compose -f docker-compose.prod.yml restart bot

# Перезапуск всех сервисов
docker-compose -f docker-compose.prod.yml restart

# Остановка всех сервисов
docker-compose -f docker-compose.prod.yml down

# Запуск всех сервисов
docker-compose -f docker-compose.prod.yml up -d
```

### Мониторинг:
```bash
# Использование ресурсов
docker stats

# Логи всех сервисов в реальном времени
docker-compose -f docker-compose.prod.yml logs -f

# Логи только FastAPI сервера
docker-compose -f docker-compose.prod.yml logs -f app

# Логи только Telegram бота
docker-compose -f docker-compose.prod.yml logs -f bot

# Проверка здоровья
curl http://localhost:8000/health

# Размер данных
du -sh /opt/llm-bot/data/*
```

### Резервное копирование:
```bash
# Создать backup
/opt/llm-bot/scripts/backup.sh

# Посмотреть список backup'ов
ls -la /opt/llm-bot/backups/

# Информация о последнем backup'е
cat /opt/llm-bot/backups/latest_info.txt
```

---

## 🚨 Решение проблем

### Бот не отвечает в Telegram:
```bash
# Проверяем логи Telegram бота (отдельный контейнер)
docker-compose -f docker-compose.prod.yml logs bot | grep -i error

# Проверяем статус bot контейнера
docker-compose -f docker-compose.prod.yml ps bot

# Проверяем BOT_TOKEN в конфигурации
grep BOT_TOKEN /opt/llm-bot/config/.env

# Перезапускаем Telegram бота
docker-compose -f docker-compose.prod.yml restart bot

# Если проблема в FastAPI - перезапускаем app
docker-compose -f docker-compose.prod.yml restart app
```

### Ошибки подключения к БД:
```bash
# Проверяем статус PostgreSQL
docker-compose -f docker-compose.prod.yml ps postgres

# Проверяем логи БД
docker-compose -f docker-compose.prod.yml logs postgres

# Проверяем пароль в конфигурации
grep POSTGRES_PASSWORD /opt/llm-bot/config/.env
```

### Проблемы с LLM:
```bash
# Для YandexGPT проверяем ключи
grep YANDEX_ /opt/llm-bot/config/.env

# Для OpenAI проверяем ключ
grep OPENAI_ /opt/llm-bot/config/.env

# Тестируем LLM в логах
docker-compose -f docker-compose.prod.yml logs app | grep -i "llm\|yandex\|openai"
```

### Нет места на диске:
```bash
# Проверяем использование диска
df -h

# Очищаем старые Docker образы
docker system prune -f

# Очищаем старые backup'ы
find /opt/llm-bot/backups -name "*.tar.gz" -mtime +30 -delete
```

---

## 📞 Поддержка и мониторинг

### Логи для отладки:
- **FastAPI сервер:** `docker-compose -f docker-compose.prod.yml logs app`
- **Telegram бот:** `docker-compose -f docker-compose.prod.yml logs bot`
- **База данных:** `docker-compose -f docker-compose.prod.yml logs postgres`
- **Все сервисы:** `docker-compose -f docker-compose.prod.yml logs`
- **Backup'ы:** `/opt/llm-bot/data/logs/backup.log`
- **Системные:** `/var/log/syslog`

### Мониторинг ресурсов:
```bash
# Загрузка системы
htop

# Использование Docker контейнерами
docker stats

# Место на диске
df -h /opt/llm-bot
```

### Health checks:
```bash
# HTTP health check
curl -f http://localhost:8000/health

# Проверка всех компонентов
/opt/llm-bot/app/scripts/health_check.sh  # если создан
```

---

## ✅ Checklist готовности

После завершения всех шагов убедитесь:

- [ ] Все Docker контейнеры запущены (`docker-compose ps`)
- [ ] Health check проходит (`curl localhost:8000/health`)
- [ ] Telegram бот отвечает на сообщения
- [ ] Веб-интерфейс доступен
- [ ] Каталог загружен и поиск работает
- [ ] Backup'ы настроены и работают
- [ ] Firewall настроен
- [ ] Скрипты обновления работают

---

## 🎯 Что дальше

### Рекомендуемые улучшения:
1. **HTTPS:** Настройте SSL сертификат через Let's Encrypt
2. **Домен:** Привяжите доменное имя к серверу
3. **Мониторинг:** Настройте Grafana/Prometheus
4. **CDN:** Для ускорения загрузки изображений товаров
5. **Backup в облако:** Автоматическая отправка backup'ов в S3/облако

### Масштабирование:
- При росте нагрузки увеличьте ресурсы VPS
- Добавьте Redis для кэширования
- Настройте load balancer для нескольких инстансов

---

## 🔧 Приложение: Устранение проблем с переменными окружения

### Проблема: environment":"development" вместо "production"

**Симптомы:**
- Health endpoint показывает `"environment":"development"`
- Переменная `DEBUG=true` несмотря на настройки

**Причина:**
Системные переменные окружения имеют **приоритет** над переменными из `.env` файлов.

**Диагностика:**
```bash
# Проверить системные переменные
env | grep DEBUG

# Проверить в контейнере
docker-compose -f docker-compose.prod.yml exec app env | grep DEBUG
```

**Решение:**
1. **В docker-compose.prod.yml** добавлена секция `environment` с принудительной установкой:
   ```yaml
   environment:
     DEBUG: "false"
     ENVIRONMENT: "production"
   ```

2. **Очистка системных переменных** перед деплоем:
   ```bash
   unset DEBUG NODE_ENV ENVIRONMENT
   ```

**Предотвращение:**
- Всегда проверяйте окружение перед деплоем
- Критичные переменные задавайте в `environment` секции Docker Compose
- Используйте изолированных пользователей для приложений

### Проблема: POSTGRES_PASSWORD не читается из .env файла

**Симптомы:**
- `WARN[0000] The "POSTGRES_PASSWORD" variable is not set`
- PostgreSQL контейнер не запускается (unhealthy)

**Причина:**
Docker Compose не может прочитать переменные из `.env` файла из-за проблем с правами доступа или путями.

**Диагностика:**
```bash
# Проверить что переменная есть в .env
grep POSTGRES_PASSWORD /opt/llm-bot/config/.env

# Проверить что Docker Compose config видит переменную
docker-compose -f docker-compose.prod.yml config | grep POSTGRES_PASSWORD
```

**Решение:**
```bash
# Временно установить переменную в окружении
export POSTGRES_PASSWORD=password

# Запустить контейнеры
docker-compose -f docker-compose.prod.yml up -d
```

**Постоянное решение:**
1. **Добавить переменные напрямую в docker-compose.prod.yml:**
   ```yaml
   postgres:
     environment:
       POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:-password}"
   ```

2. **Создать startup скрипт:**
   ```bash
   #!/bin/bash
   source /opt/llm-bot/config/.env
   export POSTGRES_PASSWORD
   docker-compose -f docker-compose.prod.yml up -d
   ```

---

**🎉 Поздравляем! Ваш ИИ-бот успешно развернут и готов к работе!**
