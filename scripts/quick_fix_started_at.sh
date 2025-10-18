#!/bin/bash
# Быстрое исправление ошибки started_at - просто очистка кэша и перезапуск

echo "⚡ Быстрое исправление ошибки started_at"
echo "========================================"
echo ""

# Проверяем окружение
if [ -f "/opt/llm-bot/config/.env" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    echo "📁 Production окружение"
    cd /opt/llm-bot/app || exit 1
elif [ -f "docker-compose.yml" ]; then
    COMPOSE_FILE="docker-compose.yml"
    echo "📁 Development окружение"
else
    echo "❌ Docker Compose файл не найден"
    exit 1
fi

echo ""
echo "1️⃣ Очищаем Python кэш в контейнере..."
docker-compose -f $COMPOSE_FILE exec web find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
docker-compose -f $COMPOSE_FILE exec web find . -type f -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo "2️⃣ Перезапускаем web контейнер..."
docker-compose -f $COMPOSE_FILE restart web

echo ""
echo "3️⃣ Ожидаем запуска (10 сек)..."
sleep 10

echo ""
echo "4️⃣ Проверяем логи..."
docker-compose -f $COMPOSE_FILE logs --tail=30 web

echo ""
echo "========================================"
echo "✅ Готово!"
echo ""
echo "💡 Следите за логами: docker-compose -f $COMPOSE_FILE logs -f web"
echo "Если ошибка повторится через 10 минут - нужно более глубокое исправление"

