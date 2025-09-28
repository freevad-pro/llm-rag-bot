#!/bin/bash
# Быстрый перезапуск production приложения для применения изменений .env
# Использование: ./scripts/prod_restart_env.sh

set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Функция для логирования
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

echo "🔄 Быстрый перезапуск для применения .env изменений..."

# Переходим в рабочую директорию
cd /opt/llm-bot/app

# Останавливаем текущие контейнеры
log "🛑 Останавливаем контейнеры..."
docker-compose -f docker-compose.prod.yml down

# Запускаем заново (БЕЗ пересборки)
log "🚀 Запускаем контейнеры с новыми настройками..."
docker-compose -f docker-compose.prod.yml up -d

# Ждем готовности
log "⏳ Ожидание готовности сервисов..."
sleep 10

# Проверяем статус
log "📊 Статус сервисов:"
docker-compose -f docker-compose.prod.yml ps

# Проверяем health endpoint
log "🔍 Проверка health endpoint..."
if curl -s http://localhost:8000/health > /dev/null; then
    success "Приложение готово к работе!"
    echo "🌐 Health: http://localhost:8000/health"
    echo "📱 Telegram бот активен"
    echo "⚙️ Настройки .env применены"
else
    warning "Приложение не отвечает. Логи последних 10 строк:"
    docker-compose -f docker-compose.prod.yml logs app | tail -10
fi

success "🎉 Перезапуск завершен!"
