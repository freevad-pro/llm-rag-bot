#!/bin/bash
# Скрипт для исправления ошибки started_at на production сервере

echo "🔧 Исправление ошибки started_at на production сервере"
echo "======================================================="
echo ""

# Проверяем что мы на production сервере
if [ ! -f "/opt/llm-bot/config/.env" ]; then
    echo "❌ Это не production сервер!"
    echo "Скрипт должен запускаться на сервере в /opt/llm-bot/app/"
    exit 1
fi

echo "📁 Рабочая директория: /opt/llm-bot/app"
cd /opt/llm-bot/app || exit 1

echo ""
echo "1️⃣ Останавливаем контейнеры..."
docker-compose -f docker-compose.prod.yml down

echo ""
echo "2️⃣ Обновляем код из Git..."
git fetch origin main
git reset --hard origin/main

echo ""
echo "3️⃣ Удаляем Python кэш..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo "4️⃣ Пересобираем Docker образ..."
docker-compose -f docker-compose.prod.yml build web

echo ""
echo "5️⃣ Запускаем контейнеры..."
docker-compose -f docker-compose.prod.yml up -d

echo ""
echo "6️⃣ Ожидаем запуска приложения (30 сек)..."
sleep 30

echo ""
echo "7️⃣ Проверяем логи на наличие ошибки started_at..."
docker-compose -f docker-compose.prod.yml logs --tail=50 web | grep -i "started_at" && echo "⚠️  Ошибка все еще есть!" || echo "✅ Ошибки started_at не найдено"

echo ""
echo "======================================================="
echo "✅ Процесс завершен!"
echo ""
echo "💡 Для проверки логов используйте:"
echo "docker-compose -f docker-compose.prod.yml logs -f web"

