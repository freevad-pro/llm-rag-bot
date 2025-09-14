# 🤖 Production Commands - Команды управления ИИ-ботом

Удобные команды для управления production развертыванием ИИ-бота на VPS.

## 🚀 Быстрый старт

После подключения к VPS просто используйте команду `bot`:

```bash
# Подключение к VPS
ssh root@YOUR_VPS_IP

# Проверка статуса
bot health

# Полный статус
bot status
```

## 📋 Основные команды

### Управление приложением

```bash
# Запустить приложение
bot start

# Остановить приложение  
bot stop

# Перезапустить с полной пересборкой
bot restart

# Быстрая проверка здоровья
bot health

# Полный статус всех сервисов
bot status
```

### Просмотр логов

```bash
# Все логи в реальном времени
bot logs

# Логи отдельных сервисов
bot logs-app      # Веб-приложение
bot logs-bot      # Telegram бот  
bot logs-db       # База данных PostgreSQL
```

### Обслуживание

```bash
# Обновить код и перезапустить
bot update

# Создать резервную копию
bot backup

# Показать справку
bot help
```

## 🔧 Прямые скрипты

Если команда `bot` недоступна, используйте прямые пути:

```bash
# Основной менеджер
/opt/llm-bot/scripts/prod.sh [команда]

# Отдельные скрипты
/opt/llm-bot/scripts/start_production.sh
/opt/llm-bot/scripts/prod_restart.sh
/opt/llm-bot/scripts/prod_stop.sh
/opt/llm-bot/scripts/prod_status.sh
/opt/llm-bot/scripts/prod_logs.sh [сервис]
```

## 📊 Мониторинг

### Проверка ресурсов

```bash
# Использование ресурсов контейнерами
docker stats --no-stream

# Использование диска
du -sh /opt/llm-bot/*

# Открытые порты
ss -tlnp | grep 8000
```

### Проверка доступности

```bash
# Health check изнутри сервера
curl http://localhost:8000/health

# Проверка извне (замените IP)
curl http://YOUR_VPS_IP:8000/health
```

## 🆘 Устранение проблем

### Если приложение не отвечает

```bash
# 1. Проверить статус
bot status

# 2. Посмотреть логи
bot logs-app

# 3. Перезапустить
bot restart
```

### Если контейнеры не запускаются

```bash
# 1. Остановить все
bot stop

# 2. Проверить конфликты
docker ps -a

# 3. Принудительная очистка
docker system prune -f

# 4. Запустить заново
bot start
```

### Проблемы с портами

```bash
# Проверить что порт 8000 свободен
ss -tlnp | grep 8000

# Убить процессы на порту 8000
sudo fuser -k 8000/tcp

# Перезапустить с правильным пробросом
bot restart
```

## 📁 Структура файлов

```
/opt/llm-bot/
├── app/                    # Код приложения
│   ├── docker-compose.prod.yml
│   └── src/
├── data/                   # Данные (сохраняются)
│   ├── postgres/
│   ├── chroma/
│   ├── uploads/
│   └── logs/
├── config/                 # Конфигурация
│   └── .env
├── scripts/                # Скрипты управления
│   ├── prod.sh            # Основной менеджер
│   ├── prod_*.sh          # Отдельные команды
│   ├── start_production.sh
│   ├── deploy.sh
│   └── backup.sh
└── backups/               # Резервные копии
```

## 🔐 Безопасность

- Все конфиденциальные данные в `/opt/llm-bot/config/.env`
- Порты PostgreSQL (5432) закрыты для внешнего доступа  
- Только порт 8000 открыт для веб-интерфейса
- Резервные копии в `/opt/llm-bot/backups/`

## 📞 Поддержка

При проблемах:

1. **Проверить логи**: `bot logs-app`
2. **Статус сервисов**: `bot status`  
3. **Перезапуск**: `bot restart`
4. **Резервная копия**: `bot backup`

---

*Создано автоматически для удобного управления ИИ-ботом в production среде* 🤖
