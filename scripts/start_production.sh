#!/bin/bash
# Production startup script
# Решает проблемы с переменными окружения автоматически

set -e

echo "🚀 Запуск ИИ-бота в production режиме..."

# Переходим в рабочую директорию
cd /opt/llm-bot/app

# Загружаем переменные из .env файла
if [ -f "/opt/llm-bot/config/.env" ]; then
    echo "📝 Загружаем переменные из .env..."
    set -a  # Автоматически экспортировать переменные
    source /opt/llm-bot/config/.env
    set +a
    echo "✅ Переменные загружены"
else
    echo "❌ Файл .env не найден!"
    exit 1
fi

# Проверяем критичные переменные
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "❌ POSTGRES_PASSWORD не установлен!"
    exit 1
fi

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN не установлен!"
    exit 1
fi

echo "✅ Критичные переменные проверены"

# Очищаем конфликтные переменные
unset DEBUG NODE_ENV ENVIRONMENT

# Запускаем контейнеры
echo "🐳 Запуск Docker контейнеров..."
docker-compose -f docker-compose.prod.yml up -d

# Ждем готовности
echo "⏳ Ожидание готовности сервисов..."
sleep 10

# Проверяем статус
echo "📊 Статус сервисов:"
docker-compose -f docker-compose.prod.yml ps

# Проверяем health endpoint
echo "🔍 Проверка health endpoint..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Приложение готово к работе!"
    echo "🌐 Health: http://localhost:8000/health"
    echo "📱 Telegram бот активен"
else
    echo "❌ Приложение не отвечает"
    echo "📝 Логи приложения:"
    docker-compose -f docker-compose.prod.yml logs app | tail -10
fi
