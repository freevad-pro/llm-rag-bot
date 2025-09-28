#!/bin/bash
# Скрипт для локального тестирования админ-панели
# Запуск: bash scripts/test_local_admin.sh

set -e  # Останавливаться при ошибках

echo "🚀 ЛОКАЛЬНОЕ ТЕСТИРОВАНИЕ АДМИН-ПАНЕЛИ"
echo "========================================"

# Проверяем наличие Docker
echo ""
echo "🐳 Проверка Docker..."
if command -v docker &> /dev/null; then
    docker_version=$(docker --version)
    echo "✓ Docker найден: $docker_version"
else
    echo "❌ Docker не найден! Установите Docker"
    exit 1
fi

# Проверяем наличие docker-compose
if command -v docker-compose &> /dev/null; then
    compose_version=$(docker-compose --version)
    echo "✓ Docker Compose найден: $compose_version"
else
    echo "❌ Docker Compose не найден!"
    exit 1
fi

# Копируем тестовые настройки
echo ""
echo "📝 Подготовка настроек..."
cp env.test .env
echo "✓ Скопированы настройки из env.test в .env"

# Останавливаем существующие контейнеры
echo ""
echo "🛑 Остановка существующих контейнеров..."
docker-compose down 2>/dev/null || true
echo "✓ Контейнеры остановлены"

# Создаем директории для данных
echo ""
echo "📁 Создание директорий для данных..."
mkdir -p data/persistent/chroma
mkdir -p data/uploads
echo "✓ Директории созданы"

# Собираем образы
echo ""
echo "🔨 Сборка Docker образов..."
docker-compose build --no-cache app
echo "✓ Образ собран успешно"

# Запускаем сервисы
echo ""
echo "🚀 Запуск сервисов..."
docker-compose up -d
echo "✓ Сервисы запущены"

# Ждем запуска базы данных
echo ""
echo "⏳ Ожидание запуска PostgreSQL..."
sleep 10

# Проверяем статус контейнеров
echo ""
echo "📋 Статус контейнеров:"
docker-compose ps

# Запускаем тестирование
echo ""
echo "🧪 Запуск тестирования..."
sleep 5
python3 scripts/test_admin_panel.py

# Показываем логи если есть ошибки
echo ""
echo "📊 Последние логи приложения:"
docker-compose logs --tail=20 app

echo ""
echo "✅ ГОТОВО К ТЕСТИРОВАНИЮ!"
echo "🌐 Откройте браузер: http://localhost:8000/admin/"
echo "📊 Health check: http://localhost:8000/health"
echo "📜 API docs: http://localhost:8000/docs"

echo ""
echo "⚙️  Полезные команды:"
echo "  Логи:        docker-compose logs -f app"
echo "  Остановка:   docker-compose down"
echo "  Перезапуск:  docker-compose restart app"
echo "  Статус:      docker-compose ps"

echo ""
echo "🎯 Для полного тестирования авторизации:"
echo "1. Замените в .env на ваши реальные Telegram ID"
echo "2. Добавьте реальный BOT_TOKEN от @BotFather"
echo "3. Перезапустите: docker-compose restart app"


